# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Sanctum Letta MCP Server is a Python-based Model Context Protocol (MCP) server that provides a plugin architecture for AI clients to interact with external tools and services. Built with FastMCP framework and aiohttp, it uses Server-Sent Events (SSE) for real-time communication.

## Key Architecture Components

### Server Core (`smcp/mcp_server.py`)
- FastMCP-based server with JSON-RPC 2.0 protocol compliance
- Plugin auto-discovery system that scans `smcp/plugins/` directory
- Dynamic tool registration based on CLI help output parsing
- Health monitoring and comprehensive error handling
- Environment variable configuration support

### Plugin System
- **Plugin Directory**: `smcp/plugins/` (configurable via `MCP_PLUGINS_DIR`)
- **Plugin Structure**: Each plugin must have a `cli.py` file as the main interface
- **Tool Registration**: Commands from CLI help output become MCP tools automatically
- **Execution Model**: CLI-based execution with JSON output required

### Transport Layer
- **Primary**: Server-Sent Events (SSE) at `/sse` endpoint
- **Message Handling**: POST `/messages/` for JSON-RPC 2.0 requests
- **Host Binding**: Default `0.0.0.0:8000` (Docker-compatible)
- **Security Options**: Configurable host binding for localhost-only or external access

## Development Commands

### Server Management
```bash
# Start the MCP server (default: localhost + Docker access)
python smcp/mcp_server.py

# Localhost-only access
python smcp/mcp_server.py --host 127.0.0.1

# Allow external connections
python smcp/mcp_server.py --allow-external

# Custom port
python smcp/mcp_server.py --port 9000

# Using environment variables
export MCP_PORT=9000
export MCP_HOST=127.0.0.1
python smcp/mcp_server.py
```

### Testing
```bash
# Run all tests with coverage (100% required)
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v  
python -m pytest tests/e2e/ -v

# Use the test runner script
python run_tests.py --all
python run_tests.py --unit
python run_tests.py --integration
python run_tests.py --e2e

# Coverage reporting
python -m pytest tests/ --cov=smcp --cov-report=html --cov-fail-under=100
```

### Environment Configuration
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Quick start with provided script
chmod +x start.sh
./start.sh
```

## Plugin Development

### Plugin Structure Requirements
```
smcp/plugins/your_plugin/
├── __init__.py          # Optional plugin metadata
├── cli.py              # Required: Main CLI interface
├── requirements.txt    # Optional: Plugin-specific dependencies
└── README.md          # Recommended: Plugin documentation
```

### CLI Interface Pattern
Plugins must implement a CLI interface with:
- Argparse-based command parsing with subcommands
- JSON output for all operations (required for MCP compatibility)
- Error handling with meaningful error messages
- Help text for automatic tool registration

### Example Plugin CLI Structure
```python
#!/usr/bin/env python3
import argparse
import json
import sys

def main():
    parser = argparse.ArgumentParser(description="Plugin Description")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add commands - each becomes an MCP tool
    cmd_parser = subparsers.add_parser("command-name", help="Command help")
    cmd_parser.add_argument("--param", required=True, help="Parameter help")
    
    args = parser.parse_args()
    
    if args.command == "command-name":
        result = execute_command(args.param)
        print(json.dumps(result))  # JSON output required
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Plugin Deployment Options
- **Direct**: Place in `smcp/plugins/` directory
- **Symlinks**: Use symbolic links for centralized plugin management
- **Environment**: Override plugins directory with `MCP_PLUGINS_DIR`

## Key Configuration

### Environment Variables
```bash
MCP_PORT=8000                    # Server port
MCP_HOST=0.0.0.0                # Host binding (0.0.0.0 for Docker compatibility)
MCP_PLUGINS_DIR=smcp/plugins/   # Plugin directory path
```

### Command Line Arguments
```bash
--host HOST          # Override host binding
--port PORT          # Override port
--allow-external     # Allow external connections (sets host to 0.0.0.0)
```

## Available Plugins

### PromptYoSelf (`smcp/plugins/promptyoself/`)
- **Purpose**: Self-hosted prompt scheduler for Letta agents
- **Key Commands**: `register`, `list`, `cancel`, `execute`, `test`, `agents`
- **Dependencies**: SQLite, APScheduler, croniter, Letta client
- **Configuration**: Requires Letta connection (API key or password)

### BotFather (`smcp/plugins/botfather/`)
- **Purpose**: Telegram BotFather automation
- **Key Commands**: `click-button`, `send-message`
- **Status**: Basic implementation (TODO items present)

### DevOps (`smcp/plugins/devops/`)
- **Purpose**: Deployment and infrastructure management
- **Status**: Basic CLI structure

## Testing Strategy

### Test Categories
- **Unit Tests** (`tests/unit/`): Core server functionality and plugin system
- **Integration Tests** (`tests/integration/`): MCP protocol compliance
- **End-to-End Tests** (`tests/e2e/`): Complete workflow validation

### Coverage Requirements
- 100% code coverage enforced via pytest configuration
- HTML coverage reports generated in `htmlcov/`
- Tests use pytest-asyncio for async code testing

### Test Configuration (`pytest.ini`)
- Timeout: 60 seconds per test
- Markers: asyncio, timeout, integration, e2e, unit
- Coverage reports: terminal and HTML

## MCP Protocol Implementation

### Client Connection Flow
1. Client establishes SSE connection at `/sse`
2. Client sends `initialize` request to `/messages/`
3. Server responds with capabilities and available tools
4. Client can call tools via `tools/call` method
5. Server streams responses via SSE

### Tool Registration
- Automatic discovery from plugin CLI help output
- Tool names format: `{plugin_name}_{command_name}`
- Parameter extraction from argparse help
- JSON schema generation for MCP compliance

### Error Handling
- Structured error responses with JSON-RPC 2.0 format
- Plugin execution errors wrapped in MCP error format
- Health check tool for server monitoring
- Comprehensive logging to `mcp.log`

## Development Patterns

### Plugin Testing
```bash
# Test plugin CLI directly
python smcp/plugins/your_plugin/cli.py command-name --param value

# Test via MCP server (requires server running)
curl -X POST http://localhost:8000/messages/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"your_plugin_command_name","arguments":{"param":"value"}}}'
```

### Plugin Dependencies
- Install plugin-specific dependencies in plugin directory
- Use `requirements.txt` in plugin directory for isolation
- Import handling for both MCP server and direct execution contexts

### Logging and Monitoring
- Server logs to `mcp.log` and stdout
- Plugin-specific logs in plugin directories (e.g., `promptyoself.log`)
- Health check endpoint available via `health` tool
- Error tracking and performance monitoring built-in

## Important Notes

### Security Considerations
- Default configuration allows Docker container access (0.0.0.0 binding)
- Use `--host 127.0.0.1` for localhost-only access in production
- Plugin execution runs in server process context
- No sandboxing - plugins have full server permissions

### Performance
- Async/await pattern throughout server code
- Plugin discovery happens at server startup
- Tool execution is synchronous within async context
- SSE connection maintains persistent client connection

### Compatibility
- Python 3.8+ required
- MCP Protocol version 2025-03-26
- FastMCP framework dependency
- Cross-platform support (Linux, macOS, Windows)