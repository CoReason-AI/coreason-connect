from mcp.server import Server

from coreason_connect.utils.logger import logger


class CoreasonConnectServer:
    """The MCP Host that aggregates tools and plugins."""

    def __init__(self, name: str = "coreason-connect", version: str = "0.1.0") -> None:
        """Initialize the MCP Server."""
        self.server = Server(name)
        self.version = version
        logger.info(f"Initialized {name} v{version}")
