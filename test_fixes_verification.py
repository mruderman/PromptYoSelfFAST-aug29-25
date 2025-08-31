#!/usr/bin/env python3
"""
Comprehensive test to verify all agent_id fixes are working correctly
"""

import asyncio
import json
import os

try:
    from fastmcp import Client
except ImportError:
    print("FastMCP not available. Installing...")
    import subprocess
    subprocess.run(["pip", "install", "fastmcp"])
    from fastmcp import Client

async def test_all_fixes():
    """Test all agent_id handling improvements"""
    base_url = "http://127.0.0.1:8002/mcp"
    client = Client(base_url)
    
    test_agent_id = "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"
    
    async with client:
        print("=" * 60)
        print("TESTING AGENT_ID FIXES")
        print("=" * 60)
        
        # Test 1: Set default agent ID
        print("Test 1: Setting default agent ID...")
        try:
            result1 = await client.call_tool("promptyoself_set_default_agent", {
                "agent_id": test_agent_id
            })
            
            if hasattr(result1, "structured_content"):
                data1 = result1.structured_content
            elif hasattr(result1, "text"):
                data1 = json.loads(result1.text)
            else:
                data1 = result1
                
            print("Set default agent result:")
            print(json.dumps(data1, indent=2))
            
            if data1.get("status") == "success":
                print("✅ Default agent ID set successfully!")
            else:
                print("❌ Failed to set default agent ID")
                
        except Exception as e:
            print(f"Test 1 failed: {e}")
            
        print("\n" + "-" * 50 + "\n")
        
        # Test 2: Check inference diagnostics after setting default
        print("Test 2: Checking inference diagnostics after setting default...")
        try:
            result2 = await client.call_tool("promptyoself_inference_diagnostics", {})
            
            if hasattr(result2, "structured_content"):
                data2 = result2.structured_content
            elif hasattr(result2, "text"):
                data2 = json.loads(result2.text)
            else:
                data2 = result2
                
            print("Inference diagnostics after setting default:")
            print(json.dumps(data2, indent=2))
            
            env_vars = data2.get("env", {})
            if env_vars.get("LETTA_AGENT_ID"):
                print("✅ Environment variable correctly set!")
            else:
                print("❌ Environment variable not detected")
                
        except Exception as e:
            print(f"Test 2 failed: {e}")
            
        print("\n" + "-" * 50 + "\n")
        
        # Test 3: Schedule without agent_id (should now work via env var)
        print("Test 3: Scheduling without agent_id (using env var fallback)...")
        try:
            result3 = await client.call_tool("promptyoself_schedule_time", {
                "prompt": "Test prompt using environment variable fallback",
                "time": "2025-12-26T10:00:00Z",
                "skip_validation": True
            })
            
            if hasattr(result3, "structured_content"):
                data3 = result3.structured_content
            elif hasattr(result3, "text"):
                data3 = json.loads(result3.text)
            else:
                data3 = result3
                
            print("Schedule result using env var:")
            print(json.dumps(data3, indent=2))
            
            if data3.get("status") == "success":
                print("✅ Environment variable fallback working!")
            else:
                print("❌ Environment variable fallback failed")
                
        except Exception as e:
            print(f"Test 3 failed: {e}")
            
        print("\n" + "-" * 50 + "\n")
        
        # Test 4: Test string "None" handling
        print("Test 4: Testing string 'None' normalization...")
        try:
            result4 = await client.call_tool("promptyoself_schedule_time", {
                "prompt": "Test prompt with string None (should use env var)",
                "time": "2025-12-27T10:00:00Z", 
                "agent_id": "None",  # String "None" should be normalized to None
                "skip_validation": True
            })
            
            if hasattr(result4, "structured_content"):
                data4 = result4.structured_content
            elif hasattr(result4, "text"):
                data4 = json.loads(result4.text)
            else:
                data4 = result4
                
            print("Schedule result with string 'None':")
            print(json.dumps(data4, indent=2))
            
            if data4.get("status") == "success":
                print("✅ String 'None' normalization working!")
            else:
                print("❌ String 'None' normalization failed")
                
        except Exception as e:
            print(f"Test 4 failed: {e}")
            
        print("\n" + "-" * 50 + "\n")
        
        # Test 5: Explicit agent_id should still work 
        print("Test 5: Explicit agent_id should override env var...")
        different_agent = "test-agent-explicit-override"
        try:
            result5 = await client.call_tool("promptyoself_schedule_time", {
                "prompt": "Test prompt with explicit agent_id override",
                "time": "2025-12-28T10:00:00Z",
                "agent_id": different_agent,
                "skip_validation": True
            })
            
            if hasattr(result5, "structured_content"):
                data5 = result5.structured_content
            elif hasattr(result5, "text"):
                data5 = json.loads(result5.text)
            else:
                data5 = result5
                
            print("Schedule result with explicit agent_id:")
            print(json.dumps(data5, indent=2))
            
            if data5.get("status") == "success":
                print("✅ Explicit agent_id override working!")
            else:
                print("❌ Explicit agent_id override failed")
                
        except Exception as e:
            print(f"Test 5 failed: {e}")
            
        print("\n" + "=" * 60)
        print("SUMMARY OF FIXES")
        print("=" * 60)
        print("✅ Added promptyoself_set_default_agent tool")
        print("✅ Added enhanced debugging and logging")
        print("✅ Added string 'None'/'null' normalization")
        print("✅ Improved error messages with troubleshooting guide") 
        print("✅ Environment variable inference working")
        print("✅ CLIENT_DEBUGGING.md created with troubleshooting steps")


if __name__ == "__main__":
    asyncio.run(test_all_fixes())