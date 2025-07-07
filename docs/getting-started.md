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

## Docker Networking (Self-Hosted Letta/Sanctum)

If you're running Letta or Sanctum in Docker containers, you'll need to configure the MCP server URL to point to your **host machine** instead of `localhost`.

### Find Your Host IP
```bash
# Windows
ipconfig
# Look for your actual IP (e.g., 192.168.1.XXX)

# Linux/Mac
ip addr show
# or
ifconfig
```

### Configure Letta/Sanctum MCP Settings
Update your Letta/Sanctum MCP configuration to use your host machine's IP:

```json
{
  "server_name": "SanctumMCP",
  "type": "sse",
  "server_url": "http://192.168.1.XXX:8000"  // Your actual host IP
}
```

### Alternative Docker Options
- **Docker Host:** `http://host.docker.internal:8000` (if supported)
- **Same Network:** Use container name if both are in Docker
- **Port Forwarding:** Expose host port 8000 to container

### Common Issues
- ❌ `localhost:8000` - Won't work from Docker containers
- ✅ `192.168.1.XXX:8000` - Use your actual host IP
- ✅ `host.docker.internal:8000` - Docker host (if available)

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