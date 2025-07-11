import pytest
import asyncio
import json
import subprocess
import sys
import time
import aiohttp
from aiohttp import ClientSession
import os

@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_mcp_sse_handshake(tmp_path):
    """Test MCP protocol handshake over SSE (hybrid mode)."""
    # Start the MCP server as a subprocess
    env = dict(**os.environ)
    env['MCP_PLUGINS_DIR'] = str(tmp_path / "plugins")
    process = subprocess.Popen(
        [sys.executable, "smcp/mcp_server.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    try:
        await asyncio.sleep(2)  # Wait for server to start
        async with ClientSession() as session:
            # Open SSE connection
            sse_resp = await session.get("http://localhost:8000/sse")
            assert sse_resp.status == 200
            # POST initialize message
            init_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "sse-test", "version": "1.0.0"}
                }
            }
            await session.post("http://localhost:8000/message", json=init_msg)
            # Read response event
            async for line in sse_resp.content:
                if line.startswith(b'data: '):
                    data = line[6:].decode().strip()
                    if data:
                        response = json.loads(data)
                        assert response["jsonrpc"] == "2.0"
                        assert response["result"]["protocolVersion"] == "2024-11-05"
                        break
            await sse_resp.release()
    finally:
        process.terminate()
        process.wait() 