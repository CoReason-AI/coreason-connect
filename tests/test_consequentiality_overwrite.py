# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from unittest.mock import MagicMock, patch

import pytest
from mcp.types import Tool

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.server import CoreasonConnectServer
from coreason_connect.types import ToolDefinition


@pytest.fixture
def mock_secrets() -> SecretsProvider:
    return MagicMock(spec=SecretsProvider)


@pytest.fixture
def server(mock_secrets: SecretsProvider) -> CoreasonConnectServer:
    return CoreasonConnectServer(secrets=mock_secrets)


@pytest.mark.asyncio
async def test_tool_overwrite_security_implications(server: CoreasonConnectServer) -> None:
    """
    Test that when a tool is overwritten by a plugin with different 'is_consequential' metadata,
    the metadata in the registry is updated to reflect the last loaded plugin.
    This confirms "Last Write Wins" behavior.
    """

    # 1. Define Safe and Unsafe plugins for the same tool name
    tool_name = "ambiguous_tool"

    class SafePlugin(ConnectorProtocol):
        def get_tools(self) -> list[ToolDefinition]:
            return [
                ToolDefinition(
                    name=tool_name,
                    tool=Tool(name=tool_name, inputSchema={}, description="Safe"),
                    is_consequential=False,
                )
            ]

        def execute(self, *args: object, **kwargs: object) -> object:
            return "Safe Executed"

    class UnsafePlugin(ConnectorProtocol):
        def get_tools(self) -> list[ToolDefinition]:
            return [
                ToolDefinition(
                    name=tool_name,
                    tool=Tool(name=tool_name, inputSchema={}, description="Unsafe"),
                    is_consequential=True,
                )
            ]

        def execute(self, *args: object, **kwargs: object) -> object:
            return "Unsafe Executed"

    safe_plugin = SafePlugin(server.secrets)
    unsafe_plugin = UnsafePlugin(server.secrets)

    # 2. Scenario A: Safe -> Unsafe
    # Mock load_all to return them in order (simulated by manual registration order)
    # Since load_all returns a dict, order is insertion order in recent Python.
    # But to be robust, we'll manually invoke _load_plugins behavior

    # Reset server
    server.tool_registry = {}
    server.plugin_registry = {}

    # Load Safe First
    server.plugin_loader.load_all = MagicMock(return_value={"safe": safe_plugin})  # type: ignore[method-assign]
    with patch("coreason_connect.server.logger"):
        server._load_plugins()

    # Verify Safe
    assert server.tool_registry[tool_name].is_consequential is False
    result = await server._call_tool_handler(tool_name, {})
    assert result[0].text == "Safe Executed"  # type: ignore[union-attr]

    # Load Unsafe Second (Overwrite)
    server.plugin_loader.load_all = MagicMock(return_value={"unsafe": unsafe_plugin})  # type: ignore[method-assign]
    with patch("coreason_connect.server.logger"):
        server._load_plugins()
        # Verify warning about overwrite (assuming we are simulating a fresh load that happens to collide
        # with existing state)
        # or if we loaded both at once. _load_plugins replaces self.plugins.
        # But wait, _load_plugins does: self.plugins = load_all().
        # But it appends to plugin_registry/tool_registry. It doesn't clear them?
        # Let's check server.py:
        # self.plugins = self.plugin_loader.load_all()
        # for plugin_id, plugin in self.plugins.items(): ...

        # It does NOT clear plugin_registry or tool_registry at the start of _load_plugins.
        # So multiple calls to _load_plugins accumulate/overwrite.

    # Verify Unsafe Overwrite
    assert server.tool_registry[tool_name].is_consequential is True
    result = await server._call_tool_handler(tool_name, {})
    assert "Action suspended" in result[0].text  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_tool_overwrite_unsafe_to_safe(server: CoreasonConnectServer) -> None:
    """Test overwriting an unsafe tool with a safe one."""
    tool_name = "flip_flop_tool"

    class UnsafePlugin(ConnectorProtocol):
        def get_tools(self) -> list[ToolDefinition]:
            return [ToolDefinition(name=tool_name, tool=Tool(name=tool_name, inputSchema={}), is_consequential=True)]

        def execute(self, *args: object, **kwargs: object) -> object:
            return "Unsafe"

    class SafePlugin(ConnectorProtocol):
        def get_tools(self) -> list[ToolDefinition]:
            return [ToolDefinition(name=tool_name, tool=Tool(name=tool_name, inputSchema={}), is_consequential=False)]

        def execute(self, *args: object, **kwargs: object) -> object:
            return "Safe"

    unsafe_plugin = UnsafePlugin(server.secrets)
    safe_plugin = SafePlugin(server.secrets)

    # 1. Load Unsafe
    server.tool_registry = {}
    server.plugin_registry = {}

    server.plugin_loader.load_all = MagicMock(return_value={"unsafe": unsafe_plugin})  # type: ignore[method-assign]
    server._load_plugins()

    assert server.tool_registry[tool_name].is_consequential is True

    # 2. Load Safe (Overwrite)
    server.plugin_loader.load_all = MagicMock(return_value={"safe": safe_plugin})  # type: ignore[method-assign]
    with patch("coreason_connect.server.logger"):
        server._load_plugins()

    # Verify Safe Overwrite
    assert server.tool_registry[tool_name].is_consequential is False
    result = await server._call_tool_handler(tool_name, {})
    assert result[0].text == "Safe"  # type: ignore[union-attr]
