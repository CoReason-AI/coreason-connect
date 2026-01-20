# coreason-connect

**The secure execution gateway for the CoReason ecosystem.**

coreason-connect transforms the CoReason "Brain" (coreason-cortex) from a passive text generator into an active **Agentic Workforce**. It solves the "Last Mile" problem of Enterprise AI by securely executing actions (RPC) on behalf of specific human users.

![License](https://img.shields.io/badge/license-Prosperity%203.0-blue)
[![Build Status](https://github.com/CoReason-AI/coreason_connect/actions/workflows/build.yml/badge.svg)](https://github.com/CoReason-AI/coreason_connect/actions)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Documentation](https://img.shields.io/badge/Docs-Product%20Requirements-informational)](docs/product_requirements.md)

## Installation

```bash
pip install coreason-connect
```

*Note: For dependency management, we recommend using a virtual environment or tools like Poetry.*

## Features

*   **MCP-First Architecture**: Implements the Model Context Protocol (MCP) as the universal interface for forward compatibility with any Agentic Framework.
*   **Dynamic Plugin Loading**: Supports a "Glass Box" architecture where plugins are hot-loaded from local paths, ensuring isolation and security.
*   **Delegated Identity**: Uses RFC 8693 patterns to exchange workload identity for specific user tokens, preserving the Chain of Custody in audit logs.
*   **Transactional Safety**: Includes a "Spend Gate" that automatically suspends `is_consequential: true` actions (like purchases) until human approval is granted.
*   **Extensible Modules**: Built-in support and examples for:
    *   **Scientific Operations**: Searching and purchasing literature (e.g., RightFind).
    *   **Productivity**: Managing Microsoft 365 calendar and emails.
    *   **DevOps**: Self-healing code via GitOps workflows.

For detailed requirements and architecture, see [Product Requirements](docs/product_requirements.md).

## Usage

Here is a simple example of how to initialize the server and load plugins:

```python
import asyncio
from coreason_connect.server import CoreasonConnectServer
from coreason_connect.config import AppConfig

async def main():
    # Initialize configuration (looks for connectors.yaml by default or env vars)
    config = AppConfig()

    # Create the server instance
    server = CoreasonConnectServer(config)

    # Start the server (this initializes plugins and the MCP server)
    # In a real deployment, this would likely run indefinitely or attach to a transport.
    await server.initialize()
    print("Coreason Connect Server initialized.")

    # Example: Listing available tools
    tools = await server.list_tools()
    for tool in tools:
        print(f"Tool: {tool.name} - {tool.description}")

if __name__ == "__main__":
    asyncio.run(main())
```
