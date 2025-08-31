> NOTE: This project now uses a FastMCP-based server that exposes the PromptYoSelf plugin directly. The legacy Sanctum HTTP/SSE server has been archived under `archive/sanctum/`.

# PromptYoSelf FastMCP Server

This repository contains the PromptYoSelf plugin and a [FastMCP](https://gofastmcp.com/)-based server to expose it as a set of tools for a Model Context Protocol (MCP) client, such as a [Letta](https://docs.letta.com/) agent.

- **Server file:** [promptyoself_mcp_server.py](promptyoself_mcp_server.py)
- **Developer Guide:** [AGENTS.md](AGENTS.md)
- **API reference:** [docs/promptyoself-tools.md](docs/promptyoself-tools.md)

## 🚀 Quick Start

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

### Docker Compose Configuration

When using Docker Compose, pass environment variables from your host:

```yaml
services:
  promptyoself:
    build: .
    environment:
      - LETTA_SERVER_PASSWORD=${LETTA_SERVER_PASSWORD}
      - LETTA_BASE_URL=http://letta:8283
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
- Fail the test run if code coverage is below 35% (temporary). We plan to raise this back toward 80% as tests are added.

To run only a specific category of tests (e.g., unit tests):

```bash
pytest tests/unit/
```

## ▶️ Next steps

- Run the server in stdio and connect from your MCP client.
- Try listing tools and calling health to verify config.
- Register a test schedule, then run execute once to see it fire.
- Open `docs/promptyoself-tools.md` for tool inputs/outputs.
- File issues or ideas in the repository tracker.

## 📄 License

This project is licensed under the Creative Commons Attribution-ShareAlike 4.0 International License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support, questions, or contributions:

- **Author**: Mark Rizzn Hopkins
- **Repository**: <https://github.com/actuallyrizzn/sanctum-letta-mcp>
- **Issues**: <https://github.com/actuallyrizzn/sanctum-letta-mcp/issues>
