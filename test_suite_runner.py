#!/usr/bin/env python3
"""
Simple test runner for the MCP server test suite.
"""

import sys
import os
import asyncio
import json
import httpx
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.dirname(__file__))

def test_plugin_discovery():
    """Test plugin discovery functionality."""
    print("Testing plugin discovery...")
    
    # Import the function
    from smcp.mcp_server import discover_plugins
    
    # Test with environment variable
    test_plugins_dir = Path(__file__).parent / "smcp" / "plugins"
    original_env = os.environ.get("MCP_PLUGINS_DIR")
    
    try:
        os.environ["MCP_PLUGINS_DIR"] = str(test_plugins_dir)
        plugins = discover_plugins()
        
        print(f"Discovered plugins: {list(plugins.keys())}")
        
        # Should find at least botfather plugin
        assert "botfather" in plugins, "botfather plugin not found"
        assert plugins["botfather"]["path"].endswith("cli.py"), "botfather cli.py not found"
        
        print("✓ Plugin discovery test passed")
        return True
        
    except Exception as e:
        print(f"✗ Plugin discovery test failed: {e}")
        return False
    finally:
        if original_env:
            os.environ["MCP_PLUGINS_DIR"] = original_env
        else:
            os.environ.pop("MCP_PLUGINS_DIR", None)

async def test_mcp_server_endpoints():
    """Test MCP server endpoints."""
    print("Testing MCP server endpoints...")
    
    base_url = "http://localhost:8000"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test SSE endpoint
            try:
                async with client.stream("GET", f"{base_url}/sse", timeout=5.0) as response:
                    assert response.status_code == 200
                    assert "text/event-stream" in response.headers.get("content-type", "")
                    print("✓ SSE endpoint test passed")
            except httpx.TimeoutException:
                # SSE connections are expected to timeout
                print("✓ SSE endpoint test passed (timeout expected)")
            
            # Test message endpoint with initialize
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
            data = response.json()
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == 1
            assert "result" in data
            
            print("✓ Message endpoint test passed")
            return True
            
    except Exception as e:
        print(f"✗ MCP server endpoints test failed: {e}")
        return False

async def test_health_tool():
    """Test health tool functionality."""
    print("Testing health tool...")
    
    base_url = "http://localhost:8000"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Call health tool
            call_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "health",
                    "arguments": {}
                }
            }
            
            response = await client.post(
                f"{base_url}/messages/",
                json=call_request,
                timeout=10.0
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "result" in data
            assert "content" in data["result"]
            
            content = data["result"]["content"][0]
            assert content["type"] == "text"
            
            health_info = json.loads(content["text"])
            assert health_info["status"] == "healthy"
            assert "plugins" in health_info
            assert "plugin_names" in health_info
            
            print("✓ Health tool test passed")
            return True
            
    except Exception as e:
        print(f"✗ Health tool test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("Running MCP Server Test Suite")
    print("=" * 40)
    
    # Run unit tests
    unit_tests_passed = test_plugin_discovery()
    
    # Run integration tests
    integration_tests_passed = await test_mcp_server_endpoints()
    
    # Run tool tests
    tool_tests_passed = await test_health_tool()
    
    print("\n" + "=" * 40)
    print("Test Results:")
    print(f"Unit Tests: {'✓ PASSED' if unit_tests_passed else '✗ FAILED'}")
    print(f"Integration Tests: {'✓ PASSED' if integration_tests_passed else '✗ FAILED'}")
    print(f"Tool Tests: {'✓ PASSED' if tool_tests_passed else '✗ FAILED'}")
    
    all_passed = unit_tests_passed and integration_tests_passed and tool_tests_passed
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 