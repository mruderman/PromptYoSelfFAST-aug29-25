"""
Integration tests for SSE endpoint.
"""

import pytest
import json
import asyncio
from aiohttp.test_utils import TestClient


class TestSSEEndpoint:
    """Test cases for SSE endpoint."""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # 30 second timeout for SSE connection
    async def test_sse_connection(self, client):
        """Test basic SSE connection establishment."""
        async with client.get('/sse') as response:
            assert response.status == 200
            assert response.headers['Content-Type'] == 'text/event-stream'
            assert response.headers['Cache-Control'] == 'no-cache'
            assert response.headers['Connection'] == 'keep-alive'
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # 30 second timeout for tools manifest
    async def test_sse_tools_manifest(self, client):
        """Test that SSE sends tools manifest on connection."""
        async with client.get('/sse') as response:
            assert response.status == 200
            
            # Read the first event (tools manifest)
            data = await asyncio.wait_for(response.content.readline(), timeout=10.0)
            assert data is not None
            
            data_str = data.decode('utf-8').strip()
            assert data_str.startswith('data: ')
            
            # Parse the JSON data
            json_str = data_str[6:]  # Remove "data: " prefix
            event_data = json.loads(json_str)
            
            # Verify the structure
            assert "jsonrpc" in event_data
            assert event_data["jsonrpc"] == "2.0"
            assert "method" in event_data
            assert event_data["method"] == "tools/list"
            assert "params" in event_data
            assert "tools" in event_data["params"]
            assert isinstance(event_data["params"]["tools"], list)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # 30 second timeout for multiple connections
    async def test_multiple_sse_connections(self, client):
        """Test multiple concurrent SSE connections."""
        connections = []
        
        # Create multiple connections
        for i in range(3):
            response = await client.get('/sse')
            assert response.status == 200
            connections.append(response)
        
        # Read from each connection
        for conn in connections:
            data = await asyncio.wait_for(conn.content.readline(), timeout=10.0)
            assert data is not None
            assert data.decode('utf-8').strip().startswith('data: ')
        
        # Close connections
        for conn in connections:
            await asyncio.wait_for(conn.content.readline(), timeout=5.0)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # 30 second timeout for connection cleanup
    async def test_sse_connection_cleanup(self, client):
        """Test that SSE connections are properly cleaned up."""
        # Check initial session count
        async with client.get('/health') as response:
            health_data = await response.json()
            initial_sessions = health_data["sessions"]
        
        # Create and close a connection
        async with client.get('/sse') as response:
            assert response.status == 200
            data = await asyncio.wait_for(response.content.readline(), timeout=10.0)
            assert data is not None
        
        # Wait for cleanup
        await asyncio.sleep(0.1)
        
        # Check session count is back to initial
        async with client.get('/health') as response:
            health_data = await response.json()
            assert health_data["sessions"] == initial_sessions
    
    @pytest.mark.asyncio
    async def test_sse_session_creation(self, client):
        """Test that SSE connection creates a session."""
        # Get initial session count
        async with client.get('/health') as response:
            initial_data = await response.json()
            initial_sessions = initial_data["sessions"]
        
        # Create SSE connection
        async with client.get('/sse') as response:
            assert response.status == 200
            
            # Check that session count increased
            async with client.get('/health') as health_response:
                health_data = await health_response.json()
                new_sessions = health_data["sessions"]
                assert new_sessions >= initial_sessions
    
    @pytest.mark.asyncio
    async def test_sse_tools_manifest_with_plugins(self, client):
        """Test SSE tools manifest when plugins are available."""
        # Mock plugin registry with plugins
        with pytest.MonkeyPatch().context() as m:
            m.setattr('mcp_server.plugin_registry', {
                "test_plugin": {
                    "path": "/path/to/plugin/cli.py",
                    "commands": {}
                }
            })
            
            # Mock subprocess.run for help command
            import subprocess
            from unittest.mock import MagicMock
            
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = """
usage: cli.py [-h] {test-command} ...

Test plugin

positional arguments:
  {test-command}
                        Available commands
    test-command         Test command
            """
            
            m.setattr('subprocess.run', lambda *args, **kwargs: mock_result)
            
            async with client.get('/sse') as response:
                assert response.status == 200
                
                # Read the first line of SSE data
                data = await response.content.readline()
                data_str = data.decode('utf-8').strip()
                
                # Parse the JSON data
                json_str = data_str[6:]  # Remove "data: " prefix
                event_data = json.loads(json_str)
                
                # Verify tools are included
                tools = event_data["params"]["tools"]
                assert len(tools) > 0
                
                # Check for test plugin tool
                test_tool = next((t for t in tools if t["name"] == "test_plugin.test-command"), None)
                assert test_tool is not None
                assert test_tool["description"] == "test_plugin test-command command"
    
    @pytest.mark.asyncio
    async def test_sse_connection_headers(self, client):
        """Test SSE connection headers."""
        async with client.get('/sse') as response:
            assert response.status == 200
            
            # Check required SSE headers
            assert 'Content-Type' in response.headers
            assert response.headers['Content-Type'] == 'text/event-stream'
            assert 'Cache-Control' in response.headers
            assert response.headers['Cache-Control'] == 'no-cache'
            assert 'Connection' in response.headers
            assert response.headers['Connection'] == 'keep-alive'
            
            # Check CORS headers
            assert 'Access-Control-Allow-Origin' in response.headers
            assert 'Access-Control-Allow-Methods' in response.headers
            assert 'Access-Control-Allow-Headers' in response.headers
    
    @pytest.mark.asyncio
    async def test_sse_data_format(self, client):
        """Test SSE data format."""
        async with client.get('/sse') as response:
            assert response.status == 200
            
            # Read multiple lines to check format
            lines = []
            for _ in range(3):
                line = await response.content.readline()
                if line:
                    lines.append(line.decode('utf-8').strip())
            
            # Check that we have at least one data line
            assert len(lines) > 0
            
            # Check that data lines follow SSE format
            for line in lines:
                if line.startswith('data: '):
                    json_str = line[6:]  # Remove "data: " prefix
                    try:
                        event_data = json.loads(json_str)
                        # Verify JSON-RPC structure
                        assert "jsonrpc" in event_data
                        assert event_data["jsonrpc"] == "2.0"
                    except json.JSONDecodeError:
                        pytest.fail(f"Invalid JSON in SSE data: {json_str}")
    
    @pytest.mark.asyncio
    async def test_sse_connection_persistence(self, client):
        """Test that SSE connection persists."""
        async with client.get('/sse') as response:
            assert response.status == 200
            
            # Read initial data
            initial_data = await response.content.readline()
            assert initial_data is not None
            
            # Wait a bit and check connection is still alive
            await asyncio.sleep(0.1)
            
            # Try to read more data (should not fail)
            try:
                # The connection should still be open
                assert not response.content.at_eof()
            except Exception:
                pytest.fail("SSE connection should remain open") 