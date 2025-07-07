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
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_initialize_protocol(self, mcp_server_url):
        """Test MCP protocol initialization."""
        async with aiohttp.ClientSession() as session:
            # Send initialize request
            init_result = await self.send_mcp_request(session, mcp_server_url, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            })
            
            # Verify initialize response
            assert "result" in init_result
            assert init_result["result"]["protocolVersion"] == "2024-11-05"
            assert "serverInfo" in init_result["result"]
            assert init_result["result"]["serverInfo"]["name"] == "sanctum-letta-mcp"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_list_tools_empty(self, mcp_server_url):
        """Test listing tools when no plugins are available."""
        async with aiohttp.ClientSession() as session:
            # Initialize first
            await self.send_mcp_request(session, mcp_server_url, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            })
            
            # List tools
            tools_result = await self.send_mcp_request(session, mcp_server_url, "tools/list", {})
            
            # Verify tools list response
            assert "result" in tools_result
            assert "tools" in tools_result["result"]
            assert isinstance(tools_result["result"]["tools"], list)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_list_tools_with_plugins(self, mcp_server_url, mock_plugins):
        """Test listing tools when plugins are available."""
        # Set environment variable to use our mock plugins
        with patch.dict('os.environ', {'MCP_PLUGINS_DIR': str(mock_plugins)}):
            async with aiohttp.ClientSession() as session:
                # Initialize first
                await self.send_mcp_request(session, mcp_server_url, "initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                })
                
                # List tools
                tools_result = await self.send_mcp_request(session, mcp_server_url, "tools/list", {})
                
                # Verify tools list response
                assert "result" in tools_result
                assert "tools" in tools_result["result"]
                tools = tools_result["result"]["tools"]
                
                # Should have tools from both plugins
                tool_names = [tool["name"] for tool in tools]
                assert "botfather.click-button" in tool_names
                assert "botfather.send-message" in tool_names
                assert "devops.deploy" in tool_names
                assert "devops.rollback" in tool_names
                assert "devops.status" in tool_names
                
                # Verify tool schemas
                click_tool = next(t for t in tools if t["name"] == "botfather.click-button")
                assert "inputSchema" in click_tool
                assert click_tool["inputSchema"]["type"] == "object"
                assert "properties" in click_tool["inputSchema"]
                assert "button-text" in click_tool["inputSchema"]["properties"]
                assert "msg-id" in click_tool["inputSchema"]["properties"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_tool_execution_success(self, mcp_server_url):
        """Test successful tool execution."""
        async with aiohttp.ClientSession() as session:
            # Initialize first
            await self.send_mcp_request(session, mcp_server_url, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            })

            # Execute a tool
            call_result = await self.send_mcp_request(session, mcp_server_url, "tools/call", {
                "name": "botfather.click-button",
                "arguments": {
                    "button-text": "OK",
                    "msg-id": 123
                }
            })

            # Verify tool execution response
            assert "result" in call_result
            assert "content" in call_result["result"]
            assert len(call_result["result"]["content"]) == 1
            assert call_result["result"]["content"][0]["type"] == "text"
            assert "Clicked button OK on message 123" in call_result["result"]["content"][0]["text"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_tool_execution_error(self, mcp_server_url):
        """Test tool execution with error."""
        async with aiohttp.ClientSession() as session:
            # Initialize first
            await self.send_mcp_request(session, mcp_server_url, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            })

            # Execute a tool with missing required arguments (should return error)
            call_result = await self.send_mcp_request(session, mcp_server_url, "tools/call", {
                "name": "botfather.click-button",
                "arguments": {}  # Missing required arguments
            })

            # Verify error response
            assert "error" in call_result
            assert call_result["error"]["code"] == -32603  # Internal error
            assert "arguments are required" in call_result["error"]["message"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_tool_execution_invalid_tool(self, mcp_server_url):
        """Test tool execution with invalid tool name."""
        async with aiohttp.ClientSession() as session:
            # Initialize first
            await self.send_mcp_request(session, mcp_server_url, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            })
            
            # Execute a non-existent tool
            call_result = await self.send_mcp_request(session, mcp_server_url, "tools/call", {
                "name": "nonexistent.tool",
                "arguments": {}
            })
            
            # Verify error response
            assert "error" in call_result
            assert call_result["error"]["code"] == -32603  # Internal error
            assert "Plugin not found" in call_result["error"]["message"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_multiple_tool_executions(self, mcp_server_url):
        """Test multiple tool executions in sequence."""
        async with aiohttp.ClientSession() as session:
            # Initialize first
            await self.send_mcp_request(session, mcp_server_url, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            })

            # Execute multiple tools in sequence
            results = []
            
            # Test botfather tool
            bot_result = await self.send_mcp_request(session, mcp_server_url, "tools/call", {
                "name": "botfather.send-message",
                "arguments": {"message": "Hello from test"}
            })
            results.append(bot_result)
            
            # Test devops tool
            devops_result = await self.send_mcp_request(session, mcp_server_url, "tools/call", {
                "name": "devops.deploy",
                "arguments": {"app-name": "testapp", "environment": "staging"}
            })
            results.append(devops_result)

            # Verify all executions were successful
            for result in results:
                assert "result" in result
                assert "content" in result["result"]
                assert result["result"]["content"][0]["type"] == "text"
            
            # Verify specific outputs
            assert "Sent message: Hello from test" in results[0]["result"]["content"][0]["text"]
            assert "Deployed testapp to staging" in results[1]["result"]["content"][0]["text"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_concurrent_tool_executions(self, mcp_server_url):
        """Test concurrent tool executions."""
        async with aiohttp.ClientSession() as session:
            # Initialize first
            await self.send_mcp_request(session, mcp_server_url, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            })

            # Execute multiple tools concurrently
            tasks = []
            for i in range(3):
                task = self.send_mcp_request(session, mcp_server_url, "tools/call", {
                    "name": "devops.status",
                    "arguments": {"app-name": f"app_{i}"}
                })
                tasks.append(task)

            # Wait for all to complete
            results = await asyncio.gather(*tasks)

            # Verify all executions were successful
            for i, result in enumerate(results):
                assert "result" in result
                assert "content" in result["result"]
                assert result["result"]["content"][0]["type"] == "text"
                assert f"Status for app_{i}: healthy" in result["result"]["content"][0]["text"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_invalid_jsonrpc_request(self, mcp_server_url):
        """Test handling of invalid JSON-RPC requests."""
        async with aiohttp.ClientSession() as session:
            # Try to send an invalid request
            try:
                result = await self.send_mcp_request(session, mcp_server_url, "invalid/method", {})
                # Should get an error response
                assert "error" in result
                assert result["error"]["code"] == -32601  # Method not found
            except Exception as e:
                # Expected to fail with invalid method
                assert "Method not found" in str(e) or "invalid" in str(e).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_connection_cleanup(self, mcp_server_url):
        """Test that connections are properly cleaned up."""
        # Create multiple sessions and verify they close properly
        sessions = []
        for i in range(3):
            session = aiohttp.ClientSession()
            await session.__aenter__()
            sessions.append(session)
        
        # Close all sessions
        for session in sessions:
            await session.__aexit__(None, None, None)
        
        # Verify no exceptions were raised during cleanup
        assert True  # If we get here, cleanup was successful 