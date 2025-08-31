import os
import pytest
from unittest.mock import patch

TEST_AGENT = "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"


@pytest.mark.asyncio
@patch("promptyoself_mcp_server._register_prompt")
async def test_schedule_time_missing_agent_inference_fails(mock_register, mcp_in_memory_client, monkeypatch):
    # Ensure no env is set and fallback disabled
    monkeypatch.delenv("PROMPTYOSELF_DEFAULT_AGENT_ID", raising=False)
    monkeypatch.delenv("LETTA_AGENT_ID", raising=False)
    monkeypatch.delenv("LETTA_DEFAULT_AGENT_ID", raising=False)
    monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "false")

    payload = {
        "prompt": "Missing agent id should fail",
        "time": "2099-12-25T10:00:00Z",
        "agent_id": None,
    }
    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", payload)
    assert "error" in result.data
    # Should not reach register when inference fails
    mock_register.assert_not_called()


@pytest.mark.asyncio
async def test_schedule_time_in_past_returns_error(mcp_in_memory_client, monkeypatch):
    # Stub validation to avoid network/Letta dependency
    import promptyoself.cli as cli

    def _ok_validate(agent_id: str):
        return {"status": "success", "exists": True, "agent_id": agent_id}

    monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
    monkeypatch.setattr(cli, "validate_agent_exists", _ok_validate)

    payload = {
        "prompt": "Past time",
        "time": "2000-01-01T00:00:00Z",
        "agent_id": None,
    }
    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", payload)
    assert "error" in result.data
    assert "future" in result.data["error"].lower()


@pytest.mark.asyncio
async def test_schedule_cron_invalid_expression(mcp_in_memory_client, monkeypatch):
    import promptyoself.cli as cli

    def _ok_validate(agent_id: str):
        return {"status": "success", "exists": True, "agent_id": agent_id}

    monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
    monkeypatch.setattr(cli, "validate_agent_exists", _ok_validate)

    payload = {
        "prompt": "Invalid cron",
        "cron": "not a cron",
        "agent_id": None,
    }
    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_cron", payload)
    assert "error" in result.data
    assert "invalid cron" in result.data["error"].lower()


@pytest.mark.asyncio
async def test_schedule_every_invalid_interval(mcp_in_memory_client, monkeypatch):
    import promptyoself.cli as cli

    def _ok_validate(agent_id: str):
        return {"status": "success", "exists": True, "agent_id": agent_id}

    monkeypatch.setattr(cli, "validate_agent_exists", _ok_validate)

    payload = {
        "agent_id": TEST_AGENT,
        "prompt": "Bad interval",
        "every": "5x",  # invalid suffix
    }
    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_every", payload)
    assert "error" in result.data
    assert "invalid interval" in result.data["error"].lower()


@pytest.mark.asyncio
async def test_schedule_every_invalid_max_repetitions(mcp_in_memory_client, monkeypatch):
    import promptyoself.cli as cli

    def _ok_validate(agent_id: str):
        return {"status": "success", "exists": True, "agent_id": agent_id}

    monkeypatch.setattr(cli, "validate_agent_exists", _ok_validate)

    payload = {
        "agent_id": TEST_AGENT,
        "prompt": "Bad max reps",
        "every": "1m",
        "max_repetitions": "abc",  # invalid type
    }
    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_every", payload)
    assert "error" in result.data
    assert "max-repetitions" in result.data["error"].lower()

