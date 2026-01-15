from typing import Any

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
        return []

    def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        if tool_name == "check_import":
            return self.client_loaded
        return "executed"
