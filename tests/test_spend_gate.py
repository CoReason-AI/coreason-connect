# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect


import pytest

from coreason_connect.server import CoreasonConnectServer
from tests.fixtures.mock_consequential_plugin import MockConsequentialPlugin


@pytest.mark.asyncio
async def test_spend_gate_interception() -> None:
    """Test that consequential tools are intercepted by the spend gate."""
    server = CoreasonConnectServer()

    # Inject our mock consequential plugin manually to bypass loader for this specific test
    mock_plugin = MockConsequentialPlugin(server.secrets)
    server.plugins["mock_consequential"] = mock_plugin

    # Register tools manually as _load_plugins is already called in __init__
    for tool_def in mock_plugin.get_tools():
        server.tool_registry[tool_def.name] = mock_plugin
        server.tool_definitions[tool_def.name] = tool_def

    # Test consequential tool
    result = await server._call_tool_handler("nuclear_launch", {})
    assert len(result) == 1
    assert result[0].type == "text"
    assert "Action suspended: Human approval required for nuclear_launch." in result[0].text

    # Test safe tool
    result_safe = await server._call_tool_handler("safe_tool", {})
    assert len(result_safe) == 1
    assert result_safe[0].type == "text"
    assert "OK" in result_safe[0].text
