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
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from coreason_connect.config import load_config
from coreason_connect.interfaces import SecretsProvider
from coreason_connect.loader import PluginLoader


class MockSecrets(SecretsProvider):
    def get_secret(self, key: str) -> str:
        return "secret"

    def get_user_credential(self, key: str) -> Any:
        return {"user": "test"}


@pytest.fixture  # type: ignore[misc]
def mock_secrets() -> SecretsProvider:
    return MockSecrets()


@pytest.fixture  # type: ignore[misc]
def fixtures_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture  # type: ignore[misc]
def config_path(fixtures_dir: str) -> str:
    return os.path.join(fixtures_dir, "connectors.yaml")


def test_load_valid_plugin(config_path: str, mock_secrets: SecretsProvider) -> None:
    """Test loading a valid plugin that imports a sibling library."""
    config = load_config(config_path)
    loader = PluginLoader(config, mock_secrets)

    plugins = loader.load_all()

    assert "valid-plugin" in plugins
    plugin = plugins["valid-plugin"]

    # Check if the sibling import worked
    # The ValidAdapter execution returns self.client_loaded for "check_import"
    is_loaded = plugin.execute("check_import")
    assert is_loaded is True


def test_load_invalid_plugin(config_path: str, mock_secrets: SecretsProvider) -> None:
    """Test that an invalid plugin (wrong interface) is gracefully skipped."""
    config = load_config(config_path)
    loader = PluginLoader(config, mock_secrets)

    plugins = loader.load_all()

    # "invalid-plugin" should not be in the results because it failed validation
    assert "invalid-plugin" not in plugins


def test_load_missing_file(mock_secrets: SecretsProvider, tmp_path: Path) -> None:
    """Test that a missing file is gracefully skipped."""
    # Create a config pointing to a non-existent file
    config_file = tmp_path / "bad_config.yaml"
    config_file.write_text("""
plugins:
  - id: "missing-plugin"
    type: "local_python"
    path: "non_existent.py"
""")

    config = load_config(str(config_file))
    loader = PluginLoader(config, mock_secrets)

    plugins = loader.load_all()
    assert "missing-plugin" not in plugins


def test_unsupported_type(mock_secrets: SecretsProvider, tmp_path: Path) -> None:
    """Test that unsupported plugin types are skipped."""
    config_file = tmp_path / "bad_type.yaml"
    config_file.write_text("""
plugins:
  - id: "openapi-plugin"
    type: "openapi"
    path: "spec.json"
""")

    config = load_config(str(config_file))
    loader = PluginLoader(config, mock_secrets)

    plugins = loader.load_all()
    assert len(plugins) == 0


def test_missing_path_field(mock_secrets: SecretsProvider, tmp_path: Path) -> None:
    """Test that a plugin without a path raises ValueError internally and is skipped."""
    config_file = tmp_path / "no_path.yaml"
    config_file.write_text("""
plugins:
  - id: "no-path-plugin"
    type: "local_python"
    # missing path
""")

    config = load_config(str(config_file))
    loader = PluginLoader(config, mock_secrets)
    plugins = loader.load_all()
    assert "no-path-plugin" not in plugins


def test_import_spec_failure(mock_secrets: SecretsProvider, tmp_path: Path) -> None:
    """Test failure when importlib cannot create a spec."""
    config_file = tmp_path / "bad_spec.yaml"

    # Use a file inside safe zone
    plugin_path = os.path.join("tests/fixtures/local_libs/crash_plugins/dummy.py")

    config_file.write_text(f"""
plugins:
  - id: "bad-spec-plugin"
    type: "local_python"
    path: "{plugin_path}"
""")
    config = load_config(str(config_file))
    loader = PluginLoader(config, mock_secrets)

    # Mock importlib.util.spec_from_file_location to return None
    with patch("importlib.util.spec_from_file_location", return_value=None):
        plugins = loader.load_all()
        assert "bad-spec-plugin" not in plugins


def test_module_execution_failure(mock_secrets: SecretsProvider, tmp_path: Path) -> None:
    """Test failure when module execution raises an exception."""
    # Use a file inside safe zone
    plugin_path = os.path.join("tests/fixtures/local_libs/crash_plugins/crash_on_load.py")

    config_file = tmp_path / "crash.yaml"
    config_file.write_text(f"""
plugins:
  - id: "crasher"
    type: "local_python"
    path: "{plugin_path}"
""")

    config = load_config(str(config_file))
    loader = PluginLoader(config, mock_secrets)

    plugins = loader.load_all()
    assert "crasher" not in plugins


def test_unsafe_path(mock_secrets: SecretsProvider, tmp_path: Path) -> None:
    """Test that path outside safe zone is rejected."""
    # create a file outside the repo (tmp_path is typically outside)
    unsafe_file = tmp_path / "unsafe.py"
    unsafe_file.write_text("pass")

    # We can mock the config object.
    from coreason_connect.config import AppConfig, PluginConfig

    mock_plugin_conf = Mock(spec=PluginConfig)
    mock_plugin_conf.id = "unsafe"
    mock_plugin_conf.type = "local_python"
    mock_plugin_conf.path = str(unsafe_file)

    mock_config = Mock(spec=AppConfig)
    mock_config.plugins = [mock_plugin_conf]

    loader = PluginLoader(mock_config, mock_secrets)
    plugins = loader.load_all()

    assert "unsafe" not in plugins
