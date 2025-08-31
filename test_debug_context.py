#!/usr/bin/env python3

import asyncio
import json
from fastmcp import Client

async def test_debug_context():
    """Test the debug context tool"""
    base_url = "http://127.0.0.1:8001/debug"
    client = Client(base_url)
    
    async with client:
        print("Calling debug_context...")
        result = await client.call_tool("debug_context", {})
        
        # Extract data from result
        if hasattr(result, "structured_content"):
            data = result.structured_content
        elif hasattr(result, "text"):
            data = json.loads(result.text)
        else:
            data = result
            
        print("Debug context result:")
        print(json.dumps(data, indent=2))

if __name__ == "__main__":
    asyncio.run(test_debug_context())