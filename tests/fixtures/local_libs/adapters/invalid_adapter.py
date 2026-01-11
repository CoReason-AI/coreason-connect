from typing import Any

from coreason_connect.interfaces import SecretsProvider


class InvalidAdapter:
    """Does not inherit from ConnectorProtocol"""

    def __init__(self, secrets: SecretsProvider):
        pass

    def get_tools(self) -> list[Any]:
        return []

    def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        return "invalid"
