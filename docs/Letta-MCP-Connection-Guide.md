# Complete Guide to Connecting MCP Servers to Letta

This guide provides comprehensive specifications for connecting Model Context Protocol (MCP) servers to Letta installations, with particular focus on Server-Sent Events (SSE) endpoints.

## Table of Contents

1. [Overview](#overview)
2. [MCP Server Types Supported](#mcp-server-types-supported)
3. [SSE Endpoint Specifications](#sse-endpoint-specifications)
4. [Authentication Methods](#authentication-methods)
5. [Configuration Methods](#configuration-methods)
6. [API Endpoints](#api-endpoints)
7. [Implementation Examples](#implementation-examples)
8. [Testing and Debugging](#testing-and-debugging)
9. [Troubleshooting](#troubleshooting)

## Overview

Letta supports three types of MCP server connections:
- **SSE (Server-Sent Events)**: For remote HTTP-based MCP servers
- **STDIO**: For local command-line MCP servers
- **Streamable HTTP**: For HTTP-based MCP servers with streaming capabilities

This guide focuses on **SSE endpoints** as they are the most common for remote MCP server implementations.

## MCP Server Types Supported

### SSE Server Configuration

```python
class SSEServerConfig(BaseServerConfig):
    type: MCPServerType = MCPServerType.SSE
    server_url: str = Field(..., description="The URL of the server (MCP SSE client will connect to this URL)")
    auth_header: Optional[str] = Field(None, description="The name of the authentication header (e.g., 'Authorization')")
    auth_token: Optional[str] = Field(None, description="The authentication token or API key value")
    custom_headers: Optional[dict[str, str]] = Field(None, description="Custom HTTP headers to include with SSE requests")
```

### STDIO Server Configuration

```python
class StdioServerConfig(BaseServerConfig):
    type: MCPServerType = MCPServerType.STDIO
    command: str = Field(..., description="The command to run (MCP 'local' client will run this command)")
    args: List[str] = Field(..., description="The arguments to pass to the command")
    env: Optional[dict[str, str]] = Field(None, description="Environment variables to set")
```

### Streamable HTTP Server Configuration

```python
class StreamableHTTPServerConfig(BaseServerConfig):
    type: MCPServerType = MCPServerType.STREAMABLE_HTTP
    server_url: str = Field(..., description="The URL path for the streamable HTTP server (e.g., 'example/mcp')")
    auth_header: Optional[str] = Field(None, description="The name of the authentication header (e.g., 'Authorization')")
    auth_token: Optional[str] = Field(None, description="The authentication token or API key value")
    custom_headers: Optional[dict[str, str]] = Field(None, description="Custom HTTP headers to include with streamable HTTP requests")
```

## SSE Endpoint Specifications

### Core Requirements

Your MCP server must implement a **Server-Sent Events (SSE) endpoint** that follows these specifications:

#### 1. HTTP Endpoint Requirements

- **Method**: GET
- **Content-Type**: `text/event-stream`
- **Connection**: Keep-alive
- **Cache-Control**: `no-cache`

#### 2. SSE Message Format

Each SSE message must follow the standard SSE format:

```
data: <JSON_MESSAGE>\n\n
```

Where `<JSON_MESSAGE>` is a valid JSON object representing the MCP protocol message.

#### 3. MCP Protocol Messages

Your SSE endpoint must handle and respond to the following MCP protocol messages:

##### Initialization Message
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {}
    },
    "clientInfo": {
      "name": "letta",
      "version": "1.0.0"
    }
  }
}
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {}
    },
    "serverInfo": {
      "name": "your-mcp-server",
      "version": "1.0.0"
    }
  }
}
```

##### List Tools Message
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "example_tool",
        "description": "An example tool",
        "inputSchema": {
          "type": "object",
          "properties": {
            "param1": {
              "type": "string",
              "description": "First parameter"
            }
          },
          "required": ["param1"]
        }
      }
    ]
  }
}
```

##### Call Tool Message
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "example_tool",
    "arguments": {
      "param1": "value1"
    }
  }
}
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Tool execution result"
      }
    ]
  }
}
```

#### 4. Error Handling

For errors, respond with:
```json
{
  "jsonrpc": "2.0",
  "id": <request_id>,
  "error": {
    "code": <error_code>,
    "message": "<error_message>"
  }
}
```

Common error codes:
- `-32600`: Invalid Request
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error

## Authentication Methods

Letta supports multiple authentication methods for MCP servers:

### 1. Bearer Token Authentication

```python
SSEServerConfig(
    server_name="my_server",
    server_url="https://api.example.com/mcp/sse",
    auth_header="Authorization",
    auth_token="Bearer your_token_here"
)
```

### 2. Custom Headers Authentication

```python
SSEServerConfig(
    server_name="my_server",
    server_url="https://api.example.com/mcp/sse",
    custom_headers={
        "X-API-Key": "your_api_key_here",
        "X-Custom-Header": "custom_value"
    }
)
```

### 3. No Authentication

```python
SSEServerConfig(
    server_name="my_server",
    server_url="https://api.example.com/mcp/sse"
)
```

## Configuration Methods

### Method 1: REST API (Recommended)

Use Letta's REST API to manage MCP servers:

#### Add MCP Server
```bash
curl -X PUT "http://localhost:8080/v1/tools/mcp/servers" \
  -H "Content-Type: application/json" \
  -H "user_id: your_user_id" \
  -d '{
    "server_name": "my_mcp_server",
    "type": "sse",
    "server_url": "https://api.example.com/mcp/sse",
    "auth_header": "Authorization",
    "auth_token": "Bearer your_token"
  }'
```

#### List MCP Servers
```bash
curl -X GET "http://localhost:8080/v1/tools/mcp/servers" \
  -H "user_id: your_user_id"
```

#### Test MCP Server Connection
```bash
curl -X POST "http://localhost:8080/v1/tools/mcp/servers/test" \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "my_mcp_server",
    "type": "sse",
    "server_url": "https://api.example.com/mcp/sse"
  }'
```

### Method 2: Configuration File (Legacy)

Create a configuration file at `~/.letta/mcp_config.json`:

```json
{
  "mcpServers": {
    "my_mcp_server": {
      "transport": "sse",
      "url": "https://api.example.com/mcp/sse",
      "headers": {
        "Authorization": "Bearer your_token_here"
      }
    }
  }
}
```

## API Endpoints

### MCP Server Management Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/tools/mcp/servers` | GET | List all configured MCP servers |
| `/v1/tools/mcp/servers` | PUT | Add a new MCP server |
| `/v1/tools/mcp/servers/{server_name}` | PATCH | Update an existing MCP server |
| `/v1/tools/mcp/servers/{server_name}` | DELETE | Remove an MCP server |
| `/v1/tools/mcp/servers/test` | POST | Test connection to an MCP server |

### Request/Response Schemas

#### Add/Update MCP Server Request
```json
{
  "server_name": "string",
  "type": "sse|stdio|streamable_http",
  "server_url": "string",
  "auth_header": "string (optional)",
  "auth_token": "string (optional)",
  "custom_headers": {
    "header_name": "header_value"
  }
}
```

#### MCP Server Response
```json
{
  "server_name": "string",
  "type": "sse|stdio|streamable_http",
  "server_url": "string",
  "auth_header": "string (optional)",
  "auth_token": "string (optional)",
  "custom_headers": {
    "header_name": "header_value"
  }
}
```

## Implementation Examples

### Python Flask SSE Server Example

```python
from flask import Flask, Response, request
import json
import uuid

app = Flask(__name__)

# Store active connections
connections = {}

@app.route('/mcp/sse')
def mcp_sse():
    def generate():
        # Generate unique connection ID
        conn_id = str(uuid.uuid4())
        connections[conn_id] = True
        
        try:
            # Send initial connection established
            yield f"data: {json.dumps({'type': 'connection_established'})}\n\n"
            
            # Handle MCP protocol messages
            while connections.get(conn_id):
                # In a real implementation, you would read from a queue
                # For this example, we'll just wait for client messages
                pass
                
        except GeneratorExit:
            # Client disconnected
            connections.pop(conn_id, None)
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
    )

@app.route('/mcp/message', methods=['POST'])
def handle_mcp_message():
    message = request.json
    
    # Handle different MCP message types
    if message.get('method') == 'initialize':
        response = {
            "jsonrpc": "2.0",
            "id": message.get('id'),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "example-mcp-server",
                    "version": "1.0.0"
                }
            }
        }
    elif message.get('method') == 'tools/list':
        response = {
            "jsonrpc": "2.0",
            "id": message.get('id'),
            "result": {
                "tools": [
                    {
                        "name": "example_tool",
                        "description": "An example tool",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "param1": {
                                    "type": "string",
                                    "description": "First parameter"
                                }
                            },
                            "required": ["param1"]
                        }
                    }
                ]
            }
        }
    elif message.get('method') == 'tools/call':
        # Execute the tool
        tool_name = message['params']['name']
        arguments = message['params']['arguments']
        
        # Your tool execution logic here
        result = execute_tool(tool_name, arguments)
        
        response = {
            "jsonrpc": "2.0",
            "id": message.get('id'),
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": result
                    }
                ]
            }
        }
    else:
        response = {
            "jsonrpc": "2.0",
            "id": message.get('id'),
            "error": {
                "code": -32601,
                "message": "Method not found"
            }
        }
    
    return json.dumps(response)

def execute_tool(tool_name, arguments):
    # Implement your tool execution logic here
    if tool_name == "example_tool":
        return f"Executed {tool_name} with arguments: {arguments}"
    return "Tool not found"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### Node.js Express SSE Server Example

```javascript
const express = require('express');
const app = express();

app.use(express.json());

// Store active connections
const connections = new Map();

app.get('/mcp/sse', (req, res) => {
    // Set SSE headers
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    });

    const connectionId = Date.now().toString();
    connections.set(connectionId, res);

    // Send initial connection message
    res.write(`data: ${JSON.stringify({type: 'connection_established'})}\n\n`);

    // Handle client disconnect
    req.on('close', () => {
        connections.delete(connectionId);
    });
});

app.post('/mcp/message', (req, res) => {
    const message = req.body;
    let response;

    switch (message.method) {
        case 'initialize':
            response = {
                jsonrpc: "2.0",
                id: message.id,
                result: {
                    protocolVersion: "2024-11-05",
                    capabilities: {
                        tools: {}
                    },
                    serverInfo: {
                        name: "example-mcp-server",
                        version: "1.0.0"
                    }
                }
            };
            break;

        case 'tools/list':
            response = {
                jsonrpc: "2.0",
                id: message.id,
                result: {
                    tools: [
                        {
                            name: "example_tool",
                            description: "An example tool",
                            inputSchema: {
                                type: "object",
                                properties: {
                                    param1: {
                                        type: "string",
                                        description: "First parameter"
                                    }
                                },
                                required: ["param1"]
                            }
                        }
                    ]
                }
            };
            break;

        case 'tools/call':
            const toolName = message.params.name;
            const arguments = message.params.arguments;
            
            // Execute tool logic here
            const result = executeTool(toolName, arguments);
            
            response = {
                jsonrpc: "2.0",
                id: message.id,
                result: {
                    content: [
                        {
                            type: "text",
                            text: result
                        }
                    ]
                }
            };
            break;

        default:
            response = {
                jsonrpc: "2.0",
                id: message.id,
                error: {
                    code: -32601,
                    message: "Method not found"
                }
            };
    }

    res.json(response);
});

function executeTool(toolName, arguments) {
    if (toolName === "example_tool") {
        return `Executed ${toolName} with arguments: ${JSON.stringify(arguments)}`;
    }
    return "Tool not found";
}

app.listen(5000, () => {
    console.log('MCP Server running on port 5000');
});
```

## Testing and Debugging

### 1. Test Your SSE Endpoint

Use a simple curl command to test your SSE endpoint:

```bash
curl -N -H "Accept: text/event-stream" \
     -H "Cache-Control: no-cache" \
     https://your-mcp-server.com/mcp/sse
```

### 2. Test with Letta

Use Letta's test endpoint to verify your MCP server:

```bash
curl -X POST "http://localhost:8080/v1/tools/mcp/servers/test" \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "test_server",
    "type": "sse",
    "server_url": "https://your-mcp-server.com/mcp/sse"
  }'
```

### 3. Common Test Scenarios

1. **Connection Test**: Verify the SSE endpoint responds with proper headers
2. **Initialization Test**: Ensure the server responds to `initialize` messages
3. **Tool Listing Test**: Verify `tools/list` returns valid tool definitions
4. **Tool Execution Test**: Test actual tool execution with `tools/call`

## Troubleshooting

### Common Issues

#### 1. Connection Refused
- **Cause**: Server not running or wrong URL
- **Solution**: Verify server is running and URL is correct

#### 2. CORS Errors
- **Cause**: Missing CORS headers
- **Solution**: Add appropriate CORS headers to your SSE endpoint

#### 3. Authentication Failures
- **Cause**: Incorrect auth headers or tokens
- **Solution**: Verify auth configuration in Letta matches your server

#### 4. Protocol Errors
- **Cause**: Invalid JSON-RPC messages
- **Solution**: Ensure all messages follow JSON-RPC 2.0 specification

#### 5. SSE Format Errors
- **Cause**: Incorrect SSE message format
- **Solution**: Ensure all messages follow `data: <json>\n\n` format

### Debug Logs

Enable debug logging in Letta to see detailed MCP communication:

```python
import logging
logging.getLogger('letta.services.mcp').setLevel(logging.DEBUG)
```

### Error Codes

| Error Code | Description | Solution |
|------------|-------------|----------|
| `MCPServerConnectionError` | Failed to connect to MCP server | Check server URL and network connectivity |
| `MCPTimeoutError` | Connection timed out | Check server response times and timeouts |
| `-32600` | Invalid Request | Verify JSON-RPC message format |
| `-32601` | Method not found | Implement required MCP methods |
| `-32602` | Invalid params | Check parameter validation |
| `-32603` | Internal error | Check server logs for internal errors |

## Best Practices

1. **Implement Proper Error Handling**: Always return valid JSON-RPC error responses
2. **Use Connection Pooling**: Manage multiple client connections efficiently
3. **Implement Heartbeats**: Send periodic keep-alive messages
4. **Validate Input**: Always validate tool parameters before execution
5. **Log Operations**: Implement comprehensive logging for debugging
6. **Handle Disconnections**: Gracefully handle client disconnections
7. **Rate Limiting**: Implement appropriate rate limiting for tool calls
8. **Security**: Use HTTPS and proper authentication for production servers

## Additional Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [Server-Sent Events Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [Letta Documentation](https://github.com/your-org/letta)

---

This guide provides the complete specifications needed to implement an MCP server that integrates seamlessly with Letta. Follow the SSE endpoint specifications carefully, and use the provided examples as starting points for your implementation. 