from mcp.server import Server

from coreason_connect.server import CoreasonConnectServer


def test_server_initialization() -> None:
    """Test that the server initializes correctly."""
    server = CoreasonConnectServer(name="test-server", version="1.0.0")
    assert isinstance(server, Server)
    assert server.name == "test-server"
    assert server.version == "1.0.0"
