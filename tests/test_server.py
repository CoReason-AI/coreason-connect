import asyncio
from typing import Any

import pytest
from mcp.server import Server
import mcp.types as types
from unittest.mock import MagicMock

from coreason_connect.config import AppConfig, PluginConfig
from coreason_connect.server import CoreasonConnectServer
from coreason_connect.secrets import EnvSecretsProvider
from coreason_connect.interfaces import ConnectorProtocol


@pytest.fixture
def mock_plugin_config() -> AppConfig:
    return AppConfig(
        plugins=[
            PluginConfig(
                id="mock-plugin",
                type="local_python",
                path="tests/fixtures/mock_plugin.py",
                description="A mock plugin for testing",
            )
        ]
    )


def test_server_initialization() -> None:
    """Test that the server initializes correctly."""
    server = CoreasonConnectServer(name="test-server", version="1.0.0")
    assert isinstance(server, Server)
    assert server.name == "test-server"
    assert server.version == "1.0.0"
    assert isinstance(server.config, AppConfig)
    assert isinstance(server.secrets, EnvSecretsProvider)


def test_server_initialization_with_plugins(mock_plugin_config: AppConfig) -> None:
    """Test that the server initializes and loads plugins correctly."""
    server = CoreasonConnectServer(config=mock_plugin_config)
    assert "mock-plugin" in server.plugins
    assert "mock_echo" in server.tool_registry


@pytest.mark.asyncio
async def test_list_tools(mock_plugin_config: AppConfig) -> None:
    """Test listing tools."""
    server = CoreasonConnectServer(config=mock_plugin_config)

    # Directly call the handler
    tools = await server._list_tools_handler()

    assert len(tools) == 1
    assert tools[0].name == "mock_echo"
    assert tools[0].description == "Echoes the input."


@pytest.mark.asyncio
async def test_call_tool(mock_plugin_config: AppConfig) -> None:
    """Test calling a tool."""
    server = CoreasonConnectServer(config=mock_plugin_config)

    result = await server._call_tool_handler(
        name="mock_echo", arguments={"message": "Hello"}
    )

    assert len(result) == 1
    assert result[0].type == "text"
    assert result[0].text == "Echo: Hello"


@pytest.mark.asyncio
async def test_call_tool_json_result(mock_plugin_config: AppConfig) -> None:
    """Test calling a tool that returns a JSON-serializable structure."""
    server = CoreasonConnectServer(config=mock_plugin_config)

    # Mock a plugin that returns a dict
    mock_plugin = MagicMock(spec=ConnectorProtocol)
    mock_plugin.execute.return_value = {"status": "success", "data": [1, 2, 3]}
    server.tool_registry["mock_json"] = mock_plugin

    result = await server._call_tool_handler(
        name="mock_json", arguments={}
    )

    assert len(result) == 1
    assert result[0].type == "text"
    assert '"status": "success"' in result[0].text
    assert '"data": [1, 2, 3]' in result[0].text


@pytest.mark.asyncio
async def test_call_tool_missing_arg(mock_plugin_config: AppConfig) -> None:
    """Test calling a tool with missing arguments."""
    server = CoreasonConnectServer(config=mock_plugin_config)

    result = await server._call_tool_handler(
        name="mock_echo", arguments={}
    )

    assert len(result) == 1
    assert result[0].type == "text"
    assert "Error executing tool" in result[0].text
    assert "Missing 'message' argument" in result[0].text


@pytest.mark.asyncio
async def test_call_unknown_tool(mock_plugin_config: AppConfig) -> None:
    """Test calling an unknown tool."""
    server = CoreasonConnectServer(config=mock_plugin_config)

    result = await server._call_tool_handler(
        name="unknown_tool", arguments={}
    )

    assert len(result) == 1
    assert result[0].type == "text"
    assert "Error: Tool 'unknown_tool' not found" in result[0].text


def test_load_plugins_error_handling(mock_plugin_config: AppConfig) -> None:
    """Test error handling during plugin loading (get_tools)."""
    server = CoreasonConnectServer(config=mock_plugin_config)

    # Mock the plugin to raise an exception during get_tools
    mock_plugin = MagicMock(spec=ConnectorProtocol)
    mock_plugin.get_tools.side_effect = Exception("Test Error")

    # Mock the loader to return our malicious plugin
    server.plugin_loader.load_all = MagicMock(return_value={"mock-plugin": mock_plugin})

    # Re-run _load_plugins to trigger the error
    server.tool_registry.clear()
    server._load_plugins()

    # Should handle exception and not crash, tool registry empty
    assert len(server.tool_registry) == 0


def test_load_plugins_duplicate_tool_warning(mock_plugin_config: AppConfig) -> None:
    """Test warning on duplicate tool names."""
    server = CoreasonConnectServer(config=mock_plugin_config)

    # Mock two plugins returning the same tool name
    mock_plugin1 = MagicMock(spec=ConnectorProtocol)
    mock_tool = types.Tool(name="duplicate_tool", inputSchema={})
    mock_plugin1.get_tools.return_value = [mock_tool]

    mock_plugin2 = MagicMock(spec=ConnectorProtocol)
    mock_plugin2.get_tools.return_value = [mock_tool]

    server.plugin_loader.load_all = MagicMock(return_value={
        "plugin1": mock_plugin1,
        "plugin2": mock_plugin2
    })

    # Re-run _load_plugins
    server.tool_registry.clear()
    server._load_plugins()

    # Should have loaded the tool (last one wins)
    assert "duplicate_tool" in server.tool_registry


@pytest.mark.asyncio
async def test_list_tools_error_handling(mock_plugin_config: AppConfig) -> None:
    """Test error handling during list_tools."""
    server = CoreasonConnectServer(config=mock_plugin_config)

    # Mock the plugin to raise an exception during get_tools
    mock_plugin = MagicMock(spec=ConnectorProtocol)
    mock_plugin.get_tools.side_effect = Exception("Test Error")
    server.plugins["mock-plugin"] = mock_plugin

    tools = await server._list_tools_handler()

    # Should handle exception and return empty list (or partial list)
    assert len(tools) == 0
