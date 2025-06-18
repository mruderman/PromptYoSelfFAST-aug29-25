"""
Pytest configuration and fixtures for MCP Server tests.
"""

import asyncio
import json
import os
import sys
import tempfile
import pytest
import aiohttp
from aiohttp.test_utils import TestClient, TestServer
from pathlib import Path
import pytest_asyncio

# Add the mcp directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp"))

from mcp_server import init_app, discover_plugins, build_tools_manifest, execute_plugin_tool


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def app():
    """Create a test application instance."""
    return await init_app()


@pytest_asyncio.fixture
async def client(app):
    """Create a test client for the application."""
    from aiohttp.test_utils import TestServer
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    try:
        yield client
    finally:
        await client.close()


@pytest.fixture
def temp_plugins_dir():
    """Create a temporary plugins directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugins_dir = Path(temp_dir) / "plugins"
        plugins_dir.mkdir()
        yield plugins_dir


@pytest.fixture
def mock_plugin_cli(temp_plugins_dir):
    """Create a mock plugin CLI for testing."""
    plugin_dir = temp_plugins_dir / "test_plugin"
    plugin_dir.mkdir()
    
    cli_path = plugin_dir / "cli.py"
    cli_content = '''#!/usr/bin/env python3
import argparse
import json
import sys

def test_command(args):
    return {"result": f"Test result: {args.get('param', 'default')}"}

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    
    test_parser = subparsers.add_parser("test-command")
    test_parser.add_argument("--param", default="default")
    
    args = parser.parse_args()
    
    if args.command == "test-command":
        result = test_command({"param": args.param})
        print(json.dumps(result))
        sys.exit(0)
    else:
        print(json.dumps({"error": "Unknown command"}))
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    with open(cli_path, 'w') as f:
        f.write(cli_content)
    
    # Make it executable
    os.chmod(cli_path, 0o755)
    
    return cli_path


@pytest.fixture
def sample_jsonrpc_request():
    """Sample JSON-RPC request for testing."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "test_plugin.test-command",
            "arguments": {
                "param": "test_value"
            }
        }
    }


@pytest.fixture
def sample_jsonrpc_response():
    """Sample JSON-RPC response for testing."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": "Test result: test_value"
                }
            ]
        }
    } 