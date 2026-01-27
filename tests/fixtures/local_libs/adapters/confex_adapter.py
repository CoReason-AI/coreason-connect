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

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.types import ToolDefinition, ToolExecutionError

# This import relies on PluginLoader injecting .../local_libs into sys.path
try:
    from confex_client import ConfexClient, ConfexError
except ImportError as e:
    raise ImportError(f"Failed to import confex_client: {e}") from e


class ConfexAdapter(ConnectorProtocol):
    """Adapter for the Confex Conference Intelligence system."""

    def __init__(self, secrets: SecretsProvider):
        super().__init__(secrets)
        # Confex might use an API key
        try:
            api_key = self.secrets.get_secret("CONFEX_API_KEY")
        except KeyError:
            api_key = None
        self.client = ConfexClient(api_key=api_key)

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="search_abstracts",
                tool=Tool(
                    name="search_abstracts",
                    description="Search conference abstracts by keywords.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "conference_id": {"type": "string", "description": "ID of the conference"},
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of search keywords",
                            },
                        },
                        "required": ["conference_id", "keywords"],
                    },
                ),
            ),
            ToolDefinition(
                name="get_session_details",
                tool=Tool(
                    name="get_session_details",
                    description="Get details for a specific conference session.",
                    inputSchema={
                        "type": "object",
                        "properties": {"session_id": {"type": "string", "description": "Unique session identifier"}},
                        "required": ["session_id"],
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
        args = arguments or {}
        try:
            if tool_name == "search_abstracts":
                return self.client.search_abstracts(
                    conference_id=args.get("conference_id", ""), keywords=args.get("keywords", [])
                )
            elif tool_name == "get_session_details":
                return self.client.get_session_details(session_id=args.get("session_id", ""))
            else:
                raise ToolExecutionError(f"Unknown tool: {tool_name}")
        except ConfexError as e:
            raise ToolExecutionError(f"Confex error: {str(e)}", retryable=False) from e
        except Exception as e:
            raise ToolExecutionError(f"Unexpected error: {str(e)}") from e
