# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from coreason_connect.interfaces import SecretsProvider
from coreason_connect.plugins.ms365 import MS365Connector
from coreason_connect.server import CoreasonConnectServiceAsync


@pytest.fixture
def mock_secrets() -> SecretsProvider:
    return MagicMock(spec=SecretsProvider)


@pytest.fixture
def mock_graph_client() -> Generator[MagicMock, None, None]:
    with patch("coreason_connect.plugins.ms365.GraphClientFactory.create_with_default_middleware") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        yield mock_client


@pytest.fixture
def ms365_plugin(mock_secrets: SecretsProvider, mock_graph_client: MagicMock) -> MS365Connector:
    return MS365Connector(mock_secrets)


@pytest.fixture
def server(mock_secrets: SecretsProvider, ms365_plugin: MS365Connector) -> CoreasonConnectServiceAsync:
    s = CoreasonConnectServiceAsync(secrets=mock_secrets)
    # Register MS365 plugin manually
    s.plugins = {"ms365": ms365_plugin}
    for tool_def in ms365_plugin.get_tools():
        s.plugin_registry[tool_def.name] = ms365_plugin
        s.tool_registry[tool_def.name] = tool_def
    return s


@pytest.mark.asyncio
async def test_full_obo_flow(server: CoreasonConnectServiceAsync, mock_graph_client: MagicMock) -> None:
    """
    Complex Workflow: Find Meeting -> Draft Email -> Send Email.
    Verifies that the same OBO token is used across all calls.
    """
    token = "secret-obo-token"
    user_context = {
        "user_id": "alice",
        "email": "alice@example.com",
        "downstream_token": token,
    }

    # Setup Mocks for the chain
    mock_response_slot = MagicMock()
    mock_response_slot.json.return_value = {"meetingTimeSlots": [{"start": "2023..."}]}

    mock_response_draft = MagicMock()
    mock_response_draft.json.return_value = {"id": "msg_123"}

    mock_response_send = MagicMock()
    mock_response_send.json.return_value = {}  # 202 Accepted

    mock_graph_client.post.side_effect = [
        mock_response_slot,
        mock_response_draft,
        mock_response_send,
    ]

    # 1. Find Meeting Slot
    res1 = await server._call_tool_handler(
        "find_meeting_slot",
        {"attendees": ["bob@example.com"], "duration": "PT1H", "user_context": user_context},
    )
    assert "meetingTimeSlots" in res1[0].text  # type: ignore[union-attr]

    # Verify headers for call 1
    args1, kwargs1 = mock_graph_client.post.call_args_list[0]
    assert kwargs1["headers"]["Authorization"] == f"Bearer {token}"

    # 2. Draft Email
    res2 = await server._call_tool_handler(
        "draft_email",
        {
            "to": "bob@example.com",
            "subject": "Meeting",
            "body": "Let's meet",
            "user_context": user_context,
        },
    )
    assert "msg_123" in res2[0].text  # type: ignore[union-attr]

    # Verify headers for call 2
    args2, kwargs2 = mock_graph_client.post.call_args_list[1]
    assert kwargs2["headers"]["Authorization"] == f"Bearer {token}"

    # 3. Send Email
    # Note: send_email is consequential, so it will be suspended by the Spend Gate.
    res3 = await server._call_tool_handler("send_email", {"id": "msg_123", "user_context": user_context})
    assert "Action suspended" in res3[0].text  # type: ignore[union-attr]

    # Verify headers for call 3
    # The plugin execute is NOT called, so we can't verify the 3rd call headers here.
    # The token propagation logic is verified by the first two calls and unit tests.
    assert mock_graph_client.post.call_count == 2


@pytest.mark.asyncio
async def test_fallback_chain_flow(server: CoreasonConnectServiceAsync, mock_graph_client: MagicMock) -> None:
    """
    Complex Workflow: Same chain but without UserContext.
    Verifies that NO Authorization header is injected (service identity fallback).
    """
    # Setup Mocks
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "123"}
    mock_graph_client.post.return_value = mock_response

    # Call Draft Email without context
    await server._call_tool_handler(
        "draft_email",
        {"to": "bob@example.com", "subject": "Meeting", "body": "Let's meet"},
    )

    args, kwargs = mock_graph_client.post.call_args
    # Headers should NOT contain Authorization (or whatever default behavior is)
    # Our code only adds it if token is present.
    assert "Authorization" not in kwargs.get("headers", {})


@pytest.mark.asyncio
async def test_mixed_identity_flow(server: CoreasonConnectServiceAsync, mock_graph_client: MagicMock) -> None:
    """
    Complex Workflow: Calls with different identities.
    """
    ctx_alice = {
        "user_id": "alice",
        "email": "alice@ex.com",
        "downstream_token": "token_alice",
    }
    ctx_bob = {
        "user_id": "bob",
        "email": "bob@ex.com",
        "downstream_token": "token_bob",
    }

    mock_graph_client.post.return_value = MagicMock(json=lambda: {"id": "1"})

    # Alice drafts
    await server._call_tool_handler("draft_email", {"to": "x", "subject": "x", "body": "x", "user_context": ctx_alice})

    # Bob drafts
    await server._call_tool_handler("draft_email", {"to": "y", "subject": "y", "body": "y", "user_context": ctx_bob})

    assert mock_graph_client.post.call_count == 2

    # Check Alice's call
    _, kwargs1 = mock_graph_client.post.call_args_list[0]
    assert kwargs1["headers"]["Authorization"] == "Bearer token_alice"

    # Check Bob's call
    _, kwargs2 = mock_graph_client.post.call_args_list[1]
    assert kwargs2["headers"]["Authorization"] == "Bearer token_bob"
