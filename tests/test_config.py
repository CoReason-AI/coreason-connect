import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from coreason_connect.config import AppConfig, load_config


def test_load_config_valid_yaml(tmp_path: Path) -> None:
    """Test loading a valid configuration file."""
    config_file = tmp_path / "test_config.yaml"
    data = {
        "plugins": [
            {
                "id": "test-plugin",
                "type": "local_python",
                "path": "./libs/test.py",
                "description": "A test plugin",
                "env_vars": {"KEY": "VALUE"},
            }
        ]
    }
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    config = load_config(config_file)
    assert isinstance(config, AppConfig)
    assert len(config.plugins) == 1
    plugin = config.plugins[0]
    assert plugin.id == "test-plugin"
    assert plugin.type == "local_python"
    assert plugin.env_vars == {"KEY": "VALUE"}


def test_load_config_missing_file() -> None:
    """Test that FileNotFoundError is raised when file is missing."""
    with pytest.raises(FileNotFoundError):
        load_config("non_existent_config.yaml")


def test_load_config_invalid_yaml(tmp_path: Path) -> None:
    """Test that ValueError is raised for invalid YAML."""
    config_file = tmp_path / "bad.yaml"
    with open(config_file, "w") as f:
        f.write("plugins: [unclosed list")

    with pytest.raises(ValueError, match="Invalid YAML"):
        load_config(config_file)


def test_load_config_validation_error(tmp_path: Path) -> None:
    """Test that ValueError is raised when Pydantic validation fails."""
    config_file = tmp_path / "invalid_schema.yaml"
    # Missing required 'id' and 'type'
    data = {"plugins": [{"path": "some/path"}]}
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    with pytest.raises(ValueError, match="Configuration validation failed"):
        load_config(config_file)


def test_load_config_env_var_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that COREASON_CONFIG_PATH overrides the default."""
    config_file = tmp_path / "env_config.yaml"
    data: dict[str, list[dict[str, str]]] = {"plugins": []}
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    monkeypatch.setenv("COREASON_CONFIG_PATH", str(config_file))
    config = load_config()  # Should pick up env var
    assert isinstance(config, AppConfig)
    assert config.plugins == []


def test_load_config_default_path_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that it defaults to connectors.yaml if env var not set."""
    monkeypatch.delenv("COREASON_CONFIG_PATH", raising=False)

    # Mock Path.exists and open to simulate connectors.yaml existing
    with patch("coreason_connect.config.Path.exists", return_value=True) as mock_exists:
        with patch("builtins.open", new_callable=MagicMock) as mock_open:
            # Mock file content
            mock_file = MagicMock()
            mock_file.__enter__.return_value = "plugins: []"
            mock_open.return_value = mock_file

            # We also need to mock yaml.safe_load because we are mocking open
            with patch("coreason_connect.config.yaml.safe_load", return_value={"plugins": []}):
                config = load_config()

    assert isinstance(config, AppConfig)
    mock_exists.assert_called()
    # Check that it checked for "connectors.yaml"
    # The path object created inside load_config will be "connectors.yaml"
    # We can check the args to the mocked exists or open
    assert "connectors.yaml" in str(mock_exists.call_args_list[0]) or "connectors.yaml" in str(mock_open.call_args[0])


def test_load_config_empty_file(tmp_path: Path) -> None:
    """Test loading an empty file results in empty config (if valid) or error."""
    config_file = tmp_path / "empty.yaml"
    with open(config_file, "w") as f:
        f.write("")  # Empty file returns None from safe_load usually

    # In our implementation we handle None -> {}
    config = load_config(config_file)
    assert isinstance(config, AppConfig)
    assert config.plugins == []


def test_load_config_not_dict_root(tmp_path: Path) -> None:
    """Test that a list root raises ValueError."""
    config_file = tmp_path / "list_root.yaml"
    with open(config_file, "w") as f:
        f.write("- item1\n- item2")

    with pytest.raises(ValueError, match="Configuration root must be a dictionary"):
        load_config(config_file)


def test_load_config_duplicate_ids(tmp_path: Path) -> None:
    """Test that duplicate plugin IDs raise a ValueError."""
    config_file = tmp_path / "dup.yaml"
    data = {
        "plugins": [
            {"id": "p1", "type": "native"},
            {"id": "p1", "type": "local_python"},
        ]
    }
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    with pytest.raises(ValueError, match="Duplicate plugin IDs found"):
        load_config(config_file)


def test_load_config_type_coercion(tmp_path: Path) -> None:
    """Test that types are coerced (e.g., int to str in env_vars)."""
    config_file = tmp_path / "coercion.yaml"
    data = {
        "plugins": [
            {
                "id": "p1",
                "type": "native",
                "env_vars": {"PORT": 8080, "DEBUG": True},
            }
        ]
    }
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    config = load_config(config_file)
    plugin = config.plugins[0]
    assert plugin.env_vars["PORT"] == "8080"
    assert plugin.env_vars["DEBUG"] == "True"  # Pydantic converts True to "True"


def test_load_config_unicode(tmp_path: Path) -> None:
    """Test handling of unicode characters."""
    config_file = tmp_path / "unicode.yaml"
    data = {
        "plugins": [
            {
                "id": "emoji-🚀",
                "type": "native",
                "description": "Café operation",
            }
        ]
    }
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True)

    config = load_config(config_file)
    plugin = config.plugins[0]
    assert plugin.id == "emoji-🚀"
    assert plugin.description == "Café operation"


def test_load_config_permission_error(tmp_path: Path) -> None:
    """Test handling of permission errors."""
    if os.name == "nt":  # Skip on Windows as chmod behavior is different
        return

    config_file = tmp_path / "protected.yaml"
    config_file.touch()

    # Remove read permissions
    config_file.chmod(0o000)

    try:
        # Pydantic/YAML load fails when file can't be opened
        # But load_config calls open(), which should raise PermissionError
        with pytest.raises(PermissionError):
            load_config(config_file)
    finally:
        # Restore permissions so cleanup works
        config_file.chmod(0o666)
