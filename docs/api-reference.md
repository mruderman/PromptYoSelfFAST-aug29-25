# API Reference (STDIO Edition)

This document describes the STDIO message protocol for MCP.

## Message Protocol

### Request (stdin → MCP)
```json
{
  "id": "uuid4",
  "command": "run" | "help" | "reload-help" | "health",
  "payload": {
    // only for "run"
    "plugin": "botfather",
    "action": "send-message",
    "args": {"msg": "/newbot"},
    "timeout": 60
  }
}
```

*One JSON object per line. Always end with `\n` and flush.*

### Response (MCP → stdout)
```json
{
  "id": "same-uuid4",
  "status": "queued" | "started" | "success" | "error" | "timeout",
  "payload": { /* result or error info */ }
}
```

*Multiple status events per job (`queued` → `started` → terminal state).* 

## Example Conversation

**Request:**
```json
{"id": "1234", "command": "run", "payload": {"plugin": "botfather", "action": "click-button", "args": {"button-text": "Payments", "msg-id": 12345678}}}
```
**Response:**
```json
{"id": "1234", "status": "queued", "payload": {}}
{"id": "1234", "status": "started", "payload": {}}
{"id": "1234", "status": "success", "payload": {"result": "Clicked button Payments on message 12345678"}}
```

## Commands

- `run`: Execute a plugin action
- `help`: Return help cache
- `reload-help`: Rebuild help cache
- `health`: Return health status

## Error Handling

| Condition                   | MCP `status` | `payload.error`              |
| --------------------------- | ------------ | ---------------------------- |
| CLI exits non-zero          | "error"      | stderr or parsed error field |
| Timeout                     | "timeout"    | "timeout"                   |
| JSON decode fail            | "error"      | "bad_json"                  |
| Unknown plugin / action     | "error"      | "not_found"                 |

## Best Practices

- Always send/expect single-line JSON, newline-delimited
- Always check the `status` field in responses
- Handle all possible status events 