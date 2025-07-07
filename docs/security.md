# Security Guide

This guide outlines the security model and best practices for the Sanctum Letta MCP system.

## Authentication
- By default, the server does not require authentication
- For production, deploy behind an authenticated proxy or add middleware
- Consider implementing API keys or OAuth for external access

## Session Management
- Each SSE client connection is tracked as a session
- Sessions are automatically cleaned up when clients disconnect
- Session statistics are available via `/health` endpoint
- Sessions are isolated and don't share state between clients

## Plugin Sandboxing
- Plugins are executed in subprocesses with no direct access to server internals
- Each plugin invocation is isolated from others
- Validate and sanitize all plugin input/output
- Plugins cannot access server memory or modify server state

## Audit Logging
- All tool invocations, errors, and session events are logged
- Logs include timestamps, session IDs, and request details (no sensitive data)
- Logs should be retained and monitored for suspicious activity
- Consider integrating with external log aggregation systems

## Network Security
- The server binds to `0.0.0.0:8000` by default (accessible from any interface)
- For production, consider:
  - Binding to specific interfaces only
  - Using HTTPS with proper certificates
  - Implementing rate limiting
  - Adding CORS restrictions if needed

## Best Practices
- Restrict plugin permissions and file system access
- Regularly review logs and update dependencies
- Monitor session counts and plugin execution times
- Implement proper error handling to prevent information leakage
- Use environment variables for configuration (MCP_PORT, MCP_HOST, MCP_PLUGINS_DIR)

## References
- [Monitoring Guide](monitoring.md)
- [Contract Analysis](mcp-contract-analysis.md) 