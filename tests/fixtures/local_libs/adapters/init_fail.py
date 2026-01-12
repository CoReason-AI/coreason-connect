from typing import Any

from mcp.types import Tool

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider


class InitFailAdapter(ConnectorProtocol):
    def __init__(self, secrets: SecretsProvider):
        super().__init__(secrets)
        raise ValueError("Simulated initialization failure")

    def get_tools(self) -> list[Tool]:
        return []

    def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        return None
