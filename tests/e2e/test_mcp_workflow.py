"""
End-to-end tests for complete MCP workflow.
"""

import pytest
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch
import mcp.client.sse.sse_client as mcp_client


class TestMCPWorkflow:
    """End-to-end tests for complete MCP workflow."""
    
    @pytest.fixture
    def mcp_server_process(self, tmp_path):
        """Start the MCP server as a subprocess."""
        # Create test plugins
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        
        # Create a simple test plugin
        test_dir = plugins_dir / "test_plugin"
        test_dir.mkdir()
        cli_path = test_dir / "cli.py"
        cli_path.write_text('''#!/usr/bin/env python3
import argparse
import json
import sys

def test_command(args):
    return {"result": f"Test command executed with param: {args.get('param', 'default')}"}

def main():
    parser = argparse.ArgumentParser(
        description="Test plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available commands:
  test-command    Run the test command

Examples:
  python cli.py test-command --param test_value
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    test_parser = subparsers.add_parser("test-command", help="Run the test command")
    test_parser.add_argument("--param", default="default", help="Parameter for test")
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "test-command":
        result = test_command({"param": args.param})
    else:
        result = {"error": "Unknown command"}
    
    print(json.dumps(result))
    sys.exit(0)

if __name__ == "__main__":
    main()
''')
        cli_path.chmod(0o755)
        
        # Set environment variable for plugins directory
        env = os.environ.copy()
        env['MCP_PLUGINS_DIR'] = str(plugins_dir)
        
        # Start the MCP server
        process = subprocess.Popen(
            [sys.executable, "mcp/mcp_server.py"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        time.sleep(2)
        
        yield process
        
        # Cleanup
        process.terminate()
        process.wait()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_complete_workflow(self, mcp_server_process):
        """Test complete workflow from server startup to tool execution."""
        # Wait a bit more for server to be ready
        await asyncio.sleep(1)
        
        # Connect to the server
        async with mcp_client.MCPClientSSE("http://localhost:8000") as client:
            # Step 1: Initialize
            init_result = await client.send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "e2e-test", "version": "1.0.0"}
            })
            
            assert "result" in init_result
            assert init_result["result"]["protocolVersion"] == "2024-11-05"
            assert "serverInfo" in init_result["result"]
            
            # Step 2: List tools
            tools_result = await client.send_request("tools/list", {})
            
            assert "result" in tools_result
            assert "tools" in tools_result["result"]
            tools = tools_result["result"]["tools"]
            
            # Should have our test tool
            tool_names = [tool["name"] for tool in tools]
            assert "test_plugin.test-command" in tool_names
            
            # Step 3: Execute tool
            call_result = await client.send_request("tools/call", {
                "name": "test_plugin.test-command",
                "arguments": {"param": "e2e_test_value"}
            })
            
            assert "result" in call_result
            assert "content" in call_result["result"]
            assert len(call_result["result"]["content"]) == 1
            assert call_result["result"]["content"][0]["type"] == "text"
            assert "e2e_test_value" in call_result["result"]["content"][0]["text"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_multiple_plugins_workflow(self, tmp_path):
        """Test workflow with multiple plugins."""
        # Create multiple plugins
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        
        # Plugin 1: BotFather
        botfather_dir = plugins_dir / "botfather"
        botfather_dir.mkdir()
        cli_path = botfather_dir / "cli.py"
        cli_path.write_text('''#!/usr/bin/env python3
import argparse
import json
import sys

def send_message(args):
    return {"result": f"Sent message: {args.get('message')}"}

def main():
    parser = argparse.ArgumentParser(
        description="BotFather plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available commands:
  send-message    Send a message

Examples:
  python cli.py send-message --message "Hello"
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    send_parser = subparsers.add_parser("send-message", help="Send a message")
    send_parser.add_argument("--message", required=True, help="Message to send")
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "send-message":
        result = send_message({"message": args.message})
    else:
        result = {"error": "Unknown command"}
    
    print(json.dumps(result))
    sys.exit(0)

if __name__ == "__main__":
    main()
''')
        cli_path.chmod(0o755)
        
        # Plugin 2: DevOps
        devops_dir = plugins_dir / "devops"
        devops_dir.mkdir()
        cli_path = devops_dir / "cli.py"
        cli_path.write_text('''#!/usr/bin/env python3
import argparse
import json
import sys

def deploy(args):
    return {"result": f"Deployed {args.get('app-name')} to {args.get('environment', 'production')}"}

def main():
    parser = argparse.ArgumentParser(
        description="DevOps plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available commands:
  deploy    Deploy an application

Examples:
  python cli.py deploy --app-name "myapp" --environment "staging"
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    deploy_parser = subparsers.add_parser("deploy", help="Deploy an application")
    deploy_parser.add_argument("--app-name", required=True, help="Name of the application to deploy")
    deploy_parser.add_argument("--environment", default="production", help="Deployment environment")
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "deploy":
        result = deploy({"app-name": args.app_name, "environment": args.environment})
    else:
        result = {"error": "Unknown command"}
    
    print(json.dumps(result))
    sys.exit(0)

if __name__ == "__main__":
    main()
''')
        cli_path.chmod(0o755)
        
        # Start server with multiple plugins
        env = os.environ.copy()
        env['MCP_PLUGINS_DIR'] = str(plugins_dir)
        
        process = subprocess.Popen(
            [sys.executable, "mcp/mcp_server.py"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Connect and test
            async with mcp_client.MCPClientSSE("http://localhost:8000") as client:
                # Initialize
                await client.send_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "multi-test", "version": "1.0.0"}
                })
                
                # List tools
                tools_result = await client.send_request("tools/list", {})
                tools = tools_result["result"]["tools"]
                
                # Should have tools from both plugins
                tool_names = [tool["name"] for tool in tools]
                assert "botfather.send-message" in tool_names
                assert "devops.deploy" in tool_names
                
                # Test botfather tool
                bot_result = await client.send_request("tools/call", {
                    "name": "botfather.send-message",
                    "arguments": {"message": "Hello from E2E test"}
                })
                
                assert "result" in bot_result
                assert "Hello from E2E test" in bot_result["result"]["content"][0]["text"]
                
                # Test devops tool
                devops_result = await client.send_request("tools/call", {
                    "name": "devops.deploy",
                    "arguments": {"app-name": "testapp", "environment": "staging"}
                })
                
                assert "result" in devops_result
                assert "testapp" in devops_result["result"]["content"][0]["text"]
                assert "staging" in devops_result["result"]["content"][0]["text"]
        
        finally:
            process.terminate()
            process.wait()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_error_handling_workflow(self, tmp_path):
        """Test workflow with error handling."""
        # Create an error plugin
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
        
        # Start server with error plugin
        env = os.environ.copy()
        env['MCP_PLUGINS_DIR'] = str(plugins_dir)
        
        process = subprocess.Popen(
            [sys.executable, "mcp/mcp_server.py"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Connect and test error handling
            async with mcp_client.MCPClientSSE("http://localhost:8000") as client:
                # Initialize
                await client.send_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "error-test", "version": "1.0.0"}
                })
                
                # List tools
                tools_result = await client.send_request("tools/list", {})
                tools = tools_result["result"]["tools"]
                
                # Should have the error tool
                tool_names = [tool["name"] for tool in tools]
                assert "error_plugin.error-command" in tool_names
                
                # Test error tool
                error_result = await client.send_request("tools/call", {
                    "name": "error_plugin.error-command",
                    "arguments": {}
                })
                
                # Should get an error response
                assert "error" in error_result
                assert error_result["error"]["code"] == -32603  # Internal error
                assert "This is a test error from the plugin" in error_result["error"]["message"]
        
        finally:
            process.terminate()
            process.wait()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_concurrent_workflow(self, tmp_path):
        """Test concurrent tool executions."""
        # Create a plugin that can handle concurrent requests
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        
        concurrent_dir = plugins_dir / "concurrent_plugin"
        concurrent_dir.mkdir()
        cli_path = concurrent_dir / "cli.py"
        cli_path.write_text('''#!/usr/bin/env python3
import argparse
import json
import sys
import time

def concurrent_command(args):
    # Simulate some work
    time.sleep(0.1)
    return {"result": f"Concurrent command executed with id: {args.get('id', 'unknown')}"}

def main():
    parser = argparse.ArgumentParser(
        description="Concurrent test plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available commands:
  concurrent-command    Run the concurrent command

Examples:
  python cli.py concurrent-command --id 123
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    concurrent_parser = subparsers.add_parser("concurrent-command", help="Run the concurrent command")
    concurrent_parser.add_argument("--id", default="unknown", help="Request ID")
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "concurrent-command":
        result = concurrent_command({"id": args.id})
    else:
        result = {"error": "Unknown command"}
    
    print(json.dumps(result))
    sys.exit(0)

if __name__ == "__main__":
    main()
''')
        cli_path.chmod(0o755)
        
        # Start server
        env = os.environ.copy()
        env['MCP_PLUGINS_DIR'] = str(plugins_dir)
        
        process = subprocess.Popen(
            [sys.executable, "mcp/mcp_server.py"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Connect and test concurrent execution
            async with mcp_client.MCPClientSSE("http://localhost:8000") as client:
                # Initialize
                await client.send_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "concurrent-test", "version": "1.0.0"}
                })
                
                # Execute multiple tools concurrently
                tasks = []
                for i in range(5):
                    task = client.send_request("tools/call", {
                        "name": "concurrent_plugin.concurrent-command",
                        "arguments": {"id": f"req_{i}"}
                    })
                    tasks.append(task)
                
                # Wait for all to complete
                results = await asyncio.gather(*tasks)
                
                # Verify all executions were successful
                for i, result in enumerate(results):
                    assert "result" in result
                    assert "content" in result["result"]
                    assert f"req_{i}" in result["result"]["content"][0]["text"]
        
        finally:
            process.terminate()
            process.wait()


# Import os for environment variable handling
import os 