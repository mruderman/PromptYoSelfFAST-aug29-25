# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PromptYoSelf is a self-hosted prompt scheduler system built around a FastMCP server that exposes scheduling functionality as Model Context Protocol (MCP) tools for AI agents, particularly Letta agents. The system allows AI agents to schedule prompts to themselves for future delivery with support for one-time, interval, and cron-based schedules.

**Key Architecture**: This project has migrated from a complex Sanctum-based server to a lightweight FastMCP-based implementation. The legacy Sanctum code is archived under `archive/sanctum/`.

## Core Technologies

- **MCP Server**: FastMCP framework for protocol-compliant tool exposure
- **Database**: SQLite with SQLAlchemy ORM for schedule persistence
- **Scheduling**: APScheduler with croniter for advanced scheduling
- **Agent Integration**: Letta-client SDK for AI agent communication
- **Transport**: stdio (local), HTTP, SSE (remote) transports supported

## Common Commands

### Development Setup
```bash
# Install server and test dependencies
pip install -r requirements.txt

# Install PromptYoSelf plugin dependencies  
pip install -r promptyoself/requirements.txt
```

### Running the Server
```bash
# STDIO transport (local development)
python promptyoself_mcp_server.py

# HTTP transport (remote agents)
python promptyoself_mcp_server.py --transport http --host 127.0.0.1 --port 8000 --path /mcp

# SSE transport (legacy)
python promptyoself_mcp_server.py --transport sse --host 127.0.0.1 --port 8000

# Using convenience script
./start.sh http  # or 'sse' or 'stdio'

# Tailscale (private remote access)
bash start.sh tailscale  # auto-detects your tailnet IPv4
python promptyoself_mcp_server.py --transport http --host 100.x.y.z --port 8000 --path /mcp

# Note: MCP HTTP is not a plain REST API—use an MCP client (e.g., FastMCP Client)
```

### Testing
```bash
# Run full test suite with coverage
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage reporting (temporary 35% minimum; stepping up toward 80%)
pytest --cov=promptyoself_mcp_server --cov=promptyoself --cov-report=html
```

### Direct CLI Usage (Development)
```bash
# Test Letta connection
python -m promptyoself.cli test

# List available agents
python -m promptyoself.cli agents

# Register a one-time schedule
python -m promptyoself.cli register --agent-id <agent_id> --prompt "prompt text" --time "2025-12-25T10:00:00Z"

# Register a cron schedule
python -m promptyoself.cli register --agent-id <agent_id> --prompt "Daily check-in" --cron "0 9 * * *"

# Register an interval schedule
python -m promptyoself.cli register --agent-id <agent_id> --prompt "Focus check" --every "30m" --start-at "2025-01-02T15:00:00Z" --max-repetitions 10

# List schedules
python -m promptyoself.cli list

# Execute due prompts
python -m promptyoself.cli execute

# Run scheduler daemon
python -m promptyoself.cli execute --loop --interval 60
```

## Architecture Overview

### Current FastMCP Architecture (2025)

```text
AI Client (Claude/Letta) → FastMCP Server → PromptYoSelf CLI Functions → SQLite DB + Letta API
```

The system consists of:

1. **FastMCP Server** (`promptyoself_mcp_server.py`): Single-file MCP server that exposes tools
2. **Plugin Package** (`promptyoself/`): Core functionality modules
3. **Database Layer**: SQLite with lazy initialization and performance indexes
4. **Scheduler Engine**: Background execution with cron support
5. **Letta Integration**: Direct SDK integration for agent communication

### MCP Tools Exposed

The FastMCP server exposes these tools:

- promptyoself_schedule: General scheduler (provide exactly one of time, cron, or every).
- promptyoself_schedule_time: Strict one-time variant with an ISO-8601 datetime (e.g., `2025-12-25T10:00:00Z`).
- promptyoself_schedule_cron: Strict recurring variant with a standard 5-field cron string (e.g., `0 9 * * *`).
- promptyoself_schedule_every: Strict interval variant with every/start_at/max_repetitions (e.g., `every="30m"`).
- promptyoself_list: List schedules with optional filtering.
- promptyoself_cancel: Cancel schedules by ID.
- promptyoself_execute: Execute due prompts (once or loop mode).
- promptyoself_test: Test Letta connectivity.
- promptyoself_agents: List available Letta agents.
- promptyoself_upload: Upload Letta-native tools from source code.
- health: Server health and configuration status.

### Core Modules

#### `promptyoself_mcp_server.py` (Main Server)

- FastMCP server implementation
- Tool registration and argument mapping
- Transport configuration (stdio/HTTP/SSE)
- Error handling and logging

#### `promptyoself/cli.py` (Core Logic)

- Schedule registration and management functions
- Agent validation and testing
- Daemon mode execution
- Direct imports by MCP server (no subprocess shelling)

#### `promptyoself/db.py` (Database Layer)

- SQLAlchemy models and session management
- Schedule CRUD operations with proper indexes
- Database initialization and migration handling
- Performance optimization for large schedule counts

#### `promptyoself/scheduler.py` (Scheduling Engine)

- APScheduler background processing
- Cron expression parsing with croniter
- Schedule calculation for multiple formats
- Robust error handling and retry logic

#### `promptyoself/letta_api.py` (Agent Integration)

- Singleton Letta client pattern
- Multiple authentication methods (API key, password, dummy)
- Retry logic with exponential backoff
- Agent validation and prompt delivery

#### `promptyoself/logging_config.py` (Structured Logging)

- JSON structured logging configuration
- Performance timing context managers
- Automatic log rotation and error separation

## Environment Configuration

### Required Environment Variables

```bash
# Letta Connection (choose one authentication method)
LETTA_API_KEY=your-api-key                    # For cloud Letta instances
LETTA_SERVER_PASSWORD=TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JTlmnopxyz           # For self-hosted Letta
LETTA_BASE_URL=https://cyansociety.a.pinggy.link/ #Letta server URL

# Database Configuration
PROMPTYOSELF_DB=/path/to/promptyoself.db     # SQLite database file

# Logging Configuration
PROMPTYOSELF_LOG_LEVEL=INFO                   # Logging level
PROMPTYOSELF_LOG_FILE=/path/to/app.log       # Log file location
PROMPTYOSELF_LOG_FORMAT=json                  # or 'text'
```

### FastMCP Transport Configuration

```bash
# Transport settings (optional)
FASTMCP_TRANSPORT=stdio                       # Transport type
FASTMCP_HOST=127.0.0.1                       # Host for HTTP/SSE
FASTMCP_PORT=8000                            # Port for HTTP/SSE
FASTMCP_PATH=/mcp                            # Path for HTTP
FASTMCP_LOG_LEVEL=INFO                       # Server log level
```

## Development Patterns

### Error Handling Strategy
- All operations wrapped in try-catch with structured logging
- JSON error responses with consistent format: `{"error": "message"}`
- Graceful degradation when external services unavailable
- Retry logic with exponential backoff for Letta API calls

### Database Operations
```python
# Always use proper session management
from promptyoself.db import get_db_session

with get_db_session() as session:
    # Database operations here
    session.commit()
```

### Letta API Integration
```python
# Use singleton client pattern
from promptyoself.letta_api import get_letta_client, send_prompt_to_agent

client = get_letta_client()
success = send_prompt_to_agent(agent_id, prompt_text, schedule_id)
```

### Structured Logging
```python
# Use performance timing and structured context
from promptyoself.logging_config import get_logger, PerformanceTimer

logger = get_logger(__name__)
with PerformanceTimer("operation_name"):
    # Timed operation here
    logger.info("Operation completed", extra={"context": "data"})
```

## Testing Architecture

The test suite is organized into three tiers:

### Unit Tests (`tests/unit/`)
- Test individual modules in isolation
- Mock external dependencies (Letta API, database)
- High coverage requirements (80% minimum)

### Integration Tests (`tests/integration/`)
- Test MCP protocol compliance
- Test database integration with real SQLite
- Test CLI function integration

### End-to-End Tests (`tests/e2e/`)
- Test complete MCP workflow
- Test FastMCP transport mechanisms
- Test agent interaction scenarios

### Test Configuration (`pytest.ini`)
```ini
[pytest]
testpaths = tests
addopts = -v --cov=promptyoself_mcp_server --cov=promptyoself --cov-fail-under=35
markers =
    unit: Unit tests
    integration: Integration tests  
    e2e: End-to-end tests
    asyncio: Async tests
```

## Database Schema

The MCP/CLI path uses a unified table named `unified_reminders` (see `promptyoself/db.py`). A legacy `schedules` table may exist for backward compatibility but new inserts/queries go through `unified_reminders` via an adapter.

Key columns:
- id INTEGER PRIMARY KEY
- message TEXT NOT NULL
- next_run DATETIME NOT NULL
- status TEXT DEFAULT "pending"
- active BOOLEAN DEFAULT 1
- created_at DATETIME DEFAULT CURRENT_TIMESTAMP
- updated_at DATETIME
- last_run DATETIME
- schedule_type TEXT — 'once', 'cron', or 'interval'
- schedule_value TEXT — cron expression or interval string (e.g., "30s", "5m", "1h")
- max_repetitions INTEGER
- repetition_count INTEGER DEFAULT 0
- agent_id TEXT — present for CLI-originated reminders
- process_name TEXT
- task_id INTEGER, user_id INTEGER — reserved for a web UI path

Performance indexes include due-time and agent/activity composites (see Index(...) declarations in `db.py`).

## Common Development Tasks

### Adding New Schedule Types
1. Update schedule type validation in `cli.py`
2. Add calculation logic in `scheduler.py:calculate_next_run()`
3. Update database schema if needed
4. Add unit tests for new schedule type
5. Update MCP tool documentation

### Extending MCP Tools
1. Add new function to `promptyoself/cli.py`
2. Import and map function in `promptyoself_mcp_server.py`
3. Add FastMCP tool decorator with proper typing
4. Write unit tests for new tool
5. Update integration tests

### Debugging Connection Issues
1. Check environment variables: `python -c "import os; print(os.environ.get('LETTA_BASE_URL'))"`
2. Test Letta connectivity: `python -m promptyoself.cli test`
3. Verify agent exists: `python -m promptyoself.cli agents`
4. Check server health: Test `health` MCP tool
5. Review structured logs for error context

### Performance Optimization
- Database indexes are optimized for schedule queries
- Singleton client pattern reduces connection overhead
- Batch processing minimizes API calls
- Cleanup operations prevent unbounded database growth

## Migration Notes

This repository underwent a major architectural migration:

### Legacy Architecture (Archived)
- **Sanctum HTTP/SSE Server**: Complex plugin auto-discovery system
- **Location**: `archive/sanctum/` 
- **Issues**: Cloudflare SSE buffering, complex protocol implementation

### Current Architecture (Active)
- **FastMCP Server**: Single-file server with direct function imports
- **Benefits**: Reliability, maintainability, transport flexibility
- **Transport**: stdio for local, HTTP for remote, SSE for legacy support

### Migration Impact
- Old REST API endpoints (`/api/schedules`) no longer exist
- MCP tools replace REST endpoints
- Plugin auto-discovery replaced with explicit imports
- Sanctum-specific documentation is outdated

## Troubleshooting

### Common Issues
1. **"No Letta client configured"**: Set `LETTA_API_KEY` or `LETTA_SERVER_PASSWORD`
2. **"Agent not found"**: Verify agent ID with `promptyoself_agents` tool
3. **"Database locked"**: Ensure only one scheduler process is running
4. **Transport errors**: Use HTTP transport for remote agents, stdio for local
5. **Schedule not executing**: Check scheduler daemon is running and logs

### Health Checking
```bash
# Test MCP tools (requires MCP client)
# Use health tool to check configuration

# Direct CLI testing
python -m promptyoself.cli test           # Test Letta connection
python -m promptyoself.cli agents         # List available agents
python -m promptyoself.cli list           # Show current schedules

# Database inspection
sqlite3 promptyoself.db "SELECT COUNT(*) FROM schedules WHERE active = 1;"
```

## Key File Locations

### Core Implementation
- `promptyoself_mcp_server.py` - Main FastMCP server (390+ lines)
- `promptyoself/cli.py` - CLI functions and core logic (400+ lines)
- `promptyoself/db.py` - Database models and operations (300+ lines)
- `promptyoself/scheduler.py` - Scheduling engine (250+ lines)
- `promptyoself/letta_api.py` - Letta integration (200+ lines)

### Configuration
- `requirements.txt` - Server and test dependencies
- `promptyoself/requirements.txt` - Plugin dependencies
- `pytest.ini` - Test configuration
- `start.sh` - Convenience startup script

### Documentation
- `README.md` - Primary documentation (accurate)
- `README_FASTMCP.md` - Technical implementation details (accurate)
- `AGENTS.md` - Plugin developer guide (current, moved to repo root)

### Testing
- `tests/unit/` - Unit tests with mocking
- `tests/integration/` - Integration and protocol tests
- `tests/e2e/` - End-to-end workflow tests
- `run_tests.py` - Test runner script

## Security Considerations

- Never commit secrets to version control (rotate any leaked passwords)
- Use environment variables for all authentication
- Validate agent IDs before scheduling
- Implement proper session management for database operations
- Use structured logging without sensitive data exposure