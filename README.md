# Sanctum Letta MCP (STDIO Edition)

A powerful, modular orchestration server designed to securely expose and manage command-line tools and automation scripts within your internal infrastructure. Built for the Letta Agentic AI framework, MCP now operates exclusively as a **STDIO daemon**—no HTTP, no sockets, no ports.

## Key Features

- **STDIO Daemon:** Communicates via newline-delimited JSON on stdin/stdout
- **Modular Plugin Architecture:** Easily extendable with custom plugins
- **Single Worker Thread:** Serializes all plugin execution for safety
- **Comprehensive Audit Logging:** All requests and results are logged (no sensitive data)
- **Internal-Only:** No network exposure, designed for container or local use

## Quick Start

1. Clone the repository and install dependencies:
   ```bash
   git clone https://github.com/actuallyrizzn/sanctum-letta-mcp.git
   cd sanctum-letta-mcp
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Run the MCP STDIO daemon:
   ```bash
   python -m mcp.mcp_stdio
   ```
   or (if running as a subprocess):
   ```bash
   python mcp/mcp_stdio.py
   ```

## Example JSON Conversation

**Request (stdin → MCP):**
```json
{"id": "1234", "command": "run", "payload": {"plugin": "botfather", "action": "click-button", "args": {"button-text": "Payments", "msg-id": 12345678}}}
```

**Response (MCP → stdout):**
```json
{"id": "1234", "status": "queued", "payload": {}}
{"id": "1234", "status": "started", "payload": {}}
{"id": "1234", "status": "success", "payload": {"result": "Clicked button Payments on message 12345678"}}
```

*All messages are single-line JSON, newline-delimited, and flushed immediately.*

## Documentation

- [Getting Started](docs/getting-started.md) - Installation and basic usage (STDIO)
- [API Reference](docs/api-reference.md) - STDIO message protocol
- [Plugin Development](docs/plugin-development.md) - Guide for creating plugins
- [Security Guide](docs/security.md) - Security best practices
- [Monitoring Guide](docs/monitoring.md) - Logging and observability

## Project Structure

- `mcp/` - Main package
  - `mcp_stdio.py` - STDIO daemon entrypoint
  - `plugins/` - Plugin implementations
  - `config.py` - Configuration management
  - `logger.py` - Logging setup
- `docs/` - Documentation

## License

This project is licensed under the Creative Commons Attribution-ShareAlike (CC BY-SA) license. See LICENSE for details. 