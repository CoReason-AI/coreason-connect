import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from coreason_connect.config import load_config

# We assume the "Safe Zone" is the project root, which we can approximate by os.getcwd()
# during tests, or specifically the directory where the config file resides?
# The spec says "Verifies plugin path is inside the allowed 'Safe Zone'".
# Usually this means the directory where the application is running or the config file directory.
# We will enforce it relative to os.getcwd() for now.


def test_plugin_path_safe(tmp_path: Path) -> None:
    """Test that a path inside the safe zone is accepted."""
    # We must run this test such that tmp_path is inside the CWD or we mock CWD.
    # To reliably test "Safe Zone" logic which usually depends on CWD, we should change CWD
    # or rely on relative paths being safe if they don't escape.

    # Let's write a config file in tmp_path
    config_file = tmp_path / "connectors.yaml"

    # Valid relative path
    data = {"plugins": [{"id": "safe-plugin", "type": "local_python", "path": "libs/plugin.py"}]}
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    # We need to simulate that we are running from tmp_path or that tmp_path is safe.
    # If the logic enforces "child of CWD", we need to make sure the checked path is child of CWD.
    # For this test, let's use a path that is definitely "safe" relative to CWD.
    # "libs/plugin.py" is safe relative to wherever we are.

    config = load_config(config_file)
    assert config.plugins[0].path == "libs/plugin.py"


def test_plugin_path_traversal_unsafe(tmp_path: Path) -> None:
    """Test that a path attempting traversal is rejected."""
    config_file = tmp_path / "unsafe.yaml"
    data = {"plugins": [{"id": "unsafe-plugin", "type": "local_python", "path": "../../../etc/passwd"}]}
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    with pytest.raises(ValueError, match="Plugin path must be within the safe zone"):
        load_config(config_file)


def test_plugin_path_absolute_unsafe(tmp_path: Path) -> None:
    """Test that an absolute path outside safe zone is rejected."""
    config_file = tmp_path / "unsafe_abs.yaml"

    # Pick a path that is definitely outside CWD. /tmp is usually safe bet on unix.
    # On windows, C:\Windows.
    unsafe_path = "/tmp/evil.py" if os.name != "nt" else "C:\\Windows\\System32\\evil.py"

    data = {"plugins": [{"id": "unsafe-abs", "type": "local_python", "path": unsafe_path}]}
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    with pytest.raises(ValueError, match="Plugin path must be within the safe zone"):
        load_config(config_file)


def test_plugin_path_normalization_bypass_attempt(tmp_path: Path) -> None:
    """Test that tricky paths like 'safe/../../unsafe' are caught."""
    config_file = tmp_path / "tricky.yaml"
    data = {"plugins": [{"id": "tricky", "type": "local_python", "path": "safe_folder/../../unsafe_file.py"}]}
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    with pytest.raises(ValueError, match="Plugin path must be within the safe zone"):
        load_config(config_file)


def test_plugin_path_none(tmp_path: Path) -> None:
    """Test that a null path is accepted (optional field)."""
    config_file = tmp_path / "none_path.yaml"
    data = {"plugins": [{"id": "none-plugin", "type": "native", "path": None}]}
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    config = load_config(config_file)
    assert config.plugins[0].path is None


def test_plugin_path_resolution_error(tmp_path: Path) -> None:
    """Test handling of path resolution errors."""
    config_file = tmp_path / "error.yaml"
    data = {"plugins": [{"id": "error-plugin", "type": "local_python", "path": "some/path"}]}
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    # Mock Path.resolve to raise an OSError
    # We need to mock where it's used: coreason_connect.config.Path.resolve
    # However, Path is a class. Mocking resolve on all Path instances is tricky.
    # Better to mock pathlib.Path.resolve globally? Or mock Path in the module.
    # The module imports Path: from pathlib import Path.
    # So we patch coreason_connect.config.Path.

    # Wait, patching Path is difficult because it's a built-in/C-extension often.
    # But we can patch the method on the class.
    # Or cleaner: patch 'coreason_connect.config.Path' to return a Mock that raises on resolve.

    with patch("coreason_connect.config.Path") as MockPath:
        # We need MockPath(v) to return an object whose resolve() raises
        instance = MockPath.return_value
        instance.resolve.side_effect = OSError("Disk failure")

        # We also need to handle other Path usages in load_config if any?
        # load_config uses Path(config_path).
        # But validate_path_safety calls Path(v).
        # If we patch Path globally in config module, it affects everything.
        # This might be too broad and break load_config itself before validation.

        # load_config calls Path(config_path).exists() etc.
        # If we mock Path, we must make sure those calls work.

        # Let's verify existing flow:
        # 1. load_config calls Path(config_path).
        # 2. Checks exists().
        # 3. Opens file.
        # 4. Parses YAML.
        # 5. Instantiates AppConfig -> PluginConfig -> validate_path_safety -> Path(v).

        # If we patch Path, we need to support step 1-3 too.

        # Better strategy: Only mock Path inside the validator context?
        # We can't easily target just the validator.

        # Alternate strategy: Mock Path.resolve directly using patch.object?
        # `patch.object(Path, 'resolve', side_effect=...)`
        # But Path is immutable/native, might not be patchable easily.

        # Let's try patching `coreason_connect.config.Path` but configure the mock to behave correctly for config file,
        # but fail for plugin path.
        # This is complex.

        # Easier way: The catch block is `except Exception`.
        # Can we pass a value for `v` that causes `Path(v)` or `resolve()` to fail?
        # Passing a null byte `\0` usually raises ValueError/TypeError in Path constructor on some versions,
        # or OSError in resolve.
        # In Python, `Path("\0")` might raise `ValueError: embedded null byte`.
        # Let's try that.
        pass

    # Let's try the null byte approach first, it's cleaner if it works.

    data_evil = {"plugins": [{"id": "error-plugin", "type": "local_python", "path": "evil\0path"}]}
    with open(config_file, "w") as f:
        # yaml.dump might struggle with null byte?
        # Use simple write?
        # YAML handles unicode, but null byte might be escaped.
        # If it's escaped, it comes back as \0 char.
        # Path("\0") raises ValueError.
        yaml.dump(data_evil, f)

    with pytest.raises(ValueError, match="Invalid path resolution"):
        load_config(config_file)
