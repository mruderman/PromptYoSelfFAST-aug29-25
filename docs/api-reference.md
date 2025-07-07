# API Reference

This document provides a detailed reference for the Model Context Protocol (MCP) API, including HTTP endpoints, plugin interfaces, and key data structures.

## HTTP Endpoints

### `/health`
- **Method:** GET
- **Description:** Returns server health and session statistics.
- **Response:**
  ```json
  {
    "status": "ok",
    "sessions": 0
  }
  ```

### `/tools/manifest`
- **Method:** GET
- **Description:** Returns the current tools manifest, listing all available plugin commands.
- **Response:**
  ```json
  {
    "tools": [
      { "name": "botfather.echo", "description": "Echo a message" },
      ...
    ]
  }
  ```

### `/rpc`
- **Method:** POST
- **Description:** JSON-RPC 2.0 endpoint for invoking plugin tools.
- **Request:**
  ```json
  {
    "jsonrpc": "2.0",
    "method": "botfather.echo",
    "params": { "message": "Hello" },
    "id": 1
  }
  ```
- **Response:**
  ```json
  {
    "jsonrpc": "2.0",
    "result": "Hello",
    "id": 1
  }
  ```

### `/sse`
- **Method:** GET
- **Description:** Server-Sent Events endpoint for real-time updates.

## Plugin Interface
- Plugins must provide a CLI with subcommands and help text.
- Each command must have a name, description, and argument specification.

## Key Data Structures
- **Tool Manifest:** List of available tools with metadata.
- **Session:** Represents a client connection and context.

For more details, see the [Plugin Development](plugin-development.md) guide. 