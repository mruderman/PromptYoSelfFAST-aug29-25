# PromptYoSelf Plugin Developer Guide

## Project Overview

PromptYoSelf is a self-hosted prompt scheduler plugin for the Letta AI framework, designed to be run as a tool server via FastMCP. It allows AI agents to schedule prompts for future delivery to themselves or other agents, supporting one-time, interval, and cron-based schedules.

The system has undergone a significant architectural update. It now uses a unified database schema to potentially support both the CLI/MCP interface and a web interface, although the web interface components are not part of this plugin.

## External Resources

This plugin interacts with two main external systems. The following links provide essential documentation for developers working on this plugin:

*   **FastMCP Documentation:** `https://gofastmcp.com/llms.txt`
*   **Letta SDK Documentation:** `https://docs.letta.com/llms.txt`

## Core Architecture

The plugin is composed of several key Python modules:

1.  **`cli.py` (CLI and Tool Definitions):**
    *   Provides a command-line interface for managing schedules using `argparse`.
    *   Defines the `promptyoself_*` functions that are exposed as tools through the FastMCP server.
    *   Contains an undocumented `upload` command for registering new tools with the Letta server.

2.  **`db.py` (Database Layer):**
    *   Uses SQLAlchemy to manage a SQLite database.
    *   **Main Table:** `unified_reminders`. This is the primary table for all new schedules. It has a flexible structure intended to support multiple interfaces.
    *   **Legacy Table:** `schedules`. This table (`PromptSchedule` model) is kept for backward compatibility but is not used by the core logic anymore.
    *   **Adapter:** A `CLIReminderAdapter` is used to map data between the `unified_reminders` table and the format expected by the CLI tools, maintaining a consistent interface despite the schema change.

3.  **`scheduler.py` (Scheduling Engine):**
    *   Contains the logic for calculating when schedules should run next.
    *   The `execute_due_prompts` function queries the database for due schedules, sends them to the target agent via the Letta API, and reschedules them if necessary.
    *   Uses the `apscheduler` library to run the execution loop in the background (daemon mode).
    *   Correctly operates on the new `UnifiedReminder` database objects.

4.  **`letta_api.py` (Letta Integration):**
    *   Manages all communication with the external Letta service using the `letta-client` SDK.
    *   Handles authentication, agent validation, and prompt delivery.
    *   Includes robust features like retry logic with exponential backoff and a specific fallback to a streaming API to handle a "ChatML bug".

5.  **`promptyoself_mcp_server.py` (MCP Server):**
    *   The main entry point for running the plugin as a service.
    *   Uses the FastMCP framework to expose the functions from `cli.py` as tools that can be called by an MCP client (such as a Letta agent).

## Database Schema

The primary table is `unified_reminders`. The old `schedules` table is deprecated.

**`unified_reminders` table:**

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | Integer | Primary Key |
| `message` | Text | The content of the prompt. |
| `next_run` | DateTime | The timestamp for the next scheduled execution. |
| `status` | String | The current status of the reminder (e.g., "pending"). |
| `active` | Boolean | Whether the schedule is currently active. |
| `schedule_type` | String | The type of schedule: `once`, `cron`, or `interval`. |
| `schedule_value` | String | The value for the schedule (e.g., cron string, interval duration). |
| `max_repetitions`| Integer | Optional limit for how many times an interval schedule should run. |
| `repetition_count`| Integer | How many times an interval schedule has already run. |
| `agent_id` | String | The ID of the target Letta agent. |
| `...` | | Other fields for web UI integration (`task_id`, `user_id`, etc.). |

## Key Commands (CLI)

The command-line interface is the primary way to interact with the plugin manually.

```bash
# Register a one-time prompt
python -m promptyoself.cli register --agent-id <agent_id> --prompt "My prompt" --time "2025-01-01T10:00:00"

# Register a recurring prompt with a cron string
python -m promptyoself.cli register --agent-id <agent_id> --prompt "Daily check-in" --cron "0 9 * * *"

# Register an interval-based prompt that runs every 15 minutes
python -m promptyoself.cli register --agent-id <agent_id> --prompt "Ping" --every "15m"

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

The project includes unit, integration, and end-to-end tests using `pytest`.

*   **Test Infrastructure (`tests/conftest.py`):** Provides fixtures for running tests against an in-memory server and a live HTTP server process. This part of the test suite is well-maintained.
*   **Unit Tests (`tests/unit/`):** These tests are intended to test individual modules in isolation. **WARNING:** Most of these tests are severely outdated and broken due to the architectural changes. They need to be rewritten.
*   **Integration & E2E Tests (`tests/integration/`, `tests/e2e/`):** These tests use the `fastmcp` client to test the server. They are in better shape but are very basic and could be expanded.

To run the full test suite, use the `pytest` command from the root of the repository. The configuration in `pytest.ini` will automatically pick up the correct settings.
