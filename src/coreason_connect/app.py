# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from mcp.server.sse import SseServerTransport

from coreason_connect.config import load_config
from coreason_connect.server import CoreasonConnectServiceAsync
from coreason_connect.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage the application lifespan.

    Initializes the Coreason Connect Service and MCP Transport.
    """
    logger.info("Initializing Coreason Connect MCP Gateway...")

    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        # We might want to exit here, but raising exception will stop startup
        raise

    # Initialize service
    service = CoreasonConnectServiceAsync(config=config)

    # Initialize transport
    # The endpoint path "/messages" informs the client where to post messages.
    transport = SseServerTransport("/messages")

    # Start service resources (e.g. HTTP client)
    await service.__aenter__()

    # Store in app state for access in endpoints
    app.state.service = service
    app.state.transport = transport

    logger.info("Coreason Connect MCP Gateway started")

    yield

    # Cleanup
    await service.__aexit__(None, None, None)
    logger.info("Coreason Connect MCP Gateway stopped")


app = FastAPI(
    title="Coreason Connect MCP Gateway",
    description="MCP Gateway Microservice for Coreason Cortex",
    version="0.3.0",
    lifespan=lifespan,
)


class McpSseResponse(Response):
    """Custom Response to handle MCP SSE connection via ASGI."""

    def __init__(self, app_state: Any) -> None:
        super().__init__()
        self.app_state = app_state

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        transport = cast(SseServerTransport, self.app_state.transport)
        service = cast(CoreasonConnectServiceAsync, self.app_state.service)

        # connect_sse yields streams which we pass to the service runner
        async with transport.connect_sse(scope, receive, send) as streams:
            read_stream, write_stream = streams
            await service.run(read_stream, write_stream, service.create_initialization_options())


class McpMessageResponse(Response):
    """Custom Response to handle MCP messages via ASGI."""

    def __init__(self, app_state: Any) -> None:
        super().__init__()
        self.app_state = app_state

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        transport = cast(SseServerTransport, self.app_state.transport)
        await transport.handle_post_message(scope, receive, send)


@app.get("/sse")
async def handle_sse(request: Request) -> Response:
    """Handle SSE handshake and connection."""
    return McpSseResponse(request.app.state)


@app.post("/messages")
async def handle_messages(request: Request) -> Response:
    """Handle JSON-RPC messages."""
    return McpMessageResponse(request.app.state)


@app.get("/health")
async def health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    service = cast(CoreasonConnectServiceAsync, request.app.state.service)
    return JSONResponse(
        {"status": "live", "plugins": list(service.plugins.keys()), "tools": list(service.tool_registry.keys())}
    )
