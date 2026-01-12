# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from typing import Any, List, Protocol, runtime_checkable

from coreason_connect.types import ToolCapability


@runtime_checkable
class SecretsProvider(Protocol):
    """
    Protocol for accessing secure credentials.
    Wraps coreason-vault logic.
    """

    def get(self, key: str) -> str:
        """
        Retrieve a secret by key.
        """
        ...  # pragma: no cover


@runtime_checkable
class CoreasonAdapter(Protocol):
    """
    Protocol that all local python adapters must implement.
    """

    def __init__(self, secrets_provider: SecretsProvider) -> None:
        """
        Initialize with a secrets provider.
        """
        ...  # pragma: no cover

    def get_capabilities(self) -> List[ToolCapability]:
        """
        Return a list of tools exposed by this adapter.
        """
        ...  # pragma: no cover

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        Execute a tool.
        """
        ...  # pragma: no cover
