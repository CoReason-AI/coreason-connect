# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from unittest.mock import MagicMock, patch

import pytest

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.server import CoreasonConnectServiceAsync
from tests.fixtures.mock_plugin import MockPlugin


@pytest.fixture
def mock_secrets() -> SecretsProvider:
    return MagicMock(spec=SecretsProvider)


@pytest.fixture
def server(mock_secrets: SecretsProvider) -> CoreasonConnectServiceAsync:
    return CoreasonConnectServiceAsync(secrets=mock_secrets)


@pytest.fixture
def mock_plugin(mock_secrets: SecretsProvider) -> MockPlugin:
    return MockPlugin(mock_secrets)


@pytest.mark.asyncio
async def test_duplicate_tool_name_warning(server: CoreasonConnectServiceAsync, mock_plugin: MockPlugin) -> None:
    """Test that a warning is logged when a duplicate tool name is encountered."""

    # Create a second plugin with the same tool name
    duplicate_plugin = MagicMock(spec=ConnectorProtocol)
    duplicate_plugin.get_tools.return_value = mock_plugin.get_tools()  # Same tools as mock_plugin

    # Mock load_all to return both
    server.plugin_loader.load_all = MagicMock(  # type: ignore[method-assign]
        return_value={"plugin1": mock_plugin, "plugin2": duplicate_plugin}
    )

    with patch("coreason_connect.server.logger") as mock_logger:
        server._load_plugins()

        # Check that warning was logged
        # "Duplicate tool name 'mock_echo' found in plugin 'plugin2'. Overwriting."
        # Note: order of iteration depends on dict order, so it might be plugin1 or plugin2 overwriting the other
        assert mock_logger.warning.call_count >= 1
        args, _ = mock_logger.warning.call_args
        assert "Duplicate tool name" in args[0]
        assert "Overwriting" in args[0]
