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
from typing import Any, Optional

import anyio
import httpx
import mcp.types as types
from coreason_identity.models import UserContext
from mcp.server import Server

from coreason_connect.config import AppConfig
from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.loader import PluginLoader
from coreason_connect.secrets import EnvSecretsProvider
from coreason_connect.types import ToolDefinition, ToolExecutionError
from coreason_connect.utils.logger import logger


class CoreasonConnectServiceAsync(Server):
    """The Async MCP Host that aggregates tools and plugins.

    This server is responsible for:
    1. Loading plugins via the PluginLoader.
    2. Aggregating tools from all loaded plugins.
    3. Handling MCP tool listing and execution requests.
    4. Enforcing the "Spend Gate" for consequential actions.
    5. Managing resources (HTTP client) via async context manager.

    Attributes:
        config: Application configuration.
        secrets: Secrets provider.
        plugin_loader: Component to load plugins.
        plugins: Dictionary of loaded plugins by ID.
        plugin_registry: Dictionary of plugins mapped by tool name.
        tool_registry: Dictionary of tool definitions mapped by tool name.
    """

    def __init__(
        self,
        config: AppConfig | None = None,
        secrets: SecretsProvider | None = None,
        client: httpx.AsyncClient | None = None,
        name: str = "coreason-connect",
        version: str = "0.3.0",
    ) -> None:
        """Initialize the MCP Server.

        Args:
            config: Configuration for the application. Defaults to standard AppConfig.
            secrets: Secrets provider for the application. Defaults to EnvSecretsProvider.
            client: Optional httpx.AsyncClient for connection pooling.
            name: Name of the server. Defaults to "coreason-connect".
            version: Version of the server. Defaults to "0.2.0".
        """
        super().__init__(name)
        self.version = version

        self.config = config or AppConfig()
        self.secrets = secrets or EnvSecretsProvider()

        self._internal_client = client is None
        self._client = client or httpx.AsyncClient()

        self.plugin_loader = PluginLoader(self.config, self.secrets)
        self.plugins: dict[str, ConnectorProtocol] = {}
        self.plugin_registry: dict[str, ConnectorProtocol] = {}
        self.tool_registry: dict[str, ToolDefinition] = {}

        # Load plugins
        # Note: We load plugins in __init__ because we are following the structure where
        # server initialization prepares the environment.
        # Future refactor could move this to __aenter__ if strictly async I/O is required.
        self._load_plugins()

        # Register handlers
        # Using type: ignore because mcp.server.Server decorators are not typed in a way mypy likes
        self.list_tools()(self._list_tools_handler)  # type: ignore[no-untyped-call]
        self.call_tool()(self._call_tool_handler)

        logger.info(
            f"Initialized {name} v{version} with {len(self.plugins)} plugins and {len(self.tool_registry)} tools"
        )

    async def __aenter__(self) -> "CoreasonConnectServiceAsync":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._internal_client:
            await self._client.aclose()

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

    async def get_all_tools(self) -> list[types.Tool]:
        """Public method to get all tools (wraps handler)."""
        return await self._list_tools_handler()

    async def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        user_context: Optional[UserContext] = None,
    ) -> Any:
        """Public method to execute a tool (wraps handler logic).

        Note: This returns raw result or raises exception, unlike _call_tool_handler which returns MCP Content.
        """
        # We can reuse the logic in _call_tool_handler but we might want the raw result.
        # For the library facade, raw result is better.
        # But _call_tool_handler handles 'Spend Gate'.
        # Let's reuse _call_tool_handler to ensure consistency, but we'll have to parse the result?
        # Or better: extract the logic.

        # Re-implementing logic here for direct usage (Library mode)
        plugin = self.plugin_registry.get(name)
        tool_def = self.tool_registry.get(name)

        if not plugin or not tool_def:
            raise ValueError(f"Tool '{name}' not found.")

        if tool_def.is_consequential:
            # In library mode, maybe we raise an error or just log?
            # The prompt says: "Action suspended: Human approval required for {name}."
            # For library usage, maybe we raise a specific exception?
            # Or just return the string message.
            msg = f"Action suspended: Human approval required for {name}."
            logger.info(f"Tool execution suspended for approval: {name}")
            return msg

        try:
            return plugin.execute(name, arguments, user_context=user_context)
        except Exception as e:
            # In library mode, we might want to propagate the exception or wrap it
            raise e

    async def _list_tools_handler(self) -> list[types.Tool]:
        """Handler for listing tools.

        Returns:
            list[types.Tool]: A list of Tool objects from all registered plugins.
        """
        return [tool_def.tool for tool_def in self.tool_registry.values()]

    async def _call_tool_handler(
        self, name: str, arguments: dict[str, Any]
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handler for calling tools.

        This method routes the execution to the appropriate plugin, enforcing
        the "Spend Gate" check for consequential tools.

        Args:
            name: The name of the tool to execute.
            arguments: A dictionary of arguments for the tool.

        Returns:
            list[types.Content]: A list containing the execution result as text content.
        """
        # Logic is similar to execute_tool but formatted for MCP
        plugin = self.plugin_registry.get(name)
        tool_def = self.tool_registry.get(name)

        if not plugin or not tool_def:
            return [types.TextContent(type="text", text=f"Error: Tool '{name}' not found.")]

        # Extract UserContext from arguments if present
        # coreason-mcp likely injects this as a hidden argument
        user_context: Optional[UserContext] = None
        # Check for common patterns for context injection
        # We look for a dictionary that matches UserContext or a reserved key
        if arguments and "user_context" in arguments:
            try:
                ctx_data = arguments.pop("user_context")
                if isinstance(ctx_data, str):
                    # Handle case where it might be a JSON string
                    try:
                        ctx_data = json.loads(ctx_data)
                    except json.JSONDecodeError:
                        logger.warning("Failed to decode user_context string")
                        ctx_data = {}
                if isinstance(ctx_data, dict):
                    user_context = UserContext(**ctx_data)
            except Exception as e:
                logger.warning(f"Failed to deserialize user_context: {e}")

        # Spend Gate / Transactional Safety Check
        if tool_def.is_consequential:
            msg = f"Action suspended: Human approval required for {name}."
            logger.info(f"Tool execution suspended for approval: {name}")
            return [types.TextContent(type="text", text=msg)]

        try:
            result = plugin.execute(name, arguments, user_context=user_context)
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


class CoreasonConnectService:
    """The Sync Facade for CoreasonConnectServiceAsync.

    Allows usage of the service in a synchronous context.
    """

    def __init__(
        self,
        config: AppConfig | None = None,
        secrets: SecretsProvider | None = None,
        client: httpx.AsyncClient | None = None,
        name: str = "coreason-connect",
        version: str = "0.3.0",
    ) -> None:
        self._async = CoreasonConnectServiceAsync(config, secrets, client, name, version)

    def __enter__(self) -> "CoreasonConnectService":
        # We start the async context in a blocking way
        anyio.run(self._async.__aenter__)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        anyio.run(self._async.__aexit__, exc_type, exc_val, exc_tb)

    def get_all_tools(self) -> list[types.Tool]:
        """Get all tools synchronously."""
        return anyio.run(self._async.get_all_tools)

    def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        user_context: Optional[UserContext] = None,
    ) -> Any:
        """Execute a tool synchronously."""
        return anyio.run(self._async.execute_tool, name, arguments, user_context)
