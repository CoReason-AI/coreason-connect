# Welcome to coreason_connect

This is the documentation for the coreason_connect project.

## Changelog

### v0.2.0 - Delegated Identity Support
*   **Delegated Identity**: Introduced `UserContext` to securely propagate user identity and authentication tokens to plugins.
*   **OBO Authentication**: Plugins like MS365 now use On-Behalf-Of (OBO) flow using `downstream_token` when available, falling back to service identity.
*   **Interface Update**: `ConnectorProtocol.execute` now accepts `user_context`.
*   **Dependencies**: Added `coreason-identity` dependency. Updated `anyio`, `httpx`, and dev tools.
