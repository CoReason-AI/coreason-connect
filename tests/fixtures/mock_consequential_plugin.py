from typing import Any

from mcp.types import Tool

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.types import ToolDefinition


class MockConsequentialPlugin(ConnectorProtocol):
    """A mock plugin with a consequential tool."""

    def __init__(self, secrets: SecretsProvider) -> None:
        super().__init__(secrets)

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="nuclear_launch",
                tool=Tool(
                    name="nuclear_launch",
                    description="Launches a nuke.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                is_consequential=True,
            ),
            ToolDefinition(
                name="safe_tool",
                tool=Tool(
                    name="safe_tool",
                    description="A safe tool.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                is_consequential=False,
            ),
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        if tool_name == "nuclear_launch":
            return "BOOM"
        if tool_name == "safe_tool":
            return "OK"
        raise ValueError(f"Unknown tool: {tool_name}")
