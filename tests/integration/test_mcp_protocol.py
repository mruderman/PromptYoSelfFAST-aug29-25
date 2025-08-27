"""
Integration tests using FastMCP's in-memory client (no network),
exercising tool discovery and health call behavior.
"""

import json
import pytest
import pytest_asyncio

# Mark module as integration for marker-based selection
pytestmark = pytest.mark.integration

try:
    from fastmcp import Client
except Exception:
    Client = None  # Skip if fastmcp not available


@pytest.mark.skipif(Client is None, reason="fastmcp is required for integration tests")
class TestMCPProtocolInMemory:
    @pytest_asyncio.fixture
    async def client(self, mcp_in_memory_client):
        # Provided by tests/conftest.py; already connected context manager
        return mcp_in_memory_client

    @pytest.mark.asyncio
    async def test_list_tools_contains_health(self, client: "Client"):
        tools = await client.list_tools()

        def get_name(t):
            return t.get("name") if isinstance(t, dict) else getattr(t, "name", None)

        names = {get_name(t) for t in tools}
        assert "health" in names

    @pytest.mark.asyncio
    async def test_call_health(self, client: "Client"):
        result = await client.call_tool("health", {})
        # FastMCP in-memory client returns a CallToolResult object
        # Access the structured content which contains the actual data
        data = result.structured_content

        assert data["status"] == "healthy"
        assert "letta_base_url" in data
        assert "db" in data
        assert "auth_set" in data