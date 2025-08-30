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

    @pytest.mark.asyncio
    async def test_full_workflow(self, http_client: "Client"):
        # 1. Register a prompt
        register_result = await http_client.call_tool(
            "promptyoself_register",
            {
                "agent_id": "e2e-test-agent",
                "prompt": "e2e test prompt",
                "time": "2025-12-31T23:59:59",
                "skip_validation": True,
            },
        )
        reg_data = register_result.structured_content
        assert reg_data["status"] == "success"
        schedule_id = reg_data["id"]

        # 2. List prompts and verify the new one is there
        list_result = await http_client.call_tool(
            "promptyoself_list", {"agent_id": "e2e-test-agent"}
        )
        list_data = list_result.structured_content
        assert list_data["status"] == "success"
        assert any(s["id"] == schedule_id for s in list_data["schedules"])

        # 3. Cancel the prompt
        cancel_result = await http_client.call_tool(
            "promptyoself_cancel", {"schedule_id": schedule_id}
        )
        cancel_data = cancel_result.structured_content
        assert cancel_data["status"] == "success"

        # 4. List prompts again (including cancelled) and verify it's inactive
        list_all_result = await http_client.call_tool(
            "promptyoself_list",
            {"agent_id": "e2e-test-agent", "include_cancelled": True},
        )
        list_all_data = list_all_result.structured_content
        cancelled_schedule = next(
            (s for s in list_all_data["schedules"] if s["id"] == schedule_id), None
        )
        assert cancelled_schedule is not None
        assert cancelled_schedule["active"] is False