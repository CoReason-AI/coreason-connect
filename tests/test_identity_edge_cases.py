# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

import asyncio
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest
from coreason_identity.models import UserContext
from mcp.types import Tool

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.server import CoreasonConnectServiceAsync
from coreason_connect.types import ToolDefinition


@pytest.fixture
def mock_secrets() -> SecretsProvider:
    return MagicMock(spec=SecretsProvider)


@pytest.fixture
def server(mock_secrets: SecretsProvider) -> CoreasonConnectServiceAsync:
    return CoreasonConnectServiceAsync(secrets=mock_secrets)


@pytest.mark.asyncio
async def test_missing_downstream_token(server: CoreasonConnectServiceAsync) -> None:
    """
    Edge Case: UserContext is present but downstream_token is None.
    Plugin should receive the context but handle missing token (usually fallback).
    """

    class TokenCheckPlugin(ConnectorProtocol):
        def get_tools(self) -> list[ToolDefinition]:
            return [
                ToolDefinition(
                    name="check_token",
                    tool=Tool(name="check_token", inputSchema={}),
                )
            ]

        def execute(
            self,
            tool_name: str,
            arguments: dict[str, Any] | None = None,
            user_context: Optional[UserContext] = None,
        ) -> Any:
            if user_context is None:
                return "No Context"
            if user_context.downstream_token is None:
                return "Context Present, No Token"
            return "Token Present"

    plugin = TokenCheckPlugin(server.secrets)
    server.plugins = {"token_check": plugin}
    server.plugin_registry["check_token"] = plugin
    server.tool_registry["check_token"] = plugin.get_tools()[0]

    # Context without token
    context_data = {
        "user_id": "u1",
        "email": "u@e.com",
        "downstream_token": None,
    }

    result = await server._call_tool_handler("check_token", {"user_context": context_data})
    assert result[0].text == "Context Present, No Token"  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_malformed_user_context_string(server: CoreasonConnectServiceAsync) -> None:
    """
    Edge Case: user_context is a string but not valid JSON.
    Server should log warning and pass None to plugin.
    """

    class StrictPlugin(ConnectorProtocol):
        def get_tools(self) -> list[ToolDefinition]:
            return [ToolDefinition(name="strict", tool=Tool(name="strict", inputSchema={}))]

        def execute(
            self,
            tool_name: str,
            arguments: dict[str, Any] | None = None,
            user_context: Optional[UserContext] = None,
        ) -> Any:
            return "None" if user_context is None else "Context"

    plugin = StrictPlugin(server.secrets)
    server.plugins = {"strict": plugin}
    server.plugin_registry["strict"] = plugin
    server.tool_registry["strict"] = plugin.get_tools()[0]

    result = await server._call_tool_handler("strict", {"user_context": "{not json"})
    assert result[0].text == "None"  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_invalid_user_context_schema(server: CoreasonConnectServiceAsync) -> None:
    """
    Edge Case: JSON is valid but missing required fields (e.g. email).
    Pydantic validation should fail, server should catch it and pass None.
    """

    class StrictPlugin(ConnectorProtocol):
        def get_tools(self) -> list[ToolDefinition]:
            return [ToolDefinition(name="strict", tool=Tool(name="strict", inputSchema={}))]

        def execute(
            self,
            tool_name: str,
            arguments: dict[str, Any] | None = None,
            user_context: Optional[UserContext] = None,
        ) -> Any:
            return "None" if user_context is None else "Context"

    plugin = StrictPlugin(server.secrets)
    server.plugins = {"strict": plugin}
    server.plugin_registry["strict"] = plugin
    server.tool_registry["strict"] = plugin.get_tools()[0]

    # Missing email
    context_data = {"user_id": "u1"}

    result = await server._call_tool_handler("strict", {"user_context": context_data})
    assert result[0].text == "None"  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_concurrency_isolation(server: CoreasonConnectServiceAsync) -> None:
    """
    Edge Case: Concurrent requests with different contexts should not interfere.
    """

    class SlowPlugin(ConnectorProtocol):
        def get_tools(self) -> list[ToolDefinition]:
            return [ToolDefinition(name="slow_whoami", tool=Tool(name="slow_whoami", inputSchema={}))]

        async def _async_execute(self, user_context: Optional[UserContext]) -> str:
            # Simulate work
            await asyncio.sleep(0.1)
            return user_context.user_id if user_context else "None"

        def execute(
            self,
            tool_name: str,
            arguments: dict[str, Any] | None = None,
            user_context: Optional[UserContext] = None,
        ) -> Any:
            # In a real sync execute we can't await, but for this test we return the coroutine
            # and let the test runner handle it if we modify _call_tool_handler or just check identity
            # Since execute is sync, we can just return the ID.
            # The concurrency happens at the server handling level (async _call_tool_handler).
            return user_context.user_id if user_context else "None"

    plugin = SlowPlugin(server.secrets)
    server.plugins = {"slow": plugin}
    server.plugin_registry["slow_whoami"] = plugin
    server.tool_registry["slow_whoami"] = plugin.get_tools()[0]

    async def call_with_user(user_id: str) -> str:
        ctx = {
            "user_id": user_id,
            "email": f"{user_id}@test.com",
            "downstream_token": f"token_{user_id}",
        }
        # _call_tool_handler is async
        res = await server._call_tool_handler("slow_whoami", {"user_context": ctx})
        return res[0].text  # type: ignore[union-attr]

    # Run 3 concurrent calls
    results = await asyncio.gather(
        call_with_user("alice"),
        call_with_user("bob"),
        call_with_user("charlie"),
    )

    assert list(results) == ["alice", "bob", "charlie"]
