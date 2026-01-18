# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from typing import Any

from mcp.types import Tool

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.types import ToolDefinition, ToolExecutionError

# This import works because the PluginLoader injects the parent directory into sys.path
try:
    from rightfind_client.rfe import RFEClient, RightFindError
    from rightfind_client.rights_advisory import RightsAdvisoryClient
except ImportError as e:
    raise ImportError(f"Failed to import rightfind_client: {e}") from e


class RightFindAdapter(ConnectorProtocol):
    """Adapter for the proprietary RightFind library."""

    def __init__(self, secrets: SecretsProvider):
        super().__init__(secrets)
        # In a real app, we would fetch creds here.
        # For this fixture, we pass None as the mock client doesn't verify them.
        user = self.secrets.get_user_credential("RF_USER")
        self.rfe = RFEClient(username=user, password=user)
        self.advisor = RightsAdvisoryClient(username=user, password=user)

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="search_literature",
                tool=Tool(
                    name="search_literature",
                    description="Search for scientific literature.",
                    inputSchema={
                        "type": "object",
                        "properties": {"query": {"type": "string", "description": "Search query"}},
                        "required": ["query"],
                    },
                ),
            ),
            ToolDefinition(
                name="check_rights",
                tool=Tool(
                    name="check_rights",
                    description="Check copyright permissions for a DOI.",
                    inputSchema={
                        "type": "object",
                        "properties": {"doi": {"type": "string", "description": "The DOI to check"}},
                        "required": ["doi"],
                    },
                ),
            ),
            ToolDefinition(
                name="purchase_article",
                is_consequential=True,
                tool=Tool(
                    name="purchase_article",
                    description="Purchase a scientific article.",
                    inputSchema={
                        "type": "object",
                        "properties": {"content_id": {"type": "string", "description": "The ID of the content to buy"}},
                        "required": ["content_id"],
                    },
                ),
            ),
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        args = arguments or {}
        try:
            if tool_name == "search_literature":
                return self.rfe.subclients.search(args.get("query"))
            elif tool_name == "check_rights":
                return self.advisor.check_rights(args.get("doi"))
            elif tool_name == "purchase_article":
                return self.rfe.subclients.orders(args.get("content_id"))
            else:
                raise ToolExecutionError(f"Unknown tool: {tool_name}")
        except RightFindError as e:
            raise ToolExecutionError(f"RightFind error: {str(e)}", retryable=False) from e
        except Exception as e:
            raise ToolExecutionError(f"Unexpected error: {str(e)}") from e
