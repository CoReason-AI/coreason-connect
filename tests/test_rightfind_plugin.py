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
from coreason_connect.interfaces import SecretsProvider
from coreason_connect.server import CoreasonConnectServer


# Mock secrets provider
class MockSecrets(SecretsProvider):
    def get_secret(self, key: str) -> str:
        return "secret_value"

    def get_user_credential(self, key: str) -> str:
        return "user_cred"


@pytest.mark.asyncio
async def test_rightfind_plugin_loading_and_execution() -> None:
    """
    Integration test for the RightFind adapter.
    Verifies:
    1. Plugin loading from disk.
    2. Sibling import injection (import rightfind_client).
    3. Tool registration.
    4. Execution of standard tools.
    5. Execution of consequential tools (Spend Gate).
    6. Error handling.
    """

    # Path to the fixture adapter
    cwd = os.getcwd()
    adapter_path = os.path.join(cwd, "tests/fixtures/local_libs/adapters/rf_adapter.py")

    config = AppConfig(
        plugins=[
            PluginConfig(
                id="rightfind",
                type="local_python",
                path=adapter_path,
                description="RightFind Adapter Fixture",
            )
        ]
    )

    secrets = MockSecrets()
    server = CoreasonConnectServer(config=config, secrets=secrets)

    # Verify plugin loaded
    assert "rightfind" in server.plugins
    assert "search_literature" in server.tool_registry
    assert "purchase_article" in server.tool_registry

    # Verify tool metadata
    purchase_tool = server.tool_registry["purchase_article"]
    assert purchase_tool.is_consequential is True

    # 1. Test standard execution (search_literature)
    # This verifies the adapter successfully imported RFEClient and called it.
    result_search = await server._call_tool_handler("search_literature", {"query": "science"})
    assert len(result_search) == 1
    assert "Novel Inhibitors" in result_search[0].text  # type: ignore[union-attr]

    # 2. Test Spend Gate (purchase_article)
    # Should return suspension message, NOT execute the order
    result_purchase = await server._call_tool_handler("purchase_article", {"content_id": "123"})
    assert len(result_purchase) == 1
    assert "Action suspended: Human approval required" in result_purchase[0].text  # type: ignore[union-attr]

    # 3. Test Error Handling (mapped exception)
    # We trigger the mocked RightFindError by passing "fail"
    result_error = await server._call_tool_handler("search_literature", {"query": "fail"})
    assert len(result_error) == 1
    # The server catches ToolExecutionError and returns a formatted message
    assert "Error: Tool 'search_literature' failed - RightFind error: Search failed" in result_error[0].text  # type: ignore[union-attr]


class BrokenSecrets(SecretsProvider):
    def get_secret(self, key: str) -> str:
        raise ValueError("Secret access denied")

    def get_user_credential(self, key: str) -> str:
        raise ValueError("User credential access denied")


@pytest.mark.asyncio
async def test_plugin_init_failure_missing_secrets() -> None:
    """Test that the server handles plugin initialization failure gracefully."""
    cwd = os.getcwd()
    adapter_path = os.path.join(cwd, "tests/fixtures/local_libs/adapters/rf_adapter.py")

    config = AppConfig(
        plugins=[
            PluginConfig(
                id="rightfind_broken",
                type="local_python",
                path=adapter_path,
                description="Broken Secrets Plugin",
            )
        ]
    )

    # Secrets provider that raises on access (used in adapter __init__)
    secrets = BrokenSecrets()

    # The server should catch the exception during loading
    server = CoreasonConnectServer(config=config, secrets=secrets)

    # Plugin should NOT be loaded
    assert "rightfind_broken" not in server.plugins
    assert "search_literature" not in server.tool_registry


@pytest.mark.asyncio
async def test_complex_workflow() -> None:
    """
    Test a simulated complex workflow: Search -> Check Rights -> Purchase.
    """
    cwd = os.getcwd()
    adapter_path = os.path.join(cwd, "tests/fixtures/local_libs/adapters/rf_adapter.py")
    config = AppConfig(
        plugins=[
            PluginConfig(
                id="rightfind",
                type="local_python",
                path=adapter_path,
            )
        ]
    )
    server = CoreasonConnectServer(config=config, secrets=MockSecrets())

    # Step 1: Search
    search_res = await server._call_tool_handler("search_literature", {"query": "science"})
    # Assume result is a JSON-like string we can parse or check
    # "[{'title': 'Novel Inhibitors', 'doi': '10.1000/1'}]"
    assert "10.1000/1" in search_res[0].text  # type: ignore[union-attr]

    # Step 2: Check Rights (simulated based on previous result)
    rights_res = await server._call_tool_handler("check_rights", {"doi": "10.1000/1"})
    assert "GRANT" in rights_res[0].text  # type: ignore[union-attr]

    # Step 3: Purchase (Spend Gate Trigger)
    purchase_res = await server._call_tool_handler("purchase_article", {"content_id": "10.1000/1"})
    assert "Action suspended" in purchase_res[0].text  # type: ignore[union-attr]
