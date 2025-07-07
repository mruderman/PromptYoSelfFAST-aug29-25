# Getting Started

Welcome to the **Sanctum Letta MCP (SSE Edition)**! This guide will help you set up the project, install dependencies, and run your first SSE-based workflow.

## Prerequisites
- Python 3.8+
- Git

## Installation
1. **Clone the repository:**
   ```sh
   git clone https://github.com/actuallyrizzn/sanctum-letta-mcp.git
   cd sanctum-letta-mcp
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

## Running the SSE Server
```sh
python -m mcp.mcp_server
```
The server will start on `http://localhost:8000` by default.

## Testing Your Installation
```sh
# Run all tests
python run_tests.py --type all

# Run specific test types
python run_tests.py --type unit      # Unit tests
python run_tests.py --type integration  # Integration tests  
python run_tests.py --type e2e       # End-to-end tests
```

## Available Plugins
Your MCP server comes with two built-in plugins:

### BotFather Plugin
- **click-button** - Click buttons in BotFather messages
- **send-message** - Send messages to BotFather

### DevOps Plugin  
- **deploy** - Deploy applications to different environments
- **rollback** - Rollback applications to specific versions
- **status** - Check application deployment status

## Next Steps
- Explore the [API Reference](api-reference.md) for SSE communication
- Learn about [Plugin Development](plugin-development.md)
- Review [Security](security.md) best practices

For troubleshooting, see the [Monitoring](monitoring.md) guide. 