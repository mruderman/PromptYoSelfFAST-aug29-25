# Sanctum Letta MCP (SSE Edition)

A powerful, modular orchestration server designed to securely expose and manage command-line tools and automation scripts within your internal infrastructure. Built for the Letta Agentic AI framework, MCP operates as a **Server-Sent Events (SSE) server** using aiohttp for real-time communication.

## Key Features

- **SSE Server:** Real-time communication via Server-Sent Events over HTTP using aiohttp
- **Modular Plugin Architecture:** Easily extendable with custom plugins
- **Single Worker Thread:** Serializes all plugin execution for safety
- **Comprehensive Audit Logging:** All requests and results are logged (no sensitive data)
- **Docker-Ready:** Designed for container deployment with Letta
- **Sanctum Stack Compatible:** Uses aiohttp, pydantic, and other Sanctum-standard libraries

## Quick Start

1. Clone the repository and install dependencies:
   ```bash
   git clone https://github.com/actuallyrizzn/sanctum-letta-mcp.git
   cd sanctum-letta-mcp
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Run the MCP SSE server:
   ```bash
   python -m mcp.mcp_server
   ```
   or (if running as a service):
   ```bash
   python mcp/mcp_server.py
   ```

## Example SSE Communication

**HTTP Request:**
```http
POST /run HTTP/1.1
Content-Type: application/json

{
  "plugin": "botfather",
  "action": "click-button",
  "args": {"button-text": "Payments", "msg-id": 12345678}
}
```

**SSE Response Stream:**
```
data: {"status": "queued", "payload": {}}

data: {"status": "started", "payload": {}}

data: {"status": "success", "payload": {"result": "Clicked button Payments on message 12345678"}}
```

## API Endpoints

- `GET /health` - Health check
- `GET /help` - Get help information for all plugins
- `POST /reload-help` - Reload the help cache
- `POST /run` - Execute a plugin command (SSE response)

## Documentation

- [Getting Started](docs/getting-started.md) - Installation and basic usage (SSE)
- [API Reference](docs/api-reference.md) - SSE message protocol
- [Plugin Development](docs/plugin-development.md) - Guide for creating plugins
- [Security Guide](docs/security.md) - Security best practices
- [Monitoring Guide](docs/monitoring.md) - Logging and observability

## Project Structure

- `mcp/` - Main package
  - `mcp_server.py` - aiohttp SSE server entrypoint
  - `plugins/` - Plugin implementations
    - `botfather/` - BotFather automation plugin
    - `devops/` - DevOps automation plugin
  - `config.py` - Configuration management
  - `logger.py` - Logging setup
- `docs/` - Documentation

## License

This project is licensed under the Creative Commons Attribution-ShareAlike (CC BY-SA) license. See LICENSE for details. 