import json
from typing import Any
from unittest.mock import MagicMock

import mcp.types as types
import pytest
from mcp.server import Server

from coreason_connect.config import AppConfig, PluginConfig
from coreason_connect.interfaces import ConnectorProtocol
from coreason_connect.secrets import EnvSecretsProvider
from coreason_connect.server import CoreasonConnectServer


@pytest.fixture  # type: ignore[misc]
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


@pytest.mark.asyncio  # type: ignore[misc]
async def test_list_tools(mock_plugin_config: AppConfig) -> None:
    """Test listing tools."""
    server = CoreasonConnectServer(config=mock_plugin_config)

    # Directly call the handler
    tools = await server._list_tools_handler()

    assert len(tools) == 1
    assert tools[0].name == "mock_echo"
    assert tools[0].description == "Echoes the input."


@pytest.mark.asyncio  # type: ignore[misc]
async def test_call_tool(mock_plugin_config: AppConfig) -> None:
    """Test calling a tool."""
    server = CoreasonConnectServer(config=mock_plugin_config)

    result = await server._call_tool_handler(name="mock_echo", arguments={"message": "Hello"})

    assert len(result) == 1
    assert result[0].type == "text"
    assert result[0].text == "Echo: Hello"


@pytest.mark.asyncio  # type: ignore[misc]
async def test_call_tool_json_result(mock_plugin_config: AppConfig) -> None:
    """Test calling a tool that returns a JSON-serializable structure."""
    server = CoreasonConnectServer(config=mock_plugin_config)

    # Mock a plugin that returns a dict
    mock_plugin = MagicMock(spec=ConnectorProtocol)
    mock_plugin.execute.return_value = {"status": "success", "data": [1, 2, 3]}
    server.tool_registry["mock_json"] = mock_plugin

    result = await server._call_tool_handler(name="mock_json", arguments={})

    assert len(result) == 1
    assert result[0].type == "text"
    # Ensure it's valid JSON string
    loaded = json.loads(result[0].text)  # type: ignore[attr-defined]
    assert loaded["status"] == "success"
    assert loaded["data"] == [1, 2, 3]


@pytest.mark.asyncio  # type: ignore[misc]
async def test_call_tool_missing_arg(mock_plugin_config: AppConfig) -> None:
    """Test calling a tool with missing arguments."""
    server = CoreasonConnectServer(config=mock_plugin_config)

    result = await server._call_tool_handler(name="mock_echo", arguments={})

    assert len(result) == 1
    assert result[0].type == "text"
    assert "Error executing tool" in result[0].text  # type: ignore[attr-defined,union-attr]
    assert "Missing 'message' argument" in result[0].text  # type: ignore[attr-defined,union-attr]


@pytest.mark.asyncio  # type: ignore[misc]
async def test_call_unknown_tool(mock_plugin_config: AppConfig) -> None:
    """Test calling an unknown tool."""
    server = CoreasonConnectServer(config=mock_plugin_config)

    result = await server._call_tool_handler(name="unknown_tool", arguments={})

    assert len(result) == 1
    assert result[0].type == "text"
    assert "Error: Tool 'unknown_tool' not found" in result[0].text  # type: ignore[attr-defined,union-attr]


def test_load_plugins_error_handling(mock_plugin_config: AppConfig) -> None:
    """Test error handling during plugin loading (get_tools)."""
    server = CoreasonConnectServer(config=mock_plugin_config)

    # Mock the plugin to raise an exception during get_tools
    mock_plugin = MagicMock(spec=ConnectorProtocol)
    mock_plugin.get_tools.side_effect = Exception("Test Error")

    # Mock the loader to return our malicious plugin
    server.plugin_loader.load_all = MagicMock(return_value={"mock-plugin": mock_plugin})  # type: ignore[method-assign]

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

    server.plugin_loader.load_all = MagicMock(  # type: ignore[method-assign]
        return_value={"plugin1": mock_plugin1, "plugin2": mock_plugin2}
    )

    # Re-run _load_plugins
    server.tool_registry.clear()
    server._load_plugins()

    # Should have loaded the tool (last one wins)
    assert "duplicate_tool" in server.tool_registry


@pytest.mark.asyncio  # type: ignore[misc]
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


@pytest.mark.asyncio  # type: ignore[misc]
async def test_stateful_plugin(mock_plugin_config: AppConfig) -> None:
    """Test that a plugin maintains state across calls."""
    server = CoreasonConnectServer(config=mock_plugin_config)

    # Define a simple stateful class
    class StatefulPlugin:
        def __init__(self) -> None:
            self.counter = 0

        def execute(self, name: str, args: dict[str, Any]) -> int:
            self.counter += 1
            return self.counter

    plugin = StatefulPlugin()
    server.tool_registry["increment"] = plugin  # type: ignore[assignment]

    # First call
    result1 = await server._call_tool_handler("increment", {})
    assert result1[0].text == "1"  # type: ignore[attr-defined,union-attr]

    # Second call
    result2 = await server._call_tool_handler("increment", {})
    assert result2[0].text == "2"  # type: ignore[attr-defined,union-attr]


@pytest.mark.asyncio  # type: ignore[misc]
async def test_call_tool_return_values(mock_plugin_config: AppConfig) -> None:
    """Test handling of various return values (None, Object)."""
    server = CoreasonConnectServer(config=mock_plugin_config)
    mock_plugin = MagicMock(spec=ConnectorProtocol)
    server.tool_registry["test_tool"] = mock_plugin

    # Case 1: None
    mock_plugin.execute.return_value = None
    result = await server._call_tool_handler("test_tool", {})
    assert result[0].text == "None"  # type: ignore[attr-defined,union-attr]

    # Case 2: Custom Object
    class CustomObj:
        def __str__(self) -> str:
            return "CustomString"

    mock_plugin.execute.return_value = CustomObj()
    result = await server._call_tool_handler("test_tool", {})
    assert result[0].text == "CustomString"  # type: ignore[attr-defined,union-attr]


@pytest.mark.asyncio  # type: ignore[misc]
async def test_call_tool_complex_args(mock_plugin_config: AppConfig) -> None:
    """Test passing complex arguments to a tool."""
    server = CoreasonConnectServer(config=mock_plugin_config)
    mock_plugin = MagicMock(spec=ConnectorProtocol)
    # Echo back the args
    mock_plugin.execute.side_effect = lambda name, args: args
    server.tool_registry["complex_tool"] = mock_plugin

    complex_args = {"user": {"id": 1, "name": "Test"}, "filters": ["active", "pending"], "meta": None}

    result = await server._call_tool_handler("complex_tool", complex_args)

    # Should be serialized back to JSON
    loaded = json.loads(result[0].text)  # type: ignore[attr-defined,arg-type,union-attr]
    assert loaded["user"]["id"] == 1
    assert "active" in loaded["filters"]
