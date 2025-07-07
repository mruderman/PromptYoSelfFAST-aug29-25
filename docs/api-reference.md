# API Reference

This document provides a detailed reference for the Sanctum Letta MCP SSE API, including HTTP endpoints, SSE communication, and plugin interfaces.

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

### `/sse`
- **Method:** GET
- **Description:** Server-Sent Events endpoint for real-time communication.
- **Headers:** `Accept: text/event-stream`
- **On Connect:** Emits tools manifest as JSON-RPC 2.0 notification
- **Example Response:**
  ```
  data: {"jsonrpc":"2.0","method":"notifications/tools/list","params":{"tools":[...]}}
  ```

### `/message`
- **Method:** POST
- **Description:** JSON-RPC 2.0 endpoint for invoking plugin tools.
- **Content-Type:** `application/json`
- **Request:**
  ```json
  {
    "jsonrpc": "2.0",
    "id": "req-1",
    "method": "tools/call",
    "params": {
      "name": "botfather.click-button",
      "arguments": {
        "button-text": "Payments",
        "msg-id": 12345678
      }
    }
  }
  ```
- **Response:**
  ```json
  {
    "jsonrpc": "2.0",
    "id": "req-1",
    "result": {
      "content": [
        {
          "type": "text",
          "text": "Clicked button Payments on message 12345678"
        }
      ]
    }
  }
  ```

## Available Tools

### BotFather Plugin
- **botfather.click-button** - Click a button in a BotFather message
  - Arguments: `button-text` (string), `msg-id` (integer)
- **botfather.send-message** - Send a message to BotFather
  - Arguments: `message` (string)

### DevOps Plugin
- **devops.deploy** - Deploy an application
  - Arguments: `app-name` (string), `environment` (string, optional)
- **devops.rollback** - Rollback an application deployment
  - Arguments: `app-name` (string), `version` (string)
- **devops.status** - Get deployment status
  - Arguments: `app-name` (string)

## Plugin Interface
- Plugins must provide a CLI with subcommands and help text
- Each command must have a name, description, and argument specification
- Help output must include an "Available commands:" section

## Key Data Structures
- **Tool Manifest:** List of available tools with metadata
- **Session:** Represents a client SSE connection and context
- **JSON-RPC 2.0:** All requests and responses follow JSON-RPC 2.0 format

## Docker Configuration
When using with self-hosted Letta/Sanctum in Docker:
- Replace `localhost` with your host machine's IP address
- Use `http://192.168.1.XXX:8000` instead of `http://localhost:8000`
- See [Getting Started](getting-started.md) for detailed Docker networking setup

For more details, see the [Plugin Development](plugin-development.md) guide. 