> NOTE: This project now uses a FastMCP-based server that exposes the PromptYoSelf plugin directly. The legacy Sanctum HTTP/SSE server has been archived under `archive/sanctum/`.

# PromptYoSelf FastMCP Server

This repository contains the PromptYoSelf plugin and a [FastMCP](https://gofastmcp.com/)-based server to expose it as a set of tools for a Model Context Protocol (MCP) client, such as a [Letta](https://docs.letta.com/) agent.

- **Server file:** [promptyoself_mcp_server.py](promptyoself_mcp_server.py)
- **Developer Guide:** [AGENTS.md](AGENTS.md)
- **API reference:** [docs/promptyoself-tools.md](docs/promptyoself-tools.md)
 - **Letta Integration:** [docs/letta-integration.md](docs/letta-integration.md)

## ⚙️ Letta Integration (Quick Ops)

For a self‑hosted Letta over Tailscale, the most reliable path is to add a managed MCP server named `promptyoself` and register all tools via the Letta API, then attach them to your agent.

Prereqs:
- Letta API URL: `http://<LETTASERVER_TAILSCALE_IP>:8283` (e.g., `http://100.126.136.121:8283`)
- Auth: use `Authorization: Bearer $LETTA_SERVER_PASSWORD` for self‑hosted `SECURE=true`
- PromptYoSelf MCP URL: `http://<PROMPTYOSELF_TAILSCALE_IP>:8000/mcp` (e.g., `http://100.76.47.25:8000/mcp`)

Steps (cURL):

```bash
export LETTA_URL="http://100.126.136.121:8283"
export LETTA_TOKEN="$LETTA_SERVER_PASSWORD"

# 1) Add managed MCP server (streamable HTTP)
curl -sS -X PUT "$LETTA_URL/v1/tools/mcp/servers" \
  -H "Authorization: Bearer $LETTA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "promptyoself",
    "type": "streamable_http",
    "server_url": "http://100.76.47.25:8000/mcp"
  }'

# 2) Register PromptYoSelf tools on this server (repeat for each)
for T in promptyoself_inference_diagnostics promptyoself_set_default_agent promptyoself_set_scoped_default_agent promptyoself_get_scoped_default_agent promptyoself_schedule_time promptyoself_schedule_cron promptyoself_schedule_every promptyoself_list promptyoself_cancel promptyoself_execute promptyoself_test promptyoself_agents promptyoself_upload health; do
  curl -sS -X POST "$LETTA_URL/v1/tools/mcp/servers/promptyoself/$T" \
    -H "Authorization: Bearer $LETTA_TOKEN" -H "Content-Type: application/json"; echo
done

# 3) Attach to your agent
AGENT_ID="agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"
curl -sS "$LETTA_URL/v1/tools/mcp/servers/promptyoself/tools" -H "Authorization: Bearer $LETTA_TOKEN" | jq -r '.[].id' | while read -r TID; do
  curl -sS -X PATCH "$LETTA_URL/v1/agents/$AGENT_ID/tools/attach/$TID" \
    -H "Authorization: Bearer $LETTA_TOKEN" -H "Content-Type: application/json"; echo
done

# 4) Ask the agent to run a smoke test
curl -sS -X POST "$LETTA_URL/v1/agents/$AGENT_ID/messages" \
  -H "Authorization: Bearer $LETTA_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "messages":[{"role":"user","content":[{"type":"text","text":"Please run MCP smoke test: diagnostics; schedule twice (one without agent_id, one with agentId); list; cancel."}]}]
  }'
```

This avoids ADE wrapper friction. If you use ADE wrappers, ensure they do not require `mcp_server_id`—Letta resolves managed servers by name.

## 🚀 Quick Start

### Quick Usage

```bash
# HTTP on localhost with persistent DB and executor autostart
./start.sh http --port 8000 --path /mcp

# HTTP bound to your Tailscale IP (auto-detected)
./start.sh tailscale --port 8000 --path /mcp

# Opt out of the background executor loop
./start.sh http --no-executor
```

1. **Install Dependencies**

  This project has two sets of dependencies. Install both.

```bash
# Install server and test dependencies
pip install -r requirements.txt

# Install PromptYoSelf plugin dependencies
pip install -r promptyoself/requirements.txt
```

1. **Run the Server**

  The server can be run in two modes:

- Standard I/O (stdio): simplest for local development or connecting to local agents.

```bash
python promptyoself_mcp_server.py
```

- HTTP: run as a web service to connect remote agents (cloud/Docker, etc.).

```bash
python promptyoself_mcp_server.py --transport http --host 127.0.0.1 --port 8000 --path /mcp
```

- HTTP over Tailscale: bind to your tailnet IP for private access.

```bash
# Convenience script (auto-detects your Tailscale IPv4)
bash start.sh tailscale

# Or explicit host (replace with your tailscale IP)
python promptyoself_mcp_server.py --transport http --host 100.x.y.z --port 8000 --path /mcp
```

Note: The MCP HTTP transport is not a plain REST API; use an MCP client (e.g., FastMCP Client). A direct browser GET to /mcp/* will 404.

### Agent ID Defaults & Diagnostics

Most tools need a Letta `agent_id`.

- Pass it explicitly with each call, or
- Set a default on the server process (`LETTA_AGENT_ID` or `PROMPTYOSELF_DEFAULT_AGENT_ID`), or
- Set a per‑client/session default using `promptyoself_set_scoped_default_agent`, or
- Enable single‑agent fallback when you have exactly one agent.

Quick helpers (call via your MCP client):

- `promptyoself_set_default_agent { "agent_id": "agt_..." }` — sets a process‑local default for this server session.
- `promptyoself_set_scoped_default_agent { "agent_id": "agt_..." }` — sets a default only for your client/session.
- `promptyoself_get_scoped_default_agent {}` — shows the scoped default (if any).
- `promptyoself_inference_diagnostics {}` — shows which agent_id will be used and why.

Note: schedule tools also accept the alias field `agentId` if your client sends camelCase.

## 🛠️ Development setup

Choose one of the following:

- Makefile (recommended)

```bash
make setup     # creates .venv and installs all deps
make test      # runs pytest with repo's pytest.ini
make run       # runs the FastMCP server (stdio)
```

- VS Code tasks
  - Run: "Python: Create venv"
  - Then: "Python: Install deps (root)" and "Python: Install deps (plugin)"
  - Test: "Test: Pytest"
  - Run: "Run: MCP Server (stdio)" or "Run: MCP Server (http)"

- Manual

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r promptyoself/requirements.txt
pytest
```

Environment file:

- Copy `example.env` to `.env` and set values for local/dev as needed.

## 🔐 Configuration

### Environment Variables

The server requires configuration for connecting to your Letta instance. **Never commit real secrets to version control!**

### Default Deployment (Recommended)

For any default deployment of the PromptYoSelf MCP Server:

- Persistence: set `PROMPTYOSELF_DB` to a volume‑mounted path. The `start.sh` script defaults to `./data/promptyoself.sqlite3` when unset, or `/data/promptyoself.sqlite3` if `/data` exists.
- Autostart executor: enable the execute loop in the background using `--autostart-executor` (or `PROMPTYOSELF_EXECUTOR_AUTOSTART=true`). The server defaults to autostart; use `start.sh --no-executor` to opt out.
- Access: bind HTTP to localhost or a Tailscale IP. Use `./start.sh http` (binds `127.0.0.1`) or `./start.sh tailscale` to bind to your tailnet address.
- Time: keep NTP synchronized on the host; scheduling uses wall‑clock time. Ensure `timedatectl`, `chrony`, or `ntpd` is configured appropriately.

### Local Development Setup

1. Copy the example configuration file:

```bash
cp example.env .env
```

Note: The MCP HTTP transport is not a plain REST API; use an MCP client (e.g., FastMCP Client). A direct browser GET to `/mcp/*` will 404.

1. Edit `.env` and set your actual values:

```bash
# For macOS/Linux:
export LETTA_SERVER_PASSWORD="your_actual_password_here"

# For Windows PowerShell:
$env:LETTA_SERVER_PASSWORD="your_actual_password_here"
```

Optional agent defaults and fallback:

```bash
# Preferred: set a default agent for the server session
export LETTA_AGENT_ID="agt_..."

# Alternate: compatible default var name
export PROMPTYOSELF_DEFAULT_AGENT_ID="agt_..."

# If you only have one agent, you can enable fallback
export PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK=true
```

### Docker Compose Configuration

When using Docker Compose, pass environment variables from your host:

```yaml
services:
  promptyoself:
    build: .
    environment:
      - LETTA_SERVER_PASSWORD=${LETTA_SERVER_PASSWORD}
      - LETTA_BASE_URL=http://letta:8283
      - LETTA_AGENT_ID=${LETTA_AGENT_ID}
      - PROMPTYOSELF_DEFAULT_AGENT_ID=${PROMPTYOSELF_DEFAULT_AGENT_ID}
      - PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK=${PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK}
```

### GitHub Actions Configuration

Set secrets in your repository settings and reference them in workflows:

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Run deployment
        env:
          LETTA_SERVER_PASSWORD: ${{ secrets.LETTA_SERVER_PASSWORD }}
        run: |
          python promptyoself_mcp_server.py
```

**Important**: GitHub does not expose secrets to `pull_request` workflows triggered from forks by default. Consider using `pull_request_target` with caution or require maintainer approval via environments for security.

### Security Recommendations

- **Rotate the leaked secret**: The LETTA_SERVER_PASSWORD that was previously committed should be rotated in your Letta server configuration
- **Use environment variables**: Never hardcode secrets in configuration files
- **Use a secrets manager**: For production deployments, consider using a dedicated secrets management service

## 🧪 Testing

This project uses `pytest` for testing. The test configuration is defined in `pytest.ini`.

To run the full test suite, including coverage analysis:

```bash
pytest
```

This will automatically:

- Discover and run all tests in the `tests/` directory.
- Measure code coverage for the `promptyoself_mcp_server` and `promptyoself` modules.
- Generate a coverage report in the terminal and as an HTML report in the `htmlcov/` directory.
- Require minimum 67% code coverage to pass.

### Recent Test Improvements

Recent fixes have significantly improved test stability:

- **Resolved 34 failing tests** down to approximately 7 remaining failures
- Fixed critical unit tests for MCP server functionality
- Improved validation and error handling in test suites
- Enhanced test reliability for schedule registration and health checks

### Test Best Practices

When writing or running tests, keep these guidelines in mind:

**Future Timestamp Requirement**: Always use future timestamps when testing scheduling functionality. Past timestamps will be rejected by the scheduler validation, causing tests to fail. For example:

```python
# ✅ Good - future timestamp
time="2025-12-25T10:00:00Z"

# ❌ Bad - past timestamp (will fail validation)
time="2024-01-01T10:00:00Z"
```

**Test Categories**: Run specific test categories as needed:

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# End-to-end tests only
pytest tests/e2e/
```

## ▶️ Next steps

- Run the server in stdio and connect from your MCP client.
- Try listing tools and calling health to verify config.
- Register a test schedule, then run execute once to see it fire.
- Open `docs/promptyoself-tools.md` for tool inputs/outputs.
- File issues or ideas in the repository tracker.

## 🛰️ start.sh convenience script

The `start.sh` script loads `.env`, supports agent defaults, and can bind to Tailscale automatically.

Examples:

```bash
# HTTP on localhost with an explicit default agent
./start.sh http --agent-id agt_abc123 --port 8000 --path /mcp

# Enable single‑agent fallback and source a custom env file
./start.sh http --single --env-file ./prod.env

# Bind to your Tailscale IPv4 (auto‑detected)
./start.sh tailscale --port 8000 --path /mcp

# Equivalent shorthand: http but with host resolved to Tailscale IP
./start.sh http --host tailscale --port 8000 --path /mcp

# Start background executor loop (auto‑deliver prompts)
./start.sh http --host tailscale --port 8000 --path /mcp \
  --executor --executor-interval 60
```

## 📄 License

This project is licensed under the Creative Commons Attribution-ShareAlike 4.0 International License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support, questions, or contributions:

- **Author**: Mark Rizzn Hopkins
- **Repository**: <https://github.com/actuallyrizzn/sanctum-letta-mcp>
- **Issues**: <https://github.com/actuallyrizzn/sanctum-letta-mcp/issues>
