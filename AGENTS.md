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
python -m promptyoself.cli register --agent-id <agent_id> --prompt "My prompt" --time "2025-01-01T10:00:00Z"

# Register a recurring prompt with a cron string
python -m promptyoself.cli register --agent-id <agent_id> --prompt "Daily check-in" --cron "0 9 * * *"

# Register an interval-based prompt that runs every 15 minutes
python -m promptyoself.cli register --agent-id <agent_id> --prompt "Ping" --every "15m" --start-at "2025-01-02T15:00:00Z" --max-repetitions 10

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

Note: Coverage enforcement is temporarily set to 35% (see `pytest.ini`) while additional tests land; the goal is to step back up toward 80%.

MCP HTTP is not a REST API; use an MCP client (e.g., FastMCP Client) to call tools like `health`.

## MCP Tools (Strict only)

The server exposes strict variants to help ADE and other clients validate inputs and avoid ambiguous arguments:

- `promptyoself_schedule_time` – one-time schedule with an ISO-8601 `time` string.
- `promptyoself_schedule_cron` – recurring schedule with a 5-field `cron` expression.
- `promptyoself_schedule_every` – interval schedule with `every` (e.g., `30m`), optional `start_at`, and optional `max_repetitions`.
