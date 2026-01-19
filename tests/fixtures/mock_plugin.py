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

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.types import ToolDefinition
from mcp.types import Tool


class MockPlugin(ConnectorProtocol):
    """A mock plugin for testing purposes."""

    def __init__(self, secrets: SecretsProvider) -> None:
        super().__init__(secrets)

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="mock_echo",
                tool=Tool(
                    name="mock_echo",
                    description="Echoes the input.",
                    inputSchema={
                        "type": "object",
                        "properties": {"message": {"type": "string"}},
                        "required": ["message"],
                    },
                ),
                is_consequential=False,
            ),
            ToolDefinition(
                name="mock_dangerous",
                tool=Tool(
                    name="mock_dangerous",
                    description="A dangerous tool.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                is_consequential=True,
            ),
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        if tool_name == "mock_echo":
            if not arguments or "message" not in arguments:
                raise ValueError("Missing 'message' argument")
            return f"Echo: {arguments['message']}"
        if tool_name == "mock_dangerous":
            return "DANGEROUS EXECUTION"
        raise ValueError(f"Unknown tool: {tool_name}")
