import requests
import json
import time

def test_mcp_protocol():
    """Test the MCP server following the Letta MCP Connection Guide protocol."""
    
    # 1. Test SSE connection (with timeout)
    print("=== Testing SSE Connection ===")
    sse_url = "http://localhost:8000/mcp/sse"
    headers = {"Accept": "text/event-stream"}
    
    try:
        with requests.get(sse_url, headers=headers, stream=True, timeout=10) as resp:
            print(f"SSE Status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"SSE connection failed: {resp.text}")
                return
            
            # Read first few SSE events with timeout
            count = 0
            for line in resp.iter_lines():
                if line:
                    decoded = line.decode()
                    if decoded.startswith("data: "):
                        data = json.loads(decoded[6:])
                        print(f"SSE Event {count}: {json.dumps(data, indent=2)}")
                        count += 1
                        if count >= 3:  # Read connection + tools list
                            break
                if count >= 3:
                    break
    except requests.exceptions.Timeout:
        print("SSE connection timed out")
        return
    except Exception as e:
        print(f"SSE connection error: {e}")
        return
    
    print("\n=== Testing JSON-RPC Message Endpoint ===")
    
    # 2. Test JSON-RPC messages via /mcp/message endpoint
    message_url = "http://localhost:8000/mcp/message"
    headers = {"Content-Type": "application/json"}
    
    # Test 1: Initialize
    print("\n--- Testing Initialize ---")
    init_message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "letta",
                "version": "1.0.0"
            }
        }
    }
    
    try:
        response = requests.post(message_url, json=init_message, headers=headers, timeout=10)
        print(f"Initialize Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Initialize Response: {json.dumps(result, indent=2)}")
        else:
            print(f"Initialize failed: {response.text}")
    except Exception as e:
        print(f"Initialize error: {e}")
    
    # Test 2: List Tools
    print("\n--- Testing Tools List ---")
    tools_message = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    
    try:
        response = requests.post(message_url, json=tools_message, headers=headers, timeout=10)
        print(f"Tools List Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Tools List Response: {json.dumps(result, indent=2)}")
        else:
            print(f"Tools List failed: {response.text}")
    except Exception as e:
        print(f"Tools List error: {e}")
    
    # Test 3: Call Tool
    print("\n--- Testing Tool Call ---")
    call_message = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "devops.status",
            "arguments": {
                "app-name": "test-app"
            }
        }
    }
    
    try:
        response = requests.post(message_url, json=call_message, headers=headers, timeout=10)
        print(f"Tool Call Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Tool Call Response: {json.dumps(result, indent=2)}")
        else:
            print(f"Tool Call failed: {response.text}")
    except Exception as e:
        print(f"Tool Call error: {e}")

if __name__ == "__main__":
    test_mcp_protocol() 