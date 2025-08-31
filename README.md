> NOTE: This project now uses a FastMCP-based server that exposes the PromptYoSelf plugin directly. The legacy Sanctum HTTP/SSE server has been archived under `archive/sanctum/`.

# PromptYoSelf FastMCP Server

This repository contains the PromptYoSelf plugin and a [FastMCP](https://gofastmcp.com/)-based server to expose it as a set of tools for a Model Context Protocol (MCP) client, such as a [Letta](https://docs.letta.com/) agent.

- **Server file:** [promptyoself_mcp_server.py](promptyoself_mcp_server.py)
- **Developer Guide:** [promptyoself/AGENTS.md](promptyoself/AGENTS.md)
- **API reference:** [docs/promptyoself-tools.md](docs/promptyoself-tools.md)

## 🚀 Quick Start

1.  **Install Dependencies**

    This project has two sets of dependencies. Install both.
    ```bash
    # Install server and test dependencies
    pip install -r requirements.txt

    # Install PromptYoSelf plugin dependencies
    pip install -r promptyoself/requirements.txt
    ```

2.  **Run the Server**

    The server can be run in two modes:

    *   **Standard I/O (stdio):** This is the simplest mode and is best for local development or connecting to local agents.
        ```bash
        python promptyoself_mcp_server.py
        ```

    *   **HTTP:** This runs the server as a web service, which is necessary for connecting to remote agents (e.g., a Letta agent running in the cloud or a Docker container).
        ```bash
        python promptyoself_mcp_server.py --transport http --host 127.0.0.1 --port 8000 --path /mcp
        ```

## 🔐 Configuration

### Environment Variables

The server requires configuration for connecting to your Letta instance. **Never commit real secrets to version control!**

### Local Development Setup

1. Copy the example configuration file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set your actual values:
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
- Fail the test run if code coverage is below 80%.

To run only a specific category of tests (e.g., unit tests):
```bash
pytest tests/unit/
```

## 📄 License

This project is licensed under the Creative Commons Attribution-ShareAlike 4.0 International License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support, questions, or contributions:

- **Author**: Mark Rizzn Hopkins
- **Repository**: https://github.com/actuallyrizzn/sanctum-letta-mcp
- **Issues**: https://github.com/actuallyrizzn/sanctum-letta-mcp/issues
