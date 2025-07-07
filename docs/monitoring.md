# Monitoring Guide

This guide describes how to monitor the health, performance, and activity of the Sanctum Letta MCP system.

## Health Checks
- **Endpoint:** `/health`
- Returns server status and session count
- Use for liveness/readiness probes in orchestration systems
- Example response:
  ```json
  {
    "status": "ok",
    "sessions": 2
  }
  ```

## Logging
- All tool invocations, errors, and session events are logged to standard output
- Log format includes timestamps, session IDs, and request details
- Example log entries:
  ```
  INFO: Session started: session-123
  INFO: Tool invoked: botfather.click-button (session-123)
  INFO: Tool completed: botfather.click-button (session-123)
  INFO: Session ended: session-123
  ```

## Metrics
- **Session count** is available via `/health`
- **Plugin discovery** logs show which plugins were found at startup
- **Tool execution times** are logged for performance monitoring
- For advanced metrics, integrate with Prometheus or similar tools

## Troubleshooting

### Common Issues
1. **Plugins not discovered:**
   - Check that plugins have `cli.py` files in `mcp/plugins/`
   - Verify help output includes "Available commands:" section
   - Check server logs for plugin discovery errors

2. **SSE connection issues:**
   - Verify client sends `Accept: text/event-stream` header
   - Check for CORS issues if connecting from web browsers
   - Ensure server is accessible on the expected port

3. **Tool invocation failures:**
   - Check plugin CLI help output format
   - Verify JSON-RPC 2.0 request format
   - Review plugin error handling and output format

### Debug Commands
```bash
# Check server health
curl http://localhost:8000/health

# Test SSE connection
curl -H "Accept: text/event-stream" http://localhost:8000/sse

# Test tool invocation
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"test","method":"tools/call","params":{"name":"botfather.send-message","arguments":{"message":"/help"}}}'
```

## References
- [API Reference](api-reference.md)
- [Security Guide](security.md) 