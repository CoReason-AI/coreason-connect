# coreason-connect

The secure execution gateway for the CoReason ecosystem. `coreason-connect` transforms the "Brain" (coreason-cortex) from a passive text generator into an active **Agentic Workforce**.

[![License: Prosperity 3.0](https://img.shields.io/badge/License-Prosperity%203.0-blue.svg)](https://prosperitylicense.com/versions/3.0.0)
[![CI](https://github.com/CoReason-AI/coreason_connect/actions/workflows/main.yml/badge.svg)](https://github.com/CoReason-AI/coreason_connect/actions)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Overview

`coreason-connect` is an MCP (Model Context Protocol) Host that solves the "Last Mile" problem of Enterprise AI: securely executing actions (RPC) on behalf of specific human users. Unlike RAG-focused systems, this platform focuses on *writing* and *transacting* (e.g., buying a paper, merging code, sending email).

It implements a **Dynamic "Glass Box" Plugin Architecture**, acting as a host shell that loads proprietary logic from local disk at runtime, ensuring sensitive vendor integrations remain isolated.

## Features

-   **MCP-First Architecture:** Adopts the Model Context Protocol (MCP) as the universal interface for tools and integrations.
-   **Dynamic "Glass Box" Plugins:** Hot-loads proprietary tools from a secure local directory at runtime, keeping core code decoupled from private logic.
-   **Transactional Safety ("Spend Gate"):** Intercepts consequential actions (e.g., spending money) to trigger a "Suspension Ticket", requiring human approval before execution.
-   **Delegated Identity:** Supports exchanging agent workload identity for specific user tokens, ensuring actions are attributed to the correct human user.
-   **Native Integrations:**
    -   **Microsoft 365:** Calendar and Email management (Draft/Send).
    -   **GitOps:** Self-healing code workflows (Create PR, Get Build Logs).
-   **Extensibility:** Supports custom local Python adapters (e.g., RightFind, Confex) via standard interfaces.

## Installation

```bash
pip install coreason-connect
```

## Usage

Here is a concise snippet showing how to initialize and run the server.

```python
import asyncio
from coreason_connect.server import CoreasonConnectServer
from coreason_connect.config import AppConfig

async def main():
    # Initialize configuration (defaults to loading from env/yaml)
    config = AppConfig()

    # Create the MCP Server instance
    server = CoreasonConnectServer(config=config)

    # Run the server (typically using stdio transport for MCP)
    # This example assumes you are integrating it into an MCP-compatible runner
    print(f"Server {server.name} initialized with {len(server.plugins)} plugins.")

    # In a real scenario, you would attach this to a transport:
    # from mcp.server.stdio import stdio_server
    # async with stdio_server() as (read_stream, write_stream):
    #     await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

Plugins are configured via a `connectors.yaml` file or equivalent configuration object.

```yaml
plugins:
  - id: "rightfind"
    type: "local_python"
    path: "./local_libs/adapters/rf_adapter.py"
  - id: "ms365"
    type: "native"
```

## License

This software is proprietary and dual-licensed.
Licensed under the **Prosperity Public License 3.0**.
Commercial use beyond a 30-day trial requires a separate license.
