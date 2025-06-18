# Sanctum Letta MCP (SSE Edition)

**Version: 2.1.0**

A powerful, modular orchestration server designed to securely expose and manage command-line tools and automation scripts within your internal infrastructure. Built for the Letta Agentic AI framework, MCP operates as a **Server-Sent Events (SSE) server** using aiohttp for real-time communication and is now fully compliant with the Model Context Protocol (MCP).

## Letta/MCP Compliance

- **MCP-Compliant SSE/JSON-RPC:** Implements the Model Context Protocol event and message contract for seamless Letta integration.
- **Dynamic Plugin Discovery:** Auto-discovers all plugins in `mcp/plugins/` at startup. No static registration—just drop in a new plugin with a `cli.py` and it will be available after a server restart.
- **Immediate Tools Manifest:** On SSE connect, emits a JSON-RPC 2.0 tools manifest event as required by Letta and MCP.
- **JSON-RPC 2.0 Everywhere:** All requests and responses (including errors) use the JSON-RPC 2.0 format.
- **Ready for Testing:** This implementation is ready for Letta, Claude Desktop, or any MCP-compliant client.

## Key Features

- **SSE Server:** Real-time communication via Server-Sent Events over HTTP using aiohttp
- **Dynamic Plugin Architecture:** Plugins are auto-discovered at startup; no code changes needed to add new tools
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
POST /message HTTP/1.1
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": "req-1",
  "method": "tools/call",
  "params": {
    "name": "botfather.click-button",
    "arguments": {"button-text": "Payments", "msg-id": 12345678}
  }
}
```

**SSE Response Stream (on connect):**
```
data: {"jsonrpc":"2.0","method":"notifications/tools/list","params":{"tools":[...]}}

```

**Tool Call Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "result": {
    "content": [
      {"type": "text", "text": "Clicked button Payments on message 12345678"}
    ]
  }
}
```

## API Endpoints

- `GET /sse` - SSE connection for real-time events (emits tools manifest on connect)
- `POST /message` - Tool invocation endpoint (JSON-RPC 2.0)
- `GET /health` - Health check

## Documentation

- [Getting Started](docs/getting-started.md) - Installation and basic usage (SSE)
- [API Reference](docs/api-reference.md) - SSE message protocol
- [Plugin Development](docs/plugin-development.md) - Guide for creating plugins
- [Security Guide](docs/security.md) - Security best practices
- [Monitoring Guide](docs/monitoring.md) - Logging and observability

## Project Structure

- `mcp/` - Main package
  - `mcp_server.py` - aiohttp SSE server entrypoint
  - `plugins/` - Plugin implementations (auto-discovered)
    - `botfather/` - BotFather automation plugin
    - `devops/` - DevOps automation plugin
  - `config.py` - Configuration management
  - `logger.py` - Logging setup
- `docs/` - Documentation

## License

This project is licensed under the Creative Commons Attribution-ShareAlike (CC BY-SA) license. See LICENSE for details.

---

**Note:**
- The legacy STDIO protocol and references have been archived. This implementation is HTTP/SSE-only and fully MCP/Letta compatible.
- For advanced plugin schema extraction or hot-reload, see future roadmap. 