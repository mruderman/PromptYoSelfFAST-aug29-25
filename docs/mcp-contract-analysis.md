# MCP Contract Analysis for Letta Integration

*Technical design notes extracted from the [MCP Everything Server](https://github.com/modelcontextprotocol/servers) reference implementation*

## 1. The Event Stream Contract

### SSE Endpoint Implementation

**File:** `temp/servers/src/everything/sse.ts`

**Endpoint:** `GET /sse`

**Key Implementation Details:**

```typescript
app.get("/sse", async (req, res) => {
  let transport: SSEServerTransport;
  const { server, cleanup } = createServer();

  if (req?.query?.sessionId) {
    // Reconnection logic (not typically used by Letta)
    const sessionId = (req?.query?.sessionId as string);
    transport = transports.get(sessionId) as SSEServerTransport;
  } else {
    // New connection - create transport and connect server
    transport = new SSEServerTransport("/message", res);
    transports.set(transport.sessionId, transport);
    await server.connect(transport);
  }
});
```

**Critical Headers:**
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`

**Event Format:**
- Each event is a single line starting with `data: `
- Events are newline-delimited with double newlines (`\n\n`)
- No event type specified (uses default `message` type)
- All data is JSON-encoded

### Message Endpoint

**Endpoint:** `POST /message`

**Purpose:** Handles tool invocations and other MCP requests

```typescript
app.post("/message", async (req, res) => {
  const sessionId = (req?.query?.sessionId as string);
  const transport = transports.get(sessionId);
  if (transport) {
    await transport.handlePostMessage(req, res);
  }
});
```

## 2. The "Tools" Manifest Schema

### Tool Definition Structure

**Location:** `temp/servers/src/everything/everything.ts` lines 410-450

**Schema:** Each tool follows the MCP Tool interface:

```typescript
interface Tool {
  name: string;                    // REQUIRED: Unique tool identifier
  description: string;             // REQUIRED: Human-readable description
  inputSchema: ToolInput;          // REQUIRED: JSON Schema for arguments
}
```

**Tool Input Schema (ToolInput):**
```typescript
// Generated from Zod schema using zodToJsonSchema()
const EchoSchema = z.object({
  message: z.string().describe("Message to echo"),
});

// Converts to:
{
  "type": "object",
  "properties": {
    "message": {
      "type": "string",
      "description": "Message to echo"
    }
  },
  "required": ["message"]
}
```

### Complete Tools Manifest Example

```json
{
  "tools": [
    {
      "name": "echo",
      "description": "Echoes back the input",
      "inputSchema": {
        "type": "object",
        "properties": {
          "message": {
            "type": "string",
            "description": "Message to echo"
          }
        },
        "required": ["message"]
      }
    },
    {
      "name": "add",
      "description": "Adds two numbers",
      "inputSchema": {
        "type": "object",
        "properties": {
          "a": {
            "type": "number",
            "description": "First number"
          },
          "b": {
            "type": "number",
            "description": "Second number"
          }
        },
        "required": ["a", "b"]
      }
    }
  ]
}
```

**Required Fields:**
- `name`: String, must be unique, case-sensitive
- `description`: String, human-readable
- `inputSchema`: JSON Schema object, defines argument validation

**Optional Fields:**
- None in the basic implementation

## 3. The Per-Tool API Contract

### Tool Invocation Request

**Endpoint:** `POST /message`

**Request Format:**
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "tools/call",
  "params": {
    "name": "echo",
    "arguments": {
      "message": "Hello, world!"
    }
  }
}
```

### Tool Response Format

**Success Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Echo: Hello, world!"
      }
    ]
  }
}
```

**Error Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": "Validation error details"
  }
}
```

### Content Types Supported

**Text Content:**
```json
{
  "type": "text",
  "text": "Your message here"
}
```

**Image Content:**
```json
{
  "type": "image",
  "data": "base64-encoded-image-data",
  "mimeType": "image/png"
}
```

**Resource Content:**
```json
{
  "type": "resource",
  "resource": {
    "uri": "test://static/resource/1",
    "name": "Resource 1",
    "mimeType": "text/plain",
    "text": "Resource content"
  }
}
```

**Annotated Content:**
```json
{
  "type": "text",
  "text": "Message with annotations",
  "annotations": {
    "priority": 0.8,
    "audience": ["user", "assistant"]
  }
}
```

## 4. Error Handling/Edge Cases

### Connection Management

**Session Handling:**
- Each SSE connection gets a unique `sessionId`
- Sessions are stored in a `Map<string, SSEServerTransport>`
- Cleanup occurs on connection close

**Reconnection Logic:**
```typescript
if (req?.query?.sessionId) {
  // Client reconnecting - reuse existing transport
  transport = transports.get(sessionId);
} else {
  // New connection - create new transport
  transport = new SSEServerTransport("/message", res);
}
```

### Error Recovery

**Missing Session:**
- Returns 400 error if sessionId not found
- Logs error: `"No transport found for sessionId ${sessionId}"`

**Unknown Tool:**
```typescript
throw new Error(`Unknown tool: ${name}`);
```

**Validation Errors:**
- Uses Zod schema validation
- Throws descriptive error messages
- Returns JSON-RPC error response

### Robustness Requirements

1. **Immediate Manifest on Connection:** Tools manifest is sent immediately when SSE connection is established
2. **No Blank Lines:** All SSE events must contain data
3. **Proper JSON-RPC Format:** All responses must follow JSON-RPC 2.0 specification
4. **Session Cleanup:** Transports must be properly cleaned up on disconnect

## 5. Minimal "Known Good" Example

### Complete Working Example

**1. Initial Tools Manifest Event (SSE):**
```
data: {"jsonrpc":"2.0","method":"notifications/tools/list","params":{"tools":[{"name":"echo","description":"Echoes back the input","inputSchema":{"type":"object","properties":{"message":{"type":"string","description":"Message to echo"}},"required":["message"]}}]}}

```

**2. Tool Invocation Request (POST /message):**
```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "method": "tools/call",
  "params": {
    "name": "echo",
    "arguments": {
      "message": "Hello, Letta!"
    }
  }
}
```

**3. Valid Tool Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Echo: Hello, Letta!"
      }
    ]
  }
}
```

### Minimal Server Implementation Checklist

**Required Endpoints:**
- `GET /sse` - SSE connection for real-time events
- `POST /message` - Tool invocation endpoint

**Required Headers:**
- SSE: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`
- POST: `Content-Type: application/json`

**Required Events:**
- `notifications/tools/list` - Initial tools manifest
- `tools/call` - Tool invocation requests
- `tools/callResult` - Tool invocation responses

**Required Error Handling:**
- JSON-RPC 2.0 error format
- Session management
- Validation errors
- Unknown tool errors

## 6. Key Insights for Letta Integration

### What Makes Letta Happy

1. **Immediate Manifest:** Tools must be available immediately on SSE connection
2. **Proper JSON-RPC:** All communication must follow JSON-RPC 2.0 spec
3. **Content Types:** Support for text, image, and resource content types
4. **Session Management:** Proper session handling with cleanup
5. **Error Handling:** Graceful error responses with proper codes

### Common Pitfalls to Avoid

1. **Missing JSON-RPC Format:** Responses must include `jsonrpc`, `id`, and `result`/`error`
2. **Incorrect SSE Format:** Events must be `data: ` prefixed with double newlines
3. **Missing Content Array:** Tool responses must wrap content in an array
4. **No Session Cleanup:** Failing to clean up sessions can cause memory leaks
5. **Invalid Schema:** Input schemas must be valid JSON Schema

### Minimum Viable Implementation

For a basic working MCP server with Letta:

1. Implement `GET /sse` with immediate tools manifest
2. Implement `POST /message` with JSON-RPC handling
3. Support at least one simple tool (like `echo`)
4. Return proper JSON-RPC responses
5. Handle basic error cases

This analysis provides the exact contract needed to build a compliant MCP server that works with Letta's SSE-based architecture. 