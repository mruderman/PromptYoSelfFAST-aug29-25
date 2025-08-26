# PromptYoSelf FastMCP Server

A lightweight, reliable MCP server exposing the PromptYoSelf CLI plugin as first-class MCP tools. This replaces the broken Sanctum server path with a simple, maintainable FastMCP-based design.

Key properties:
- Single-file server: promptyoself_mcp_server.py
- Tools map directly to PromptYoSelf CLI functions (no subprocess shelling)
- Supports stdio (local) and HTTP/SSE (remote) transports
- Reuses existing DB, scheduler, and Letta integration from the plugin

Archived legacy content:
- The previous Sanctum server and docs were archived under archive/sanctum/

## Why this approach

- Minimal surface area: No custom protocol plumbing; FastMCP handles MCP
- Reliability: Leverages the existing, tested PromptYoSelf CLI internals
- Portability: stdio for local agents; HTTP/SSE for remote usage
- Maintainability: Clear mapping of CLI commands to MCP tools

## Prerequisites

- Python 3.10+
- pip

## Install

- Core server and tests:
  ```
  pip install -r requirements.txt
  ```
- PromptYoSelf plugin dependencies:
  ```
  pip install -r smcp/plugins/promptyoself/requirements.txt
  ```

Note: requirements.txt now includes fastmcp>=2.7.

## Run

- STDIO (local CLI-style integration):
  ```
  python promptyoself_mcp_server.py
  ```
- HTTP server on 127.0.0.1:8000:
  ```
  python promptyoself_mcp_server.py --transport http --host 127.0.0.1 --port 8000 --path /mcp
  ```
- SSE server on 127.0.0.1:8000 (legacy):
  ```
  python promptyoself_mcp_server.py --transport sse --host 127.0.0.1 --port 8000
  ```

Environment variables (optional):
- LETTA_BASE_URL (default http://localhost:8283)
- LETTA_API_KEY or LETTA_SERVER_PASSWORD (for Letta auth)
- PROMPTYOSELF_DB (defaults to promptyoself.db)

## Tools

All tools return JSON-friendly dictionaries. Errors are returned as {"error": "..."}.

- promptyoself_register(agent_id, prompt, time=None, cron=None, every=None, skip_validation=False, max_repetitions=None, start_at=None)
  - Registers a schedule for an agent
  - Returns on success:
    ```
    {
      "status": "success",
      "id": <int>,
      "next_run": "<ISO timestamp>",
      "message": "Prompt scheduled with ID <id>"
    }
    ```
  - Validation:
    - specify exactly one of time, cron, every
    - time/start_at must be in the future
    - every supports "Xs"/"Xm"/"Xh" or raw seconds

- promptyoself_list(agent_id=None, include_cancelled=False)
  - Lists schedules, optionally filtering by agent
  - Returns:
    ```
    {
      "status": "success",
      "schedules": [...],
      "count": <int>
    }
    ```

- promptyoself_cancel(schedule_id)
  - Cancels a schedule by numeric ID
  - Returns:
    ```
    {
      "status": "success",
      "cancelled_id": <int>,
      "message": "Schedule <id> cancelled"
    }
    ```

- promptyoself_execute(loop=False, interval=60)
  - Executes due prompts once or runs a scheduler loop
  - Returns once mode:
    ```
    {
      "status": "success",
      "executed": [...],
      "message": "N prompts executed"
    }
    ```
  - Returns loop mode:
    ```
    {
      "status": "success",
      "message": "Scheduler loop completed"
    }
    ```

- promptyoself_test()
  - Tests Letta connectivity
  - Returns a result dict from the Letta client (status/message)

- promptyoself_agents()
  - Lists available Letta agents
  - Returns:
    ```
    {
      "status": "success",
      "agents": [...]
    }
    ```

- promptyoself_upload(source_code, name=None, description=None)
  - Uploads a Letta-native tool from full function source code
  - Requires LETTA_API_KEY or LETTA_SERVER_PASSWORD
  - Returns:
    ```
    {
      "status": "success",
      "tool_id": "<id>",
      "name": "<derived_name_or_none>"
    }
    ```

- health()
  - Returns a simple health/config summary:
    ```
    {
      "status": "healthy",
      "letta_base_url": "...",
      "db": "...",
      "auth_set": true|false
    }
    ```

## Architecture

```mermaid
flowchart TD
  A[AI Client (Claude/Letta ADE)] -->|MCP tools| B[FastMCP Server]
  B -->|tool call| C[PromptYoSelf CLI functions]
  C --> D[SQLite DB (promptyoself.db)]
  C --> E[Letta API (LETTA_BASE_URL)]
  C --> F[Scheduler Engine]
```

## File Map

- promptyoself_mcp_server.py — FastMCP server exposing the tools above
- smcp/plugins/promptyoself/cli.py — CLI entry (imported by the server)
- smcp/plugins/promptyoself/db.py — DB models/operations
- smcp/plugins/promptyoself/scheduler.py — Execution/scheduling
- smcp/plugins/promptyoself/letta_api.py — Letta client integration
- archive/sanctum/** — Archived legacy Sanctum server and docs

## Client integration

- STDIO mode: configure client to spawn the Python process
- HTTP mode: point client to http://host:port/path (default /mcp)
- SSE mode: point client to http://host:port/sse (legacy)

Refer to FastMCP docs for client patterns and transports. Tools are auto-namespaced by the server label in most clients.

## Migration notes

- The old Sanctum server is archived; this repo no longer relies on it
- PromptYoSelf plugin code remains the source of truth for scheduling
- Tests should target the new FastMCP server endpoints or in-memory transport

## Troubleshooting

- "No Letta client configured": Set LETTA_API_KEY or LETTA_SERVER_PASSWORD
- "Agent not found": Verify with promptyoself_agents
- "Database locked": Ensure only one scheduler loop is running
- Schedules not executing: Try promptyoself_execute(loop=True, interval=60) and check logs

## Next steps

- Add launch scripts for stdio and HTTP modes
- Add unit tests with in-memory FastMCP transport
- Update docs/Letta-MCP-Connection-Guide.md mapping to the new server
- Document the exact JSON contracts (per-tool) for external automation