# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from unittest.mock import MagicMock

import pytest

from coreason_connect.interfaces import SecretsProvider
from coreason_connect.server import CoreasonConnectService
from tests.fixtures.mock_plugin import MockPlugin


@pytest.fixture
def mock_secrets() -> SecretsProvider:
    return MagicMock(spec=SecretsProvider)


@pytest.fixture
def sync_service(mock_secrets: SecretsProvider) -> CoreasonConnectService:
    return CoreasonConnectService(secrets=mock_secrets)


@pytest.fixture
def mock_plugin(mock_secrets: SecretsProvider) -> MockPlugin:
    return MockPlugin(mock_secrets)


def test_service_initialization(sync_service: CoreasonConnectService) -> None:
    """Test that the service facade initializes correctly."""
    assert sync_service._async is not None
    assert sync_service._async.name == "coreason-connect"


def test_service_context_manager(sync_service: CoreasonConnectService) -> None:
    """Test that the service facade works as a context manager."""
    with sync_service as svc:
        assert svc is sync_service


def test_get_all_tools(sync_service: CoreasonConnectService, mock_plugin: MockPlugin) -> None:
    """Test get_all_tools synchronously."""
    # Setup
    sync_service._async.plugins = {"mock": mock_plugin}
    for tool_def in mock_plugin.get_tools():
        sync_service._async.plugin_registry[tool_def.name] = mock_plugin
        sync_service._async.tool_registry[tool_def.name] = tool_def

    tools = sync_service.get_all_tools()
    assert len(tools) == 2


def test_execute_tool(sync_service: CoreasonConnectService, mock_plugin: MockPlugin) -> None:
    """Test execute_tool synchronously."""
    # Setup
    sync_service._async.plugins = {"mock": mock_plugin}
    for tool_def in mock_plugin.get_tools():
        sync_service._async.plugin_registry[tool_def.name] = mock_plugin
        sync_service._async.tool_registry[tool_def.name] = tool_def

    result = sync_service.execute_tool("mock_echo", {"message": "Sync"})
    assert result == "Echo: Sync"


def test_execute_tool_spend_gate(sync_service: CoreasonConnectService, mock_plugin: MockPlugin) -> None:
    """Test execute_tool with spend gate interception."""
    # Setup
    sync_service._async.plugins = {"mock": mock_plugin}
    for tool_def in mock_plugin.get_tools():
        sync_service._async.plugin_registry[tool_def.name] = mock_plugin
        sync_service._async.tool_registry[tool_def.name] = tool_def

    result = sync_service.execute_tool("mock_dangerous", {})
    assert "Action suspended: Human approval required for mock_dangerous." in result


def test_execute_tool_not_found(sync_service: CoreasonConnectService) -> None:
    """Test execute_tool when tool is not found."""
    with pytest.raises(ValueError, match="Tool 'non_existent' not found."):
        sync_service.execute_tool("non_existent", {})


def test_execute_tool_exception(sync_service: CoreasonConnectService, mock_plugin: MockPlugin) -> None:
    """Test execute_tool when plugin raises exception."""
    # Setup
    mock_plugin.execute = MagicMock(side_effect=Exception("Plugin crash"))  # type: ignore[method-assign]
    sync_service._async.plugins = {"mock": mock_plugin}
    for tool_def in mock_plugin.get_tools():
        sync_service._async.plugin_registry[tool_def.name] = mock_plugin
        sync_service._async.tool_registry[tool_def.name] = tool_def

    with pytest.raises(Exception, match="Plugin crash"):
        sync_service.execute_tool("mock_echo", {})
