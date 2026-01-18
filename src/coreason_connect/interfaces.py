# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from mcp.types import Tool  # noqa: F401

from coreason_connect.types import ToolDefinition

__all__ = ["SecretsProvider", "ConnectorProtocol", "ToolDefinition"]


@runtime_checkable
class SecretsProvider(Protocol):
    """Protocol for accessing secrets and credentials."""

    def get_secret(self, key: str) -> str:
        """Retrieve a simple secret (e.g. API key) by key."""
        ...

    def get_user_credential(self, key: str) -> Any:
        """Retrieve a user credential (e.g. username/password object) by key."""
        ...


class ConnectorProtocol(ABC):
    """The contract that all adapters must fulfill."""

    def __init__(self, secrets: SecretsProvider) -> None:
        """Inject vault access at initialization."""
        self.secrets = secrets

    @abstractmethod
    def get_tools(self) -> list[ToolDefinition]:
        """Return list of available MCP tools wrapped in ToolDefinition."""
        pass  # pragma: no cover

    @abstractmethod
    def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Execute the logic."""
        pass  # pragma: no cover
