# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from abc import abstractmethod
from typing import Any, Optional

import pytest
from coreason_identity.models import UserContext
from mcp.types import Tool

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.types import ToolDefinition


class MockSecretsProvider:
    """Mock implementation of SecretsProvider."""

    def get_secret(self, key: str) -> str:
        return f"secret_for_{key}"

    def get_user_credential(self, key: str) -> Any:
        return {"user": "test", "pass": "test"}


class ConcreteConnector(ConnectorProtocol):
    """Concrete implementation of ConnectorProtocol."""

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="test_tool",
                tool=Tool(
                    name="test_tool",
                    description="A test tool",
                    inputSchema={"type": "object", "properties": {}},
                ),
            )
        ]

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        user_context: Optional[UserContext] = None,
    ) -> Any:
        args_str = str(arguments) if arguments else "None"
        return f"executed_{tool_name}_with_{args_str}"


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
    assert isinstance(tools[0], ToolDefinition)
    assert tools[0].name == "test_tool"

    result = connector.execute("test_tool", {"foo": "bar"})
    assert result == "executed_test_tool_with_{'foo': 'bar'}"


def test_secrets_provider_protocol_runtime() -> None:
    """Ensure runtime_checkable works for SecretsProvider."""
    # 1. Valid implementation
    valid = MockSecretsProvider()
    assert isinstance(valid, SecretsProvider)

    # 2. Invalid implementation (missing methods)
    class InvalidProvider:
        def get_secret(self, key: str) -> str:
            return "k"

    invalid = InvalidProvider()
    assert not isinstance(invalid, SecretsProvider)

    # 3. Invalid implementation (missing all methods)
    class EmptyProvider:
        pass

    empty = EmptyProvider()
    assert not isinstance(empty, SecretsProvider)


def test_complex_connector_scenario() -> None:
    """Test a connector that uses secrets to determine available tools."""

    class DynamicConnector(ConnectorProtocol):
        def get_tools(self) -> list[ToolDefinition]:
            # Simulate checking a license key from secrets
            license_key = self.secrets.get_secret("LICENSE_KEY")
            tools = []
            if license_key == "secret_for_LICENSE_KEY":
                tools.append(
                    ToolDefinition(
                        name="premium_tool",
                        tool=Tool(name="premium_tool", inputSchema={}, description="Premium"),
                    )
                )
            return tools

        def execute(
            self,
            tool_name: str,
            arguments: dict[str, Any] | None = None,
            user_context: Optional[UserContext] = None,
        ) -> Any:
            return "ok"

    secrets = MockSecretsProvider()
    connector = DynamicConnector(secrets)

    tools = connector.get_tools()
    assert len(tools) == 1
    assert tools[0].name == "premium_tool"


def test_connector_argument_defaults() -> None:
    """Test that execute handles None arguments as per signature default."""
    secrets = MockSecretsProvider()
    connector = ConcreteConnector(secrets)

    # Call without arguments provided
    result = connector.execute("test_tool")
    assert "with_None" in result

    # Call with explicit None
    result_none = connector.execute("test_tool", None)
    assert "with_None" in result_none


def test_connector_inheritance_chain() -> None:
    """Test multi-level inheritance for connectors."""

    class BaseFeatureConnector(ConnectorProtocol):
        """Intermediate class adding shared helper methods."""

        def helper(self) -> str:
            return "helper"

        @abstractmethod
        def specific_task(self) -> None:
            pass

    class FinalConnector(BaseFeatureConnector):
        def get_tools(self) -> list[ToolDefinition]:
            return []

        def execute(
            self,
            tool_name: str,
            arguments: dict[str, Any] | None = None,
            user_context: Optional[UserContext] = None,
        ) -> Any:
            return self.helper()

        def specific_task(self) -> None:
            pass

    secrets = MockSecretsProvider()
    connector = FinalConnector(secrets)

    assert isinstance(connector, ConnectorProtocol)
    assert isinstance(connector, BaseFeatureConnector)
    assert connector.execute("foo") == "helper"
