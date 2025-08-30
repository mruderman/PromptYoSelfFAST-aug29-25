import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_health_tool(mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("health")
    assert result.data["status"] == "healthy"

@pytest.mark.asyncio
@patch("promptyoself_mcp_server._register_prompt", return_value={"status": "success", "id": 123})
async def test_register_tool(mock_register, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool(
        "promptyoself_register",
        {"agent_id": "test-agent", "prompt": "test prompt", "time": "2025-01-01T00:00:00"}
    )
    assert result.data["status"] == "success"
    assert result.data["id"] == 123
    mock_register.assert_called_once()

@pytest.mark.asyncio
@patch("promptyoself_mcp_server._list_prompts", return_value={"status": "success", "schedules": []})
async def test_list_tool(mock_list, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_list", {"agent_id": "test-agent"})
    assert result.data["status"] == "success"
    mock_list.assert_called_once()

@pytest.mark.asyncio
@patch("promptyoself_mcp_server._cancel_prompt", return_value={"status": "success", "cancelled_id": 456})
async def test_cancel_tool(mock_cancel, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_cancel", {"schedule_id": 456})
    assert result.data["status"] == "success"
    assert result.data["cancelled_id"] == 456
    mock_cancel.assert_called_once()

@pytest.mark.asyncio
@patch("promptyoself_mcp_server._execute_prompts", return_value={"status": "success", "executed": []})
async def test_execute_tool(mock_execute, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_execute")
    assert result.data["status"] == "success"
    mock_execute.assert_called_once()

@pytest.mark.asyncio
@patch("promptyoself_mcp_server._test_connection", return_value={"status": "success"})
async def test_test_tool(mock_test, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_test")
    assert result.data["status"] == "success"
    mock_test.assert_called_once()

@pytest.mark.asyncio
@patch("promptyoself_mcp_server._list_agents", return_value={"status": "success", "agents": []})
async def test_agents_tool(mock_list_agents, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_agents")
    assert result.data["status"] == "success"
    mock_list_agents.assert_called_once()
