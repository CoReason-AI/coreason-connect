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
from coreason_identity.models import UserContext
from httpx import HTTPStatusError, Request, Response

from coreason_connect.interfaces import SecretsProvider
from coreason_connect.plugins.ms365 import MS365Connector
from coreason_connect.types import ToolExecutionError


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
def connector(mock_secrets: SecretsProvider, mock_graph_client: MagicMock) -> MS365Connector:
    return MS365Connector(mock_secrets)


def test_init_failure(mock_secrets: SecretsProvider) -> None:
    with patch(
        "coreason_connect.plugins.ms365.GraphClientFactory.create_with_default_middleware",
        side_effect=Exception("Init Failed"),
    ):
        with pytest.raises(Exception, match="Init Failed"):
            MS365Connector(mock_secrets)


def test_get_tools(connector: MS365Connector) -> None:
    tools = connector.get_tools()
    assert len(tools) == 3
    tool_names = {t.name for t in tools}
    assert tool_names == {"find_meeting_slot", "draft_email", "send_email"}

    send_tool = next(t for t in tools if t.name == "send_email")
    assert send_tool.is_consequential is True

    find_tool = next(t for t in tools if t.name == "find_meeting_slot")
    assert find_tool.is_consequential is False


def test_find_meeting_slot(connector: MS365Connector, mock_graph_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {"meetingTimeSlots": []}
    mock_graph_client.post.return_value = mock_response

    result = connector.execute("find_meeting_slot", {"attendees": ["test@example.com"], "duration": "PT1H"})

    assert result == {"meetingTimeSlots": []}
    mock_graph_client.post.assert_called_once()
    args, kwargs = mock_graph_client.post.call_args
    assert args[0] == "/me/findMeetingTimes"
    assert kwargs["json"]["meetingDuration"] == "PT1H"


def test_draft_email(connector: MS365Connector, mock_graph_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "123", "subject": "Test"}
    mock_graph_client.post.return_value = mock_response

    result = connector.execute("draft_email", {"to": "test@example.com", "subject": "Test", "body": "Hello"})

    assert result == {"id": "123", "subject": "Test"}
    mock_graph_client.post.assert_called_once()
    args, kwargs = mock_graph_client.post.call_args
    assert args[0] == "/me/messages"
    assert kwargs["json"]["subject"] == "Test"


def test_send_email(connector: MS365Connector, mock_graph_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_graph_client.post.return_value = mock_response

    result = connector.execute("send_email", {"id": "123"})

    assert result == {"status": "sent", "message_id": "123"}
    mock_graph_client.post.assert_called_once()
    args, _ = mock_graph_client.post.call_args
    assert args[0] == "/me/messages/123/send"


def test_send_email_missing_id(connector: MS365Connector) -> None:
    with pytest.raises(ToolExecutionError, match="Message ID is required"):
        connector.execute("send_email", {})


def test_execute_unknown_tool(connector: MS365Connector) -> None:
    with pytest.raises(ToolExecutionError, match="Unknown tool: unknown"):
        connector.execute("unknown", {})


def test_execute_failure(connector: MS365Connector, mock_graph_client: MagicMock) -> None:
    mock_graph_client.post.side_effect = Exception("API Error")

    with pytest.raises(ToolExecutionError, match="MS365 error: API Error"):
        connector.execute("send_email", {"id": "123"})


# --- Edge Case Tests ---


def test_find_meeting_slot_empty_attendees(connector: MS365Connector, mock_graph_client: MagicMock) -> None:
    """Test finding meeting slot with no attendees."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"meetingTimeSlots": []}
    mock_graph_client.post.return_value = mock_response

    result = connector.execute("find_meeting_slot", {"attendees": [], "duration": "PT30M"})

    assert result == {"meetingTimeSlots": []}
    args, kwargs = mock_graph_client.post.call_args
    assert kwargs["json"]["attendees"] == []


def test_api_http_error(connector: MS365Connector, mock_graph_client: MagicMock) -> None:
    """Test handling of HTTP error codes."""
    # Simulate a 401 Unauthorized
    request = Request("POST", "https://graph.microsoft.com/v1.0/me/messages")
    response = Response(401, request=request, text="Unauthorized")
    error = HTTPStatusError("401 Unauthorized", request=request, response=response)

    # We must mock raise_for_status to raise this error,
    # OR mock the side_effect of the post call if the client raises it immediately.
    # The current implementation calls raise_for_status() on the returned response object.

    mock_response_obj = MagicMock()
    mock_response_obj.raise_for_status.side_effect = error
    mock_graph_client.post.return_value = mock_response_obj

    with pytest.raises(ToolExecutionError, match="MS365 error: 401 Unauthorized"):
        connector.execute("send_email", {"id": "123"})


def test_api_malformed_response(connector: MS365Connector, mock_graph_client: MagicMock) -> None:
    """Test when API returns invalid JSON."""
    mock_response = MagicMock()
    # json() raising ValueError simulates malformed JSON body
    mock_response.json.side_effect = ValueError("Expecting value")
    mock_graph_client.post.return_value = mock_response

    with pytest.raises(ToolExecutionError, match="MS365 error: Expecting value"):
        connector.execute("draft_email", {"to": "a", "subject": "b", "body": "c"})


def test_complex_scenario_chain(connector: MS365Connector, mock_graph_client: MagicMock) -> None:
    """
    Simulate a chain: find slot -> draft email -> send email.
    Note: In unit tests we mock the state, but we can verify the sequence of calls.
    """
    # 1. Find Slot
    mock_response_slot = MagicMock()
    mock_response_slot.json.return_value = {"meetingTimeSlots": [{"start": "..."}]}

    # 2. Draft Email
    mock_response_draft = MagicMock()
    mock_response_draft.json.return_value = {"id": "draft_123"}

    # 3. Send Email
    mock_response_send = MagicMock()

    mock_graph_client.post.side_effect = [mock_response_slot, mock_response_draft, mock_response_send]

    # Execute Chain
    slot_res = connector.execute("find_meeting_slot", {"attendees": ["a@b.com"], "duration": "PT1H"})
    assert slot_res["meetingTimeSlots"]

    draft_res = connector.execute("draft_email", {"to": "a@b.com", "subject": "Meeting", "body": "Let's meet"})
    assert draft_res["id"] == "draft_123"

    send_res = connector.execute("send_email", {"id": draft_res["id"]})
    assert send_res["status"] == "sent"

    assert mock_graph_client.post.call_count == 3


def test_execute_with_user_context(connector: MS365Connector, mock_graph_client: MagicMock) -> None:
    """Test execution with user context injecting token."""
    user_context = UserContext(user_id="user1", email="u@e.com", groups=[], scopes=[], downstream_token="abc-123")
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "123"}
    mock_graph_client.post.return_value = mock_response

    connector.execute(
        "draft_email",
        {"to": "a", "subject": "b", "body": "c"},
        user_context=user_context,
    )

    args, kwargs = mock_graph_client.post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer abc-123"
