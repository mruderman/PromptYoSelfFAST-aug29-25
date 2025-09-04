import pytest
from unittest.mock import patch


@pytest.mark.asyncio
@patch("promptyoself_mcp_server._list_prompts", side_effect=RuntimeError("bad list"))
async def test_list_tool_error(_mock, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_list", {"agent_id": "a"})
    assert "error" in result.structured_content


@pytest.mark.asyncio
@patch("promptyoself_mcp_server._cancel_prompt", side_effect=RuntimeError("bad cancel"))
async def test_cancel_tool_error(_mock, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_cancel", {"schedule_id": 1})
    assert "error" in result.structured_content


@pytest.mark.asyncio
@patch("promptyoself_mcp_server._execute_prompts", side_effect=RuntimeError("bad execute"))
async def test_execute_tool_error(_mock, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_execute", {"loop": False})
    assert "error" in result.structured_content


@pytest.mark.asyncio
@patch("promptyoself_mcp_server._test_connection", side_effect=RuntimeError("bad test"))
async def test_test_tool_error(_mock, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_test")
    assert "error" in result.structured_content


@pytest.mark.asyncio
@patch("promptyoself_mcp_server._list_agents", side_effect=RuntimeError("bad agents"))
async def test_agents_tool_error(_mock, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_agents")
    assert "error" in result.structured_content

