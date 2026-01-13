# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from mcp.server import Server
from mcp.types import Tool

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.server import CoreasonConnectServer
from tests.fixtures.mock_plugin import MockPlugin


@pytest.fixture  # type: ignore[misc]
def mock_secrets() -> SecretsProvider:
    """Fixture for a mock secrets provider."""
    secrets = MagicMock(spec=SecretsProvider)
    secrets.get_secret.return_value = "mock_secret"
    secrets.get_user_credential.return_value = "mock_token"
    return secrets


@pytest.fixture  # type: ignore[misc]
def mock_plugin(mock_secrets: SecretsProvider) -> MockPlugin:
    """Fixture for a mock plugin."""
    return MockPlugin(mock_secrets)


@pytest.fixture  # type: ignore[misc]
def server(mock_secrets: SecretsProvider) -> CoreasonConnectServer:
    """Fixture for the MCP server."""
    return CoreasonConnectServer(secrets=mock_secrets)


def test_server_initialization(server: CoreasonConnectServer) -> None:
    """Test that the server initializes correctly."""
    assert isinstance(server, Server)
    assert server.version == "0.1.0"
    assert server.config is not None
    assert server.secrets is not None
    assert server.plugin_loader is not None


@pytest.mark.asyncio  # type: ignore[misc]
async def test_list_tools_handler_empty(server: CoreasonConnectServer) -> None:
    """Test listing tools when no plugins are loaded."""
    # Ensure no plugins are loaded
    server.plugins = {}
    tools = await server._list_tools_handler()
    assert tools == []


@pytest.mark.asyncio  # type: ignore[misc]
async def test_list_tools_handler_with_plugins(server: CoreasonConnectServer, mock_plugin: MockPlugin) -> None:
    """Test listing tools with loaded plugins."""
    # Manually inject a plugin
    server.plugins = {"mock-plugin": mock_plugin}

    tools = await server._list_tools_handler()
    assert len(tools) == 1
    assert isinstance(tools[0], Tool)
    # The MockPlugin from fixture returns "mock_echo", but previous tests expected "echo"
    # The fixture MockPlugin defines "mock_echo".
    assert tools[0].name == "mock_echo"
    assert tools[0].description == "Echoes the input."


@pytest.mark.asyncio  # type: ignore[misc]
async def test_call_tool_handler_success(server: CoreasonConnectServer, mock_plugin: MockPlugin) -> None:
    """Test calling a tool successfully."""
    # Manually inject a plugin and register it
    server.plugins = {"mock-plugin": mock_plugin}
    server.tool_registry["mock_echo"] = mock_plugin

    result = await server._call_tool_handler("mock_echo", {"message": "Hello MCP"})
    assert len(result) == 1
    assert result[0].type == "text"
    # We cast because mypy might not know result[0] is TextContent
    # but at runtime we know it is.
    text_content = result[0]
    # Accessing .text on Union[TextContent, ImageContent, EmbeddedResource]
    # requires checking type or ignoring if we know it's TextContent
    assert hasattr(text_content, "text")
    # Cast to Any or ignore to access .text without extensive isinstance checks for test brevity
    assert text_content.text is not None

    # The result from server is "Echo: Hello MCP" (not JSON)
    assert text_content.text == "Echo: Hello MCP"


@pytest.mark.asyncio  # type: ignore[misc]
async def test_call_tool_handler_execution_error(server: CoreasonConnectServer, mock_plugin: MockPlugin) -> None:
    """Test calling a tool that raises an error during execution."""
    # Manually inject a plugin and register it
    server.plugins = {"mock-plugin": mock_plugin}
    server.tool_registry["mock_echo"] = mock_plugin

    # Mock the plugin to raise an exception
    mock_plugin.execute = MagicMock(side_effect=Exception("Execution failed"))  # type: ignore[method-assign]

    with patch("coreason_connect.server.logger") as mock_logger:
        result = await server._call_tool_handler("mock_echo", {"message": "fail"})
        assert len(result) == 1
        text = result[0].text  # type: ignore[union-attr]
        assert "Error executing tool" in text
        assert "Execution failed" in text

        # Verify logger was called
        mock_logger.error.assert_called()
        assert "Error executing tool 'mock_echo': Execution failed" in str(mock_logger.error.call_args)


@pytest.mark.asyncio  # type: ignore[misc]
async def test_call_tool_handler_unknown_tool(server: CoreasonConnectServer) -> None:
    """Test calling a tool that does not exist."""
    result = await server._call_tool_handler("unknown_tool", {})
    assert len(result) == 1
    text = result[0].text  # type: ignore[union-attr]
    assert "Error: Tool 'unknown_tool' not found" in text


def test_load_plugins_integration(server: CoreasonConnectServer, mock_plugin: MockPlugin) -> None:
    """Test the _load_plugins method (integration with loader)."""
    # Mock the loader to return our mock plugin
    server.plugin_loader.load_all = MagicMock(return_value={"mock-plugin": mock_plugin})  # type: ignore[method-assign]

    server._load_plugins()

    assert len(server.plugins) == 1
    assert "mock-plugin" in server.plugins
    # The mock plugin defines "mock_echo"
    assert "mock_echo" in server.tool_registry
    assert server.tool_registry["mock_echo"] == mock_plugin


def test_load_plugins_duplicate_tool_warning(
    server: CoreasonConnectServer,
    mock_plugin: MockPlugin,
) -> None:
    """Test that a warning is logged when duplicate tools are found."""
    # Create a second plugin with the same tool
    # We need to create a new instance of MockPlugin.
    # We can reuse the secrets fixture indirectly or mock it.
    mock_secrets = MagicMock(spec=SecretsProvider)
    mock_plugin2 = MockPlugin(mock_secrets)

    # Mock the loader to return both plugins
    server.plugin_loader.load_all = MagicMock(  # type: ignore[method-assign]
        return_value={"p1": mock_plugin, "p2": mock_plugin2}
    )

    with patch("coreason_connect.server.logger") as mock_logger:
        server._load_plugins()
        mock_logger.warning.assert_called()
        assert "Duplicate tool name 'mock_echo' found in plugin 'p2'" in str(mock_logger.warning.call_args)


@pytest.mark.asyncio  # type: ignore[misc]
async def test_list_tools_handler_plugin_error(
    server: CoreasonConnectServer,
    mock_plugin: MockPlugin,
) -> None:
    """Test listing tools when a plugin raises an error."""
    # Mock plugin raises error on get_tools
    mock_plugin.get_tools = MagicMock(side_effect=Exception("Plugin error"))  # type: ignore[method-assign]
    server.plugins = {"mock-plugin": mock_plugin}

    with patch("coreason_connect.server.logger") as mock_logger:
        tools = await server._list_tools_handler()
        assert tools == []
        mock_logger.error.assert_called()
        assert "Error listing tools for plugin 'mock-plugin': Plugin error" in str(mock_logger.error.call_args)


@pytest.mark.asyncio  # type: ignore[misc]
async def test_stateful_plugin_execution(server: CoreasonConnectServer, mock_secrets: SecretsProvider) -> None:
    """Test that plugins maintain state across calls."""

    # Define a simple stateful plugin
    class StatefulPlugin(ConnectorProtocol):
        def __init__(self, secrets: SecretsProvider) -> None:
            super().__init__(secrets)
            self.count = 0

        def get_tools(self) -> list[Tool]:
            return [
                Tool(
                    name="increment",
                    description="Increments a counter",
                    inputSchema={"type": "object", "properties": {}},
                )
            ]

        def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
            self.count += 1
            return str(self.count)

    plugin = StatefulPlugin(mock_secrets)
    server.plugins = {"stateful": plugin}
    server.tool_registry["increment"] = plugin

    result1 = await server._call_tool_handler("increment", {})
    text1 = result1[0].text  # type: ignore[union-attr]
    assert text1 == "1"

    result2 = await server._call_tool_handler("increment", {})
    text2 = result2[0].text  # type: ignore[union-attr]
    assert text2 == "2"


@pytest.mark.asyncio  # type: ignore[misc]
async def test_complex_return_types(server: CoreasonConnectServer, mock_plugin: MockPlugin) -> None:
    """Test that the server handles different return types from plugins."""

    # Test returning None
    mock_plugin.execute = MagicMock(return_value=None)  # type: ignore[method-assign]
    server.plugins = {"mock": mock_plugin}
    server.tool_registry["mock_echo"] = mock_plugin

    result = await server._call_tool_handler("mock_echo", {})
    text = result[0].text  # type: ignore[union-attr]
    assert text == "None"

    # Test returning a non-JSON-serializable object (fallback to str)
    class CustomObj:
        def __str__(self) -> str:
            return "CustomString"

    mock_plugin.execute = MagicMock(return_value=CustomObj())  # type: ignore[method-assign]
    result = await server._call_tool_handler("mock_echo", {})
    text = result[0].text  # type: ignore[union-attr]
    assert text == "CustomString"


@pytest.mark.asyncio  # type: ignore[misc]
async def test_complex_arguments(server: CoreasonConnectServer, mock_plugin: MockPlugin) -> None:
    """Test passing complex arguments to tools."""
    server.plugins = {"mock": mock_plugin}
    server.tool_registry["mock_echo"] = mock_plugin

    complex_args = {"nested": {"a": 1, "b": [1, 2]}, "list": [{"id": 1}]}

    # Mock the execute to return the arguments so we can verify them
    mock_plugin.execute = MagicMock(return_value=complex_args)  # type: ignore[method-assign]

    result = await server._call_tool_handler("mock_echo", complex_args)
    text = result[0].text  # type: ignore[union-attr]
    loaded = json.loads(text)
    assert loaded == complex_args
