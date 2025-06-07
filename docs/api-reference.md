# API Reference

This document provides detailed information about the MCP API endpoints, request/response formats, and error handling.

## Base URL

All API endpoints are relative to the base URL where MCP is running. By default, this is:
```
http://localhost:5000
```

## Authentication

Currently, MCP is designed for internal use only and does not require authentication when running on localhost or private networks. If exposed to external networks, authentication will be required.

## Endpoints

### GET /help

Returns information about available plugins and their commands.

#### Request
```http
GET /help
```

#### Response
```json
{
  "plugins": {
    "botfather": {
      "commands": {
        "send-message": {
          "description": "Send a message to BotFather",
          "args": {
            "msg": {
              "type": "string",
              "required": true,
              "description": "Message to send"
            }
          }
        },
        "get-replies": {
          "description": "Get replies from BotFather",
          "args": {
            "limit": {
              "type": "integer",
              "required": false,
              "description": "Maximum number of replies to return",
              "default": 10
            }
          }
        },
        "click-button": {
          "description": "Click a button in BotFather's message",
          "args": {
            "button-text": {
              "type": "string",
              "required": true,
              "description": "Text of the button to click"
            },
            "msg-id": {
              "type": "integer",
              "required": true,
              "description": "ID of the message containing the button"
            }
          }
        }
      }
    }
  }
}
```

### POST /run

Executes a command through a specified plugin.

#### Request
```http
POST /run
Content-Type: application/json

{
  "plugin": "string",
  "command": "string",
  "args": {
    "key": "value"
  },
  "timeout": integer  // optional, in seconds
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| plugin | string | Yes | Name of the plugin to use |
| command | string | Yes | Command to execute |
| args | object | Yes | Arguments for the command |
| timeout | integer | No | Custom timeout in seconds (default: 60) |

#### Response

Success Response:
```json
{
  "status": "success",
  "plugin": "string",
  "command": "string",
  "args": {
    "key": "value"
  },
  "output": {
    // Plugin-specific output
  },
  "error": null
}
```

Error Response:
```json
{
  "status": "error",
  "plugin": "string",
  "command": "string",
  "args": {
    "key": "value"
  },
  "output": null,
  "error": "Error message"
}
```

## Error Codes

MCP uses standard HTTP status codes:

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Plugin or command not found |
| 408 | Request Timeout - Command execution timed out |
| 500 | Internal Server Error |

## Rate Limiting

Currently, MCP does not implement rate limiting. However, it is recommended to:
- Implement rate limiting at the network level if exposed externally
- Use the queue system to prevent resource contention
- Monitor usage patterns and implement rate limiting if needed

## Best Practices

1. **Error Handling**
   - Always check the `status` field in responses
   - Handle both success and error cases
   - Implement retry logic for transient failures

2. **Timeouts**
   - Set appropriate timeouts for long-running commands
   - Monitor command execution times
   - Adjust timeouts based on observed performance

3. **Resource Management**
   - Use the queue system to prevent resource contention
   - Monitor system resources during command execution
   - Implement proper cleanup after command completion

## Examples

### Example 1: Sending a Message to BotFather

```bash
curl -X POST http://localhost:5000/run \
  -H "Content-Type: application/json" \
  -d '{
    "plugin": "botfather",
    "command": "send-message",
    "args": {
      "msg": "Hello BotFather"
    }
  }'
```

### Example 2: Getting Replies with Custom Timeout

```bash
curl -X POST http://localhost:5000/run \
  -H "Content-Type: application/json" \
  -d '{
    "plugin": "botfather",
    "command": "get-replies",
    "args": {
      "limit": 5
    },
    "timeout": 120
  }'
``` 