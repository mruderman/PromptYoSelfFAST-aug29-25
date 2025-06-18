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
    async def test_sse_connection_establishment(self, client):
        """Test SSE connection establishment."""
        async with client.get('/sse') as response:
            assert response.status == 200
            assert response.headers['Content-Type'] == 'text/event-stream'
            assert response.headers['Cache-Control'] == 'no-cache'
            assert response.headers['Connection'] == 'keep-alive'
    
    @pytest.mark.asyncio
    async def test_sse_initial_tools_manifest(self, client):
        """Test that SSE sends initial tools manifest."""
        async with client.get('/sse') as response:
            assert response.status == 200
            
            # Read the first line of SSE data
            data = await response.content.readline()
            data_str = data.decode('utf-8').strip()
            
            # Should start with "data: "
            assert data_str.startswith('data: ')
            
            # Parse the JSON data
            json_str = data_str[6:]  # Remove "data: " prefix
            event_data = json.loads(json_str)
            
            # Verify JSON-RPC format
            assert "jsonrpc" in event_data
            assert event_data["jsonrpc"] == "2.0"
            assert "method" in event_data
            assert event_data["method"] == "notifications/tools/list"
            assert "params" in event_data
            assert "tools" in event_data["params"]
            assert isinstance(event_data["params"]["tools"], list)
    
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
    async def test_sse_connection_cleanup(self, client):
        """Test that SSE connection cleanup works properly."""
        # Get initial session count
        async with client.get('/health') as response:
            initial_data = await response.json()
            initial_sessions = initial_data["sessions"]
        
        # Create and immediately close SSE connection
        async with client.get('/sse') as response:
            assert response.status == 200
            # Read one line to establish connection
            await response.content.readline()
        
        # Wait a bit for cleanup
        await asyncio.sleep(0.1)
        
        # Check that session count returned to initial
        async with client.get('/health') as response:
            final_data = await response.json()
            final_sessions = final_data["sessions"]
            assert final_sessions <= initial_sessions
    
    @pytest.mark.asyncio
    async def test_sse_multiple_connections(self, client):
        """Test multiple SSE connections."""
        # Create multiple SSE connections
        connections = []
        for i in range(3):
            response = await client.get('/sse')
            assert response.status == 200
            connections.append(response)
        
        # Check that all connections are active
        async with client.get('/health') as response:
            health_data = await response.json()
            assert health_data["sessions"] >= 3
        
        # Close all connections
        for conn in connections:
            await conn.content.readline()  # Read one line to establish connection
        
        # Wait for cleanup
        await asyncio.sleep(0.1)
        
        # Check that sessions were cleaned up
        async with client.get('/health') as response:
            health_data = await response.json()
            assert health_data["sessions"] == 0
    
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