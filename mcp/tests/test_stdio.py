import subprocess
import sys
import os
import json
import uuid
import time
import threading
import tempfile
import pytest

pytestmark = pytest.mark.timeout(10)

MCP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp_stdio.py")
PYTHON = sys.executable

# Helper to send/receive JSON lines
class MCPStdioClient:
    def __init__(self):
        self.proc = subprocess.Popen(
            [PYTHON, MCP_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        # Wait for ready
        try:
            ready = self._read_line(timeout=2)
        except Exception as e:
            stderr = self.proc.stderr.read()
            raise RuntimeError(f"MCP process failed to start: {e}\nStderr: {stderr}")
        if 'ready' not in ready:
            stderr = self.proc.stderr.read()
            raise RuntimeError(f"MCP did not print ready. Output: {ready}\nStderr: {stderr}")

    def _read_line(self, timeout=5):
        line = ''
        start = time.time()
        while True:
            if self.proc.poll() is not None:
                raise RuntimeError("MCP process exited unexpectedly")
            if self.proc.stdout.readable():
                line = self.proc.stdout.readline()
                if line:
                    return line.strip()
            if time.time() - start > timeout:
                raise TimeoutError("Timeout waiting for MCP response")
            time.sleep(0.01)

    def send(self, obj):
        self.proc.stdin.write(json.dumps(obj) + '\n')
        self.proc.stdin.flush()

    def recv(self, expect_id=None, timeout=5):
        while True:
            line = self._read_line(timeout)
            if not line:
                continue
            try:
                msg = json.loads(line)
            except Exception:
                continue
            if expect_id is None or msg.get('id') == expect_id:
                return msg

    def close(self):
        self.proc.stdin.close()
        self.proc.terminate()
        self.proc.wait(timeout=5)

# Tests

def test_help():
    client = MCPStdioClient()
    req_id = str(uuid.uuid4())
    client.send({"id": req_id, "command": "help"})
    resp = client.recv(expect_id=req_id)
    assert resp["status"] == "success"
    assert "botfather" in resp["payload"]
    client.close()

def test_reload_help():
    client = MCPStdioClient()
    req_id = str(uuid.uuid4())
    client.send({"id": req_id, "command": "reload-help"})
    resp = client.recv(expect_id=req_id)
    assert resp["status"] == "success"
    assert resp["payload"] == "ok"
    client.close()

def test_health():
    client = MCPStdioClient()
    req_id = str(uuid.uuid4())
    client.send({"id": req_id, "command": "health"})
    resp = client.recv(expect_id=req_id)
    assert resp["status"] == "success"
    assert resp["payload"] == "ok"
    client.close()

def test_run_success():
    client = MCPStdioClient()
    req_id = str(uuid.uuid4())
    payload = {
        "plugin": "botfather",
        "action": "click-button",
        "args": {"button-text": "Payments", "msg-id": 12345678},
        "timeout": 5
    }
    client.send({"id": req_id, "command": "run", "payload": payload})
    assert client.recv(expect_id=req_id)["status"] == "queued"
    assert client.recv(expect_id=req_id)["status"] == "started"
    final = client.recv(expect_id=req_id)
    if final["status"] != "success":
        print("FAIL PAYLOAD:", final["payload"])
    assert final["status"] == "success"
    assert "Clicked button" in json.dumps(final["payload"])
    client.close()

def test_run_error():
    client = MCPStdioClient()
    req_id = str(uuid.uuid4())
    payload = {
        "plugin": "botfather",
        "action": "not-a-real-action",
        "args": {},
        "timeout": 5
    }
    client.send({"id": req_id, "command": "run", "payload": payload})
    assert client.recv(expect_id=req_id)["status"] == "queued"
    assert client.recv(expect_id=req_id)["status"] == "started"
    final = client.recv(expect_id=req_id)
    if final["status"] != "error":
        print("FAIL PAYLOAD:", final["payload"])
    assert final["status"] == "error"
    assert "not found" in json.dumps(final["payload"]).lower() or "unknown" in json.dumps(final["payload"]).lower()
    client.close()

def test_run_unknown_plugin():
    client = MCPStdioClient()
    req_id = str(uuid.uuid4())
    payload = {
        "plugin": "notaplugin",
        "action": "foo",
        "args": {}
    }
    client.send({"id": req_id, "command": "run", "payload": payload})
    assert client.recv(expect_id=req_id)["status"] == "queued"
    assert client.recv(expect_id=req_id)["status"] == "started"
    final = client.recv(expect_id=req_id)
    assert final["status"] == "error"
    assert "not_found" in json.dumps(final["payload"]).lower() or "not found" in json.dumps(final["payload"]).lower()
    client.close()

def test_bad_json():
    client = MCPStdioClient()
    # Send a bad JSON line
    client.proc.stdin.write('this is not json\n')
    client.proc.stdin.flush()
    # Should not crash, just ignore
    req_id = str(uuid.uuid4())
    client.send({"id": req_id, "command": "health"})
    resp = client.recv(expect_id=req_id)
    assert resp["status"] == "success"
    client.close() 