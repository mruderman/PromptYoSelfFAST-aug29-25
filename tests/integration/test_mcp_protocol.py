"""
Integration tests for MCP protocol using official MCP client.
"""

import sys
sys.path.insert(0, 'venv/Lib/site-packages')

import pytest
import asyncio
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import mcp.client.sse.sse_client as mcp_client


class TestMCPProtocol:
    """Integration tests for MCP protocol using official client."""
    
    @pytest.fixture
    def mcp_server_url(self):
        """Get the MCP server URL."""
        return "http://localhost:8000"
    
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
        async with mcp_client.MCPClientSSE(mcp_server_url) as client:
            # Send initialize request
            init_result = await client.send_request("initialize", {
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
        async with mcp_client.MCPClientSSE(mcp_server_url) as client:
            # Initialize first
            await client.send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            })
            
            # List tools
            tools_result = await client.send_request("tools/list", {})
            
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
            async with mcp_client.MCPClientSSE(mcp_server_url) as client:
                # Initialize first
                await client.send_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                })
                
                # List tools
                tools_result = await client.send_request("tools/list", {})
                
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
    async def test_tool_execution_success(self, mcp_server_url, mock_plugins):
        """Test successful tool execution."""
        with patch.dict('os.environ', {'MCP_PLUGINS_DIR': str(mock_plugins)}):
            async with mcp_client.MCPClientSSE(mcp_server_url) as client:
                # Initialize first
                await client.send_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                })
                
                # Execute a tool
                call_result = await client.send_request("tools/call", {
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
                assert "Clicked button: OK in message 123" in call_result["result"]["content"][0]["text"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_tool_execution_error(self, mcp_server_url, error_plugin):
        """Test tool execution with error."""
        with patch.dict('os.environ', {'MCP_PLUGINS_DIR': str(error_plugin)}):
            async with mcp_client.MCPClientSSE(mcp_server_url) as client:
                # Initialize first
                await client.send_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                })
                
                # Execute a tool that returns an error
                call_result = await client.send_request("tools/call", {
                    "name": "error_plugin.error-command",
                    "arguments": {}
                })
                
                # Verify error response
                assert "error" in call_result
                assert call_result["error"]["code"] == -32603  # Internal error
                assert "This is a test error from the plugin" in call_result["error"]["message"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_tool_execution_invalid_tool(self, mcp_server_url):
        """Test tool execution with invalid tool name."""
        async with mcp_client.MCPClientSSE(mcp_server_url) as client:
            # Initialize first
            await client.send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            })
            
            # Execute a non-existent tool
            call_result = await client.send_request("tools/call", {
                "name": "nonexistent.tool",
                "arguments": {}
            })
            
            # Verify error response
            assert "error" in call_result
            assert call_result["error"]["code"] == -32603  # Internal error
            assert "Plugin not found" in call_result["error"]["message"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_multiple_tool_executions(self, mcp_server_url, mock_plugins):
        """Test multiple tool executions in sequence."""
        with patch.dict('os.environ', {'MCP_PLUGINS_DIR': str(mock_plugins)}):
            async with mcp_client.MCPClientSSE(mcp_server_url) as client:
                # Initialize first
                await client.send_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                })
                
                # Execute multiple tools
                results = []
                tools_to_test = [
                    ("botfather.send-message", {"message": "Hello"}),
                    ("devops.deploy", {"app-name": "testapp", "environment": "staging"}),
                    ("devops.status", {"app-name": "testapp"})
                ]
                
                for tool_name, arguments in tools_to_test:
                    result = await client.send_request("tools/call", {
                        "name": tool_name,
                        "arguments": arguments
                    })
                    results.append(result)
                
                # Verify all executions were successful
                for result in results:
                    assert "result" in result
                    assert "content" in result["result"]
                    assert len(result["result"]["content"]) == 1
                    assert result["result"]["content"][0]["type"] == "text"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_concurrent_tool_executions(self, mcp_server_url, mock_plugins):
        """Test concurrent tool executions."""
        with patch.dict('os.environ', {'MCP_PLUGINS_DIR': str(mock_plugins)}):
            async with mcp_client.MCPClientSSE(mcp_server_url) as client:
                # Initialize first
                await client.send_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                })
                
                # Execute tools concurrently
                tasks = []
                for i in range(3):
                    task = client.send_request("tools/call", {
                        "name": "devops.status",
                        "arguments": {"app-name": f"app{i}"}
                    })
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks)
                
                # Verify all executions were successful
                for result in results:
                    assert "result" in result
                    assert "content" in result["result"]
                    assert len(result["result"]["content"]) == 1
                    assert result["result"]["content"][0]["type"] == "text"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_invalid_jsonrpc_request(self, mcp_server_url):
        """Test handling of invalid JSON-RPC requests."""
        async with mcp_client.MCPClientSSE(mcp_server_url) as client:
            # Try to send an invalid request (this might not be possible with the official client)
            # This test verifies the server handles malformed requests gracefully
            try:
                # The official client should handle this, but we can test error responses
                await client.send_request("invalid/method", {})
            except Exception as e:
                # Expected to fail with invalid method
                assert "Method not found" in str(e) or "invalid" in str(e).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_connection_cleanup(self, mcp_server_url):
        """Test that connections are properly cleaned up."""
        # Create multiple connections and verify they close properly
        connections = []
        for i in range(3):
            client = mcp_client.MCPClientSSE(mcp_server_url)
            await client.__aenter__()
            connections.append(client)
        
        # Close all connections
        for client in connections:
            await client.__aexit__(None, None, None)
        
        # Verify no exceptions were raised during cleanup
        assert True  # If we get here, cleanup was successful 