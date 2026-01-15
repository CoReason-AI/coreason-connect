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

import mcp.types as types
from mcp.server import Server

from coreason_connect.config import AppConfig
from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.loader import PluginLoader
from coreason_connect.secrets import EnvSecretsProvider
from coreason_connect.types import ToolExecutionError
from coreason_connect.utils.logger import logger


class CoreasonConnectServer(Server):
    """The MCP Host that aggregates tools and plugins."""

    def __init__(
        self,
        config: AppConfig | None = None,
        secrets: SecretsProvider | None = None,
        name: str = "coreason-connect",
        version: str = "0.1.0",
    ) -> None:
        """Initialize the MCP Server."""
        super().__init__(name)
        self.version = version

        self.config = config or AppConfig()
        self.secrets = secrets or EnvSecretsProvider()

        self.plugin_loader = PluginLoader(self.config, self.secrets)
        self.plugins: dict[str, ConnectorProtocol] = {}
        self.tool_registry: dict[str, ConnectorProtocol] = {}

        # Load plugins
        self._load_plugins()

        # Register handlers
        # Using type: ignore because mcp.server.Server decorators are not typed in a way mypy likes
        self.list_tools()(self._list_tools_handler)  # type: ignore[no-untyped-call]
        self.call_tool()(self._call_tool_handler)

        logger.info(
            f"Initialized {name} v{version} with {len(self.plugins)} plugins and {len(self.tool_registry)} tools"
        )

    def _load_plugins(self) -> None:
        """Load plugins and build the tool registry."""
        self.plugins = self.plugin_loader.load_all()
        for plugin_id, plugin in self.plugins.items():
            try:
                tools = plugin.get_tools()
                for tool in tools:
                    if tool.name in self.tool_registry:
                        logger.warning(f"Duplicate tool name '{tool.name}' found in plugin '{plugin_id}'. Overwriting.")
                    self.tool_registry[tool.name] = plugin
            except Exception as e:
                logger.error(f"Failed to get tools from plugin '{plugin_id}': {e}")

    async def _list_tools_handler(self) -> list[types.Tool]:
        """Handler for listing tools."""
        all_tools: list[types.Tool] = []
        for plugin_id, plugin in self.plugins.items():
            try:
                all_tools.extend(plugin.get_tools())
            except Exception as e:
                logger.error(f"Error listing tools for plugin '{plugin_id}': {e}")
        return all_tools

    async def _call_tool_handler(
        self, name: str, arguments: dict[str, Any]
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handler for calling tools."""
        plugin = self.tool_registry.get(name)
        if not plugin:
            return [types.TextContent(type="text", text=f"Error: Tool '{name}' not found.")]

        try:
            result = plugin.execute(name, arguments)
            if isinstance(result, (dict, list)):
                result_str = json.dumps(result)
            else:
                result_str = str(result)
            return [types.TextContent(type="text", text=result_str)]
        except ToolExecutionError as e:
            logger.warning(f"Tool '{name}' execution failed (retryable={e.retryable}): {e}")
            return [types.TextContent(type="text", text=f"Error: Tool '{name}' failed - {e.message}")]
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}")
            return [types.TextContent(type="text", text=f"Error executing tool: {str(e)}")]
