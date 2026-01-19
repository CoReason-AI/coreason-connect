# Product Requirements Document: coreason-connect

**Domain**: Enterprise Integration, Action Orchestration, & Dynamic Plugin Hosting
**Architectural Role**: The "Hands" / The MCP Host
**Core Philosophy**: "The Interface is Standard (MCP). The Logic is Private. The Identity is Delegated."
**Dependencies**: coreason-identity, coreason-vault, coreason-human-layer, mcp (Python SDK)

---

## 1. Executive Summary

coreason-connect is the secure execution gateway for the CoReason ecosystem. It transforms the "Brain" (coreason-cortex) from a passive text generator into an active **Agentic Workforce**.

It solves the "Last Mile" problem of Enterprise AI: securely executing actions (RPC) on behalf of specific human users. Unlike coreason-mcp (which focuses on *reading* data for RAG), coreason-connect focuses on *writing* and *transacting* (e.g., buying a paper, merging code, sending email).

Critically, it implements a **Dynamic "Glass Box" Plugin Architecture**. It acts as a host shell that loads proprietary logic (such as the private rightfind_client) from local disk at runtime, ensuring that sensitive vendor integrations remain isolated within the client's infrastructure and are never bundled into the core platform code.

## 2. Functional Philosophy

### 2.1 MCP-First Architecture (SOTA)

We adopt the **Model Context Protocol (MCP)** as the universal interface.

*   **The Host:** coreason-connect runs as an MCP Server.
*   **The Tools:** Every internal adapter (RightFind) or external integration (Jira) is exposed as an MCP Tool.
*   **The Benefit:** This ensures forward compatibility with any LLM or Agentic Framework that speaks MCP.

### 2.2 Delegated Identity (The "Act As" Protocol)

Agents must never use shared "Service Accounts" for GxP-relevant actions.

*   **Token Exchange:** We utilize **RFC 8693** patterns. The agent exchanges its workload identity for a specific user's downstream token.
*   **Attribution:** When an agent creates a Jira ticket, the audit log must read "Created by Agent (on behalf of User X)," preserving the Chain of Custody.

### 2.3 The "Glass Box" Plugin Strategy

*   **Decoupling:** The core package knows nothing about specific proprietary tools at build time.
*   **Late Binding:** At startup, the service scans a secure local directory (/opt/coreason/plugins), validates Python modules against a strict interface, and hot-loads them.
*   **Isolation:** If the rightfind_client plugin crashes, it must be contained, preventing a system-wide outage.

### 2.4 Transactional Safety

*   **The "Spend" Gate:** Any tool tagged `is_consequential: true` (e.g., spending money, deleting data) automatically triggers a **Suspension Ticket** via coreason-human-layer. The agent halts until a human explicitly approves the action.

---

## 3. Core Functional Requirements (Component Level)

### 3.1 The MCP Aggregator (The Host)

**Concept:** A server that aggregates multiple internal adapters into a single tool list.

*   **Mechanism:**
    *   Initializes the `mcp.server.Server`.
    *   Iterates through loaded plugins.
    *   Registers each plugin's functions as MCP Tools (JSON-RPC).
*   **Capabilities:** Handles `list_tools`, `call_tool`, and exposes a `list_resources` endpoint for browsing available actions.

### 3.2 The Dynamic Loader (The Adapter Engine)

**Concept:** A secure importer for local proprietary code.

*   **Input:** Reads `connectors.yaml` to find plugin paths.
*   **Security:**
    *   **Path Traversal Check:** Verifies plugin path is inside the allowed "Safe Zone."
    *   **Interface Validation:** Ensures the loaded module implements the `CoreasonConnector` ABC (Abstract Base Class).
*   **Injection:** Injects a `SecretsProvider` into the plugin. The plugin uses this provider to request credentials (e.g., `secrets.get('RF_PASSWORD')`) without handling encryption itself.

### 3.3 The Credential Broker (Identity Manager)

**Concept:** A multi-tenant secret manager mapping Users to Provider Identities.

*   **Storage:** Uses coreason-vault to encrypt tokens at rest (AES-256).
*   **Flows:**
    *   **OAuth2 Code Flow:** For Microsoft 365, Google, Slack.
    *   **API Key Injection:** For Confex, RightFind (Legacy).
    *   **Auto-Refresh:** Background daemon refreshes expired OAuth tokens proactively.

### 3.4 The Event Listener (The Ear)

**Concept:** Maps external asynchronous events to internal suspended threads.

*   **Endpoint:** `/webhooks/{provider_id}`.
*   **Signature Verification:** Validates HMAC signatures (e.g., GitHub Secret) to prevent spoofing.
*   **Routing:** Extracts correlation IDs (e.g., Jira Issue Key) from the payload to wake up the specific agent waiting for that event.

---

## 4. Specific Module Requirements (The Plugins)

### Module A: Scientific Operations (RightFind Wrapper)

*   **Goal:** Operationalize the proprietary rightfind_client.
*   **Source:** Loaded dynamically from `local_libs/rightfind_adapter.py`.
*   **Tools Exposed:**
    *   `search_literature(query)`: Wraps `RFEClient.subclients.search`. Returns standardized JSON.
    *   `check_rights(doi)`: Wraps `RightsAdvisoryClient`. Returns "GRANT" or "DENY".
    *   `purchase_article(content_id)`: Wraps `RFEClient.subclients.orders`. **CRITICAL:** Tagged `is_consequential: true`. Triggers Human Approval if price > $0.

### Module B: Conference Intelligence (Confex)

*   **Goal:** Track scientific abstract submissions.
*   **Source:** Can be a Python Adapter or an OpenAPI Spec.
*   **Tools Exposed:**
    *   `search_abstracts(conference_id, keywords)`: Scrapes or queries conference programs.
    *   `get_session_details(session_id)`: Retrieves time, location, and speakers.

### Module C: Productivity (Microsoft 365)

*   **Goal:** Calendar and Email management.
*   **Implementation:** Uses `msgraph-core` library.
*   **Tools Exposed:**
    *   `find_meeting_slot(attendees, duration)`: Uses Graph API `/me/findMeetingTimes`.
    *   `draft_email(to, subject, body)`: Creates a message in "Drafts" folder.
    *   `send_email(id)`: Sends a draft. Tagged `is_consequential: true`.

### Module D: DevOps (GitOps)

*   **Goal:** Self-healing code and configuration.
*   **Tools Exposed:**
    *   `git_create_pr(repo, branch, changes)`: Automates the Fork -> Branch -> Commit -> PR workflow.
    *   `git_get_build_logs(commit_sha)`: Retrieves CI/CD failure logs for analysis.

---

## 5. User Stories

### Story A: The R&D Procurement Loop (RightFind)

*   **Context:** Agent identifies a critical paper, "Novel Inhibitors of Target X," but it is paywalled.
*   **Action:** Agent calls `connect.rightfind_purchase(doi="...")`.
*   **Safety Intercept:** coreason-connect sees `is_consequential: true`. It suspends the agent.
*   **Notification:** Manager receives Slack DM: "Agent X wants to buy this paper ($35). Approve?"
*   **Resolution:** Manager clicks "Approve." connect resumes the agent, executes the purchase via rightfind_client, and returns the download link.

### Story B: The "Meeting Scheduler" (MS Graph)

*   **Context:** Agent needs to convene the "Safety Review Board" urgently.
*   **Action:** Agent calls `connect.ms365_find_slot(attendees=['Dr. Smith', 'Dr. Jones'])`.
*   **Result:** Returns "Tuesday 2 PM."
*   **Action:** Agent calls `connect.ms365_draft_invite(time="Tue 2pm", subject="Safety Review")`.
*   **Outcome:** Invite sits in Dr. Smith's (the user's) Drafts folder for final review before sending.

### Story C: The "Self-Correction" (GitOps)

*   **Context:** Agent modifies a YAML config. The CI pipeline fails 10 minutes later.
*   **Event:** GitHub sends `check_run.completed` webhook (failure).
*   **Listener:** coreason-connect receives webhook, maps it to the Agent ID.
*   **Resume:** Agent wakes up, calls `git_get_build_logs`, reads the error, commits a fix, and updates the PR.

---

## 6. Data Schema & Configuration

### connectors.yaml (The Host Config)

```yaml
plugins:
  - id: "rightfind"
    type: "local_python"
    path: "./local_libs/adapters/rf_adapter.py"
    description: "Search and buy scientific papers."
    env_vars:
      RF_BASE_URL: "https://generated.copyright.com"

  - id: "confex"
    type: "openapi"
    path: "./specs/confex_v1.json"
    base_url: "https://confex.com/api"

  - id: "ms365"
    type: "native"  # Built-in to the package
    scopes: ["Calendars.ReadWrite", "Mail.Send"]
```

### ConnectorProtocol (Python Interface)

```python
class ConnectorProtocol(ABC):
    """The contract that all adapters must fulfill."""

    def __init__(self, secrets: SecretsProvider):
        """Inject vault access at initialization."""
        self.secrets = secrets

    @abstractmethod
    def get_tools(self) -> List[ToolDefinition]:
        """Return list of available MCP tools."""
        pass

    @abstractmethod
    def execute(self, tool_name: str, arguments: dict) -> Any:
        """Execute the logic."""
        pass
```
