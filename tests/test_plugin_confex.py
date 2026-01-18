# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

import os

import pytest

from coreason_connect.config import AppConfig, PluginConfig
from coreason_connect.secrets import EnvSecretsProvider
from coreason_connect.server import CoreasonConnectServer

# Setup paths
FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__)) + "/fixtures"
LOCAL_LIBS_DIR = os.path.join(FIXTURES_DIR, "local_libs")
CONFEX_ADAPTER_PATH = os.path.join(LOCAL_LIBS_DIR, "adapters/confex_adapter.py")


@pytest.fixture
def confex_server(monkeypatch: pytest.MonkeyPatch) -> CoreasonConnectServer:
    """Create a server instance with the Confex plugin loaded."""
    # Ensure environment has secret
    monkeypatch.setenv("CONFEX_API_KEY", "test-key-123")

    config = AppConfig(
        plugins=[
            PluginConfig(
                id="confex", type="local_python", path=CONFEX_ADAPTER_PATH, description="Conference Intelligence"
            )
        ]
    )
    secrets = EnvSecretsProvider()
    return CoreasonConnectServer(config=config, secrets=secrets)


@pytest.mark.asyncio
async def test_confex_plugin_loading(confex_server: CoreasonConnectServer) -> None:
    """Test that the Confex plugin loads and registers tools."""
    # Check plugin registry
    assert "confex" in confex_server.plugins

    # Check tool registry
    tools = await confex_server._list_tools_handler()
    tool_names = [t.name for t in tools]
    assert "search_abstracts" in tool_names
    assert "get_session_details" in tool_names


@pytest.mark.asyncio
async def test_search_abstracts(confex_server: CoreasonConnectServer) -> None:
    """Test the search_abstracts tool."""
    # Call the tool
    results = await confex_server._call_tool_handler(
        "search_abstracts", {"conference_id": "conf_2023", "keywords": ["AI"]}
    )

    # Verify output
    assert len(results) == 1
    text_content = results[0]
    assert text_content.type == "text"
    assert "Advances in AI" in text_content.text
    assert "abs_123" in text_content.text


@pytest.mark.asyncio
async def test_get_session_details(confex_server: CoreasonConnectServer) -> None:
    """Test the get_session_details tool."""
    # Call the tool
    results = await confex_server._call_tool_handler("get_session_details", {"session_id": "sess_999"})

    # Verify output
    assert len(results) == 1
    assert "Keynote: The Future" in results[0].text  # type: ignore[union-attr]
    assert "Grand Ballroom" in results[0].text  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_confex_error_handling(confex_server: CoreasonConnectServer) -> None:
    """Test error handling in Confex tool."""
    # Call with invalid conference ID (mock raises error)
    results = await confex_server._call_tool_handler("search_abstracts", {"conference_id": "INVALID", "keywords": []})

    assert "Error: Tool 'search_abstracts' failed - Confex error: Invalid conference ID" in results[0].text  # type: ignore[union-attr]
