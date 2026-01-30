# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_service() -> Generator[MagicMock, None, None]:
    with patch("coreason_connect.app.CoreasonConnectServiceAsync") as MockService:
        instance = MockService.return_value
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock()
        instance.plugins = {"test_plugin": MagicMock()}
        instance.tool_registry = {"test_tool": MagicMock()}
        instance.run = AsyncMock()
        instance.create_initialization_options = MagicMock()
        yield instance


@pytest.fixture
def mock_config() -> Generator[MagicMock, None, None]:
    with patch("coreason_connect.app.load_config") as mock_load:
        mock_load.return_value = MagicMock()
        yield mock_load


@pytest.fixture
def mock_transport() -> Generator[MagicMock, None, None]:
    with patch("coreason_connect.app.SseServerTransport") as MockTransport:
        instance = MockTransport.return_value

        @asynccontextmanager
        async def mock_connect(
            scope: Any, receive: Any, send: Any
        ) -> AsyncGenerator[tuple[AsyncMock, AsyncMock], None]:
            # Simulate sending headers for SSE
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"text/event-stream")],
                }
            )
            # Simulate sending empty body to establish connection (TestClient might need it)
            # In reality, EventSourceResponse keeps stream open.
            # For test, we close it immediately by sending body with more_body=False
            await send(
                {
                    "type": "http.response.body",
                    "body": b"",
                    "more_body": False,
                }
            )

            read_stream = AsyncMock()
            write_stream = AsyncMock()
            yield (read_stream, write_stream)

        async def mock_handle_message_impl(scope: Any, receive: Any, send: Any) -> None:
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"{}",
                    "more_body": False,
                }
            )

        instance.connect_sse = mock_connect
        instance.handle_post_message = AsyncMock(side_effect=mock_handle_message_impl)
        yield instance


@pytest.fixture
def client(
    mock_service: MagicMock, mock_config: MagicMock, mock_transport: MagicMock
) -> Generator[TestClient, None, None]:
    from coreason_connect.app import app

    # Ensure app state is clean or refreshed if needed, but TestClient handles lifespan
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client: TestClient, mock_service: MagicMock) -> None:
    """Test the /health endpoint returns correct status and plugins."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "live"
    assert "test_plugin" in data["plugins"]
    assert "test_tool" in data["tools"]


def test_sse_endpoint(client: TestClient, mock_service: MagicMock, mock_transport: MagicMock) -> None:
    """Test the /sse endpoint initiates connection."""
    # When we hit /sse, it should call transport.connect_sse
    # and then service.run.
    # Since service.run is mocked to return immediately, the connection should close.
    response = client.get("/sse")
    assert response.status_code == 200

    # Verify service.run was called
    mock_service.run.assert_awaited_once()


def test_messages_endpoint(client: TestClient, mock_transport: MagicMock) -> None:
    """Test the /messages endpoint routes to transport."""
    response = client.post("/messages", json={"jsonrpc": "2.0", "method": "ping"})
    assert response.status_code == 200

    mock_transport.handle_post_message.assert_awaited_once()


def test_startup_config_error() -> None:
    """Test that app startup fails if config loading fails."""
    from coreason_connect.app import app

    with patch("coreason_connect.app.load_config", side_effect=RuntimeError("Config Error")):
        # TestClient calls lifespan on enter
        with pytest.raises(RuntimeError, match="Config Error"):
            with TestClient(app):
                pass
