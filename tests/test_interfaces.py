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

import pytest
from mcp.types import Tool

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider


class MockSecretsProvider:
    """Mock implementation of SecretsProvider."""

    def get_secret(self, key: str) -> str:
        return f"secret_for_{key}"

    def get_user_credential(self, key: str) -> Any:
        return {"user": "test", "pass": "test"}


class ConcreteConnector(ConnectorProtocol):
    """Concrete implementation of ConnectorProtocol."""

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="test_tool",
                description="A test tool",
                inputSchema={"type": "object", "properties": {}},
            )
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        return f"executed_{tool_name}"


def test_cannot_instantiate_abstract_connector() -> None:
    """Ensure ConnectorProtocol cannot be instantiated directly."""
    secrets = MockSecretsProvider()
    with pytest.raises(TypeError):
        ConnectorProtocol(secrets)  # type: ignore


def test_cannot_instantiate_incomplete_connector() -> None:
    """Ensure a subclass missing abstract methods cannot be instantiated."""

    class IncompleteConnector(ConnectorProtocol):
        pass

    secrets = MockSecretsProvider()
    with pytest.raises(TypeError):
        IncompleteConnector(secrets)  # type: ignore


def test_concrete_connector_instantiation() -> None:
    """Ensure a properly implemented connector works."""
    secrets = MockSecretsProvider()
    connector = ConcreteConnector(secrets)

    assert isinstance(connector, ConnectorProtocol)
    assert connector.secrets is secrets


def test_concrete_connector_methods() -> None:
    """Ensure methods of the concrete connector work as expected."""
    secrets = MockSecretsProvider()
    connector = ConcreteConnector(secrets)

    tools = connector.get_tools()
    assert len(tools) == 1
    assert isinstance(tools[0], Tool)
    assert tools[0].name == "test_tool"

    result = connector.execute("test_tool", {})
    assert result == "executed_test_tool"


def test_secrets_provider_protocol() -> None:
    """Ensure MockSecretsProvider satisfies SecretsProvider protocol (static check mostly)."""
    # Runtime check
    secrets = MockSecretsProvider()
    assert isinstance(
        secrets, SecretsProvider
    )  # This works with runtime_checkable if added, but Protocol by default isn't runtime checkable without decoration.
    # Actually Protocol without @runtime_checkable won't work with isinstance.
    # However, for Python typing, it matters.
    # We can check signatures manually or just rely on Mypy.

    assert hasattr(secrets, "get_secret")
    assert hasattr(secrets, "get_user_credential")
    assert secrets.get_secret("foo") == "secret_for_foo"
