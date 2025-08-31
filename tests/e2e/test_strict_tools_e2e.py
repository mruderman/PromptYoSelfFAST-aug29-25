import os
import pytest

TEST_AGENT = "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"


@pytest.mark.asyncio
async def test_e2e_schedule_time_through_cli(monkeypatch, mcp_in_memory_client):
    # Stub letta_client before importing CLI to avoid external dependency
    import sys
    import types
    fake_letta = types.SimpleNamespace(Letta=object, MessageCreate=object, TextContent=object)
    monkeypatch.setitem(sys.modules, 'letta_client', fake_letta)
    # Patch CLI validation and persistence to avoid DB/HTTP
    import promptyoself.cli as cli

    def _ok_validate(agent_id: str):
        return {"status": "success", "exists": True, "agent_id": agent_id}

    def _fake_add_schedule(agent_id, prompt_text, schedule_type, schedule_value, next_run, max_repetitions=None):
        # return a deterministic id
        return 301

    monkeypatch.setattr(cli, "validate_agent_exists", _ok_validate)
    monkeypatch.setattr(cli, "add_schedule", _fake_add_schedule)

    # Use env inference for agent_id
    monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)

    payload = {
        "prompt": "End-to-end time schedule",
        "time": "2025-12-25T10:00:00Z",
        "agent_id": None,
    }
    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", payload)
    assert result.structured_content["status"] == "success"
    assert result.structured_content["id"] == 301
    assert "next_run" in result.structured_content


@pytest.mark.asyncio
async def test_e2e_schedule_cron_through_cli(monkeypatch, mcp_in_memory_client):
    import sys
    import types
    fake_letta = types.SimpleNamespace(Letta=object, MessageCreate=object, TextContent=object)
    monkeypatch.setitem(sys.modules, 'letta_client', fake_letta)
    import promptyoself.cli as cli

    def _ok_validate(agent_id: str):
        return {"status": "success", "exists": True, "agent_id": agent_id}

    def _fake_add_schedule(agent_id, prompt_text, schedule_type, schedule_value, next_run, max_repetitions=None):
        return 302

    monkeypatch.setattr(cli, "validate_agent_exists", _ok_validate)
    monkeypatch.setattr(cli, "add_schedule", _fake_add_schedule)
    monkeypatch.setenv("PROMPTYOSELF_DEFAULT_AGENT_ID", TEST_AGENT)

    payload = {
        "prompt": "End-to-end cron schedule",
        "cron": "*/10 * * * *",
        "agent_id": None,
    }
    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_cron", payload)
    assert result.structured_content["status"] == "success"
    assert result.structured_content["id"] == 302
    assert "next_run" in result.structured_content


@pytest.mark.asyncio
async def test_e2e_schedule_every_through_cli(monkeypatch, mcp_in_memory_client):
    import sys
    import types
    fake_letta = types.SimpleNamespace(Letta=object, MessageCreate=object, TextContent=object)
    monkeypatch.setitem(sys.modules, 'letta_client', fake_letta)
    import promptyoself.cli as cli

    def _ok_validate(agent_id: str):
        return {"status": "success", "exists": True, "agent_id": agent_id}

    def _fake_add_schedule(agent_id, prompt_text, schedule_type, schedule_value, next_run, max_repetitions=None):
        return 303

    monkeypatch.setattr(cli, "validate_agent_exists", _ok_validate)
    monkeypatch.setattr(cli, "add_schedule", _fake_add_schedule)

    # No env needed if explicit agent passed
    payload = {
        "agent_id": TEST_AGENT,
        "prompt": "End-to-end every schedule",
        "every": "2m",
        "max_repetitions": 1,
    }
    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_every", payload)
    assert result.structured_content["status"] == "success"
    assert result.structured_content["id"] == 303
    assert "next_run" in result.structured_content
