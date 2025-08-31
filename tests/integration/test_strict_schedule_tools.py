import os
import pytest
from unittest.mock import patch

TEST_AGENT = "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"


@pytest.mark.asyncio
@patch("promptyoself_mcp_server._register_prompt", return_value={"status": "success", "id": 201, "next_run": "2025-01-01T00:00:00Z", "message": "ok"})
async def test_schedule_time_with_env_inference(mock_register, mcp_in_memory_client, monkeypatch):
    monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
    payload = {
        "prompt": "Test one-time",
        "time": "2025-12-25T10:00:00Z",
        "agent_id": None,
    }
    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", payload)
    assert result.data["status"] == "success"
    assert result.data["id"] == 201
    mock_register.assert_called_once()


@pytest.mark.asyncio
@patch("promptyoself_mcp_server._register_prompt", return_value={"status": "success", "id": 202, "next_run": "2025-01-01T00:05:00Z", "message": "ok"})
async def test_schedule_cron_with_env_inference(mock_register, mcp_in_memory_client, monkeypatch):
    monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
    payload = {
        "prompt": "Test cron",
        "cron": "*/5 * * * *",
        "agent_id": None,
    }
    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_cron", payload)
    assert result.data["status"] == "success"
    assert result.data["id"] == 202
    mock_register.assert_called_once()


@pytest.mark.asyncio
@patch("promptyoself_mcp_server._register_prompt", return_value={"status": "success", "id": 203, "next_run": "2025-01-01T00:00:30Z", "message": "ok"})
async def test_schedule_every_with_env_inference(mock_register, mcp_in_memory_client, monkeypatch):
    monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
    payload = {
        "prompt": "Test every",
        "every": "30s",
        "agent_id": None,
    }
    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_every", payload)
    assert result.data["status"] == "success"
    assert result.data["id"] == 203
    mock_register.assert_called_once()
