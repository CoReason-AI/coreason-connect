from typing import Any

from mcp.types import Tool

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.types import ToolDefinition


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
            )
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        if tool_name == "mock_echo":
            if not arguments or "message" not in arguments:
                raise ValueError("Missing 'message' argument")
            return f"Echo: {arguments['message']}"
        raise ValueError(f"Unknown tool: {tool_name}")
