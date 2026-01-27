# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from typing import Any, Optional

from coreason_identity.models import UserContext
from mcp.types import Tool
from msgraph_core import APIVersion, GraphClientFactory

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.types import ToolDefinition, ToolExecutionError
from coreason_connect.utils.logger import logger


class MS365Connector(ConnectorProtocol):
    """Native plugin for Microsoft 365 integration using msgraph-core."""

    def __init__(self, secrets: SecretsProvider) -> None:
        """Initialize the MS365 connector.

        Args:
            secrets: The secrets provider for obtaining credentials.
        """
        super().__init__(secrets)
        # In a real implementation, we would set up the authentication provider here
        # using secrets (e.g., Azure Identity credentials).
        # For now, we initialize a basic client.
        try:
            # We are using a simple anonymous client for the structure,
            # as the actual auth provider logic depends on azure-identity which wasn't requested.
            # In tests, we will mock this client.
            self.client = GraphClientFactory.create_with_default_middleware(api_version=APIVersion.v1)
        except Exception as e:
            logger.error(f"Failed to initialize Graph client: {e}")
            raise

    def get_tools(self) -> list[ToolDefinition]:
        """Return a list of available tools.

        Returns:
            list[ToolDefinition]: A list of ToolDefinition objects.
        """
        return [
            ToolDefinition(
                name="find_meeting_slot",
                tool=Tool(
                    name="find_meeting_slot",
                    description="Find meeting times for attendees.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "attendees": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of attendee email addresses",
                            },
                            "duration": {
                                "type": "string",
                                "description": "Duration of the meeting (e.g., 'PT1H' for 1 hour)",
                            },
                        },
                        "required": ["attendees", "duration"],
                    },
                ),
            ),
            ToolDefinition(
                name="draft_email",
                tool=Tool(
                    name="draft_email",
                    description="Create a draft email.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Recipient email address"},
                            "subject": {"type": "string", "description": "Email subject"},
                            "body": {"type": "string", "description": "Email body content"},
                        },
                        "required": ["to", "subject", "body"],
                    },
                ),
            ),
            ToolDefinition(
                name="send_email",
                is_consequential=True,
                tool=Tool(
                    name="send_email",
                    description="Send a draft email.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "The ID of the draft email to send"},
                        },
                        "required": ["id"],
                    },
                ),
            ),
        ]

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        user_context: Optional[UserContext] = None,
    ) -> Any:
        """Execute an MS365 tool.

        Args:
            tool_name: The name of the tool to execute.
            arguments: A dictionary of arguments for the tool.
            user_context: The user context containing identity and tokens.

        Returns:
            Any: The result of the tool execution.

        Raises:
            ToolExecutionError: If the tool fails or is unknown.
        """
        args = arguments or {}
        try:
            if tool_name == "find_meeting_slot":
                return self._find_meeting_slot(args, user_context)
            elif tool_name == "draft_email":
                return self._draft_email(args, user_context)
            elif tool_name == "send_email":
                return self._send_email(args, user_context)
            else:
                raise ToolExecutionError(f"Unknown tool: {tool_name}")
        except Exception as e:
            if isinstance(e, ToolExecutionError):
                raise
            raise ToolExecutionError(f"MS365 error: {str(e)}") from e

    def _get_request_headers(self, user_context: Optional[UserContext]) -> dict[str, str]:
        """Get the headers for the request, injecting the token if available.

        Args:
            user_context: The user context containing identity and tokens.

        Returns:
            dict[str, str]: The headers dictionary.
        """
        headers = {}
        if user_context and user_context.downstream_token:
            headers["Authorization"] = f"Bearer {user_context.downstream_token.get_secret_value()}"
        else:
            logger.warning("Delegated Identity is missing; using Service Identity.")
        return headers

    def _find_meeting_slot(self, args: dict[str, Any], user_context: Optional[UserContext] = None) -> Any:
        """Find meeting times.

        Args:
            args: Dictionary containing 'attendees' and 'duration'.
            user_context: The user context containing identity and tokens.

        Returns:
            Any: The JSON response from the Graph API.
        """
        attendees = args.get("attendees", [])
        duration = args.get("duration", "PT30M")

        payload = {
            "attendees": [{"emailAddress": {"address": email}, "type": "required"} for email in attendees],
            "timeConstraint": {
                "activityDomain": "work",
                "timeSlots": [
                    {
                        "start": {"dateTime": "2023-01-01T09:00:00", "timeZone": "UTC"},
                        "end": {"dateTime": "2023-01-01T17:00:00", "timeZone": "UTC"},
                    }
                ],
            },
            "meetingDuration": duration,
        }
        # This is a synchronous call using the wrapped httpx client
        headers = self._get_request_headers(user_context)
        response = self.client.post("/me/findMeetingTimes", json=payload, headers=headers)
        response.raise_for_status()
        return dict(response.json())

    def _draft_email(self, args: dict[str, Any], user_context: Optional[UserContext] = None) -> Any:
        """Draft an email.

        Args:
            args: Dictionary containing 'to', 'subject', and 'body'.
            user_context: The user context containing identity and tokens.

        Returns:
            Any: The JSON response from the Graph API.
        """
        to_email = args.get("to")
        subject = args.get("subject")
        body = args.get("body")

        payload = {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to_email}}],
        }

        headers = self._get_request_headers(user_context)
        response = self.client.post("/me/messages", json=payload, headers=headers)
        response.raise_for_status()
        return dict(response.json())

    def _send_email(self, args: dict[str, Any], user_context: Optional[UserContext] = None) -> Any:
        """Send a draft email.

        Args:
            args: Dictionary containing 'id' of the message.
            user_context: The user context containing identity and tokens.

        Returns:
            dict[str, str]: A status dictionary.

        Raises:
            ToolExecutionError: If 'id' is missing.
        """
        message_id = args.get("id")
        if not message_id:
            raise ToolExecutionError("Message ID is required")

        headers = self._get_request_headers(user_context)
        response = self.client.post(f"/me/messages/{message_id}/send", headers=headers)
        response.raise_for_status()
        # The send endpoint usually returns 202 Accepted and no content,
        # but we return a success message
        return {"status": "sent", "message_id": message_id}
