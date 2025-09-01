# PromptYoSelf Plugin Developer Guide

This document was moved from `promptyoself/AGENTS.md` to the repository root to make it more visible.

## Project Overview

PromptYoSelf is a self-hosted prompt scheduler plugin for the Letta AI framework, designed to be run as a tool server via FastMCP. It allows AI agents to schedule prompts for future delivery to themselves or other agents, supporting one-time, interval, and cron-based schedules.

The system has undergone a significant architectural update. It now uses a unified database schema to potentially support both the CLI/MCP interface and a web interface, although the web interface components are not part of this plugin.

## External Resources

This plugin interacts with two main external systems. The following links provide essential documentation for developers working on this plugin:

- FastMCP Documentation: <https://gofastmcp.com/llms.txt>
- Letta SDK Documentation: <https://docs.letta.com/llms.txt>

## Core Architecture

The plugin is composed of several key Python modules:

1. `cli.py` (CLI and Tool Definitions):
   - Provides a command-line interface for managing schedules using `argparse`.
   - Defines the `promptyoself_*` functions that are exposed as tools through the FastMCP server.
   - Contains an undocumented `upload` command for registering new tools with the Letta server.

2. `db.py` (Database Layer):
   - Uses SQLAlchemy to manage a SQLite database.
   - Primary Table: `unified_reminders` (used by MCP/CLI path).
   - Legacy Table: `schedules` (kept for backward compatibility; not used by new inserts).
   - Adapter: `CLIReminderAdapter` maps data between the `unified_reminders` table and the CLI-facing format.

3. `scheduler.py` (Scheduling Engine):
   - Calculates next-run times for schedules.
   - `execute_due_prompts` sends due prompts to the target agent via the Letta API and reschedules as needed.
   - Uses `apscheduler` to run the execution loop in the background.

4. `letta_api.py` (Letta Integration):
   - Communicates with the Letta service using the `letta-client` SDK.
   - Handles authentication, agent validation, and prompt delivery.
   - Includes retry logic with exponential backoff and a streaming fallback for a known ChatML issue.

5. `promptyoself_mcp_server.py` (MCP Server):
   - Entry point for running the plugin as a service.
   - Uses FastMCP to expose functions from `cli.py` as MCP tools.
   - Supports stdio, HTTP, and SSE transports. For private remote access, you can bind HTTP to a Tailscale IP (see `start.sh tailscale`).

## Database Schema

Primary table: `unified_reminders`. The legacy `schedules` table remains for compatibility but is not used by new code paths.

| Column | Type | Description |
| :--- | :--- | :--- |
| id | Integer | Primary Key |
| message | Text | The content of the prompt |
| next_run | DateTime | Timestamp for the next scheduled execution |
| status | String | Current status (e.g., "pending") |
| active | Boolean | Whether the schedule is active |
| schedule_type | String | `once`, `cron`, or `interval` |
| schedule_value | String | Cron string or interval duration |
| max_repetitions | Integer | Optional max runs for interval schedules |
| repetition_count | Integer | Number of times already run |
| agent_id | String | Target Letta agent ID |

## CLI Commands

```bash
# Register a one-time prompt
python -m promptyoself.cli register --agent-id <agent_id> --prompt "My prompt" --time "2025-12-25T10:00:00Z"

# Register a recurring prompt with a cron string
python -m promptyoself.cli register --agent-id <agent_id> --prompt "Daily check-in" --cron "0 9 * * *"

# Register an interval-based prompt that runs every 15 minutes
python -m promptyoself.cli register --agent-id <agent_id> --prompt "Ping" --every "15m" --start-at "2025-12-26T15:00:00Z" --max-repetitions 10

# List all active schedules
python -m promptyoself.cli list

# Cancel a schedule by its ID
python -m promptyoself.cli cancel --id <schedule_id>

# Execute all due prompts once
python -m promptyoself.cli execute

# Run the scheduler in a continuous loop (daemon mode)
python -m promptyoself.cli execute --loop --interval 60

# Test the connection to the Letta server
python -m promptyoself.cli test

# List all available agents on the Letta server
python -m promptyoself.cli agents

# Upload a new tool to the Letta server (undocumented feature)
python -m promptyoself.cli upload --source-code "def my_tool(): ..." --description "My new tool"
```

## Testing

- Test infrastructure (tests/conftest.py) provides fixtures for in-memory and live HTTP server tests.
- Unit tests under tests/unit/ need updates to match the new architecture.
- Integration and E2E tests (tests/integration/, tests/e2e/) use fastmcp and cover basic flows.

Run the full test suite from repo root:

```bash
pytest
```

Note: Coverage enforcement is set to 67% (see `pytest.ini`).

MCP HTTP is not a REST API; use an MCP client (e.g., FastMCP Client) to call tools like `health`.

## MCP Tools (Primary - Strict only)

The server exposes these strict variants as the primary scheduling tools to ensure clear, unambiguous API usage. These are the recommended tools for all scheduling operations, providing better validation and simpler schemas for ADE and other clients:

- `promptyoself_schedule_time` – Schedule a one-time prompt at an exact datetime. Requires `agent_id`, `prompt`, and `time` (ISO 8601 datetime in the future). Optional `skip_validation`.
- `promptyoself_schedule_cron` – Schedule a recurring prompt using a cron expression. Requires `agent_id`, `prompt`, and `cron` (5-field cron expression). Optional `skip_validation`.
- `promptyoself_schedule_every` – Schedule a repeating prompt using an interval. Requires `agent_id`, `prompt`, and `every` (interval like "30s", "5m", "1h"). Optional `start_at`, `max_repetitions`, and `skip_validation`.

**Important Note:** Always use future timestamps in examples and actual usage. Past timestamps will be rejected by the scheduler.

## Letta MCP (Managed) — Recommended

For production, add PromptYoSelf as a managed MCP server in Letta and register all tools under the server name `promptyoself`. This avoids per‑call server selectors and reduces ADE wrapper friction.

Quick steps (self‑hosted, Tailscale):

```bash
export LETTA_URL="http://100.126.136.121:8283"           # Letta server over Tailscale
export LETTA_TOKEN="$LETTA_SERVER_PASSWORD"              # SECURE=true auth

# Add managed MCP server
curl -sS -X PUT "$LETTA_URL/v1/tools/mcp/servers" \
  -H "Authorization: Bearer $LETTA_TOKEN" -H "Content-Type: application/json" \
  -d '{"server_name":"promptyoself","type":"streamable_http","server_url":"http://100.76.47.25:8000/mcp"}'

# Register tools
for T in promptyoself_inference_diagnostics promptyoself_set_default_agent promptyoself_set_scoped_default_agent promptyoself_get_scoped_default_agent promptyoself_schedule_time promptyoself_schedule_cron promptyoself_schedule_every promptyoself_list promptyoself_cancel promptyoself_execute promptyoself_test promptyoself_agents promptyoself_upload health; do
  curl -sS -X POST "$LETTA_URL/v1/tools/mcp/servers/promptyoself/$T" \
    -H "Authorization: Bearer $LETTA_TOKEN" -H "Content-Type: application/json"; echo
done

# Attach to agent
AGENT_ID="agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"
curl -sS "$LETTA_URL/v1/tools/mcp/servers/promptyoself/tools" -H "Authorization: Bearer $LETTA_TOKEN" | jq -r '.[].id' | while read -r TID; do
  curl -sS -X PATCH "$LETTA_URL/v1/agents/$AGENT_ID/tools/attach/$TID" \
    -H "Authorization: Bearer $LETTA_TOKEN" -H "Content-Type: application/json"; echo
done
```

Then send your agent a smoke test message to verify diagnostics, schedule/list/cancel flows.

Wrapper tip: If you do use ADE wrappers, do not require `mcp_server_id`; prefer optional `mcp_server_name` defaulting to `promptyoself`. The MCP server accepts and ignores pass‑through fields like `mcp_server_name`/`request_heartbeat`.

## Agent ID Handling

Most tools require a target Letta `agent_id`. You can provide it explicitly or rely on inference. Inference order:

1. Request context metadata from the MCP client (e.g., `ctx.request_context.metadata.agent_id`, or nested `metadata.agent.id`).
2. Per‑client/session scoped default (set via `promptyoself_set_scoped_default_agent`).
3. Environment defaults set on the server process (`PROMPTYOSELF_DEFAULT_AGENT_ID`, `LETTA_AGENT_ID`, `LETTA_DEFAULT_AGENT_ID`).
4. Optional single‑agent fallback if `PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK=true` and exactly one agent exists.

Notes:
- If context explicitly includes an invalid/null `agent_id`, the server treats that as authoritative and will not fall back.
- Schedule tools accept `agent_id` or the alias `agentId` for compatibility with clients that use camelCase.

Diagnostics and helpers:
- `promptyoself_inference_diagnostics {}` — shows what `agent_id` would be used and why.
- `promptyoself_set_default_agent { "agent_id": "agt_..." }` — sets a process‑local default (env) for this server session.
- `promptyoself_set_scoped_default_agent { "agent_id": "agt_..." }` — sets a per‑client/session default without changing env.
- `promptyoself_get_scoped_default_agent {}` — returns the scoped default for the current client/session.

## start.sh Convenience Script

`start.sh` activates a local venv, loads `.env`, supports default agent flags, and can bind HTTP to your Tailscale IP.

Examples:

```bash
# HTTP on localhost with explicit default agent
./start.sh http --agent-id agt_abc123 --port 8000 --path /mcp

# Enable single‑agent fallback and source an additional env file
./start.sh http --single --env-file ./prod.env

# Bind to your Tailscale IPv4 (auto‑detected)
./start.sh tailscale --port 8000 --path /mcp

# HTTP with host resolved to Tailscale IP
./start.sh http --host tailscale --port 8000 --path /mcp
```

Relevant env:

```bash
export LETTA_AGENT_ID=agt_...
export PROMPTYOSELF_DEFAULT_AGENT_ID=agt_...
export PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK=true  # optional
```

## Multi‑Agent Usage

When multiple Letta agents share the same PromptYoSelf server:
- Prefer explicit `agent_id` per call, or
- Set a scoped default per client/session so each Letta client automatically uses its own agent, or
- Avoid enabling single‑agent fallback.
