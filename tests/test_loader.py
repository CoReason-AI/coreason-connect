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
import sys
from pathlib import Path
from typing import Any, Optional
from unittest.mock import Mock, patch

import pytest
from coreason_identity.models import UserContext

from coreason_connect.config import load_config
from coreason_connect.interfaces import SecretsProvider
from coreason_connect.loader import PluginLoader


class MockSecrets(SecretsProvider):
    def get_secret(self, key: str) -> str:
        return "secret"

    def get_user_credential(self, key: str) -> Any:
        return {"user": "test"}


@pytest.fixture
def mock_secrets() -> SecretsProvider:
    return MockSecrets()


@pytest.fixture
def fixtures_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def config_path(fixtures_dir: str) -> str:
    return os.path.join(fixtures_dir, "connectors.yaml")


def normalize_path(path: str) -> str:
    """Normalize path to posix style to avoid YAML escape issues on Windows."""
    return Path(path).as_posix()


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


def test_valid_plugin_has_get_data_tool(config_path: str, mock_secrets: SecretsProvider) -> None:
    """Test that the valid plugin exposes the 'get_data' tool."""
    config = load_config(config_path)
    loader = PluginLoader(config, mock_secrets)

    plugins = loader.load_all()
    plugin = plugins["valid-plugin"]

    tools = plugin.get_tools()
    tool_names = [t.name for t in tools]
    assert "get_data" in tool_names


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
    plugin_path = normalize_path(os.path.join("tests/fixtures/local_libs/crash_plugins/dummy.py"))

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
    plugin_path = normalize_path(os.path.join("tests/fixtures/local_libs/crash_plugins/crash_on_load.py"))

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


def test_mixed_plugins_resilience(mock_secrets: SecretsProvider, tmp_path: Path, fixtures_dir: str) -> None:
    """Test that valid plugins load even if others fail."""
    # Create a mixed config
    # 1. Valid plugin (from fixtures)
    # 2. Init fail plugin (from fixtures)
    # 3. Execution fail plugin (created here)

    valid_path = normalize_path(os.path.join(fixtures_dir, "local_libs/adapters/valid_adapter.py"))
    init_fail_path = normalize_path(os.path.join(fixtures_dir, "local_libs/adapters/init_fail.py"))

    # We need a safe zone execution fail plugin
    # existing fixture: tests/fixtures/local_libs/crash_plugins/crash_on_load.py
    crash_path = normalize_path(os.path.join(fixtures_dir, "local_libs/crash_plugins/crash_on_load.py"))

    config_file = tmp_path / "mixed.yaml"
    config_file.write_text(f"""
plugins:
  - id: "valid"
    type: "local_python"
    path: "{valid_path}"
  - id: "init-fail"
    type: "local_python"
    path: "{init_fail_path}"
  - id: "crasher"
    type: "local_python"
    path: "{crash_path}"
""")

    config = load_config(str(config_file))
    loader = PluginLoader(config, mock_secrets)

    plugins = loader.load_all()

    # Assert valid plugin loaded
    assert "valid" in plugins

    # Assert faulty ones are missing
    assert "init-fail" not in plugins
    assert "crasher" not in plugins

    # Assert count
    assert len(plugins) == 1


def test_load_native_plugin(mock_secrets: SecretsProvider, tmp_path: Path) -> None:
    """Test loading a native plugin."""
    config_file = tmp_path / "native.yaml"
    config_file.write_text("""
plugins:
  - id: "test-native"
    type: "native"
""")

    config = load_config(str(config_file))
    loader = PluginLoader(config, mock_secrets)

    # We need to mock importlib.import_module to return a dummy module
    # containing a valid ConnectorProtocol implementation
    from coreason_connect.interfaces import ConnectorProtocol, ToolDefinition

    class MockNativePlugin(ConnectorProtocol):
        def get_tools(self) -> list[ToolDefinition]:
            return []

        def execute(
            self,
            tool_name: str,
            arguments: dict[str, Any] | None = None,
            user_context: Optional[UserContext] = None,
        ) -> Any:
            return "executed"

    mock_module = Mock()
    mock_module.MockNativePlugin = MockNativePlugin

    with patch("importlib.import_module", return_value=mock_module) as mock_import:
        plugins = loader.load_all()

        mock_import.assert_called_with("coreason_connect.plugins.test_native")
        assert "test-native" in plugins
        assert isinstance(plugins["test-native"], MockNativePlugin)


def test_native_plugin_not_found(mock_secrets: SecretsProvider, tmp_path: Path) -> None:
    """Test failure when native plugin module is missing."""
    config_file = tmp_path / "native_missing.yaml"
    config_file.write_text("""
plugins:
  - id: "missing-native"
    type: "native"
""")

    config = load_config(str(config_file))
    loader = PluginLoader(config, mock_secrets)

    with patch("importlib.import_module", side_effect=ImportError("Not found")):
        plugins = loader.load_all()
        assert "missing-native" not in plugins


def test_native_plugin_runtime_error(mock_secrets: SecretsProvider, tmp_path: Path) -> None:
    """Test resilience when a native plugin crashes during import."""
    config_file = tmp_path / "native_crash.yaml"
    config_file.write_text("""
plugins:
  - id: "crash-native"
    type: "native"
""")

    config = load_config(str(config_file))
    loader = PluginLoader(config, mock_secrets)

    with patch("importlib.import_module", side_effect=RuntimeError("Module crashed")):
        plugins = loader.load_all()
        assert "crash-native" not in plugins


def test_native_plugin_no_connector(mock_secrets: SecretsProvider, tmp_path: Path) -> None:
    """Test failure when native plugin module has no ConnectorProtocol."""
    config_file = tmp_path / "native_empty.yaml"
    config_file.write_text("""
plugins:
  - id: "empty-native"
    type: "native"
""")

    config = load_config(str(config_file))
    loader = PluginLoader(config, mock_secrets)

    # Mock module with no classes
    mock_module = Mock()
    # Ensure inspect.getmembers returns nothing useful
    mock_module.SomeClass = type("SomeClass", (), {})

    with patch("importlib.import_module", return_value=mock_module):
        plugins = loader.load_all()
        assert "empty-native" not in plugins


def test_native_plugin_normalization(mock_secrets: SecretsProvider, tmp_path: Path) -> None:
    """Test that plugin ID normalization works correctly."""
    config_file = tmp_path / "native_norm.yaml"
    config_file.write_text("""
plugins:
  - id: "my-cool-plugin"
    type: "native"
""")

    config = load_config(str(config_file))
    loader = PluginLoader(config, mock_secrets)

    from coreason_connect.interfaces import ConnectorProtocol, ToolDefinition

    class MockPlugin(ConnectorProtocol):
        def get_tools(self) -> list[ToolDefinition]:
            return []

        def execute(
            self,
            tool_name: str,
            arguments: dict[str, Any] | None = None,
            user_context: Optional[UserContext] = None,
        ) -> Any:
            return "ok"

    mock_module = Mock()
    mock_module.Plugin = MockPlugin

    with patch("importlib.import_module", return_value=mock_module) as mock_import:
        plugins = loader.load_all()

        # The key check: ensure it tried to import 'coreason_connect.plugins.my_cool_plugin'
        mock_import.assert_called_with("coreason_connect.plugins.my_cool_plugin")
        assert "my-cool-plugin" in plugins


def test_isolation_class_names(mock_secrets: SecretsProvider, tmp_path: Path, fixtures_dir: str) -> None:
    """Test loading two plugins with the same class name but different IDs."""

    path1 = normalize_path(os.path.join(fixtures_dir, "local_libs/adapters/valid_adapter.py"))
    path2 = normalize_path(os.path.join(fixtures_dir, "local_libs/adapters/duplicate_class.py"))

    config_file = tmp_path / "collision.yaml"
    config_file.write_text(f"""
plugins:
  - id: "first"
    type: "local_python"
    path: "{path1}"
  - id: "second"
    type: "local_python"
    path: "{path2}"
""")

    config = load_config(str(config_file))
    loader = PluginLoader(config, mock_secrets)

    plugins = loader.load_all()

    assert "first" in plugins
    assert "second" in plugins

    # Verify they are distinct objects of different classes (even if name is same)
    obj1 = plugins["first"]
    obj2 = plugins["second"]

    assert obj1 is not obj2
    assert obj1.__class__.__name__ == "ValidAdapter"
    assert obj2.__class__.__name__ == "ValidAdapter"

    # Verify behavior
    assert obj1.execute("check_import") is True  # From valid_adapter.py
    assert obj2.execute("any") == "duplicate"  # From duplicate_class.py


def test_sys_path_hygiene(mock_secrets: SecretsProvider, tmp_path: Path, fixtures_dir: str) -> None:
    """Verify sys.path is clean after a plugin crash."""
    crash_path = normalize_path(os.path.join(fixtures_dir, "local_libs/crash_plugins/crash_on_load.py"))

    # The expected temporary path is .../tests/fixtures/local_libs/crash_plugins/.. -> crash_plugins
    # Wait, the logic is parent.parent.
    # crash_plugins/crash_on_load.py -> parent: crash_plugins -> parent: local_libs

    lib_root = str(Path(crash_path).resolve().parent.parent)

    config_file = tmp_path / "hygiene.yaml"
    config_file.write_text(f"""
plugins:
  - id: "crasher"
    type: "local_python"
    path: "{crash_path}"
""")

    config = load_config(str(config_file))
    loader = PluginLoader(config, mock_secrets)

    # Ensure it's not there before
    assert lib_root not in sys.path

    loader.load_all()

    # Ensure it's not there after
    assert lib_root not in sys.path


def test_init_failure(mock_secrets: SecretsProvider, tmp_path: Path, fixtures_dir: str) -> None:
    """Test plugin that fails during __init__."""
    init_fail_path = normalize_path(os.path.join(fixtures_dir, "local_libs/adapters/init_fail.py"))

    config_file = tmp_path / "init_fail.yaml"
    config_file.write_text(f"""
plugins:
  - id: "init-fail"
    type: "local_python"
    path: "{init_fail_path}"
""")

    config = load_config(str(config_file))
    loader = PluginLoader(config, mock_secrets)

    plugins = loader.load_all()

    assert "init-fail" not in plugins
