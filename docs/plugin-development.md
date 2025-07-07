# Plugin Development Guide

This guide explains how to develop, test, and integrate plugins for the Letta Internal MCP system.

## Plugin Structure
- Each plugin is a Python package with a CLI entry point (e.g., `cli.py`).
- Use `argparse` with subparsers for each command.
- Each command must have a name, description, and argument specification.

## CLI Requirements
- Help output must include an "Available commands:" section.
- Each command should be listed as `command_name  Description`.
- Arguments should be clearly documented in help text.

## Example Plugin CLI
```python
import argparse
parser = argparse.ArgumentParser(description='My Plugin')
subparsers = parser.add_subparsers(dest='command')
# Add commands here
```

## Best Practices
- Use clear, descriptive command names.
- Return structured output (JSON or plain text).
- Handle errors gracefully and print helpful messages.

## Testing Plugins
- Write unit tests for each command.
- Use the MCP test suite for integration/e2e testing.

## References
- [API Reference](api-reference.md)
- [Testing Guide](testing.md) 