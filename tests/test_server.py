from typing import Any
from unittest.mock import patch

import pytest
from mcp.server import Server
from mcp.types import (
    CallToolRequest,
    EmbeddedResource,
    ImageContent,
    ListToolsRequest,
    TextContent,
    Tool,
)

from coreason_connect.server import CoreasonConnectServer


def test_server_initialization() -> None:
    """Test that the server initializes correctly."""
    server = CoreasonConnectServer(name="test-server", version="1.0.0")

    assert isinstance(server, Server)
    assert server.version == "1.0.0"
    assert server.name == "test-server"


def test_server_default_initialization() -> None:
    """Test default initialization."""
    server = CoreasonConnectServer()
    assert server.name == "coreason-connect"
    assert server.version == "0.1.0"


@pytest.mark.parametrize(  # type: ignore[misc]
    ("name", "version"),
    [
        ("", ""),
        ("   ", "   "),
        ("!@#$%^&*()", "v1.0.0-beta+exp"),
        ("emoji_🚀", "1.0.0"),
        ("a" * 1000, "1.0.0"),
    ],
)
def test_server_initialization_edge_cases(name: str, version: str) -> None:
    """Test server initialization with various edge case strings."""
    server = CoreasonConnectServer(name=name, version=version)
    assert server.name == name
    assert server.version == version


def test_server_logging_behavior() -> None:
    """Test that the server logs its initialization correctly."""
    with patch("coreason_connect.server.logger") as mock_logger:
        CoreasonConnectServer(name="test-logger", version="9.9.9")
        mock_logger.info.assert_called_once_with("Initialized test-logger v9.9.9")


def test_server_inheritance_functional_integration() -> None:
    """
    Complex Scenario: Verify that the subclassed server behaves like an MCP Server.
    We check if we can register handlers for tool listing and execution using the
    inherited decorators.
    """
    server = CoreasonConnectServer(name="integration-test", version="1.0.0")

    # 1. Register a List Tools handler
    @server.list_tools()  # type: ignore[misc, no-untyped-call]
    async def list_tools() -> list[Tool]:
        return []

    # 2. Register a Call Tool handler
    @server.call_tool()  # type: ignore[misc]
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent | EmbeddedResource]:
        return []

    # 3. Verify handlers are registered in the base class's request_handlers map
    # Note: request_handlers is an internal implementation detail of mcp.server.Server
    # but accessing it is the only way to verify without starting a full transport loop.
    assert ListToolsRequest in server.request_handlers
    assert CallToolRequest in server.request_handlers

    # 4. Verify the registered handler is actually ours (indirectly)
    # We can't easily check equality of wrapped functions, but presence is good enough.
    assert callable(server.request_handlers[ListToolsRequest])
    assert callable(server.request_handlers[CallToolRequest])
