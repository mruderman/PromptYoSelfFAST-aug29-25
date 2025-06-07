# MCP Documentation (STDIO Edition)

Welcome to the MCP (Master Control Program) documentation. This documentation will help you understand, set up, and use the MCP system in STDIO mode (no HTTP, no SSE).

## Table of Contents

1. [Getting Started](getting-started.md)
2. [API Reference](api-reference.md)
3. [Plugin Development](plugin-development.md)
4. [Security](security.md)
5. [Monitoring](monitoring.md)
6. [Project Plan](project-plan.md)

## Quick Start

For a quick start guide, see [Getting Started](getting-started.md).

## STDIO Usage Example

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

## Contributing

To contribute, see [Plugin Development](plugin-development.md).

## Support

For issues or questions, create an issue in the GitHub repository. 