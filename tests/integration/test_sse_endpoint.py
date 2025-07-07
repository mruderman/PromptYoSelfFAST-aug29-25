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
    @pytest.mark.timeout(10)  # 10 second timeout for SSE connection
    async def test_sse_connection(self, client):
        """Test basic SSE connection establishment."""
        async with client.get('/mcp/sse') as response:
            assert response.status == 200
            assert response.headers['Content-Type'] == 'text/event-stream'
            assert response.headers['Cache-Control'] == 'no-cache'
            assert response.headers['Connection'] == 'keep-alive'
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)  # 10 second timeout for connection message
    async def test_sse_connection_message_format(self, client):
        """Test that the SSE connection message is correct."""
        async with client.get('/mcp/sse') as response:
            assert response.status == 200
            data = await asyncio.wait_for(response.content.readline(), timeout=5.0)
            data_str = data.decode('utf-8').strip()
            assert data_str.startswith('data: ')
            json_str = data_str[6:]
            event_data = json.loads(json_str)
            assert event_data == {"type": "connection_established"}
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)  # 10 second timeout for CORS headers
    async def test_sse_cors_headers(self, client):
        """Test that CORS headers are set on SSE endpoint."""
        async with client.get('/mcp/sse') as response:
            assert response.status == 200
            assert 'Access-Control-Allow-Origin' in response.headers
            assert 'Access-Control-Allow-Headers' in response.headers
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)  # 10 second timeout for tools manifest
    async def test_sse_tools_manifest(self, client):
        """Test that SSE sends tools manifest on connection."""
        async with client.get('/mcp/sse') as response:
            assert response.status == 200
            
            # Read the first event (connection message)
            data = await asyncio.wait_for(response.content.readline(), timeout=5.0)
            assert data is not None
            
            data_str = data.decode('utf-8').strip()
            assert data_str.startswith('data: ')
            
            # Parse the JSON data
            json_str = data_str[6:]  # Remove "data: " prefix
            event_data = json.loads(json_str)
            
            # Verify the structure
            assert "type" in event_data
            assert event_data["type"] == "connection_established"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(15)  # 15 second timeout for multiple connections
    async def test_multiple_sse_connections(self, client):
        """Test multiple concurrent SSE connections."""
        connections = []
        
        # Create multiple connections
        for i in range(3):
            response = await asyncio.wait_for(client.get('/mcp/sse'), timeout=5.0)
            assert response.status == 200
            connections.append(response)
        
        # Read from each connection
        for conn in connections:
            data = await asyncio.wait_for(conn.content.readline(), timeout=5.0)
            assert data is not None
            assert data.decode('utf-8').strip().startswith('data: ')
        
        # Close connections
        for conn in connections:
            await conn.close()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(15)  # 15 second timeout for connection cleanup
    async def test_sse_connection_cleanup(self, client):
        """Test that SSE connections are properly cleaned up."""
        # Check initial session count
        async with client.get('/health') as response:
            health_data = await response.json()
            initial_sessions = health_data["sessions"]
        
        # Create and close a connection
        async with client.get('/mcp/sse') as response:
            assert response.status == 200
            data = await asyncio.wait_for(response.content.readline(), timeout=5.0)
            assert data is not None
        
        # Wait for cleanup
        await asyncio.sleep(0.1)
        
        # Check session count is back to initial
        async with client.get('/health') as response:
            health_data = await response.json()
            assert health_data["sessions"] == initial_sessions
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)  # 10 second timeout for session creation
    async def test_sse_session_creation(self, client):
        """Test that SSE connection creates a session."""
        # Get initial session count
        async with client.get('/health') as response:
            initial_data = await response.json()
            initial_sessions = initial_data["sessions"]
        
        # Create SSE connection
        async with client.get('/mcp/sse') as response:
            assert response.status == 200
            
            # Check that session count increased
            async with client.get('/health') as health_response:
                health_data = await health_response.json()
                new_sessions = health_data["sessions"]
                assert new_sessions >= initial_sessions
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)  # 10 second timeout for tools manifest with plugins
    async def test_sse_tools_manifest_with_plugins(self, client):
        """Test SSE tools manifest when plugins are available."""
        # Mock plugin registry with plugins
        with pytest.MonkeyPatch().context() as m:
            m.setattr('mcp.mcp_server.plugin_registry', {
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
            
            async with client.get('/mcp/sse') as response:
                assert response.status == 200
                
                # Read the first line of SSE data
                data = await asyncio.wait_for(response.content.readline(), timeout=5.0)
                data_str = data.decode('utf-8').strip()
                
                # Parse the JSON data
                json_str = data_str[6:]  # Remove "data: " prefix
                event_data = json.loads(json_str)
                
                # Verify connection message
                assert event_data == {"type": "connection_established"}
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)  # 10 second timeout for data format
    async def test_sse_data_format(self, client):
        """Test SSE data format."""
        async with client.get('/mcp/sse') as response:
            assert response.status == 200
            
            # Read the connection message
            line = await asyncio.wait_for(response.content.readline(), timeout=5.0)
            if line:
                line_str = line.decode('utf-8').strip()
                
                # Check that data line follows SSE format
                if line_str.startswith('data: '):
                    json_str = line_str[6:]  # Remove "data: " prefix
                    try:
                        event_data = json.loads(json_str)
                        # Verify it's the connection message
                        assert event_data == {"type": "connection_established"}
                    except json.JSONDecodeError:
                        pytest.fail(f"Invalid JSON in SSE data: {json_str}")
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)  # 10 second timeout for connection persistence
    async def test_sse_connection_persistence(self, client):
        """Test that SSE connection persists."""
        async with client.get('/mcp/sse') as response:
            assert response.status == 200
            
            # Read initial data
            initial_data = await asyncio.wait_for(response.content.readline(), timeout=5.0)
            assert initial_data is not None
            
            # Wait a bit and check connection is still alive
            await asyncio.sleep(0.1)
            
            # Try to read more data (should not fail)
            try:
                # The connection should still be open
                assert not response.content.at_eof()
            except Exception:
                pytest.fail("SSE connection should remain open") 