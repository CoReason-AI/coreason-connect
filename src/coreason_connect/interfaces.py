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
from typing import Any, Optional, Protocol, runtime_checkable

from coreason_identity.models import UserContext
from mcp.types import Tool  # noqa: F401

from coreason_connect.types import ToolDefinition

__all__ = ["SecretsProvider", "ConnectorProtocol", "ToolDefinition"]


@runtime_checkable
class SecretsProvider(Protocol):
    """Protocol for accessing secrets and credentials."""

    def get_secret(self, key: str) -> str:
        """Retrieve a simple secret (e.g. API key) by key.

        Args:
            key: The identifier of the secret to retrieve.

        Returns:
            The secret value as a string.

        Raises:
            KeyError: If the secret key is not found.
        """
        ...

    def get_user_credential(self, key: str) -> Any:
        """Retrieve a user credential (e.g. username/password object) by key.

        Args:
            key: The identifier of the credential to retrieve.

        Returns:
            The credential object.

        Raises:
            KeyError: If the credential key is not found.
        """
        ...


class ConnectorProtocol(ABC):
    """The contract that all adapters must fulfill."""

    def __init__(self, secrets: SecretsProvider) -> None:
        """Inject vault access at initialization.

        Args:
            secrets: The SecretsProvider instance to use for retrieving credentials.
        """
        self.secrets = secrets

    @abstractmethod
    def get_tools(self) -> list[ToolDefinition]:
        """Return list of available MCP tools wrapped in ToolDefinition.

        Returns:
            A list of ToolDefinition objects representing the tools exposed by this connector.
        """
        pass  # pragma: no cover

    @abstractmethod
    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        user_context: Optional[UserContext] = None,
    ) -> Any:
        """Execute the logic.

        Args:
            tool_name: The name of the tool to execute.
            arguments: A dictionary of arguments for the tool.
            user_context: The user context containing identity and tokens.

        Returns:
            The result of the tool execution.

        Raises:
            ToolExecutionError: If the tool execution fails.
        """
        pass  # pragma: no cover
