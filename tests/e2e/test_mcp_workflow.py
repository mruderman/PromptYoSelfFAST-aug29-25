"""
End-to-end tests for complete MCP workflow.
"""

import pytest
import asyncio
import json
import subprocess
import sys
import time
import os
import uuid
import aiohttp
from pathlib import Path
from unittest.mock import patch


class TestMCPWorkflow:
    """End-to-end tests for complete MCP workflow."""
    
    async def send_mcp_request(self, session, method, params=None):
        """Send an MCP request and return the response."""
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        async with session.post("http://localhost:8000/mcp/message", json=request) as response:
            return await response.json()
    
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
            [sys.executable, "smcp/mcp_server.py"],
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
        async with aiohttp.ClientSession() as session:
            # Step 1: Initialize
            init_result = await self.send_mcp_request(session, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "e2e-test", "version": "1.0.0"}
            })
            
            assert "result" in init_result
            assert init_result["result"]["protocolVersion"] == "2024-11-05"
            assert "serverInfo" in init_result["result"]
            
            # Step 2: List tools
            tools_result = await self.send_mcp_request(session, "tools/list", {})
            
            assert "result" in tools_result
            assert "tools" in tools_result["result"]
            tools = tools_result["result"]["tools"]
            
            # Should have our real plugins
            tool_names = [tool["name"] for tool in tools]
            assert "botfather.click-button" in tool_names
            assert "botfather.send-message" in tool_names
            assert "devops.deploy" in tool_names
            assert "devops.rollback" in tool_names
            assert "devops.status" in tool_names
            
            # Step 3: Execute a tool
            call_result = await self.send_mcp_request(session, "tools/call", {
                "name": "botfather.send-message",
                "arguments": {"message": "Hello from E2E test"}
            })
            
            assert "result" in call_result
            assert "content" in call_result["result"]
            assert call_result["result"]["content"][0]["type"] == "text"
            assert "Sent message: Hello from E2E test" in call_result["result"]["content"][0]["text"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_multiple_plugins_workflow(self, tmp_path):
        """Test workflow with multiple plugins."""
        # Start server with default plugins
        process = subprocess.Popen(
            [sys.executable, "smcp/mcp_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        try:
            # Wait for server to start
            time.sleep(2)

            # Connect and test
            async with aiohttp.ClientSession() as session:
                # Initialize
                await self.send_mcp_request(session, "initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "multi-test", "version": "1.0.0"}
                })

                # List tools
                tools_result = await self.send_mcp_request(session, "tools/list", {})
                tools = tools_result["result"]["tools"]

                # Should have tools from both plugins
                tool_names = [tool["name"] for tool in tools]
                assert "botfather.send-message" in tool_names
                assert "devops.deploy" in tool_names

                # Test botfather tool
                bot_result = await self.send_mcp_request(session, "tools/call", {
                    "name": "botfather.send-message",
                    "arguments": {"message": "Hello from E2E test"}
                })

                assert "result" in bot_result
                assert "Hello from E2E test" in bot_result["result"]["content"][0]["text"]

                # Test devops tool
                devops_result = await self.send_mcp_request(session, "tools/call", {
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
        # Start server with default plugins
        process = subprocess.Popen(
            [sys.executable, "smcp/mcp_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        try:
            # Wait for server to start
            time.sleep(2)

            # Connect and test error handling
            async with aiohttp.ClientSession() as session:
                # Initialize
                await self.send_mcp_request(session, "initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "error-test", "version": "1.0.0"}
                })

                # List tools
                tools_result = await self.send_mcp_request(session, "tools/list", {})
                tools = tools_result["result"]["tools"]

                # Should have our real plugins
                tool_names = [tool["name"] for tool in tools]
                assert "botfather.click-button" in tool_names
                assert "devops.deploy" in tool_names

                # Test error handling by calling a tool with missing required arguments
                error_result = await self.send_mcp_request(session, "tools/call", {
                    "name": "botfather.click-button",
                    "arguments": {}  # Missing required arguments
                })

                # Verify error response
                assert "error" in error_result
                assert error_result["error"]["code"] == -32603  # Internal error
                assert "arguments are required" in error_result["error"]["message"]

        finally:
            process.terminate()
            process.wait()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_concurrent_workflow(self, tmp_path):
        """Test concurrent tool executions."""
        # Start server with default plugins
        process = subprocess.Popen(
            [sys.executable, "smcp/mcp_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        try:
            # Wait for server to start
            time.sleep(2)

            # Connect and test concurrent execution
            async with aiohttp.ClientSession() as session:
                # Initialize
                await self.send_mcp_request(session, "initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "concurrent-test", "version": "1.0.0"}
                })

                # Execute multiple tools concurrently
                tasks = []
                for i in range(5):
                    task = self.send_mcp_request(session, "tools/call", {
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

        finally:
            process.terminate()
            process.wait()


# Import os for environment variable handling
import os 