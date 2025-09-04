"""
Pytest configuration and fixtures for FastMCP-based PromptYoSelf server tests.
Replaces legacy Sanctum plugin-host fixtures with FastMCP in-memory and HTTP client fixtures.
"""

import os
import sys
import time
import httpx
import pytest
import asyncio
import subprocess
import pytest_asyncio
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the new FastMCP server instance
# Ensure 'letta_client' is stubbed if not installed to avoid import errors
try:
    import letta_client  # type: ignore
except Exception:
    import types
    import sys as _sys
    _fake = types.SimpleNamespace(Letta=object, MessageCreate=object, TextContent=object)
    _sys.modules['letta_client'] = _fake

# Defer importing the server until fixtures run to ensure coverage captures it
srv = None  # will be imported inside fixtures


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for asyncio tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def mcp_in_memory_client():
    """
    Fast, in-process client using FastMCP's in-memory transport.
    Ideal for unit/integration tests without starting a subprocess or binding ports.
    """
    try:
        from fastmcp import Client
    except ImportError as e:
        pytest.skip(f"fastmcp is required for these tests: {e}")

    # Import the server lazily to avoid importing before coverage starts
    global srv
    if srv is None:
        import promptyoself_mcp_server as srv  # type: ignore

    client = Client(srv.mcp)  # in-memory transport by passing server instance
    async with client:
        yield client


def _wait_for_server(base_url: str, timeout: int = 10) -> bool:
    """
    Wait for the server to respond to HTTP requests.
    
    Args:
        base_url: The base URL of the server (e.g., http://127.0.0.1:8100/mcp)
        timeout: Maximum time to wait in seconds
        
    Returns:
        True if server is responsive, False otherwise
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Try a simple GET request to see if server is responsive
            response = httpx.get(f"{base_url}/", timeout=1.0)
            # If we get any response (even 404), the server is running
            return True
        except Exception:
            # Server not ready yet, wait a bit and try again
            time.sleep(0.5)
    return False


@pytest.fixture
def http_server_process(tmp_path):
    """
    Start the FastMCP server (HTTP transport) as a subprocess for E2E tests.
    Uses 127.0.0.1:8100 by default to avoid conflicts.
    """
    host = os.environ.get("TEST_MCP_HOST", "127.0.0.1")
    port = os.environ.get("TEST_MCP_PORT", "8100")
    path = os.environ.get("TEST_MCP_PATH", "/mcp")

    cmd = [
        sys.executable,
        "promptyoself_mcp_server.py",
        "--transport",
        "http",
        "--host",
        host,
        "--port",
        port,
        "--path",
        path,
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(PROJECT_ROOT),
        text=True,
    )

    base_url = f"http://{host}:{port}{path}"
    
    # Give the server time to bind the port and start responding
    time.sleep(1.0)  # Initial wait
    
    # Check if the process is still running
    if proc.poll() is not None:
        # Process has terminated, collect output for debugging
        stdout, stderr = proc.communicate()
        raise RuntimeError(f"Server process terminated unexpectedly.\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")
    
    # Wait for server to be responsive
    if not _wait_for_server(base_url, timeout=10):
        # Server didn't start in time, collect output for debugging
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            # If we can't get output even after 5 seconds, terminate the process
            proc.kill()
            stdout, stderr = proc.communicate()
        raise RuntimeError(f"Server failed to start within timeout period.\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")

    yield {
        "process": proc,
        "host": host,
        "port": int(port),
        "path": path,
        "base_url": base_url,
    }

    # Cleanup
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
