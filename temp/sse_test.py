import requests
import json
import threading
import time
import sys

SSE_URL = "http://localhost:8000/mcp/sse"
MESSAGE_URL = "http://localhost:8000/mcp/message"

sse_events = []
sse_running = True
sse_resp = None

def sse_listener():
    global sse_running, sse_resp
    headers = {"Accept": "text/event-stream"}
    try:
        with requests.get(SSE_URL, headers=headers, stream=True, timeout=30) as resp:
            sse_resp = resp
            print(f"[SSE] Status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"[SSE] Connection failed: {resp.text}")
                return
            for line in resp.iter_lines():
                if not sse_running:
                    break
                if line:
                    decoded = line.decode()
                    if decoded.startswith("data: "):
                        data = json.loads(decoded[6:])
                        print(f"[SSE] Event: {json.dumps(data, indent=2)}")
                        sse_events.append(data)
    except Exception as e:
        print(f"[SSE] Listener error: {e}")

def test_mcp_protocol():
    global sse_running, sse_resp
    test_success = True
    # Start SSE listener in background
    sse_thread = threading.Thread(target=sse_listener, daemon=True)
    sse_thread.start()
    
    try:
        # Wait for SSE connection and initial events
        time.sleep(2)
        headers = {"Content-Type": "application/json"}
        
        # Test 1: Initialize
        print("\n--- Testing Initialize ---")
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "letta", "version": "1.0.0"}
            }
        }
        response = requests.post(MESSAGE_URL, json=init_message, headers=headers, timeout=10)
        print(f"[MSG] Initialize Status: {response.status_code}")
        print(f"[MSG] Initialize Response: {json.dumps(response.json(), indent=2)}")
        if response.status_code != 200:
            test_success = False
        
        # Test 2: List Tools
        print("\n--- Testing Tools List ---")
        tools_message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        response = requests.post(MESSAGE_URL, json=tools_message, headers=headers, timeout=10)
        print(f"[MSG] Tools List Status: {response.status_code}")
        print(f"[MSG] Tools List Response: {json.dumps(response.json(), indent=2)}")
        if response.status_code != 200:
            test_success = False
        
        # Test 3: Call Tool
        print("\n--- Testing Tool Call ---")
        call_message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "devops.status",
                "arguments": {"app-name": "test-app"}
            }
        }
        response = requests.post(MESSAGE_URL, json=call_message, headers=headers, timeout=10)
        print(f"[MSG] Tool Call Status: {response.status_code}")
        print(f"[MSG] Tool Call Response: {json.dumps(response.json(), indent=2)}")
        if response.status_code != 200:
            test_success = False
        
        # Let the SSE connection run for a few more seconds to simulate a real client
        time.sleep(2)
    except Exception as e:
        print(f"[TEST] Error: {e}")
        test_success = False
    finally:
        sse_running = False
        # Force close the SSE connection from the main thread
        if sse_resp is not None:
            try:
                sse_resp.close()
            except Exception:
                pass
        sse_thread.join(timeout=5)
        if sse_thread.is_alive():
            print("[SSE] Listener did not exit cleanly!")
            test_success = False
        else:
            print("[SSE] Listener closed.")
        if test_success:
            print("\n[TEST] MCP protocol test completed successfully.")
            sys.exit(0)
        else:
            print("\n[TEST] MCP protocol test failed.")
            sys.exit(1)

if __name__ == "__main__":
    # Strict total test timeout
    timer = threading.Timer(20, lambda: (print("\n[TEST] Timeout exceeded. Exiting."), sys.exit(2)))
    timer.start()
    test_mcp_protocol()
    timer.cancel() 