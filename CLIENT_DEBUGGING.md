# MCP Client Debugging Guide for Agent ID Issues

## Problem
Your MCP client is sending `agent_id: null` instead of the actual agent ID you're providing.

## Debugging Steps

### 1. Verify Your MCP Client Call
Ensure you're calling the tool with the correct parameter name and format:

```javascript
// Correct format
await mcpClient.callTool("promptyoself_schedule_time", {
  "prompt": "Test prompt",
  "time": "2025-12-25T10:00:00Z", 
  "agent_id": "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a",  // String, not null
  "skip_validation": false
});
```

### 2. Check for Parameter Name Variations
Some clients might expect different parameter names. Try these variations:

```javascript
// Variations to try
"agent_id": "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"
"agentId": "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"  
"agent-id": "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"
```

### 3. Enable Client-Side Debugging
If your MCP client supports debugging, enable it to see the actual JSON being sent:

```bash
# For Letta or similar clients
DEBUG=1 your_mcp_client_command
```

### 4. Test with curl
Test the raw HTTP request to isolate the issue:

```bash
curl -X POST http://100.76.47.25:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "promptyoself_schedule_time",
      "arguments": {
        "prompt": "Test prompt", 
        "time": "2025-12-25T10:00:00Z",
        "agent_id": "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a",
        "skip_validation": true
      }
    }
  }'
```

## Quick Workarounds

### Option A: Set Environment Variable
Set a default agent ID as an environment variable on the server:

```bash
export LETTA_AGENT_ID="agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"
```

### Option B: Enable Single-Agent Fallback
If you only have one agent, enable automatic fallback:

```bash
export PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK=true
```

### Option C: Use Context Metadata (Advanced)
Ensure your MCP client passes agent_id in the context metadata:

```javascript
// Client should set context metadata
context.metadata.agent_id = "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"
```