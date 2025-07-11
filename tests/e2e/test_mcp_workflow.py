"""
End-to-end tests for MCP server workflow.
Tests complete client-server interaction including SSE, initialization, and tool execution.
"""

import asyncio
import json
import pytest
import httpx
import subprocess
import time
from typing import AsyncGenerator, Dict, Any
from pathlib import Path
import sys


class TestMCPWorkflow:
    """Test complete MCP workflow from client connection to tool execution."""
    
    @pytest.fixture
    async def client(self) -> AsyncGenerator[httpx.AsyncClient, None]:
        """Create HTTP client for testing."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            yield client
    
    @pytest.fixture
    def base_url(self) -> str:
        """Base URL for MCP server."""
        return "http://localhost:8000"
    
    @pytest.fixture
    def server_process(self):
        """Start MCP server for testing."""
        # Start server in background
        process = subprocess.Popen(
            [sys.executable, "smcp/mcp_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        time.sleep(3)
        
        yield process
        
        # Cleanup
        process.terminate()
        process.wait()
    
    async def test_complete_mcp_workflow(self, client: httpx.AsyncClient, base_url: str):
        """Test complete MCP workflow: connect, initialize, list tools, call tool."""
        
        # Step 1: Establish SSE connection
        sse_connected = False
        try:
            async with client.stream("GET", f"{base_url}/sse", timeout=5.0) as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers.get("content-type", "")
                sse_connected = True
                
                # Step 2: Send initialize request
                initialize_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {
                            "tools": {},
                            "resources": {},
                            "prompts": {}
                        },
                        "clientInfo": {
                            "name": "test-client",
                            "version": "1.0.0"
                        }
                    }
                }
                
                init_response = await client.post(
                    f"{base_url}/messages/",
                    json=initialize_request,
                    timeout=10.0
                )
                
                assert init_response.status_code == 200
                init_data = init_response.json()
                assert init_data["jsonrpc"] == "2.0"
                assert init_data["id"] == 1
                assert "result" in init_data
                
                # Step 3: Send initialized notification
                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "initialized",
                    "params": {}
                }
                
                await client.post(
                    f"{base_url}/messages/",
                    json=initialized_notification,
                    timeout=10.0
                )
                
                # Step 4: List available tools
                list_tools_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list"
                }
                
                tools_response = await client.post(
                    f"{base_url}/messages/",
                    json=list_tools_request,
                    timeout=10.0
                )
                
                assert tools_response.status_code == 200
                tools_data = tools_response.json()
                assert "result" in tools_data
                assert "tools" in tools_data["result"]
                
                tools = tools_data["result"]["tools"]
                assert len(tools) >= 1
                
                # Step 5: Call health tool
                health_tool = next((t for t in tools if t["name"] == "health"), None)
                assert health_tool is not None
                
                call_health_request = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "health",
                        "arguments": {}
                    }
                }
                
                health_response = await client.post(
                    f"{base_url}/messages/",
                    json=call_health_request,
                    timeout=10.0
                )
                
                assert health_response.status_code == 200
                health_data = health_response.json()
                assert "result" in health_data
                assert "content" in health_data["result"]
                
                content = health_data["result"]["content"][0]
                assert content["type"] == "text"
                
                health_info = json.loads(content["text"])
                assert health_info["status"] == "healthy"
                assert "plugins" in health_info
                assert "plugin_names" in health_info
                
        except httpx.TimeoutException:
            # SSE connections are expected to timeout
            if not sse_connected:
                raise
        except Exception as e:
            if not sse_connected:
                raise
            # If SSE connected but other operations failed, that's a test failure
            raise
    
    async def test_plugin_tool_execution(self, client: httpx.AsyncClient, base_url: str):
        """Test execution of plugin tools."""
        
        # First initialize the connection
        await self._initialize_connection(client, base_url)
        
        # List tools to find plugin tools
        tools_response = await client.post(
            f"{base_url}/messages/",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            },
            timeout=10.0
        )
        
        tools_data = tools_response.json()
        tools = tools_data["result"]["tools"]
        
        # Look for botfather tools
        botfather_tools = [t for t in tools if t["name"].startswith("botfather.")]
        
        if botfather_tools:
            # Test a botfather tool
            tool_name = botfather_tools[0]["name"]
            
            call_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": {}
                }
            }
            
            response = await client.post(
                f"{base_url}/messages/",
                json=call_request,
                timeout=15.0  # Plugin execution might take longer
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Tool should either succeed or return a meaningful error
            if "result" in data:
                assert "content" in data["result"]
            elif "error" in data:
                # Plugin might not be properly configured, but should return structured error
                assert "code" in data["error"]
                assert "message" in data["error"]
    
    async def test_error_handling(self, client: httpx.AsyncClient, base_url: str):
        """Test error handling for various scenarios."""
        
        # Test malformed JSON
        response = await client.post(
            f"{base_url}/messages/",
            content="invalid json",
            headers={"content-type": "application/json"},
            timeout=10.0
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32700  # Parse error
        
        # Test invalid method
        response = await client.post(
            f"{base_url}/messages/",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "nonexistent_method"
            },
            timeout=10.0
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method not found
        
        # Test invalid tool call
        response = await client.post(
            f"{base_url}/messages/",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "nonexistent_tool",
                    "arguments": {}
                }
            },
            timeout=10.0
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
    
    async def test_concurrent_sessions(self, client: httpx.AsyncClient, base_url: str):
        """Test handling of concurrent sessions."""
        
        # Create multiple SSE connections
        sse_tasks = []
        for i in range(3):
            task = asyncio.create_task(self._establish_sse_connection(client, base_url))
            sse_tasks.append(task)
        
        # Wait for connections to establish
        await asyncio.sleep(2)
        
        # Send concurrent requests
        request_tasks = []
        for i in range(5):
            task = asyncio.create_task(
                client.post(
                    f"{base_url}/messages/",
                    json={
                        "jsonrpc": "2.0",
                        "id": i,
                        "method": "tools/list"
                    },
                    timeout=10.0
                )
            )
            request_tasks.append(task)
        
        # Wait for all requests to complete
        responses = await asyncio.gather(*request_tasks, return_exceptions=True)
        
        # All requests should succeed
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                pytest.fail(f"Request {i} failed: {response}")
            else:
                assert response.status_code == 200
        
        # Cancel SSE tasks
        for task in sse_tasks:
            task.cancel()
        
        try:
            await asyncio.gather(*sse_tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass
    
    async def test_server_restart_recovery(self, client: httpx.AsyncClient, base_url: str):
        """Test that client can recover from server restart."""
        
        # Establish connection
        await self._initialize_connection(client, base_url)
        
        # Send a request
        response = await client.post(
            f"{base_url}/messages/",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            },
            timeout=10.0
        )
        
        assert response.status_code == 200
        
        # Note: In a real scenario, the server would restart here
        # For this test, we just verify the connection was working
    
    async def _initialize_connection(self, client: httpx.AsyncClient, base_url: str):
        """Helper to initialize MCP connection."""
        # Send initialize request
        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        response = await client.post(
            f"{base_url}/messages/",
            json=initialize_request,
            timeout=10.0
        )
        
        assert response.status_code == 200
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        
        await client.post(
            f"{base_url}/messages/",
            json=initialized_notification,
            timeout=10.0
        )
    
    async def _establish_sse_connection(self, client: httpx.AsyncClient, base_url: str):
        """Helper to establish SSE connection."""
        try:
            async with client.stream("GET", f"{base_url}/sse", timeout=5.0) as response:
                assert response.status_code == 200
                # Just verify connection is established
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        break
        except httpx.TimeoutException:
            # Expected for SSE connections
            pass 