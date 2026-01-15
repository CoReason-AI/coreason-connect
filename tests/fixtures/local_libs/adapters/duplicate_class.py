from typing import Any

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.types import ToolDefinition


class ValidAdapter(ConnectorProtocol):
    """
    This class has the same name as the one in valid_adapter.py.
    This tests that the loader handles module isolation correctly.
    """

    def __init__(self, secrets: SecretsProvider):
        super().__init__(secrets)
        self.id = "duplicate"

    def get_tools(self) -> list[ToolDefinition]:
        return []

    def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        return self.id
