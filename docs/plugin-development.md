# Plugin Development Guide

This guide explains how to create and integrate new plugins into the MCP system.

## Plugin Architecture

MCP plugins are Python modules that follow a specific structure and interface. Each plugin should:

1. Be placed in the `mcp/plugins/` directory
2. Implement the required interface
3. Handle its own configuration and dependencies
4. Provide clear documentation

## Plugin Structure

A basic plugin structure looks like this:

```
mcp/plugins/
└── my_plugin/
    ├── __init__.py
    ├── cli.py
    ├── config.py
    └── README.md
```

### Required Files

1. `__init__.py` - Plugin registration and metadata
2. `cli.py` - Command-line interface implementation
3. `config.py` - Configuration handling
4. `README.md` - Plugin documentation

## Creating a New Plugin

### 1. Create Plugin Directory

```bash
mkdir -p mcp/plugins/my_plugin
touch mcp/plugins/my_plugin/__init__.py
touch mcp/plugins/my_plugin/cli.py
touch mcp/plugins/my_plugin/config.py
touch mcp/plugins/my_plugin/README.md
```

### 2. Implement Plugin Interface

#### `__init__.py`
```python
from typing import Dict, Any

def get_commands() -> Dict[str, Any]:
    """Return plugin command definitions."""
    return {
        "my-command": {
            "description": "Description of my command",
            "args": {
                "required_arg": {
                    "type": "string",
                    "required": True,
                    "description": "Description of required argument"
                },
                "optional_arg": {
                    "type": "integer",
                    "required": False,
                    "description": "Description of optional argument",
                    "default": 0
                }
            }
        }
    }
```

#### `cli.py`
```python
import json
import sys
from typing import Dict, Any

def run_command(command: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the specified command with given arguments."""
    if command == "my-command":
        return handle_my_command(args)
    raise ValueError(f"Unknown command: {command}")

def handle_my_command(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle the my-command command."""
    try:
        # Implement command logic here
        result = {
            "status": "success",
            "data": {
                "message": f"Processed {args['required_arg']}"
            }
        }
        return result
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    # Handle command-line invocation
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No command specified"}))
        sys.exit(1)
    
    command = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    
    try:
        result = run_command(command, args)
        print(json.dumps(result))
        sys.exit(0 if result["status"] == "success" else 1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
```

#### `config.py`
```python
import os
from typing import Dict, Any

def get_config() -> Dict[str, Any]:
    """Load and return plugin configuration."""
    return {
        "api_key": os.getenv("MY_PLUGIN_API_KEY"),
        "timeout": int(os.getenv("MY_PLUGIN_TIMEOUT", "60"))
    }
```

### 3. Add Plugin Documentation

#### `README.md`
```markdown
# My Plugin

## Description
Brief description of what the plugin does.

## Commands

### my-command
Description of the command and its usage.

#### Arguments
- `required_arg` (string, required): Description
- `optional_arg` (integer, optional): Description (default: 0)

#### Example
```bash
python -m mcp.plugins.my_plugin.cli my-command '{"required_arg": "value"}'
```

## Configuration
Required environment variables:
- `MY_PLUGIN_API_KEY`: API key for the service
- `MY_PLUGIN_TIMEOUT`: Command timeout in seconds (default: 60)
```

## Best Practices

1. **Error Handling**
   - Always return JSON responses
   - Use appropriate HTTP status codes
   - Include detailed error messages
   - Handle timeouts gracefully

2. **Configuration**
   - Use environment variables for sensitive data
   - Provide default values where appropriate
   - Document all configuration options

3. **Testing**
   - Write unit tests for your plugin
   - Test error cases and edge conditions
   - Verify timeout handling
   - Test with various input combinations

4. **Documentation**
   - Document all commands and arguments
   - Include usage examples
   - Explain configuration options
   - Document any dependencies

5. **Security**
   - Never log sensitive data
   - Validate all input
   - Use secure defaults
   - Follow principle of least privilege

## Example Plugin

Here's a complete example of a simple plugin that implements a calculator:

```python
# mcp/plugins/calculator/cli.py
import json
import sys
from typing import Dict, Any

def run_command(command: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute calculator commands."""
    if command == "add":
        return handle_add(args)
    elif command == "subtract":
        return handle_subtract(args)
    raise ValueError(f"Unknown command: {command}")

def handle_add(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle addition command."""
    try:
        a = float(args["a"])
        b = float(args["b"])
        return {
            "status": "success",
            "result": a + b
        }
    except (KeyError, ValueError) as e:
        return {
            "status": "error",
            "error": f"Invalid arguments: {str(e)}"
        }

def handle_subtract(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle subtraction command."""
    try:
        a = float(args["a"])
        b = float(args["b"])
        return {
            "status": "success",
            "result": a - b
        }
    except (KeyError, ValueError) as e:
        return {
            "status": "error",
            "error": f"Invalid arguments: {str(e)}"
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No command specified"}))
        sys.exit(1)
    
    command = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    
    try:
        result = run_command(command, args)
        print(json.dumps(result))
        sys.exit(0 if result["status"] == "success" else 1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
```

## Testing Your Plugin

1. Create a test file in `mcp/plugins/my_plugin/tests/`:

```python
# mcp/plugins/my_plugin/tests/test_cli.py
import unittest
from mcp.plugins.my_plugin.cli import run_command

class TestMyPlugin(unittest.TestCase):
    def test_my_command_success(self):
        result = run_command("my-command", {"required_arg": "test"})
        self.assertEqual(result["status"], "success")
        self.assertIn("data", result)

    def test_my_command_missing_arg(self):
        result = run_command("my-command", {})
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)

if __name__ == "__main__":
    unittest.main()
```

2. Run the tests:
```bash
python -m pytest mcp/plugins/my_plugin/tests/
```

## Contributing

When contributing a new plugin:

1. Follow the established structure
2. Include comprehensive tests
3. Provide clear documentation
4. Handle errors gracefully
5. Follow security best practices
6. Submit a pull request with a clear description 