# PromptYoSelf MCP Tools Specification (FastMCP)

This document defines the MCP tools exposed by the PromptYoSelf FastMCP server and their request/response contracts. The server directly imports and delegates to the PromptYoSelf CLI module, preserving all existing logic and JSON shapes.

Server entry:
- promptyoself FastMCP server: promptyoself_mcp_server.py

Transports:
- stdio (default), http, sse

Environment:
- LETTA_BASE_URL (default http://localhost:8283)
- LETTA_API_KEY or LETTA_SERVER_PASSWORD (for Letta auth and upload)
- PROMPTYOSELF_DB (default promptyoself.db)

---

## Tool: promptyoself_list

List scheduled prompts, optionally filtered by agent.

Arguments:
- agent_id (str, optional) — Only schedules for this agent
- include_cancelled (bool, optional, default False) — Include cancelled schedules

Success response:
{
  "status": "success",
  "schedules": [
    {
      "id": 42,
      "agent_id": "agent-123",
      "prompt_text": "Daily report",
      "schedule_type": "cron" | "once" | "interval",
      "schedule_value": "0 9 * * *",
      "next_run": "2025-01-02T09:00:00+00:00",
      "active": true,
      "created_at": "2025-01-01T09:00:00+00:00",
      "last_run": null,
      "max_repetitions": null,
      "repetition_count": 0
    }
  ],
  "count": 1
}

Error response:
- {"error": "Failed to list prompts: <exception>"}

---

## Tool: promptyoself_schedule_time

Schedule a one-time prompt at an exact datetime.

Inputs
- agent_id (str, optional)
- prompt (str, required)
- time (str, required) — ISO 8601 datetime in the future. Accepted forms:
  - 2025-08-31T09:50:22Z (UTC)
  - 2025-08-31T09:50:22+00:00 (offset)
  - 2025-08-31 09:50:22 UTC (normalized to Z)
- skip_validation (bool, optional, default False)

Example
{
  "agent_id": "agt_abc123",
  "prompt": "Ping me once",
  "time": "2025-12-25T10:00:00Z"
}

---

## Tool: promptyoself_schedule_cron

Schedule a recurring prompt using a cron expression.

Inputs
- agent_id (str, optional)
- prompt (str, required)
- cron (str, required) — Standard 5-field cron (m h dom mon dow). Examples:
  - "0 9 * * *" (every day at 09:00)
  - "*/15 * * * *" (every 15 minutes)
  - "0 9 * * MON-FRI" (weekdays at 09:00) if your cron parser supports names
- skip_validation (bool, optional, default False)

Example
{
  "agent_id": "agt_abc123",
  "prompt": "Daily standup",
  "cron": "0 9 * * *"
}

---

## Tool: promptyoself_schedule_every

Schedule a repeating prompt using an interval.

Inputs
- agent_id (str, optional)
- prompt (str, required)
- every (str, required) — Interval like "30s", "5m", or "1h" (integer seconds allowed, e.g., "45")
- start_at (str, optional) — ISO datetime in the future when the interval should begin
- max_repetitions (int, optional) — Positive cap on repeats
- skip_validation (bool, optional, default False)

Example
{
  "agent_id": "agt_abc123",
  "prompt": "Focus check",
  "every": "30m",
  "start_at": "2025-01-02T15:00:00Z",
  "max_repetitions": 10
}

---

## Agent ID Inference & Diagnostics

PromptYoSelf needs a valid Letta `agent_id` to deliver prompts. You can provide it explicitly, or let the server infer it in this order:
- context metadata (if your MCP client forwards it),
- environment variables set on the server process,
- single-agent fallback (if enabled and exactly one agent exists).

Supported context metadata keys:
- `metadata.agent_id`, `metadata.agentId`, `metadata.letta_agent_id`, `metadata.caller_agent_id`
- Nested: `metadata.agent.id`, `metadata.agent.agent_id`, `metadata.agent.agentId`
- Direct attribute: `ctx.agent_id`

Environment variables (set on the MCP server process):
- `PROMPTYOSELF_DEFAULT_AGENT_ID`
- `LETTA_AGENT_ID`
- `LETTA_DEFAULT_AGENT_ID`
- Optional fallback: `PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK=true`

Quick env examples:
- Bash (shell):
  - `export PROMPTYOSELF_DEFAULT_AGENT_ID=agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a`
  - `export PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK=true`
- systemd service:
  - In your unit file under `[Service]`:
    - `Environment=PROMPTYOSELF_DEFAULT_AGENT_ID=agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a`
    - `Environment=PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK=true`
- Docker Compose:
  -
    - `environment:`
    - `  - PROMPTYOSELF_DEFAULT_AGENT_ID=agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a`
    - `  - PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK=true`
- Kubernetes Deployment:
  - Under `spec.template.spec.containers.env`:
    - `- name: PROMPTYOSELF_DEFAULT_AGENT_ID`
    - `  value: agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a`
    - `- name: PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK`
    - `  value: "true"`
- GitHub Actions:
  - `env:`
    - `PROMPTYOSELF_DEFAULT_AGENT_ID: agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a`

Diagnostics tool:
- Use `promptyoself_inference_diagnostics` to see what the server can infer for the current request. It returns:
  - `inferred_agent_id` and `inference_debug` with `source`, context keys seen, env presence, and fallback flags.

Example result (abbreviated):
```
{
  "status": "ok",
  "ctx_present": true,
  "ctx_metadata_keys": ["agent_id"],
  "env": {"PROMPTYOSELF_DEFAULT_AGENT_ID": false, "LETTA_AGENT_ID": true, "LETTA_DEFAULT_AGENT_ID": false},
  "single_agent_fallback_enabled": false,
  "inferred_agent_id": "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a",
  "inference_debug": {"source": "env", "key": "LETTA_AGENT_ID"}
}
```

Recipe: two minutes from now
- Use interval once:
```
{
  "prompt": "Ping me in two minutes",
  "every": "2m",
  "max_repetitions": 1
}
```
Note: still requires a resolvable `agent_id` via explicit arg, ctx, or env.

---

## Tool: promptyoself_cancel

Cancel a scheduled prompt by ID.

Arguments:
- schedule_id (int, required)

Success response:
{
  "status": "success",
  "cancelled_id": 42,
  "message": "Schedule 42 cancelled"
}

Error responses:
- {"error": "Schedule ID must be a number"}
- {"error": "Schedule 42 not found or already cancelled"}
- {"error": "Failed to cancel prompt: <exception>"}

---

## Agent ID Inference

When `agent_id` is not provided, the server tries to infer it in this order:

- Context metadata: If the MCP client provides `ctx.metadata` with `agent_id`/`agentId`/`letta_agent_id`/`caller_agent_id`, or a direct `ctx.agent_id` attribute.
- Environment defaults: `PROMPTYOSELF_DEFAULT_AGENT_ID`, `LETTA_AGENT_ID`, or `LETTA_DEFAULT_AGENT_ID`.
- Single‑agent fallback: If `PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK=true` and the Letta server lists exactly one agent, it will be used.

If none of these yield an agent ID, the request fails with `{ "error": "agent_id is required and could not be inferred" }`. In multi‑agent setups, prefer explicit `agent_id`.

---

## Tool: promptyoself_execute

Execute due prompts once, or run in loop mode.

Arguments:
- loop (bool, optional, default False) — If true, run scheduler loop
- interval (int, optional, default 60) — Loop interval in seconds (only when loop=true)

Once-mode success response:
{
  "status": "success",
  "executed": [
    {
      "id": 42,
      "agent_id": "agent-123",
      "delivered": true,
      "next_run": null,
      "repetition_count": 1,
      "max_repetitions": null,
      "completed": false
    }
  ],
  "message": "1 prompts executed"
}

Loop-mode success response:
{
  "status": "success",
  "message": "Scheduler loop completed"
}

Error responses:
- {"error": "Interval must be a number (seconds)"} (when loop=true)
- {"error": "Failed to execute prompts: <exception>"}

Note:
- Loop mode is a long-running operation; ensure a single loop instance to avoid DB locks.

---

## Tool: promptyoself_test

Test connectivity to the Letta server.

Arguments:
- (none)

Success response:
- Shape delegated to promptyoself.letta_api.test_letta_connection(), typically:
{
  "status": "success",
  "message": "Connected",
  "details": { "...": "..." }
}

Error response:
- {"error": "Failed to test connection: <exception>"}

---

## Tool: promptyoself_agents

List available Letta agents.

Arguments:
- (none)

Success response:
{
  "status": "success",
  "agents": [
    {"id": "agent-123", "name": "Support", "description": "..."},
    {"id": "agent-456", "name": "Research", "description": "..."}
  ]
}

Error response:
- {"error": "Failed to list agents: <exception>"}

---

## Tool: promptyoself_upload

Upload a Letta-native tool from complete Python source code.

Arguments:
- source_code (str, required) — Complete top-level Python function with docstring and type hints
- name (str, optional) — Optional reference name for logs
- description (str, optional) — Optional description stored in Letta

Auth:
- Requires LETTA_API_KEY or LETTA_SERVER_PASSWORD
- Uses LETTA_BASE_URL (default http://localhost:8283)

Success response:
{
  "status": "success",
  "tool_id": "<tool_id>",
  "name": "<derived_or_none>"
}

Error responses:
- {"error": "Missing LETTA_API_KEY or LETTA_SERVER_PASSWORD"}
- {"error": "Upload failed: <exception>"}

---

## Health tool

Utility health tool to report configuration state.

Arguments:
- (none)

Success response:
{
  "status": "healthy",
  "letta_base_url": "http://localhost:8283",
  "db": "promptyoself.db",
  "auth_set": true
}

---

## Examples

Register (cron):
{
  "agent_id": "agent-123",
  "prompt": "Daily report",
  "cron": "0 9 * * *"
}

Register (interval with start):
{
  "agent_id": "agent-123",
  "prompt": "Focus check",
  "every": "5m",
  "max_repetitions": 10,
  "start_at": "2025-01-02T15:00:00Z"
}

List:
{
  "agent_id": "agent-123",
  "include_cancelled": false
}

Cancel:
{
  "schedule_id": 42
}

Execute (once):
{
  "loop": false
}

Execute (loop):
{
  "loop": true,
  "interval": 60
}
