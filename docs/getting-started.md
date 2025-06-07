# Getting Started with MCP (STDIO Edition)

This guide will help you get up and running with MCP in STDIO mode.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/actuallyrizzn/sanctum-letta-mcp.git
   cd sanctum-letta-mcp
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On Unix/MacOS
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running MCP (STDIO)

Run the STDIO daemon:
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

## Next Steps

- Read the [API Reference](api-reference.md) for the STDIO message protocol
- See [Plugin Development](plugin-development.md) to create new plugins
- Review [Security](security.md) best practices 