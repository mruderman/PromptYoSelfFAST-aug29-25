# Changelog

## [Unreleased] — 2024-06-07

### Major Changes
- **Full STDIO refactor:** MCP now operates exclusively as a STDIO daemon (no HTTP/SSE, no network ports).
- **Protocol:** All communication is newline-delimited, single-line JSON via stdin/stdout.
- **Plugin execution:** Plugins are run as subprocesses with robust handling (no stdin inheritance, always JSON output, timeouts enforced).
- **Test suite:** Comprehensive new tests for all STDIO protocol features, round-trip, error, and edge cases. No HTTP/SSE tests remain.
- **Windows compatibility:** Fixed subprocess and import issues for Windows (stdin handling, absolute/relative imports).
- **Documentation:** All docs updated for STDIO-only operation. Legacy HTTP/SSE API archived for reference.
- **Security:** No network exposure; all security guidance updated for local-only operation.
- **Bugfixes:**
  - Plugin subprocesses no longer hang or block on stdin
  - CLI plugins always emit JSON (success or error)
  - Daemon robust to plugin errors, timeouts, and bad JSON

### Minor
- Improved logging and diagnostics for plugin execution and errors
- Plugin development guide updated for STDIO/CLI best practices

---

## [1.0.0-stdio] - 2024-06-XX
- MCP refactored to operate exclusively as a STDIO daemon
- All HTTP/SSE code and endpoints removed
- New mcp_stdio.py entrypoint
- Documentation and usage examples updated for STDIO
- Logging and plugin architecture unchanged

## [0.1.0] - Initial Release
- Project renamed to Sanctum Letta MCP
- Plugin autodiscovery and help caching implemented
- /reload-help endpoint and core help documentation added
- Licensed under CC BY-SA 4.0 