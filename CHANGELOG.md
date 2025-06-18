# Changelog

## [2.1.0] — 2024-06-07

### Added/Changed
- **MCP-Compliant SSE/JSON-RPC Architecture:**
  - Implements the Model Context Protocol event and message contract for Letta and other MCP clients.
  - All endpoints and responses use JSON-RPC 2.0.
- **Dynamic Plugin Discovery:**
  - Plugins are auto-discovered at startup from `mcp/plugins/`.
  - No static registration—just drop in a new plugin with a `cli.py` and it will be available after a server restart.
- **Immediate Tools Manifest:**
  - On SSE connect, emits a JSON-RPC 2.0 tools manifest event as required by Letta and MCP.
- **Letta Compatibility:**
  - This implementation is ready for Letta, Claude Desktop, or any MCP-compliant client.
- **Minimal, Extensible, Production-Ready:**
  - This is a minimal, compliant implementation—ready for integration and extension.
- **STDIO References Archived:**
  - All legacy STDIO protocol references have been removed or archived. This implementation is HTTP/SSE-only.

### Notes
- **Version Bump:**
  - Minor version bump to 2.1.0 for MCP/Letta compliance and dynamic plugin system.
  - Major version bump will follow after full production validation and testing.
- **Testing:**
  - Ready for integration and production testing. Please report any issues or edge cases.

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