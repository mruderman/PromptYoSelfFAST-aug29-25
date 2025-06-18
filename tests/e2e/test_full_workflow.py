"""
End-to-end tests for full workflow scenarios.
"""

import pytest
import json
import asyncio
import subprocess
from pathlib import Path
from aiohttp.test_utils import TestClient


class TestFullWorkflow:
    """Test cases for full workflow scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_plugin_workflow(self, client, temp_plugins_dir):
        """Test complete workflow from plugin discovery to execution."""
        # Create a real plugin for testing
        plugin_dir = temp_plugins_dir / "workflow_test_plugin"
        plugin_dir.mkdir()
        
        cli_path = plugin_dir / "cli.py"
        cli_content = '''#!/usr/bin/env python3
import argparse
import json
import sys

def workflow_command(args):
    param = args.get("param", "default")
    return {"result": f"Workflow executed with param: {param}"}

def main():
    parser = argparse.ArgumentParser(description="Workflow test plugin")
    subparsers = parser.add_subparsers(dest="command")
    
    workflow_parser = subparsers.add_parser("workflow-command")
    workflow_parser.add_argument("--param", default="default")
    
    args = parser.parse_args()
    
    if args.command == "workflow-command":
        result = workflow_command({"param": args.param})
        print(json.dumps(result))
        sys.exit(0)
    else:
        print(json.dumps({"error": "Unknown command"}))
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        with open(cli_path, 'w') as f:
            f.write(cli_content)
        
        # Make it executable
        import os
        os.chmod(cli_path, 0o755)
        
        # Mock the plugins directory path
        with pytest.MonkeyPatch().context() as m:
            m.setattr('mcp_server.Path', lambda x: type('MockPath', (), {
                'parent': temp_plugins_dir.parent,
                '__truediv__': lambda self, other: temp_plugins_dir / other if other == 'plugins' else Path(x) / other
            })())
            
            # Test 1: Health check shows no plugins initially
            async with client.get('/health') as response:
                health_data = await response.json()
                assert health_data["plugins"] == 0
            
            # Test 2: SSE connection shows tools manifest
            async with client.get('/sse') as response:
                assert response.status == 200
                
                # Read tools manifest
                data = await response.content.readline()
                data_str = data.decode('utf-8').strip()
                json_str = data_str[6:]  # Remove "data: " prefix
                event_data = json.loads(json_str)
                
                # Should have tools from our plugin
                tools = event_data["params"]["tools"]
                assert len(tools) > 0
                
                # Find our workflow tool
                workflow_tool = next((t for t in tools if t["name"] == "workflow_test_plugin.workflow-command"), None)
                assert workflow_tool is not None
                assert "param" in workflow_tool["inputSchema"]["properties"]
            
            # Test 3: Execute the plugin tool
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "workflow_test_plugin.workflow-command",
                    "arguments": {"param": "test_value"}
                }
            }
            
            async with client.post('/message', json=request) as response:
                assert response.status == 200
                
                data = await response.json()
                assert "jsonrpc" in data
                assert data["jsonrpc"] == "2.0"
                assert "result" in data
                assert "content" in data["result"]
                assert len(data["result"]["content"]) == 1
                assert data["result"]["content"][0]["type"] == "text"
                assert "Workflow executed with param: test_value" in data["result"]["content"][0]["text"]
            
            # Test 4: Health check shows plugin count
            async with client.get('/health') as response:
                health_data = await response.json()
                assert health_data["plugins"] > 0
    
    @pytest.mark.asyncio
    async def test_multiple_plugins_workflow(self, client, temp_plugins_dir):
        """Test workflow with multiple plugins."""
        # Create multiple plugins
        plugins = ["plugin_a", "plugin_b", "plugin_c"]
        
        for plugin_name in plugins:
            plugin_dir = temp_plugins_dir / plugin_name
            plugin_dir.mkdir()
            
            cli_path = plugin_dir / "cli.py"
            cli_content = f'''#!/usr/bin/env python3
import argparse
import json
import sys

def test_command(args):
    return {{"result": f"{plugin_name} executed successfully"}}

def main():
    parser = argparse.ArgumentParser(description="{plugin_name}")
    subparsers = parser.add_subparsers(dest="command")
    
    test_parser = subparsers.add_parser("test-command")
    
    args = parser.parse_args()
    
    if args.command == "test-command":
        result = test_command({{}})
        print(json.dumps(result))
        sys.exit(0)
    else:
        print(json.dumps({{"error": "Unknown command"}}))
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
            
            with open(cli_path, 'w') as f:
                f.write(cli_content)
            
            import os
            os.chmod(cli_path, 0o755)
        
        # Mock the plugins directory path
        with pytest.MonkeyPatch().context() as m:
            m.setattr('mcp_server.Path', lambda x: type('MockPath', (), {
                'parent': temp_plugins_dir.parent,
                '__truediv__': lambda self, other: temp_plugins_dir / other if other == 'plugins' else Path(x) / other
            })())
            
            # Test SSE shows all plugins
            async with client.get('/sse') as response:
                assert response.status == 200
                
                data = await response.content.readline()
                data_str = data.decode('utf-8').strip()
                json_str = data_str[6:]
                event_data = json.loads(json_str)
                
                tools = event_data["params"]["tools"]
                assert len(tools) == len(plugins)  # One tool per plugin
                
                # Check all plugins are present
                for plugin_name in plugins:
                    tool_name = f"{plugin_name}.test-command"
                    tool = next((t for t in tools if t["name"] == tool_name), None)
                    assert tool is not None
            
            # Test executing each plugin
            for plugin_name in plugins:
                request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": f"{plugin_name}.test-command",
                        "arguments": {}
                    }
                }
                
                async with client.post('/message', json=request) as response:
                    assert response.status == 200
                    
                    data = await response.json()
                    assert "result" in data
                    assert f"{plugin_name} executed successfully" in data["result"]["content"][0]["text"]
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, client, temp_plugins_dir):
        """Test error handling in complete workflow."""
        # Create a plugin that will fail
        plugin_dir = temp_plugins_dir / "error_plugin"
        plugin_dir.mkdir()
        
        cli_path = plugin_dir / "cli.py"
        cli_content = '''#!/usr/bin/env python3
import argparse
import json
import sys

def error_command(args):
    return {"error": "This is a test error"}

def main():
    parser = argparse.ArgumentParser(description="Error test plugin")
    subparsers = parser.add_subparsers(dest="command")
    
    error_parser = subparsers.add_parser("error-command")
    
    args = parser.parse_args()
    
    if args.command == "error-command":
        result = error_command({})
        print(json.dumps(result))
        sys.exit(0)
    else:
        print(json.dumps({"error": "Unknown command"}))
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        with open(cli_path, 'w') as f:
            f.write(cli_content)
        
        import os
        os.chmod(cli_path, 0o755)
        
        # Mock the plugins directory path
        with pytest.MonkeyPatch().context() as m:
            m.setattr('mcp_server.Path', lambda x: type('MockPath', (), {
                'parent': temp_plugins_dir.parent,
                '__truediv__': lambda self, other: temp_plugins_dir / other if other == 'plugins' else Path(x) / other
            })())
            
            # Test error handling
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "error_plugin.error-command",
                    "arguments": {}
                }
            }
            
            async with client.post('/message', json=request) as response:
                assert response.status == 200
                
                data = await response.json()
                assert "error" in data
                assert data["error"]["code"] == -32603  # Internal error
                assert "This is a test error" in data["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_workflow(self, client, temp_plugins_dir):
        """Test handling of concurrent requests."""
        # Create a plugin for concurrent testing
        plugin_dir = temp_plugins_dir / "concurrent_plugin"
        plugin_dir.mkdir()
        
        cli_path = plugin_dir / "cli.py"
        cli_content = '''#!/usr/bin/env python3
import argparse
import json
import sys
import time

def concurrent_command(args):
    # Simulate some work
    time.sleep(0.1)
    return {"result": "Concurrent execution completed"}

def main():
    parser = argparse.ArgumentParser(description="Concurrent test plugin")
    subparsers = parser.add_subparsers(dest="command")
    
    concurrent_parser = subparsers.add_parser("concurrent-command")
    
    args = parser.parse_args()
    
    if args.command == "concurrent-command":
        result = concurrent_command({})
        print(json.dumps(result))
        sys.exit(0)
    else:
        print(json.dumps({"error": "Unknown command"}))
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        with open(cli_path, 'w') as f:
            f.write(cli_content)
        
        import os
        os.chmod(cli_path, 0o755)
        
        # Mock the plugins directory path
        with pytest.MonkeyPatch().context() as m:
            m.setattr('mcp_server.Path', lambda x: type('MockPath', (), {
                'parent': temp_plugins_dir.parent,
                '__truediv__': lambda self, other: temp_plugins_dir / other if other == 'plugins' else Path(x) / other
            })())
            
            # Test concurrent requests
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "concurrent_plugin.concurrent-command",
                    "arguments": {}
                }
            }
            
            # Send multiple concurrent requests
            tasks = []
            for i in range(5):
                task = client.post('/message', json=request)
                tasks.append(task)
            
            # Wait for all requests to complete
            responses = await asyncio.gather(*tasks)
            
            # Check all responses
            for response in responses:
                assert response.status == 200
                
                data = await response.json()
                assert "result" in data
                assert "Concurrent execution completed" in data["result"]["content"][0]["text"]
    
    @pytest.mark.asyncio
    async def test_session_management_workflow(self, client):
        """Test session management in workflow."""
        # Test multiple SSE connections
        connections = []
        
        # Create multiple SSE connections
        for i in range(3):
            response = await client.get('/sse')
            assert response.status == 200
            connections.append(response)
        
        # Check session count
        async with client.get('/health') as response:
            health_data = await response.json()
            assert health_data["sessions"] >= 3
        
        # Read from each connection
        for conn in connections:
            data = await conn.content.readline()
            assert data is not None
        
        # Close connections
        for conn in connections:
            await conn.content.readline()  # Read one more line to establish connection
        
        # Wait for cleanup
        await asyncio.sleep(0.1)
        
        # Check session cleanup
        async with client.get('/health') as response:
            health_data = await response.json()
            assert health_data["sessions"] == 0 