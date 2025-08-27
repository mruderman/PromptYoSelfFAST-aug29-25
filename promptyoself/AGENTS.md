# CLAUDE.md - PromptYoSelf Plugin

## ✅ **BREAKTHROUGH: ALL TOOL ATTACHMENT ISSUES RESOLVED! (2025-08-13)**

### ✅ **Complete Success Summary**
- **Status**: ✅ **100% RESOLVED** - All 6 promptyoself tools attached to target agent
- **Target Agent**: Zhang (agent-ff18d65c-1f8f-4ca7-9013-2e4e526fd2f4) - 17 tools total  
- **Tools Working**: register, list, test, cancel, execute, agents (all 6 functional)
- **Authentication**: token-based auth fully operational
- **Resolution Method**: Manual tool creation + agent attachment via letta-client

### 🎉 **BREAKTHROUGH: HTTP Transport Success! (2025-08-13)**
- **✅ COMPLETE RESOLUTION**: Successfully migrated from SSE to HTTP transport
- **New URL**: https://smoke-drinking-docs-integrate.trycloudflare.com/mcp
- **Transport**: Streamable HTTP (FastMCP v2.11.3)
- **Tools Status**: ✅ All 6 promptyoself tools successfully registered and working
- **Result**: Eliminated all Cloudflare SSE buffering issues completely

### 🚀 **All Tools Successfully Registered (2025-08-13)**
- ✅ `promptyoself_register` - Schedule new prompts
- ✅ `promptyoself_list` - List existing schedules  
- ✅ `promptyoself_cancel` - Cancel schedules
- ✅ `promptyoself_execute` - Execute due prompts
- ✅ `promptyoself_test` - Test Letta connection
- ✅ `promptyoself_agents` - List available agents

**Status**: 🟢 **PRODUCTION READY** - Ready for Letta ADE connection testing

## Project Overview

PromptYoSelf is a self-hosted prompt scheduler plugin for Letta agents, enabling temporal autonomy through scheduled message delivery. Part of the Sanctum Letta MCP server ecosystem, it allows AI agents to schedule prompts to themselves for future delivery with support for one-time, interval, daily, and cron-based schedules.

## Key Commands

### Running the Scheduler
```bash
# Start the background scheduler daemon
python -m smcp.plugins.promptyoself.cli execute --daemon

# Execute due prompts once
python -m smcp.plugins.promptyoself.cli execute

# Test Letta connection
python -m smcp.plugins.promptyoself.cli test
```

### Managing Schedules
```bash
# Create a one-time schedule
python -m smcp.plugins.promptyoself.cli register <agent_id> "prompt text" once "2024-12-25 10:00:00"

# Create an interval schedule (every 30 minutes)
python -m smcp.plugins.promptyoself.cli register <agent_id> "prompt text" interval "30 minutes"

# Create a daily schedule
python -m smcp.plugins.promptyoself.cli register <agent_id> "prompt text" daily "18:00"

# Create a cron schedule
python -m smcp.plugins.promptyoself.cli register <agent_id> "prompt text" cron "0 9 * * MON-FRI"

# List all schedules
python -m smcp.plugins.promptyoself.cli list

# List schedules for specific agent
python -m smcp.plugins.promptyoself.cli list --agent-id <agent_id>

# Cancel a schedule
python -m smcp.plugins.promptyoself.cli cancel <schedule_id>
```

### Testing and Development
```bash
# Run from the sanctum-letta-mcp directory
cd /root/Compose-Main/config/letta/sanctum-letta-mcp

# List available agents
python -m smcp.plugins.promptyoself.cli agents

# Check database status
sqlite3 promptyoself.db "SELECT COUNT(*) FROM schedules WHERE active = 1;"

# View logs
tail -f promptyoself.log
tail -f promptyoself_errors.log

# Test API endpoints (when MCP server is running)
curl http://localhost:8000/api/schedules
curl http://localhost:8000/api/agents
```

## Architecture

### Core Components

1. **Database Layer (`db.py`)**: SQLite database with schedule management
   - Lazy initialization pattern for database creation
   - CRUD operations with performance indexes
   - Cleanup operations for old schedules
   - Statistics and monitoring functions

2. **Scheduler Engine (`scheduler.py`)**: Background execution engine
   - APScheduler for background tasks
   - Cron expression parsing with croniter
   - Multi-format schedule calculation
   - Robust error handling with retry logic

3. **Letta Integration (`letta_api.py`)**: Agent communication
   - Singleton client pattern
   - Multiple authentication methods (API key, password, dummy)
   - Retry logic with exponential backoff
   - ChatML bug workaround with streaming fallback

4. **CLI Interface (`cli.py`)**: Command-line management
   - Complete schedule management commands
   - Agent validation and testing
   - Daemon mode for continuous execution

5. **Logging System (`logging_config.py`)**: Advanced structured logging
   - JSON structured logging
   - Automatic rotation and error separation
   - Performance timing context managers

### Database Schema

```sql
schedules table:
- id: Primary key
- agent_id: Target Letta agent
- prompt_text: Message content
- schedule_type: 'once', 'cron', 'interval', 'daily'
- schedule_value: Schedule configuration
- next_run: Next execution timestamp
- active: Boolean status
- created_at: Creation timestamp
- last_run: Last execution timestamp
- max_repetitions: Optional limit (NULL = infinite)
- repetition_count: Current execution count

Indexes:
- idx_schedules_due: For finding due schedules
- idx_schedules_agent_active: For agent queries
- idx_schedules_created_at: For historical analysis
```

### API Integration

The plugin exposes REST API endpoints through the MCP server:

```python
# Base URL: http://localhost:8000

GET /api/schedules          # List schedules with filtering
GET /api/schedules/calendar # Calendar-formatted events
GET /api/agents             # Available Letta agents
GET /api/stats              # Database statistics
```

## Important Configuration

### Environment Variables
```bash
# Letta Connection
LETTA_API_KEY=your-api-key           # For cloud authentication
LETTA_BASE_URL=http://localhost:8283 # For self-hosted
LETTA_SERVER_PASSWORD=password       # Alternative auth

# Database
PROMPTYOSELF_DB=/path/to/promptyoself.db

# Logging
PROMPTYOSELF_LOG_LEVEL=INFO
PROMPTYOSELF_LOG_FILE=/path/to/promptyoself.log
PROMPTYOSELF_LOG_FORMAT=json  # or 'text'
```

### Default Settings
- Scheduler interval: 60 seconds
- Database: SQLite with automatic initialization
- Logging: Multi-format with rotation
- Authentication: Flexible fallback (API key → password → dummy)

## Development Patterns

### Error Handling Strategy
- All operations wrapped in try-catch with structured logging
- Retry logic with exponential backoff for Letta API calls
- Graceful degradation when services unavailable
- ChatML compatibility workaround using streaming API

### Logging Patterns
```python
# Use structured logging with context
from smcp.plugins.promptyoself.logging_config import log_operation

with log_operation("schedule_create", {"agent_id": agent_id}):
    # Operation code here
    pass
```

### Database Operations
```python
# Always use context managers for database operations
from smcp.plugins.promptyoself.db import get_db_session

with get_db_session() as session:
    # Database operations here
    session.commit()
```

### Letta API Calls
```python
# Use the singleton client with error handling
from smcp.plugins.promptyoself.letta_api import get_letta_client, send_prompt_to_agent

client = get_letta_client()
success = send_prompt_to_agent(agent_id, prompt_text, schedule_id)
```

## Common Workflows

### Adding New Schedule Types
1. Update `schedule_type` enum in database schema
2. Add calculation logic in `scheduler.calculate_next_run_for_schedule()`
3. Update CLI argument parser in `cli.py`
4. Add validation in `db.add_schedule()`

### Testing Schedule Execution
1. Create a test schedule with short interval
2. Run daemon mode: `python -m smcp.plugins.promptyoself.cli execute --daemon`
3. Monitor logs: `tail -f promptyoself.log`
4. Check database: `sqlite3 promptyoself.db "SELECT * FROM schedules;"`

### Debugging Connection Issues
1. Test connection: `python -m smcp.plugins.promptyoself.cli test`
2. Check environment variables are set correctly
3. Verify Letta server is running: `curl http://localhost:8283/v1/health/`
4. Review error logs: `tail -f promptyoself_errors.log`

### Database Maintenance
```bash
# Backup database
cp promptyoself.db promptyoself.db.backup

# Clean old schedules
sqlite3 promptyoself.db "DELETE FROM schedules WHERE active = 0 AND last_run < datetime('now', '-30 days');"

# Reset schedule counts
sqlite3 promptyoself.db "UPDATE schedules SET repetition_count = 0 WHERE active = 1;"
```

## Plugin Integration with MCP Server

The plugin is auto-discovered by the MCP server through:
1. Presence of `cli.py` in plugin directory
2. Dynamic tool registration based on CLI help output
3. MCP-compliant tool execution through `mcp_server.py`

To verify integration:
```bash
# Check MCP server logs
docker compose logs sanctum-mcp | grep promptyoself

# Test MCP tool execution
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "promptyoself", "args": ["list"]}'
```

## Troubleshooting

### Common Issues

1. **"No Letta client configured"**: Set LETTA_API_KEY or LETTA_SERVER_PASSWORD
2. **"Agent not found"**: Verify agent ID with `cli agents` command
3. **Database locked**: Stop duplicate scheduler processes
4. **ChatML errors**: Automatic fallback to streaming API should handle this
5. **Schedules not executing**: Check scheduler daemon is running and logs for errors

### Performance Considerations

- Database indexes optimize query performance for large schedule counts
- Cleanup operations prevent unbounded database growth
- Singleton client pattern reduces connection overhead
- Batch processing of due schedules minimizes API calls

## Key Files Reference

- `db.py`: Database models and operations (250+ lines)
- `scheduler.py`: Scheduling engine (170+ lines)
- `letta_api.py`: Letta integration (230+ lines)
- `cli.py`: Command-line interface (270+ lines)
- `logging_config.py`: Logging configuration (140+ lines)
- `promptyoself.db`: Main database with active schedules
- `api/schedules_api.py`: REST API endpoints (in parent directory)