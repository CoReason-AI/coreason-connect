from unittest.mock import patch

import pytest
from mcp.server import Server

from coreason_connect.server import CoreasonConnectServer


def test_server_initialization() -> None:
    """Test that the server initializes correctly."""
    server_wrapper = CoreasonConnectServer(name="test-server", version="1.0.0")

    assert isinstance(server_wrapper.server, Server)
    assert server_wrapper.version == "1.0.0"
    assert server_wrapper.server.name == "test-server"


def test_server_default_initialization() -> None:
    """Test default initialization."""
    server_wrapper = CoreasonConnectServer()
    assert server_wrapper.server.name == "coreason-connect"
    assert server_wrapper.version == "0.1.0"


@pytest.mark.parametrize(  # type: ignore[misc]
    ("name", "version"),
    [
        ("", ""),
        ("   ", "   "),
        ("!@#$%^&*()", "v1.0.0-beta+exp"),
        ("emoji_🚀", "1.0.0"),
        ("a" * 1000, "1.0.0"),
    ],
)
def test_server_initialization_edge_cases(name: str, version: str) -> None:
    """Test server initialization with various edge case strings."""
    server = CoreasonConnectServer(name=name, version=version)
    assert server.server.name == name
    assert server.version == version


def test_server_logging_behavior() -> None:
    """Test that the server logs its initialization correctly."""
    with patch("coreason_connect.server.logger") as mock_logger:
        CoreasonConnectServer(name="test-logger", version="9.9.9")
        mock_logger.info.assert_called_once_with("Initialized test-logger v9.9.9")
