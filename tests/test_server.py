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
