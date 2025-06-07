# MCP (Master Control Program) — Internal Tools Orchestration Daemon (STDIO Edition)

## Overview

The MCP is a modular, extensible **internal orchestration daemon** designed to securely expose command-line tools and automation scripts ("plugins") to trusted agents, operators, and internal systems. It centralizes control of critical automations—such as Telegram bot management (BotFather), devops scripts, or other host-level tasks—behind a unified, queue-based STDIO protocol.

**MCP is for internal use only:**
It should be deployed behind the firewall, on trusted hosts, and *never* exposed to the public internet.

---

## Key Features

* **Modular Plugin Architecture:**
  Each supported command-line tool or script is registered as a "plugin" (e.g., `botfather`, `devops`, `monitoring`, etc.).
* **Unified STDIO Protocol:**
  All tools are accessible via a single STDIO message protocol (newline-delimited JSON).
* **Queue/Serialization:**
  Jobs are queued and executed serially by default (to prevent resource contention and concurrency bugs).
* **Extensible:**
  New plugins/tools can be added easily—no core MCP changes required.
* **Help/Introspection:**
  Agents and humans can query available plugins/commands and usage details via the `help` command.
* **Pluggable Timeouts:**
  Each job may specify a custom timeout; MCP enforces a default but allows override per job.
* **Audit Logging:**
  All job requests and results are logged (with sensitive data redacted) for audit and debugging.

---

## MCP Architecture (STDIO)

* **mcp_stdio.py** — Main daemon script. Reads JSON requests from `stdin`, routes them to plugins, writes JSON responses to `stdout`.
* **plugins/** — Directory for all available command-line tools/scripts (each as a module/wrapper)
* **queue/** — Job management/serialization (using `queue.Queue`)
* **.env / config** — Environment variables and sensitive credentials (never logged)
* **README.md / docs/** — Documentation for devs and agents

---

## STDIO Message Protocol

### Request (stdin → MCP)
```json
{
  "id": "uuid4",
  "command": "run" | "help" | "reload-help" | "health",
  "payload": {
    // only for "run"
    "plugin": "botfather",
    "action": "send-message",
    "args": {"msg": "/newbot"},
    "timeout": 60
  }
}
```
*One JSON object per line. Always end with `\n` and flush.*

### Response (MCP → stdout)
```json
{
  "id": "same-uuid4",
  "status": "queued" | "started" | "success" | "error" | "timeout",
  "payload": { /* result or error info */ }
}
```
*Multiple status events per job (`queued` → `started` → terminal state).* 

---

## Commands

- `run`: Execute a plugin action
- `help`: Return help cache
- `reload-help`: Rebuild help cache
- `health`: Return health status

---

## Error Handling

| Condition                   | MCP `status` | `payload.error`              |
| --------------------------- | ------------ | ---------------------------- |
| CLI exits non-zero          | "error"      | stderr or parsed error field |
| Timeout                     | "timeout"    | "timeout"                   |
| JSON decode fail            | "error"      | "bad_json"                  |
| Unknown plugin / action     | "error"      | "not_found"                 |

---

## Plugin (Tool) Requirements

* **CLI-based:**
  Plugins must be executable as command-line scripts, accept arguments, and print results to stdout (JSON only).
* **Exit Codes:**
  Must return exit code 0 for success, nonzero for error (with error info in output).
* **Output Format:**
  Must return JSON on both success and error.
* **Timeout-Aware:**
  Should not run longer than needed. MCP enforces a global or per-job timeout, but plugins should also fail gracefully if interrupted.

---

## Queue Implementation

* **In-memory queue** for v1 (jobs do not survive restarts)
* **Single worker thread** for job serialization
* **Job Status Tracking:**
  - Unique job ID per request
  - Status states: queued, started, success, error, timeout

---

## Security Model

* **Internal use only** (no network exposure)
* **File permissions** and environment variable secrets
* **Audit logging** (no sensitive data)
* **Plugin input validation**

---

## Monitoring and Observability

* **Log file:** All job invocations and results are logged to `mcp.log`
* **Health check:** Use the `health` command via STDIO
* **Metrics:** (Optional/future) Prometheus/Grafana integration if needed

---

## Deployment Strategy

* **Single instance** for v1
* **Docker/container support** (optional)
* **Config via `.env`**

---

## Plugin Folder Structure and Autodiscovery

- Each plugin must reside in its own directory under `plugins/` (e.g., `plugins/botfather/`).
- Each plugin directory must contain a `cli.py` entrypoint script.
- MCP will automatically discover plugins by scanning the `plugins/` directory for subdirectories containing a `cli.py` file.
- MCP will use `python plugins/<plugin>/cli.py --help` and `python plugins/<plugin>/cli.py <command> --help` to introspect available commands and arguments via argparse.
- All plugin commands and arguments must be documented and addressable via argparse in CLI mode.
- Plugin output must be JSON (success or error), and exit codes must follow the convention: 0 = success, nonzero = error.

---

## Example Directory Structure

```
mcp/
  plugins/
    botfather/
      cli.py
      utils.py
    devops/
      cli.py
      deploy.py
```

---

## Best Practices

* Plugin output and errors must always be parseable by MCP.
* Never run more than one Telethon/SQLite-based plugin action at a time (serialization is handled by MCP queue).
* Timeout is overridable for long-running jobs (specify in request payload).
* Document every command in plugin help so agents can stay in sync.

---

## Summary

MCP is a universal "internal API for command-line tools," allowing your stack to coordinate automations, bot management, and DevOps with perfect isolation and serialization.

First up: BotFather CLI plugin.
Next: Add any host-level or agent action as you scale.

---

# [ARCHIVE] Legacy HTTP/SSE API (for historical context)

_The following sections describe the original HTTP/SSE API, which is no longer implemented. MCP is now STDIO-only. This is retained for reference only._

## **MCP Architecture**

* **mcp.py** — Main server script (Flask, FastAPI, or similar lightweight framework)
* **plugins/** — Directory for all available command-line tools/scripts (each as a module/wrapper)
* **queue/** — Job management/serialization (using `queue.Queue` or similar)
* **.env / config** — Environment variables and sensitive credentials (never logged)
* **README.md / docs/** — Documentation for devs and agents

---

## **API Specification**

### **Endpoints**

#### `POST /run`

* **Description:** Queue and execute a command from a registered plugin.

* **Request Payload:**

  ```json
  {
    "plugin": "botfather",
    "command": "click-button",
    "args": {
      "button-text": "Payments",
      "msg-id": 12345678
    },
    "timeout": 90  // optional, overrides default
  }
  ```

* **Behavior:**

  * Command is queued and run in a subprocess (calls plugin CLI with given args).
  * MCP waits for completion or timeout, returns stdout/stderr in JSON response.
  * **Timeout** defaults to 60s if not specified, but can be set per-job.

* **Response Example:**

  ```json
  {
    "status": "success",
    "plugin": "botfather",
    "command": "click-button",
    "args": { ... },
    "output": { /* JSON or text result from plugin */ },
    "error": null
  }
  ```

#### `GET /help` or `POST /help`

* **Description:** Returns list of available plugins, their commands, required/optional arguments, and usage examples.
* **Response Example:**

  ```json
  {
    "plugins": {
      "botfather": {
        "send-message": {
          "description": "Send a message to BotFather",
          "args": ["--msg"]
        },
        "get-replies": {
          "description": "Get replies from BotFather",
          "args": ["--limit"]
        },
        "click-button": {
          "description": "Click a button in BotFather's message",
          "args": ["--button-text", "--row", "--col", "--msg-id"]
        }
      },
      "devops": {
        "deploy": { ... }
      }
    }
  }
  ```

---

## **Plugin (Tool) Requirements**

* **CLI-based:**
  Plugins must be executable as command-line scripts, accept arguments, and print results to stdout (preferably JSON).
* **Exit Codes:**
  Must return exit code 0 for success, nonzero for error (with error info in output).
* **Output Format:**
  Should return JSON on both success and error when possible.
* **Timeout-Aware:**
  Should not run longer than needed. MCP will enforce a global or per-job timeout, but plugins should also fail gracefully if interrupted.

---

## **Security & Deployment Notes**

* **Internal Only:**
  MCP should bind to localhost or private interfaces. Exposing it externally requires authentication and strong firewall rules.
* **Secrets Management:**
  Store API keys and sensitive config in `.env` or environment variables; never print them in logs.
* **Audit Logging:**
  All job invocations are logged with timestamp, plugin, command, arguments (redacted where sensitive), and status.
* **Resource Limits:**
  If a plugin fails, hangs, or returns non-JSON, MCP should catch and report the error.

---

## **Extending MCP**

1. **Add a new plugin:**

   * Place the script/wrapper in `plugins/`.
   * Register its available commands and argument schema in the MCP config/help.
2. **Document in `/help`:**

   * Every plugin/command must describe its args and usage for agent/human consumption.
3. **Test:**

   * Validate the new plugin via CLI, then via MCP POST `/run`.

---

## **Sample Use Case: BotFather Integration**

* **Plugin:** `botfather_cli.py` (already robust, JSON output)
* **Agent calls:** MCP `/run` endpoint with payload for BotFather command
* **MCP:** queues, runs the CLI tool, returns output
* **Agents (Monday, Letta, etc.):** use `/help` for discovery and command syntax

---

## **Best Practices**

* **Plugin output and errors must always be parseable by MCP.**
* **Never run more than one Telethon/SQLite-based plugin action at a time** (serialization is handled by MCP queue).
* **Timeout is overridable** for long-running jobs (specify in API payload).
* **Document every command in MCP `/help` so agents can stay in sync.**

---

## **Summary**

MCP is a universal "internal API for command-line tools,"
allowing your stack to coordinate automations, bot management, and DevOps with perfect isolation and serialization.

First up: BotFather CLI plugin.
Next: Add any host-level or agent action as you scale.

---

**Drop this into your design doc and you're ready to build—no more tangled APIs or concurrency hell.
If you need a starter skeleton, sample queue logic, or plugin template, just ping me.**

## **Plugin Architecture Details**

* **Plugin Loading:**
  * Static registration at startup for v1
  * Each plugin is a standalone executable or Python script in `plugins/` directory
  * Dynamic loading is a future enhancement
* **Plugin Lifecycle:**
  * No persistent or stateful plugins for v1
  * Each job is a one-off subprocess call
  * No resident plugin processes
* **Error Handling:**
  * Nonzero exit code indicates failure
  * Plugins should emit JSON on both success and error
  * Stderr is captured and included in MCP's error response
  * Timeout errors are explicitly marked in response

## **Queue Implementation**

* **Persistence:**
  * In-memory queues for v1
  * Jobs do not survive server restarts
  * Durable jobs can be proposed as future enhancement
* **Priority:**
  * All jobs are equal priority in v1
  * Priority queuing can be added based on use cases
* **Job Status Tracking:**
  * Unique job ID per request
  * Status states: queued, running, success, error, timeout
  * `/status` endpoint for future versions
  * MVP returns response on job completion
* **Concurrency:**
  * No concurrent execution of jobs for the same plugin by default
  * Plugin safety declarations for parallel execution if needed

## **Security Model**

* **Access Control:**
  * Internal use only by default
  * Bind to localhost or private network
  * No authentication for v1 unless exposed externally
* **Permissions:**
  * All authenticated users can use all plugins in v1
  * Plugin/command-level auth can be added later
* **Rate Limiting:**
  * Not required for v1
  * Designed for easy addition at HTTP handler layer
* **API Key Management:**
  * Only if exposed outside trusted network
  * Use `.env` or config files, never hardcoded

## **Monitoring and Observability**

* **Audit Logging:**
  * All job invocations logged to disk
  * Arguments redacted as needed
  * Status and output/errors included
  * Log rotation recommended
* **Metrics Collection:**
  * Job counts per plugin
  * Execution times
  * Current queue length
  * Exposed via `/metrics` or logs
* **Health Checks:**
  * Basic `/health` endpoint
  * Returns 200 OK if server and queue are up
* **Alerting:**
  * Not required for MVP
  * Can set thresholds for future alert integration

## **Deployment Strategy**

* **Scale:**
  * Single instance for v1
  * Expect <5 concurrent jobs, <10 plugins
  * Worker pools and plugin safety declarations for future scale
* **Containerization:**
  * Docker container support
  * Plugin scripts mapped/mounted in
  * Environment config via `.env` or Docker secrets
* **Configuration Management:**
  * Config file or `.env` for:
    * Plugin registry
    * Plugin script paths
    * Timeouts and queue settings
    * Secrets/keys (never in repo)

## **Plugin Folder Structure and Autodiscovery**

- Each plugin must reside in its own directory under `plugins/` (e.g., `plugins/botfather/`).
- Each plugin directory must contain a `cli.py` entrypoint script.
- MCP will automatically discover plugins by scanning the `plugins/` directory for subdirectories containing a `cli.py` file.
- MCP will use `python plugins/<plugin>/cli.py --help` and `python plugins/<plugin>/cli.py <command> --help` to introspect available commands and arguments via argparse.
- All plugin commands and arguments must be documented and addressable via argparse in CLI mode.
- Plugin output must be JSON (success or error), and exit codes must follow the convention: 0 = success, nonzero = error.

### Example Directory Structure

```
mcp/
  plugins/
    botfather/
      cli.py
      utils.py
    devops/
      cli.py
      deploy.py
```

### Plugin Discovery and Registration

- On startup or `/help` request, MCP will:
  1. Scan `plugins/` for directories.
  2. For each directory, look for `cli.py`.
  3. Run `python cli.py --help` to extract available commands and arguments.
  4. Register the plugin and its commands for `/help` and `/run` endpoints.

### Benefits
- Zero config: Drop a new plugin folder in, and it's auto-discovered.
- Self-documenting: Argparse help is the single source of truth for commands/args.
- Extensible: No MCP code changes needed for new plugins.

---

# Addendum: MCP → STDIO Refactor Plan (New Direction)

*A single-source design brief for the dev-swarm. Copy-paste into the repo / ticket board exactly as-is.*

---

### Goal

Refactor the current SSE-based MCP into a **STDIO daemon** that Letta can launch as a local subprocess. All communication must occur **exclusively via stdin/stdout** (newline-delimited JSON messages).
No HTTP, no sockets, no ports, no Docker networking.

---

## 1 · High-Level Architecture

| Component         | Responsibility                                                                                                     |
| ----------------- | ------------------------------------------------------------------------------------------------------------------ |
| **mcp_stdio.py**  | Long-running process. Reads JSON requests from `stdin`, routes them to plugins, writes JSON responses to `stdout`. |
| **plugins/**      | Unchanged directory of CLI tools (BotFather, DevOps, etc.).                                                        |
| **help cache**    | Built once at daemon start and on explicit `reload-help` command.                                                  |
| **job queue**     | In-process `queue.Queue` (single worker thread) to serialize plugin calls.                                         |

---

## 2 · Message Protocol

### 2.1 Request (stdin → MCP)

```json
{
  "id": "uuid4",
  "command": "run" | "help" | "reload-help" | "health",
  "payload": {
    // only for "run"
    "plugin": "botfather",
    "action": "send-message",
    "args": {"msg": "/newbot"},
    "timeout": 60          // optional, overrides default
  }
}
```

*One JSON object **per line**. Always end with `\n` and flush.*

### 2.2 Response (MCP → stdout)

```json
{
  "id": "same-uuid4",
  "status": "queued" | "started" | "success" | "error" | "timeout",
  "payload": { /* arbitrary result or error info */ }
}
```

*Send **multiple** status events per job (`queued` → `started` → terminal state).* 

---

## 3 · Daemon Lifecycle

1. **Startup**
   * Build help cache (`cli.py --help` for each plugin).
   * Print `{status: "ready"}` to stdout and flush.
2. **Main loop**
   * Block on `stdin.readline()`.
   * Parse JSON; ignore/404 on invalid.
   * Dispatch:
     * `help` → return full help cache.
     * `reload-help` → rebuild cache, return `"ok"`.
     * `health` → return `"ok"`.
     * `run` → enqueue job, immediately reply `"queued"`, then stream subsequent events.
3. **Shutdown**
   * On EOF (Ctrl-D) or SIGTERM, flush `"shutdown"` event and exit 0.

---

## 4 · Plugin Invocation Rules

* Path discovery unchanged (`plugins/<name>/cli.py`).
* Spawn with `subprocess.run([...], capture_output=True, text=True, timeout=<job-timeout>)`.
* Expect **JSON on stdout** ; fallback to raw text if parse fails.

---

## 5 · Timeouts & Error Handling

| Condition                   | MCP `status` | `payload.error`              |
| --------------------------- | ------------ | ---------------------------- |
| CLI exits non-zero          | `"error"`    | stderr or parsed error field |
| `subprocess.TimeoutExpired` | `"timeout"`  | `"timeout"`                  |
| JSON decode fail            | `"error"`    | `"bad_json"`                 |
| Unknown plugin / action     | `"error"`    | `"not_found"`                |

---

## 6 · Logging & Observability

* Use existing `logger.py`.
* Log **every** request & terminal response with job ID, plugin, action, status, duration.
* *Do **NOT** log sensitive env vars or token values.*

---

## 7 · Security

* **Internal-only** tool — no network exposure.
* Running in Letta's container means file paths must be baked into the image or volume-mounted.

---

## 8 · Deliverables

1. **`mcp_stdio.py`** (new entrypoint).
2. Unit tests:
   * Round-trip `run → success` and `run → error`.
   * `help` and `reload-help` actions.
3. **Updated README** section:
   * How to run MCP in stdio mode.
   * Example JSON conversation.
4. **Dockerfile changes** (if needed) to place `mcp_stdio.py` inside Letta container.

---

## 9 · Negative Prompts (DO **NOT**)

* **DO NOT** listen on any TCP/UDP port.
* **DO NOT** depend on asyncio `StreamingResponse`, SSE, or websockets.
* **DO NOT** print multi-line JSON objects (must be single-line newline-delimited).
* **DO NOT** spawn more than **one** worker thread for plugin execution.
* **DO NOT** remove existing plugin directory structure.
* **DO NOT** log plaintext API keys or Telegram session data.

---

### 📌 Acceptance Criteria

* Letta can "Add Server" in **stdio** mode with
  `Command: python3 /path/to/mcp_stdio.py`
  `Arguments: (none)`
  and run BotFather actions end-to-end.
* All unit tests pass.
* CPU & RAM footprint comparable to current MCP.

---
