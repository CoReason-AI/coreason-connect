# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

import json
import os

import pytest

from coreason_connect.config import AppConfig, PluginConfig
from coreason_connect.secrets import EnvSecretsProvider
from coreason_connect.server import CoreasonConnectServiceAsync

# Setup paths
FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__)) + "/fixtures"
LOCAL_LIBS_DIR = os.path.join(FIXTURES_DIR, "local_libs")
CONFEX_ADAPTER_PATH = os.path.join(LOCAL_LIBS_DIR, "adapters/confex_adapter.py")


@pytest.fixture
def confex_server(monkeypatch: pytest.MonkeyPatch) -> CoreasonConnectServiceAsync:
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
    return CoreasonConnectServiceAsync(config=config, secrets=secrets)


@pytest.mark.asyncio
async def test_confex_plugin_loading(confex_server: CoreasonConnectServiceAsync) -> None:
    """Test that the Confex plugin loads and registers tools."""
    # Check plugin registry
    assert "confex" in confex_server.plugins

    # Check tool registry
    tools = await confex_server._list_tools_handler()
    tool_names = [t.name for t in tools]
    assert "search_abstracts" in tool_names
    assert "get_session_details" in tool_names


@pytest.mark.asyncio
async def test_search_abstracts(confex_server: CoreasonConnectServiceAsync) -> None:
    """Test the search_abstracts tool."""
    # Call the tool
    results = await confex_server._call_tool_handler(
        "search_abstracts", {"conference_id": "conf_2023", "keywords": ["AI"]}
    )

    # Verify output
    assert len(results) == 1
    assert "Advances in AI" in results[0].text  # type: ignore[union-attr]
    assert "abs_123" in results[0].text  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_get_session_details(confex_server: CoreasonConnectServiceAsync) -> None:
    """Test the get_session_details tool."""
    # Call the tool
    results = await confex_server._call_tool_handler("get_session_details", {"session_id": "sess_999"})

    # Verify output
    assert len(results) == 1
    assert "Keynote: The Future" in results[0].text  # type: ignore[union-attr]
    assert "Grand Ballroom" in results[0].text  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_confex_error_handling(confex_server: CoreasonConnectServiceAsync) -> None:
    """Test error handling in Confex tool."""
    # Call with invalid conference ID (mock raises error)
    results = await confex_server._call_tool_handler("search_abstracts", {"conference_id": "INVALID", "keywords": []})

    assert "Error: Tool 'search_abstracts' failed - Confex error: Invalid conference ID" in results[0].text  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_search_abstracts_empty(confex_server: CoreasonConnectServiceAsync) -> None:
    """Test search_abstracts returning no results."""
    # The mock client returns [] for conference_id="EMPTY"
    results = await confex_server._call_tool_handler(
        "search_abstracts", {"conference_id": "EMPTY", "keywords": ["nothing"]}
    )

    assert len(results) == 1
    assert results[0].text == "[]"  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_initialization_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the adapter initializes gracefully without an API key."""
    # Remove the key
    monkeypatch.delenv("CONFEX_API_KEY", raising=False)

    config = AppConfig(
        plugins=[
            PluginConfig(
                id="confex", type="local_python", path=CONFEX_ADAPTER_PATH, description="Conference Intelligence"
            )
        ]
    )
    secrets = EnvSecretsProvider()

    # This should not raise an exception
    server = CoreasonConnectServiceAsync(config=config, secrets=secrets)
    assert "confex" in server.plugins

    # Tools should still work (mock client doesn't check key strictly, but we verify it doesn't crash)
    results = await server._call_tool_handler("search_abstracts", {"conference_id": "conf_2023", "keywords": ["AI"]})
    assert len(results) == 1
    assert "Advances in AI" in results[0].text  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_extra_arguments(confex_server: CoreasonConnectServiceAsync) -> None:
    """Test robustness against extra arguments."""
    # Extra arguments should be ignored by the adapter or safely passed
    # (mock accepts kwargs in execute but only uses specific ones)
    results = await confex_server._call_tool_handler(
        "get_session_details", {"session_id": "sess_999", "extraneous_param": "should_be_ignored"}
    )

    assert len(results) == 1
    assert "Keynote: The Future" in results[0].text  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_complex_search_and_retrieve_flow(confex_server: CoreasonConnectServiceAsync) -> None:
    """Simulate a workflow: Search -> Extract ID -> Get Details."""
    # 1. Search
    search_results = await confex_server._call_tool_handler(
        "search_abstracts", {"conference_id": "conf_2023", "keywords": ["AI"]}
    )

    # Parse result
    data = json.loads(search_results[0].text)  # type: ignore[union-attr]
    assert len(data) > 0
    # In a real scenario, we'd pick an ID from here.
    # Our mock search returns 'abs_123', but our mock details knows 'sess_999'.
    # Let's pretend the agent decided to lookup 'sess_999' based on external knowledge or a different search.

    target_id = "sess_999"

    # 2. Get Details
    detail_results = await confex_server._call_tool_handler("get_session_details", {"session_id": target_id})

    details = json.loads(detail_results[0].text)  # type: ignore[union-attr]
    assert details["id"] == target_id
    assert details["location"] == "Grand Ballroom"
