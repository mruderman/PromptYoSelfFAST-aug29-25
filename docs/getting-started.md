# Getting Started with MCP

This guide will help you get up and running with MCP quickly.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/actuallyrizzn/sanctum-letta-mcp.git
   cd sanctum-letta-mcp
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On Unix/MacOS
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your configuration:
   ```env
   # Server Configuration
   MCP_HOST=localhost
   MCP_PORT=5000
   
   # Plugin-specific configurations
   BOTFATHER_API_KEY=your_api_key_here
   ```

## Running MCP

1. Start the server:
   ```bash
   python -m mcp.main
   ```

2. The server will start on the configured host and port (default: http://localhost:5000)

## Basic Usage

### Checking Available Plugins

To see what plugins and commands are available:

```bash
curl http://localhost:5000/help
```

### Running a Command

To execute a command through a plugin:

```bash
curl -X POST http://localhost:5000/run \
  -H "Content-Type: application/json" \
  -d '{
    "plugin": "botfather",
    "command": "click-button",
    "args": {
      "button-text": "Payments",
      "msg-id": 12345678
    }
  }'
```

### Response Format

Successful responses will look like:
```json
{
  "status": "success",
  "plugin": "botfather",
  "command": "click-button",
  "args": { ... },
  "output": { /* JSON or text result from plugin */ },
  "error": null
}
```

Error responses will include an error message:
```json
{
  "status": "error",
  "plugin": "botfather",
  "command": "click-button",
  "args": { ... },
  "output": null,
  "error": "Error message here"
}
```

## Next Steps

- Read the [API Reference](api-reference.md) for detailed endpoint documentation
- Check out [Plugin Development](plugin-development.md) if you want to create new plugins
- Review [Security](security.md) best practices for production deployment 