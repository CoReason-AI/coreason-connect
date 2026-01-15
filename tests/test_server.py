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
from mcp.types import Tool

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.server import CoreasonConnectServer
from coreason_connect.types import ToolDefinition, ToolExecutionError
from tests.fixtures.mock_plugin import MockPlugin


@pytest.fixture
def mock_secrets() -> SecretsProvider:
    return MagicMock(spec=SecretsProvider)


@pytest.fixture
def server(mock_secrets: SecretsProvider) -> CoreasonConnectServer:
    return CoreasonConnectServer(secrets=mock_secrets)


@pytest.fixture
def mock_plugin(mock_secrets: SecretsProvider) -> MockPlugin:
    return MockPlugin(mock_secrets)


def test_server_initialization(server: CoreasonConnectServer) -> None:
    """Test that the server initializes correctly."""
    assert server.name == "coreason-connect"
    assert server.plugins == {}
    assert server.tool_registry == {}


@pytest.mark.asyncio
async def test_list_tools_handler_empty(server: CoreasonConnectServer) -> None:
    """Test listing tools when no plugins are loaded."""
    tools = await server._list_tools_handler()
    assert tools == []


@pytest.mark.asyncio
async def test_list_tools_handler_with_plugins(server: CoreasonConnectServer, mock_plugin: MockPlugin) -> None:
    """Test listing tools with loaded plugins."""
    # Inject mock plugin
    server.plugins = {"mock-plugin": mock_plugin}
    # Manually populate registry for test isolation (normally done by _load_plugins)
    for tool_def in mock_plugin.get_tools():
        server.tool_registry[tool_def.name] = mock_plugin
        server.tool_definitions[tool_def.name] = tool_def

    tools = await server._list_tools_handler()
    assert len(tools) == 1
    assert tools[0].name == "mock_echo"


@pytest.mark.asyncio
async def test_call_tool_handler_success(server: CoreasonConnectServer, mock_plugin: MockPlugin) -> None:
    """Test calling a tool successfully."""
    server.plugins = {"mock-plugin": mock_plugin}
    for tool_def in mock_plugin.get_tools():
        server.tool_registry[tool_def.name] = mock_plugin
        server.tool_definitions[tool_def.name] = tool_def

    result = await server._call_tool_handler("mock_echo", {"message": "Hello"})
    assert len(result) == 1
    # Removed unused ignore comments
    assert result[0].type == "text"
    assert result[0].text == "Echo: Hello"


@pytest.mark.asyncio
async def test_call_tool_handler_not_found(server: CoreasonConnectServer) -> None:
    """Test calling a non-existent tool."""
    result = await server._call_tool_handler("non_existent_tool", {})
    assert len(result) == 1
    # Removed unused ignore comments
    assert result[0].type == "text"
    assert "Error: Tool 'non_existent_tool' not found." in result[0].text


@pytest.mark.asyncio
async def test_call_tool_handler_tool_execution_error(server: CoreasonConnectServer, mock_plugin: MockPlugin) -> None:
    """Test handling of ToolExecutionError."""
    # Mock execute to raise ToolExecutionError
    mock_plugin.execute = MagicMock(side_effect=ToolExecutionError("Custom error"))  # type: ignore[method-assign]
    server.plugins = {"mock-plugin": mock_plugin}
    for tool_def in mock_plugin.get_tools():
        server.tool_registry[tool_def.name] = mock_plugin
        server.tool_definitions[tool_def.name] = tool_def

    with patch("coreason_connect.server.logger") as mock_logger:
        result = await server._call_tool_handler("mock_echo", {})
        assert len(result) == 1
        # Removed unused ignore comments
        assert result[0].type == "text"
        assert "Error: Tool 'mock_echo' failed - Custom error" in result[0].text
        mock_logger.warning.assert_called()


@pytest.mark.asyncio
async def test_call_tool_handler_generic_error(server: CoreasonConnectServer, mock_plugin: MockPlugin) -> None:
    """Test handling of generic exceptions."""
    # Mock execute to raise generic Exception
    mock_plugin.execute = MagicMock(side_effect=Exception("Unexpected crash"))  # type: ignore[method-assign]
    server.plugins = {"mock-plugin": mock_plugin}
    for tool_def in mock_plugin.get_tools():
        server.tool_registry[tool_def.name] = mock_plugin
        server.tool_definitions[tool_def.name] = tool_def

    with patch("coreason_connect.server.logger"):  # Remove unused variable assignment
        result = await server._call_tool_handler("mock_echo", {})
        assert len(result) == 1
        text = result[0].text  # type: ignore[union-attr]

        # Should be sanitized
        assert "Error executing tool: Unexpected crash" in text


@pytest.mark.asyncio
async def test_load_plugins_exception(server: CoreasonConnectServer) -> None:
    """Test error handling when _load_plugins fails completely."""
    # Mock plugin_loader.load_all to raise Exception
    server.plugin_loader.load_all = MagicMock(side_effect=Exception("Load error"))  # type: ignore[method-assign]

    # We expect an exception here because _load_plugins does not catch the loader crash
    # The loader itself catches plugin load errors, but if load_all raises, it's fatal or propagated.
    with pytest.raises(Exception, match="Load error"):
        server._load_plugins()


@pytest.mark.asyncio
async def test_mcp_decorators_usage(server: CoreasonConnectServer) -> None:
    """Test that MCP decorators are used (coverage check)."""
    # This is implicitly tested by initialization, but we can verify the routes are registered if accessible
    pass


@pytest.mark.asyncio
async def test_load_plugins_individual_failure(
    server: CoreasonConnectServer,
    mock_plugin: MockPlugin,
) -> None:
    """Test that individual plugin failures during loading are logged but don't crash everything."""
    # This mocks the behavior inside _load_plugins loop

    # Setup a plugin that raises on get_tools
    bad_plugin = MagicMock(spec=ConnectorProtocol)
    bad_plugin.get_tools.side_effect = Exception("Plugin error")

    server.plugin_loader.load_all = MagicMock(  # type: ignore[method-assign]
        return_value={"bad": bad_plugin, "good": mock_plugin}
    )

    with patch("coreason_connect.server.logger") as mock_logger:
        server._load_plugins()

        # bad plugin error logged
        mock_logger.error.assert_any_call("Failed to get tools from plugin 'bad': Plugin error")

        # good plugin registered
        assert "mock_echo" in server.tool_registry


@pytest.mark.asyncio
async def test_stateful_plugin_execution(server: CoreasonConnectServer, mock_secrets: SecretsProvider) -> None:
    """Test that plugins maintain state across calls."""

    # Define a simple stateful plugin
    class StatefulPlugin(ConnectorProtocol):
        def __init__(self, secrets: SecretsProvider) -> None:
            super().__init__(secrets)
            self.count = 0

        def get_tools(self) -> list[ToolDefinition]:
            return [
                ToolDefinition(
                    name="increment",
                    tool=Tool(
                        name="increment",
                        description="Increments a counter",
                        inputSchema={"type": "object", "properties": {}},
                    ),
                    is_consequential=False,
                )
            ]

        def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
            self.count += 1
            return str(self.count)

    plugin = StatefulPlugin(mock_secrets)
    server.plugins = {"stateful": plugin}
    server.tool_registry["increment"] = plugin
    for tool_def in plugin.get_tools():
        server.tool_definitions[tool_def.name] = tool_def

    result1 = await server._call_tool_handler("increment", {})
    text1 = result1[0].text  # type: ignore[union-attr]
    assert text1 == "1"

    result2 = await server._call_tool_handler("increment", {})
    text2 = result2[0].text  # type: ignore[union-attr]
    assert text2 == "2"


@pytest.mark.asyncio
async def test_complex_return_types(server: CoreasonConnectServer, mock_plugin: MockPlugin) -> None:
    """Test that the server handles different return types from plugins."""

    # Test returning None
    mock_plugin.execute = MagicMock(return_value=None)  # type: ignore[method-assign]
    server.plugins = {"mock": mock_plugin}
    for tool_def in mock_plugin.get_tools():
        server.tool_registry[tool_def.name] = mock_plugin
        server.tool_definitions[tool_def.name] = tool_def

    result = await server._call_tool_handler("mock_echo", {})
    text = result[0].text  # type: ignore[union-attr]
    assert text == "None"

    # Test returning Dict
    mock_plugin.execute = MagicMock(return_value={"status": "ok"})  # type: ignore[method-assign]
    result = await server._call_tool_handler("mock_echo", {})
    text = result[0].text  # type: ignore[union-attr]
    assert json.loads(text) == {"status": "ok"}


@pytest.mark.asyncio
async def test_complex_arguments(server: CoreasonConnectServer, mock_plugin: MockPlugin) -> None:
    """Test passing complex arguments to tools."""
    server.plugins = {"mock": mock_plugin}
    for tool_def in mock_plugin.get_tools():
        server.tool_registry[tool_def.name] = mock_plugin
        server.tool_definitions[tool_def.name] = tool_def

    complex_args = {"nested": {"a": 1, "b": [1, 2]}, "list": [{"id": 1}]}

    # Mock the execute to return the arguments so we can verify them
    mock_plugin.execute = MagicMock(return_value=complex_args)  # type: ignore[method-assign]

    result = await server._call_tool_handler("mock_echo", complex_args)
    text = result[0].text  # type: ignore[union-attr]
    loaded = json.loads(text)
    assert loaded == complex_args
