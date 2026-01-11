import os
from pathlib import Path

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
