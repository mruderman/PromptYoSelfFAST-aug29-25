#!/usr/bin/env python3
"""
Quick test to call the inference diagnostics tool and see what context information is available
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

async def test_inference():
    """Test the inference diagnostics tool"""
    base_url = "http://127.0.0.1:8000/mcp"
    client = Client(base_url)
    
    async with client:
        # Test inference diagnostics
        print("Calling promptyoself_inference_diagnostics...")
        result = await client.call_tool("promptyoself_inference_diagnostics", {})
        
        # Extract data from result
        if hasattr(result, "structured_content"):
            data = result.structured_content
        elif hasattr(result, "text"):
            data = json.loads(result.text)
        else:
            data = result
            
        print("Inference diagnostics result:")
        print(json.dumps(data, indent=2))
        
        # Also test a failing schedule call to see the error
        print("\nTesting schedule call without agent_id...")
        try:
            schedule_result = await client.call_tool("promptyoself_schedule_time", {
                "prompt": "Test prompt",
                "time": "2025-12-25T10:00:00Z",
                "skip_validation": True
            })
            if hasattr(schedule_result, "structured_content"):
                sched_data = schedule_result.structured_content
            elif hasattr(schedule_result, "text"):
                sched_data = json.loads(schedule_result.text)
            else:
                sched_data = schedule_result
                
            print("Schedule result:")
            print(json.dumps(sched_data, indent=2))
        except Exception as e:
            print(f"Schedule call failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_inference())