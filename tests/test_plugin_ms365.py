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
from coreason_connect.interfaces import SecretsProvider
from coreason_connect.plugins.ms365 import MS365Connector
from coreason_connect.types import ToolExecutionError


@pytest.fixture
def mock_secrets() -> SecretsProvider:
    return MagicMock(spec=SecretsProvider)


@pytest.fixture
def mock_graph_client() -> MagicMock:
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
