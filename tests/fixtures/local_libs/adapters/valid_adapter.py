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
from coreason_connect.types import ToolDefinition

# This import tests that the loader correctly sets up sys.path
try:
    import rightfind_client
except ImportError:
    rightfind_client = None


class ValidAdapter(ConnectorProtocol):
    def __init__(self, secrets: SecretsProvider):
        super().__init__(secrets)
        self.client_loaded = rightfind_client is not None

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="get_data",
                tool=Tool(
                    name="get_data",
                    description="Retrieves data",
                    inputSchema={"type": "object", "properties": {}},
                ),
            )
        ]

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        user_context: Optional[UserContext] = None,
    ) -> Any:
        if tool_name == "check_import":
            return self.client_loaded
        if tool_name == "get_data":
            return {"data": "test_data"}
        return "executed"
