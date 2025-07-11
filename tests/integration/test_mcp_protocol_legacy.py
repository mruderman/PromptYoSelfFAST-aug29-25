"""
ARCHIVED: Legacy integration tests for MCP protocol using POST endpoints.
This file is kept for backward compatibility only. The current MCP protocol uses SSE for all communication.
"""

# --- Legacy test code below ---

"""
Integration tests for MCP protocol using official MCP client.
"""

import pytest
import asyncio
import json
import subprocess
import aiohttp
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestMCPProtocol:
    """Integration tests for MCP protocol using aiohttp client."""
    
    @pytest.fixture
    def mcp_server_url(self):
        """Get the MCP server URL."""
        return "http://localhost:8000"
    
    async def send_mcp_request(self, session, mcp_server_url, method, params=None):
        """Send an MCP request and return the response."""
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        async with session.post(f"{mcp_server_url}/mcp/message", json=request) as response:
            return await response.json()
    
    @pytest.fixture
    def mock_plugins(self, tmp_path):
        """Create mock plugins for testing."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        
        # Create botfather plugin
        botfather_dir = plugins_dir / "botfather"
        botfather_dir.mkdir()
        cli_path = botfather_dir / "cli.py"
        cli_path.write_text('''#!/usr/bin/env python3
import argparse
import json
import sys

def click_button(args):
    return {"result": f"Clicked button: {args.get('button-text')} in message {args.get('msg-id')}"}

def send_message(args):
    return {"result": f"Sent message: {args.get('message')}"}

def main():
    parser = argparse.ArgumentParser(
        description="BotFather automation plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available commands:
  click-button    Click a button in a message
  send-message    Send a message to BotFather

Examples:
  python cli.py click-button --button-text "OK" --msg-id 123
  python cli.py send-message --message "Hello"
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    click_parser = subparsers.add_parser("click-button", help="Click a button in a message")
    click_parser.add_argument("--button-text", required=True, help="Text of the button to click")
    click_parser.add_argument("--msg-id", type=int, required=True, help="Message ID containing the button")
    
    send_parser = subparsers.add_parser("send-message", help="Send a message to BotFather")
    send_parser.add_argument("--message", required=True, help="Message to send")
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "click-button":
        result = click_button({"button-text": args.button_text, "msg-id": args.msg_id})
    elif args.command == "send-message":
        result = send_message({"message": args.message})
    else:
        result = {"error": "Unknown command"}
    
    print(json.dumps(result))
    sys.exit(0)

if __name__ == "__main__":
    main()
''')
        cli_path.chmod(0o755)
        
        # Create devops plugin
        devops_dir = plugins_dir / "devops"
        devops_dir.mkdir()
        cli_path = devops_dir / "cli.py"
        cli_path.write_text('''#!/usr/bin/env python3
import argparse
import json
import sys

def deploy(args):
    return {"result": f"Deployed {args.get('app-name')} to {args.get('environment', 'production')}"}

def rollback(args):
    return {"result": f"Rolled back {args.get('app-name')} to version {args.get('version')}"}

def status(args):
    return {"result": f"Status of {args.get('app-name')}: Running"}

def main():
    parser = argparse.ArgumentParser(
        description="DevOps automation plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available commands:
  deploy    Deploy an application
  rollback  Rollback an application deployment
  status    Get deployment status

Examples:
  python cli.py deploy --app-name "myapp" --environment "staging"
  python cli.py rollback --app-name "myapp" --version "1.2.3"
  python cli.py status --app-name "myapp"
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    deploy_parser = subparsers.add_parser("deploy", help="Deploy an application")
    deploy_parser.add_argument("--app-name", required=True, help="Name of the application to deploy")
    deploy_parser.add_argument("--environment", default="production", help="Deployment environment")
    
    rollback_parser = subparsers.add_parser("rollback", help="Rollback an application deployment")
    rollback_parser.add_argument("--app-name", required=True, help="Name of the application to rollback")
    rollback_parser.add_argument("--version", required=True, help="Version to rollback to")
    
    status_parser = subparsers.add_parser("status", help="Get deployment status")
    status_parser.add_argument("--app-name", required=True, help="Name of the application")
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "deploy":
        result = deploy({"app-name": args.app_name, "environment": args.environment})
    elif args.command == "rollback":
        result = rollback({"app-name": args.app_name, "version": args.version})
    elif args.command == "status":
        result = status({"app-name": args.app_name})
    else:
        result = {"error": "Unknown command"}
    
    print(json.dumps(result))
    sys.exit(0)

if __name__ == "__main__":
    main()
''')
        cli_path.chmod(0o755)
        
        return plugins_dir
    
    @pytest.fixture
    def error_plugin(self, tmp_path):
        """Create an error plugin for testing error handling."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        
        error_dir = plugins_dir / "error_plugin"
        error_dir.mkdir()
        cli_path = error_dir / "cli.py"
        cli_path.write_text('''#!/usr/bin/env python3
import argparse
import json
import sys

def error_command(args):
    return {"error": "This is a test error from the plugin"}

def main():
    parser = argparse.ArgumentParser(
        description="Error test plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available commands:
  error-command    Run the error command

Examples:
  python cli.py error-command
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    error_parser = subparsers.add_parser("error-command", help="Run the error command")
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "error-command":
        result = error_command({})
    else:
        result = {"error": "Unknown command"}
    
    print(json.dumps(result))
    sys.exit(0)

if __name__ == "__main__":
    main()
''')
        cli_path.chmod(0o755)
        
        return plugins_dir
    
    # ... rest of the legacy test code ... 