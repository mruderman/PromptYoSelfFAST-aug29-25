# Changelog

## [Unreleased] — 2024-06-07

### Major Changes
- **Pivot to SSE Architecture:** MCP now operates as a Server-Sent Events (SSE) server for Docker compatibility with Letta.
- **aiohttp Integration:** Switched from FastAPI/uvicorn to aiohttp for consistency with Sanctum stack.
- **Protocol:** All communication via HTTP/SSE for real-time updates and Docker-friendly operation.
- **Plugin execution:** Plugins are run as subprocesses with robust handling (no stdin inheritance, always JSON output, timeouts enforced).
- **Test suite:** Comprehensive tests for all SSE protocol features, round-trip, error, and edge cases.
- **Windows compatibility:** Fixed subprocess and import issues for Windows (stdin handling, absolute/relative imports).
- **Documentation:** All docs updated for SSE operation. Legacy STDIO approach archived for reference.
- **Security:** Network exposure controlled via Docker networking; all security guidance updated for container operation.
- **Bugfixes:**
  - Plugin subprocesses no longer hang or block on stdin
  - CLI plugins always emit JSON (success or error)
  - Server robust to plugin errors, timeouts, and bad JSON

### Minor
- Improved logging and diagnostics for plugin execution and errors
- Plugin development guide updated for SSE/CLI best practices
- Stack alignment with Sanctum standards (aiohttp, pydantic, python-dotenv)

---

## [2.0.0-sse] - 2024-06-XX
- MCP refactored to operate as a Server-Sent Events (SSE) server using aiohttp
- All STDIO code removed in favor of HTTP/SSE for Docker compatibility
- New mcp_server.py entrypoint with aiohttp architecture
- Documentation and usage examples updated for SSE
- Logging and plugin architecture unchanged
- Stack aligned with Sanctum standards

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