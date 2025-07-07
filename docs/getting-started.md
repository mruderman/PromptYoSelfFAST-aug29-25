# Getting Started

Welcome to the Letta Internal MCP! This guide will help you set up the project, install dependencies, and run your first workflow.

## Prerequisites
- Python 3.8+
- Node.js (for plugin development)
- Git

## Installation
1. **Clone the repository:**
   ```sh
   git clone <repo-url>
   cd letta-internal-mcp
   ```
2. **Set up a virtual environment:**
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install Python dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

## Running the Server
```sh
python -m mcp.mcp_server
```

## Running Tests
```sh
pytest
```

## Next Steps
- Explore the [API Reference](api-reference.md)
- Learn about [Plugin Development](plugin-development.md)
- Review [Security](security.md) best practices

For troubleshooting, see the [Monitoring](monitoring.md) guide. 