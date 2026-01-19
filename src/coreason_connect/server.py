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
from coreason_connect.types import ToolDefinition, ToolExecutionError
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
        """Initialize the MCP Server.

        Args:
            config: Configuration for the application. Defaults to standard AppConfig.
            secrets: Secrets provider for the application. Defaults to EnvSecretsProvider.
            name: Name of the server. Defaults to "coreason-connect".
            version: Version of the server. Defaults to "0.1.0".
        """
        super().__init__(name)
        self.version = version

        self.config = config or AppConfig()
        self.secrets = secrets or EnvSecretsProvider()

        self.plugin_loader = PluginLoader(self.config, self.secrets)
        self.plugins: dict[str, ConnectorProtocol] = {}
        self.plugin_registry: dict[str, ConnectorProtocol] = {}
        self.tool_registry: dict[str, ToolDefinition] = {}

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
                for tool_def in tools:
                    if tool_def.name in self.tool_registry:
                        logger.warning(
                            f"Duplicate tool name '{tool_def.name}' found in plugin '{plugin_id}'. Overwriting."
                        )
                    self.plugin_registry[tool_def.name] = plugin
                    self.tool_registry[tool_def.name] = tool_def
            except Exception as e:
                logger.error(f"Failed to get tools from plugin '{plugin_id}': {e}")

    async def _list_tools_handler(self) -> list[types.Tool]:
        """Handler for listing tools.

        Returns:
            A list of Tool objects from all registered plugins.
        """
        return [tool_def.tool for tool_def in self.tool_registry.values()]

    async def _call_tool_handler(
        self, name: str, arguments: dict[str, Any]
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handler for calling tools.

        Args:
            name: The name of the tool to execute.
            arguments: A dictionary of arguments for the tool.

        Returns:
            A list containing the execution result as text content.
        """
        plugin = self.plugin_registry.get(name)
        tool_def = self.tool_registry.get(name)

        if not plugin or not tool_def:
            return [types.TextContent(type="text", text=f"Error: Tool '{name}' not found.")]

        # Spend Gate / Transactional Safety Check
        if tool_def.is_consequential:
            msg = f"Action suspended: Human approval required for {name}."
            logger.info(f"Tool execution suspended for approval: {name}")
            return [types.TextContent(type="text", text=msg)]

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
