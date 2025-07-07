# Monitoring Guide

This guide describes how to monitor the health, performance, and activity of the Letta Internal MCP system.

## Health Checks
- **Endpoint:** `/health`
- Returns server status and session count.
- Use for liveness/readiness probes in orchestration systems.

## Logging
- All tool invocations, errors, and session events are logged.
- Logs are written to standard output by default.
- Integrate with external log aggregators as needed.

## Metrics
- Session count is available via `/health`.
- For advanced metrics, integrate with Prometheus or similar tools.

## Troubleshooting
- Check logs for errors or warnings.
- Use `/health` to verify server status.
- Ensure plugins are discoverable and listed in `/tools/manifest`.

## References
- [API Reference](api-reference.md)
- [Security Guide](security.md) 