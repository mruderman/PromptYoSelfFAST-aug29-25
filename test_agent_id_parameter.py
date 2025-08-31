#!/usr/bin/env python3
"""
Test to verify agent_id parameter handling in MCP tools
"""

import asyncio
import json

try:
    from fastmcp import Client
except ImportError:
    print("FastMCP not available. Installing...")
    import subprocess
    subprocess.run(["pip", "install", "fastmcp"])
    from fastmcp import Client

async def test_agent_id_handling():
    """Test agent_id parameter handling"""
    base_url = "http://127.0.0.1:8002/mcp"  # Local endpoint for testing
    client = Client(base_url)
    
    test_agent_id = "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"
    
    async with client:
        # Test 1: Pass agent_id explicitly
        print("Test 1: Calling schedule_time with explicit agent_id...")
        try:
            result1 = await client.call_tool("promptyoself_schedule_time", {
                "prompt": "Test prompt with explicit agent_id",
                "time": "2025-12-25T10:00:00Z",
                "agent_id": test_agent_id,
                "skip_validation": True
            })
            
            if hasattr(result1, "structured_content"):
                data1 = result1.structured_content
            elif hasattr(result1, "text"):
                data1 = json.loads(result1.text)
            else:
                data1 = result1
                
            print("Result with explicit agent_id:")
            print(json.dumps(data1, indent=2))
        except Exception as e:
            print(f"Test 1 failed: {e}")
            
        print("\n" + "="*50 + "\n")
            
        # Test 2: Pass agent_id as None explicitly
        print("Test 2: Calling schedule_time with agent_id=None...")
        try:
            result2 = await client.call_tool("promptyoself_schedule_time", {
                "prompt": "Test prompt with None agent_id",
                "time": "2025-12-25T10:00:00Z",
                "agent_id": None,
                "skip_validation": True
            })
            
            if hasattr(result2, "structured_content"):
                data2 = result2.structured_content
            elif hasattr(result2, "text"):
                data2 = json.loads(result2.text)
            else:
                data2 = result2
                
            print("Result with agent_id=None:")
            print(json.dumps(data2, indent=2))
        except Exception as e:
            print(f"Test 2 failed: {e}")
            
        print("\n" + "="*50 + "\n")
            
        # Test 3: Omit agent_id parameter entirely
        print("Test 3: Calling schedule_time without agent_id parameter...")
        try:
            result3 = await client.call_tool("promptyoself_schedule_time", {
                "prompt": "Test prompt without agent_id param",
                "time": "2025-12-25T10:00:00Z",
                "skip_validation": True
            })
            
            if hasattr(result3, "structured_content"):
                data3 = result3.structured_content
            elif hasattr(result3, "text"):
                data3 = json.loads(result3.text)
            else:
                data3 = result3
                
            print("Result without agent_id parameter:")
            print(json.dumps(data3, indent=2))
        except Exception as e:
            print(f"Test 3 failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_agent_id_handling())