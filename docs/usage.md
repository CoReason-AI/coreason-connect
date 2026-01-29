# Usage Guide

Coreason Connect can be run as a Dockerized Microservice Gateway or used as a library.

## Running via Docker (Recommended)

The standard deployment method is using the Docker image.

### Prerequisites

*   Docker installed on your machine.
*   A `connectors.yaml` configuration file.

### Steps

1.  **Build the Image**:
    ```bash
    docker build -t coreason-connect:latest .
    ```

2.  **Run the Container**:
    Mount your configuration file to the container.
    ```bash
    docker run -d \
      -p 8000:8000 \
      -v $(pwd)/connectors.yaml:/app/connectors.yaml \
      -e COREASON_CONFIG_PATH=/app/connectors.yaml \
      coreason-connect:latest
    ```

3.  **Verify Status**:
    Check the health endpoint:
    ```bash
    curl http://localhost:8000/health
    ```

## Connecting an MCP Client

The service exposes the Model Context Protocol over Server-Sent Events (SSE).

*   **SSE Endpoint**: `http://localhost:8000/sse`
*   **Messages Endpoint**: `http://localhost:8000/messages`

### Example: Python Client

```python
import asyncio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def main():
    async with sse_client("http://localhost:8000/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools]}")

            # Call a tool
            result = await session.call_tool("git_get_build_logs", {"pr_id": 123})
            print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## Running Locally (Development)

1.  **Install Dependencies**:
    ```bash
    poetry install
    ```

2.  **Start the Server**:
    ```bash
    poetry run uvicorn coreason_connect.app:app --reload
    ```
