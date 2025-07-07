# Plugin Development Guide

This guide explains how to develop, test, and integrate plugins for the Sanctum Letta MCP system.

## Plugin Structure
Each plugin is a Python package in `mcp/plugins/` with a CLI entry point (`cli.py`). The server auto-discovers all plugins at startup.

### Directory Structure
```
mcp/plugins/
├── your-plugin/
│   ├── __init__.py
│   └── cli.py          # Main CLI entry point
```

## CLI Requirements
- Use `argparse` with subparsers for each command
- Help output must include an "Available commands:" section
- Each command should be listed as `command_name  Description`
- Arguments should be clearly documented in help text
- Return JSON output for all commands

## Example Plugin CLI
```python
#!/usr/bin/env python3
import argparse
import json
import sys
from typing import Dict, Any

def my_command(args: Dict[str, Any]) -> Dict[str, Any]:
    """Your command implementation."""
    param = args.get("param")
    if not param:
        return {"error": "Missing required argument: param"}
    
    return {"result": f"Processed: {param}"}

def main():
    parser = argparse.ArgumentParser(
        description="Your plugin description",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available commands:
  my-command    Description of your command

Examples:
  python cli.py my-command --param "value"
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add your command
    cmd_parser = subparsers.add_parser("my-command", help="Description")
    cmd_parser.add_argument("--param", required=True, help="Parameter description")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == "my-command":
            result = my_command({"param": args.param})
        else:
            result = {"error": f"Unknown command: {args.command}"}
        
        print(json.dumps(result))
        sys.exit(0 if "error" not in result else 1)
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Best Practices
- Use clear, descriptive command names (e.g., `click-button`, `send-message`)
- Return structured JSON output with `result` or `error` keys
- Handle errors gracefully and print helpful messages
- Follow the existing plugin patterns (see `botfather/` and `devops/` plugins)
- Use type hints for better code clarity

## Testing Plugins
- Write unit tests for each command in `tests/unit/test_plugins/`
- Use the MCP test suite for integration/e2e testing
- Test both success and error cases
- Ensure help output parsing works correctly

## Plugin Discovery
The server automatically discovers plugins by:
1. Scanning `mcp/plugins/` directory
2. Looking for `cli.py` files
3. Parsing help output to extract commands
4. Building the tools manifest

## References
- [API Reference](api-reference.md)
- [Testing Guide](testing.md)
- [Existing Plugins](../mcp/plugins/) 