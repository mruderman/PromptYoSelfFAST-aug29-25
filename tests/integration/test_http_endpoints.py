"""
Integration tests for HTTP endpoints.
"""

import pytest
import json
from aiohttp.test_utils import TestClient


class TestHTTPEndpoints:
    """Test cases for HTTP endpoints."""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # 30 second timeout for health check
    async def test_health_endpoint(self, client):
        """Test health check endpoint."""
        async with client.get('/health') as response:
            assert response.status == 200
            assert response.headers['Content-Type'] == 'application/json'
            
            data = await response.json()
            assert "status" in data
            assert data["status"] == "healthy"
            assert "plugins" in data
            assert "sessions" in data
            assert isinstance(data["plugins"], int)
            assert isinstance(data["sessions"], int)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # 30 second timeout for message endpoint
    async def test_message_endpoint_valid_request(self, client, sample_jsonrpc_request, sample_jsonrpc_response):
        """Test message endpoint with valid JSON-RPC request."""
        async with client.post('/message', json=sample_jsonrpc_request) as response:
            assert response.status == 200
            
            data = await response.json()
            assert "jsonrpc" in data
            assert data["jsonrpc"] == "2.0"
            assert "id" in data
            assert data["id"] == sample_jsonrpc_request["id"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # 30 second timeout for invalid JSON
    async def test_message_endpoint_invalid_json(self, client):
        """Test message endpoint with invalid JSON."""
        async with client.post('/message', data="invalid json") as response:
            assert response.status == 400
            assert response.headers['Content-Type'] == 'application/json'
            
            data = await response.json()
            assert "error" in data
            assert data["error"]["code"] == -32700  # Parse error
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # 30 second timeout for invalid method
    async def test_message_endpoint_invalid_jsonrpc_version(self, client):
        """Test message endpoint with invalid JSON-RPC version."""
        request = {
            "jsonrpc": "1.0",
            "id": 1,
            "method": "tools/call",
            "params": {}
        }
        
        async with client.post('/message', json=request) as response:
            assert response.status == 200
            
            data = await response.json()
            assert "jsonrpc" in data
            assert data["jsonrpc"] == "2.0"
            assert "error" in data
            assert data["error"]["code"] == -32600  # Invalid Request
            assert "jsonrpc must be '2.0'" in data["error"]["message"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # 30 second timeout for missing tool name
    async def test_message_endpoint_missing_tool_name(self, client):
        """Test message endpoint with missing tool name."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "arguments": {"param": "value"}
            }
        }
        
        async with client.post('/message', json=request) as response:
            assert response.status == 200
            
            data = await response.json()
            assert "jsonrpc" in data
            assert data["jsonrpc"] == "2.0"
            assert "error" in data
            assert data["error"]["code"] == -32602  # Invalid params
            assert "missing tool name" in data["error"]["message"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # 30 second timeout for unknown method
    async def test_message_endpoint_unknown_method(self, client):
        """Test message endpoint with unknown method."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unknown/method",
            "params": {}
        }
        
        async with client.post('/message', json=request) as response:
            assert response.status == 200
            
            data = await response.json()
            assert "jsonrpc" in data
            assert data["jsonrpc"] == "2.0"
            assert "error" in data
            assert data["error"]["code"] == -32601  # Method not found
            assert "Method not found" in data["error"]["message"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # 30 second timeout for non-dict body
    async def test_message_endpoint_non_dict_body(self, client):
        """Test message endpoint with non-dict body."""
        async with client.post('/message', json="not a dict") as response:
            assert response.status == 200
            
            data = await response.json()
            assert "jsonrpc" in data
            assert data["jsonrpc"] == "2.0"
            assert "error" in data
            assert data["error"]["code"] == -32600  # Invalid Request
            assert "Invalid Request" in data["error"]["message"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # 30 second timeout for tools call
    async def test_message_endpoint_tool_execution_success(self, client):
        """Test message endpoint with successful tool execution."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "test_plugin.test-command",
                "arguments": {"param": "test_value"}
            }
        }
        
        # Mock the plugin registry and execution
        with pytest.MonkeyPatch().context() as m:
            m.setattr('mcp_server.plugin_registry', {
                "test_plugin": {
                    "path": "/path/to/plugin/cli.py",
                    "commands": {}
                }
            })
            
            # Mock subprocess.run to return success
            import subprocess
            from unittest.mock import MagicMock
            
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps({"result": "Test result: test_value"})
            
            m.setattr('subprocess.run', lambda *args, **kwargs: mock_result)
            
            async with client.post('/message', json=request) as response:
                assert response.status == 200
                
                data = await response.json()
                assert "jsonrpc" in data
                assert data["jsonrpc"] == "2.0"
                assert "result" in data
                assert "content" in data["result"]
                assert len(data["result"]["content"]) == 1
                assert data["result"]["content"][0]["type"] == "text"
                assert "Test result: test_value" in data["result"]["content"][0]["text"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # 30 second timeout for tools call
    async def test_message_endpoint_tool_execution_error(self, client):
        """Test message endpoint with tool execution error."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "test_plugin.test-command",
                "arguments": {}
            }
        }
        
        # Mock the plugin registry and execution
        with pytest.MonkeyPatch().context() as m:
            m.setattr('mcp_server.plugin_registry', {
                "test_plugin": {
                    "path": "/path/to/plugin/cli.py",
                    "commands": {}
                }
            })
            
            # Mock subprocess.run to return error
            import subprocess
            from unittest.mock import MagicMock
            
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Plugin execution failed"
            
            m.setattr('subprocess.run', lambda *args, **kwargs: mock_result)
            
            async with client.post('/message', json=request) as response:
                assert response.status == 200
                
                data = await response.json()
                assert "jsonrpc" in data
                assert data["jsonrpc"] == "2.0"
                assert "error" in data
                assert data["error"]["code"] == -32603  # Internal error
                assert "Plugin execution failed" in data["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_cors_headers(self, client):
        """Test that CORS headers are properly set."""
        async with client.get('/health') as response:
            assert response.status == 200
            
            # Check for CORS headers
            assert 'Access-Control-Allow-Origin' in response.headers
            assert 'Access-Control-Allow-Methods' in response.headers
            assert 'Access-Control-Allow-Headers' in response.headers
    
    @pytest.mark.asyncio
    async def test_options_request(self, client):
        """Test OPTIONS request for CORS preflight."""
        async with client.options('/message') as response:
            assert response.status == 200
            
            # Check for CORS headers
            assert 'Access-Control-Allow-Origin' in response.headers
            assert 'Access-Control-Allow-Methods' in response.headers
            assert 'Access-Control-Allow-Headers' in response.headers 