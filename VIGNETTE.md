# The Architecture and Utility of coreason-connect

### 1. The Philosophy (The Why)

In the rapidly evolving landscape of Agentic AI, a critical gap exists between *thinking* and *doing*. While Large Language Models (LLMs) act as the "Brain," generating text and plans, they lack safe, reliable "Hands" to interact with the real world. Existing solutions often force a binary choice: unsafe, unbridled execution or rigid, hard-coded integrations that stifle flexibility.

**coreason-connect** solves this by acting as the secure execution gateway for the enterprise. It transforms passive text generators into an active workforce capable of transacting—buying research papers, scheduling meetings, or merging code—without compromising security.

The architecture is built on three pillars:
1.  **Standardization:** It adopts the **Model Context Protocol (MCP)** as the universal interface, ensuring forward compatibility with any agentic framework.
2.  **The "Glass Box" Strategy:** It decouples the core engine from proprietary logic. Plugins are loaded dynamically from local storage, keeping sensitive vendor integrations isolated and inspectable.
3.  **Transactional Safety:** It introduces the concept of a "Spend Gate." Actions tagged as "consequential" (like spending money) are intercepted at the protocol level, mandating human approval before execution. This ensures that while the identity is delegated, the ultimate authority remains human.

### 2. Under the Hood (The Dependencies & Logic)

The package leverages a concise but powerful stack to deliver its promises:

*   **`mcp`**: The backbone of the system. By building directly on the Model Context Protocol SDK, `coreason-connect` speaks the native language of modern AI agents, exposing tools and resources via a standardized JSON-RPC interface.
*   **`msgraph-core`**: Represents the "Enterprise Reach." It provides a robust, middleware-centric client for Microsoft 365, enabling deep integration with the most common corporate productivity suite (Email, Calendar) without reinventing authentication wheels.
*   **`loguru`**: Structured, asynchronous logging is non-negotiable in transaction-heavy environments. `loguru` ensures that every decision, suspension, and error is captured with context, vital for the "Chain of Custody" audit logs.

**The Internal Logic**
At its heart, `coreason-connect` is an **Aggregation Host**. Upon startup, the `PluginLoader` scans a designated secure directory. It doesn't just import modules; it validates them against the `ConnectorProtocol` interface, injects a `SecretsProvider` (so plugins never handle raw vault keys), and dynamically manipulates `sys.path` to resolve local dependencies.

The `CoreasonConnectServer` then aggregates these disparate tools into a single registry. Crucially, the `call_tool` handler acts as a middleware layer. Before routing a command to a plugin, it checks the `is_consequential` flag. If true, it short-circuits the execution, returning a suspension signal to the agent—effectively freezing the agent's workflow until a human says "Proceed."

### 3. In Practice (The How)

Here is how the architecture manifests in code, prioritizing safety and developer ergonomics.

**Defining a High-Stakes Plugin**
Developers implement the `ConnectorProtocol` to expose capabilities. Notice how easily a tool is marked as dangerous (`is_consequential=True`), enabling the platform's safety features with a single boolean.

```python
from mcp.types import Tool
from coreason_connect.interfaces import ConnectorProtocol, ToolDefinition

class ScientificPurchasing(ConnectorProtocol):
    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="purchase_article",
                is_consequential=True,  # <--- The Spend Gate Trigger
                tool=Tool(
                    name="purchase_article",
                    description="Purchase and download a research paper.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "doi": {"type": "string"},
                            "max_price_usd": {"type": "number"},
                        },
                        "required": ["doi"],
                    },
                ),
            )
        ]

    def execute(self, tool_name: str, arguments: dict) -> str:
        # This code ONLY runs if the server (and human) approves.
        if tool_name == "purchase_article":
            return self._process_payment(arguments["doi"])
        raise NotImplementedError(f"Unknown tool: {tool_name}")
```

**The Safety Intercept**
The server's internal logic acts as a guardian. When an agent attempts to call a consequential tool, `coreason-connect` intervenes before the plugin is even touched.

```python
# Inside CoreasonConnectServer._call_tool_handler

async def _call_tool_handler(self, name: str, arguments: dict) -> list[types.TextContent]:
    tool_def = self.tool_registry.get(name)

    # 1. The Intercept
    if tool_def and tool_def.is_consequential:
        # The agent is halted immediately.
        # In a full deployment, this triggers a push notification to a human.
        return [
            types.TextContent(
                type="text",
                text=f"Action suspended: Human approval required for {name}."
            )
        ]

    # 2. The Execution (Happy Path)
    # Only reached if the tool is safe or approval was pre-granted (context dependent).
    plugin = self.plugin_registry.get(name)
    result = plugin.execute(name, arguments)
    return [types.TextContent(type="text", text=str(result))]
```
