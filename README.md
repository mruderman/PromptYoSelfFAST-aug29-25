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

## 🔒 Security

### History Scrub Documentation

If you need to remove sensitive information from Git history, see:
- **Documentation**: [docs/history-scrub.md](docs/history-scrub.md)
- **Helper Script**: [scripts/scrub-password-history.sh](scripts/scrub-password-history.sh)

⚠️ **Warning**: History rewriting operations are destructive and require careful coordination.

## 📞 Support

For support, questions, or contributions:

- **Author**: Mark Rizzn Hopkins
- **Repository**: https://github.com/actuallyrizzn/sanctum-letta-mcp
- **Issues**: https://github.com/actuallyrizzn/sanctum-letta-mcp/issues
