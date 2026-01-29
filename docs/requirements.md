# Requirements

## Runtime Dependencies

The coreason-connect service relies on the following key libraries:

*   **FastAPI** (`>=0.100.0`): Web framework for the MCP Gateway.
*   **Uvicorn** (`>=0.20.0`): ASGI server implementation.
*   **MCP** (`>=1.26.0`): Model Context Protocol SDK for Python.
*   **HTTPX** (`^0.28.1`): Async HTTP client for plugin interactions.
*   **AnyIO** (`^4.12.1`): Asynchronous I/O support.
*   **Loguru** (`^0.7.2`): Structured logging.
*   **Pydantic** (`^2.12.5`): Data validation and settings management.

## Development Dependencies

For development, testing, and documentation:

*   **Poetry**: Dependency management and packaging.
*   **Pytest**: Testing framework (`^9.0.2`).
*   **Ruff**: Linting and formatting (`^0.14.14`).
*   **Mypy**: Static type checking (`^1.19.1`).
*   **MkDocs**: Documentation generator (`^1.6.0`).
