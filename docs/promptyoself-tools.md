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

Status conventions:
- Success returns a dict with "status": "success" (and additional fields)
- Errors return a dict with "error": "message"

---

## Tool: promptyoself_register

Register a new scheduled prompt for a Letta agent.

Arguments:
- agent_id (str, required) — Target Letta agent ID
- prompt (str, required) — Prompt content
- time (str, optional) — ISO datetime for one-time schedule (e.g., 2025-12-25T10:00:00)
- cron (str, optional) — Cron expression for recurring schedule (e.g., "0 9 * * *")
- every (str, optional) — Interval expression for recurring schedules, supported formats:
  - "30s" (seconds), "5m" (minutes), "1h" (hours), or integer seconds (e.g., "45")
- skip_validation (bool, optional, default False) — Skip agent existence validation
- max_repetitions (int, optional) — Max repeat count for interval schedules (must be positive)
- start_at (str, optional) — ISO datetime for when interval schedules should begin (must be in the future)

Validation rules:
- Exactly one of time, cron, every must be provided
- time and start_at must be in the future
- cron must be a valid cron expression
- every must parse as seconds (via suffix or integer)
- max_repetitions must be positive if provided

Success response:
{
  "status": "success",
  "id": <int>,
  "next_run": "<ISO timestamp>",
  "message": "Prompt scheduled with ID <id>"
}

Error responses:
- {"error": "Missing required arguments: agent-id and prompt"}
- {"error": "Must specify one of --time, --cron, or --every"}
- {"error": "Cannot specify multiple scheduling options"}
- {"error": "Agent validation failed: <message>"} (unless skip_validation)
- {"error": "Scheduled time must be in the future"}
- {"error": "Invalid cron expression: <expr>"}
- {"error": "Invalid interval format: <every>. Use formats like '30s', '5m', '1h'"}
- {"error": "max-repetitions must be a positive integer"}
- {"error": "Failed to register prompt: <exception>"}

Example:
{
  "status": "success",
  "id": 42,
  "next_run": "2025-01-01T14:30:00+00:00",
  "message": "Prompt scheduled with ID 42"
}

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
      "schedule_id": 42,
      "agent_id": "agent-123",
      "prompt_text": "Daily report",
      "sent": true,
      "error": null
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
- Shape delegated to smcp.plugins.promptyoself.letta_api.test_letta_connection(), typically:
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
  "start_at": "2025-01-02T15:00:00"
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