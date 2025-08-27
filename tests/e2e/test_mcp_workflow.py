"""
End-to-end tests for the FastMCP-based PromptYoSelf server over HTTP transport,
using the official FastMCP Client instead of raw HTTP JSON-RPC.
"""

import json
import pytest
import pytest_asyncio

# Mark module as e2e for marker-based selection
pytestmark = pytest.mark.e2e

try:
    from fastmcp import Client
except Exception:
    Client = None  # Tests will be skipped if fastmcp is not installed


@pytest.mark.skipif(Client is None, reason="fastmcp is required for E2E tests")
class TestMCPWorkflowHTTP:
    @pytest_asyncio.fixture
    async def http_client(self, http_server_process):
        """
        Yield a connected FastMCP client that talks to the spawned HTTP server.
        http_server_process fixture provides base_url like http://127.0.0.1:8100/mcp
        """
        base_url = http_server_process["base_url"]
        client = Client(base_url)
        async with client:
            yield client

    @pytest.mark.asyncio
    async def test_list_tools_and_call_health(self, http_client: "Client"):
        # List tools
        tools = await http_client.list_tools()
        # tools may be list of dicts or objects; normalize to names
        def tool_name(t):
            return t.get("name") if isinstance(t, dict) else getattr(t, "name", None)

        names = {tool_name(t) for t in tools}
        assert "health" in names

        # Call health
        result = await http_client.call_tool("health", {})
        # Result may be an object with text attribute, structured_content, or a dict
        if hasattr(result, "structured_content"):
            # CallToolResult object from FastMCP client
            data = result.structured_content
        else:
            # Legacy handling for other result types
            text = getattr(result, "text", None)
            if text is None and isinstance(result, dict):
                # some client versions return dict
                data = result
            else:
                data = json.loads(text)

        assert data["status"] == "healthy"
        assert "letta_base_url" in data
        assert "db" in data
        assert "auth_set" in data