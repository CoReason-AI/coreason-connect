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
from typing import Any

import pytest

from coreason_connect.config import load_config
from coreason_connect.interfaces import SecretsProvider
from coreason_connect.loader import PluginLoader
from tests.test_loader import MockSecrets


@pytest.fixture
def mock_secrets() -> SecretsProvider:
    return MockSecrets()

@pytest.fixture
def valid_plugin(mock_secrets: SecretsProvider) -> Any:
    """Load and return the valid-plugin instance."""
    cwd = os.getcwd()
    config_path = os.path.join(cwd, "tests/fixtures/connectors.yaml")
    config = load_config(config_path)
    loader = PluginLoader(config, mock_secrets)
    plugins = loader.load_all()
    return plugins["valid-plugin"]

def test_valid_adapter_extraneous_arguments(valid_plugin: Any) -> None:
    """
    Edge Case: Verify that the adapter handles extraneous arguments gracefully.
    It should not crash and should still execute the core logic.
    """
    # Pass 'extra_junk' which is not defined in the input schema
    result = valid_plugin.execute("get_data", {"extra_junk": 123, "more_junk": "test"})

    # Expect success (dictionaries in Python ignore extra keys unless validated strictly)
    # The adapter implementation just returns {"data": "test_data"} ignoring args
    assert result == {"data": "test_data"}

def test_valid_adapter_sequential_execution(valid_plugin: Any) -> None:
    """
    Complex Scenario: Execute multiple tools in sequence to ensure no state contamination.
    """
    # 1. Check Import status
    loaded = valid_plugin.execute("check_import")
    assert loaded is True  # Should be true in the test environment if sibling import works

    # 2. Get Data
    data = valid_plugin.execute("get_data")
    assert data == {"data": "test_data"}

    # 3. Check Import again (should still be true)
    loaded_again = valid_plugin.execute("check_import")
    assert loaded_again is True

def test_valid_adapter_unknown_tool(valid_plugin: Any) -> None:
    """
    Edge Case: Execute a tool that doesn't exist.
    The execute method in ValidAdapter falls through to "executed" string or None?
    Let's check the implementation:
      if tool_name == "check_import": ...
      if tool_name == "get_data": ...
      return "executed"

    So it returns "executed" for unknown tools currently.
    """
    result = valid_plugin.execute("unknown_tool_xyz")
    assert result == "executed"
