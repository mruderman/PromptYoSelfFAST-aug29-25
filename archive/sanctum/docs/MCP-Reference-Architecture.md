# MCP Reference Architecture Documentation

## Overview

The Model Context Protocol (MCP) is a standardized protocol for communication between AI clients and servers. This document describes the reference architecture for MCP servers using Server-Sent Events (SSE) as the transport layer.

## Core Architecture

### Transport Layer: SSE (Server-Sent Events)

MCP uses a hybrid HTTP approach with SSE for server-to-client communication and HTTP POST for client-to-server communication:

1. **SSE Connection** (`GET /sse`): Establishes a persistent connection for server-to-client messages
2. **Message Endpoint** (`POST /messages`): Handles client-to-server JSON-RPC messages

### Key Components

#### 1. SseServerTransport

The core transport class that manages SSE connections and message handling:

```python
class SseServerTransport:
    """
    SSE server transport for MCP. This class provides _two_ ASGI applications:
    
    1. connect_sse() - ASGI app for GET requests to establish SSE streams
    2. handle_post_message() - ASGI app for POST requests with client messages
    """
```

**Key Features:**
- Session management with UUID-based session IDs
- Memory object streams for bidirectional communication
- DNS rebinding protection via TransportSecurityMiddleware
- Automatic endpoint discovery for clients

#### 2. ServerSession

Manages the MCP protocol session and handles message routing:

```python
class ServerSession:
    """
    Manages communication between server and client in the MCP framework.
    Handles initialization, capability negotiation, and message processing.
    """
```

**Key Responsibilities:**
- Protocol initialization and version negotiation
- Client capability checking
- Message routing and response handling
- Session state management

#### 3. Message Structure

MCP uses JSON-RPC 2.0 for message format:

```python
class JSONRPCMessage:
    """Union of JSON-RPC request, notification, response, and error types"""
    
class SessionMessage:
    """Message wrapper with transport-specific metadata"""
    message: JSONRPCMessage
    metadata: MessageMetadata = None
```

## Protocol Flow

### 1. Connection Establishment

1. **Client connects to SSE endpoint** (`GET /sse`)
2. **Server creates session** with unique UUID
3. **Server sends endpoint event** with POST URI for client messages
4. **SSE connection remains open** for server-to-client communication

### 2. Initialization

1. **Client sends initialize request** via POST to `/messages?session_id=<uuid>`
2. **Server responds with capabilities** and protocol version
3. **Client sends initialized notification**
4. **Session is ready** for normal operation

### 3. Message Exchange

- **Client → Server**: HTTP POST to `/messages?session_id=<uuid>` with JSON-RPC message
- **Server → Client**: SSE events with JSON-RPC messages

## Message Types

### Requests (Client → Server)

```python
# Core Protocol
InitializeRequest
InitializedNotification
PingRequest

# Resources
ListResourcesRequest
ReadResourceRequest
SubscribeRequest
UnsubscribeRequest

# Tools
ListToolsRequest
CallToolRequest

# Prompts
ListPromptsRequest
GetPromptRequest

# Logging
SetLevelRequest

# Sampling (Server → Client)
CreateMessageRequest

# Roots (Server → Client)
ListRootsRequest

# Elicitation (Server → Client)
ElicitRequest
```

### Notifications

```python
# Progress
ProgressNotification

# Resource Updates
ResourceUpdatedNotification
ResourceListChangedNotification

# Tool Updates
ToolListChangedNotification

# Prompt Updates
PromptListChangedNotification

# Logging
LoggingMessageNotification

# Cancellation
CancelledNotification
```

## Capability System

MCP uses a capability-based system for feature negotiation:

```python
class ClientCapabilities:
    experimental: dict[str, dict[str, Any]] | None = None
    sampling: SamplingCapability | None = None
    elicitation: ElicitationCapability | None = None
    roots: RootsCapability | None = None

class ServerCapabilities:
    experimental: dict[str, dict[str, Any]] | None = None
    logging: LoggingCapability | None = None
    prompts: PromptsCapability | None = None
    resources: ResourcesCapability | None = None
    tools: ToolsCapability | None = None
    completions: CompletionsCapability | None = None
```

## Implementation Example

```python
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import Response
from mcp.server.sse import SseServerTransport
from mcp.server.session import ServerSession
from mcp.server.models import InitializationOptions

# Create SSE transport
sse = SseServerTransport("/messages/")

# Define SSE handler
async def handle_sse(request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        # Create server session
        init_options = InitializationOptions(
            server_name="my-mcp-server",
            server_version="1.0.0",
            capabilities=ServerCapabilities(
                tools=ToolsCapability(),
                resources=ResourcesCapability()
            )
        )
        
        session = ServerSession(
            read_stream=streams[0],
            write_stream=streams[1],
            init_options=init_options
        )
        
        # Run the session
        await session.run()
    
    return Response()

# Create routes
routes = [
    Route("/sse", endpoint=handle_sse, methods=["GET"]),
    Mount("/messages/", app=sse.handle_post_message),
]

# Create and run app
app = Starlette(routes=routes)
```

## Security Considerations

### DNS Rebinding Protection

The SSE transport includes built-in DNS rebinding protection:

```python
class TransportSecurityMiddleware:
    """Validates request headers for DNS rebinding protection"""
    
    async def validate_request(self, request: Request, is_post: bool) -> Response | None:
        # Validates Origin, Host, and other security headers
        pass
```

### Session Management

- Each SSE connection gets a unique session ID
- Session IDs are UUIDs for security
- Sessions are tracked in memory with automatic cleanup
- Client must include session_id in POST requests

## Error Handling

### JSON-RPC Error Codes

```python
# SDK error codes
CONNECTION_CLOSED = -32000

# Standard JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
```

### Error Response Format

```python
class JSONRPCError:
    jsonrpc: Literal["2.0"]
    id: str | int
    error: ErrorData

class ErrorData:
    code: int
    message: str
    data: Any | None = None
```

## Best Practices

### 1. Session Management
- Always validate session IDs in POST requests
- Clean up sessions when SSE connections close
- Use UUIDs for session identification

### 2. Message Handling
- Validate all incoming JSON-RPC messages
- Handle initialization state properly
- Check client capabilities before using features

### 3. Error Handling
- Return appropriate JSON-RPC error codes
- Provide meaningful error messages
- Log errors for debugging

### 4. Performance
- Use memory object streams for efficient message passing
- Implement proper connection cleanup
- Handle large message payloads appropriately

## Protocol Versions

```python
LATEST_PROTOCOL_VERSION = "2025-06-18"
DEFAULT_NEGOTIATED_VERSION = "2025-03-26"
```

The server should negotiate the highest supported version between client and server capabilities.

## Conclusion

This reference architecture provides a robust foundation for implementing MCP servers using SSE transport. The hybrid HTTP/SSE approach offers the benefits of both protocols: reliable request/response handling via HTTP POST and efficient server-to-client streaming via SSE.

Key advantages:
- **Bidirectional communication**: Full duplex communication between client and server
- **Session management**: Robust session handling with automatic cleanup
- **Security**: Built-in DNS rebinding protection and session validation
- **Scalability**: Efficient memory-based message passing
- **Standards compliance**: Full JSON-RPC 2.0 compliance with MCP extensions 