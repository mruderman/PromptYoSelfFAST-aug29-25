# Security Guide

This guide outlines the security model and best practices for the Letta Internal MCP system.

## Authentication
- By default, the server does not require authentication.
- For production, deploy behind an authenticated proxy or add middleware.

## Session Management
- Each client connection is tracked as a session.
- Sessions are cleaned up when clients disconnect.
- Session statistics are available via `/health`.

## Plugin Sandboxing
- Plugins are executed in subprocesses.
- No direct access to server internals.
- Validate and sanitize all plugin input/output.

## Audit Logging
- All tool invocations and errors are logged.
- Logs should be retained and monitored for suspicious activity.

## Best Practices
- Restrict plugin permissions.
- Regularly review logs and update dependencies.

## References
- [Monitoring Guide](monitoring.md)
- [Contract Analysis](mcp-contract-analysis.md) 