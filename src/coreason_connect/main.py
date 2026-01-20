# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

import asyncio
from contextlib import suppress

from coreason_connect.config import AppConfig
from coreason_connect.server import CoreasonConnectServiceAsync
from coreason_connect.utils.logger import logger


async def hello_world() -> None:
    """Run the Coreason Connect server.

    This function initializes the server configuration, starts the
    CoreasonConnectServiceAsync, and keeps it running indefinitely.
    """
    logger.info("Starting Coreason Connect...")
    config = AppConfig()

    async with CoreasonConnectServiceAsync(config) as server:
        # In a real app, we would attach this to a transport (stdio or SSE)
        # For now, we just simulate running
        logger.info(f"Server '{server.name}' v{server.version} is ready.")

        # Keep alive loop simulation
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info("Shutting down...")


def main() -> None:
    """Entry point for the application.

    Sets up the asyncio event loop and runs the hello_world function.
    Handles keyboard interrupts gracefully.
    """
    with suppress(KeyboardInterrupt):
        asyncio.run(hello_world())


if __name__ == "__main__":  # pragma: no cover
    main()
