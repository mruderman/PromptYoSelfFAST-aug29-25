import os
import pytest
from unittest.mock import patch


@pytest.mark.asyncio
@patch("promptyoself_mcp_server._register_prompt", return_value={"status": "success", "id": 999})
async def test_schedule_cron_tool(mock_register, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool(
        "promptyoself_schedule_cron",
        {"agent_id": "agt_x", "prompt": "p", "cron": "0 9 * * *"}
    )
    assert result.structured_content["status"] == "success"
    mock_register.assert_called_once()


@pytest.mark.asyncio
@patch("promptyoself_mcp_server._register_prompt", return_value={"status": "success", "id": 1000})
async def test_schedule_every_tool(mock_register, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool(
        "promptyoself_schedule_every",
        {"agent_id": "agt_x", "prompt": "p", "every": "15m"}
    )
    assert result.structured_content["status"] == "success"
    mock_register.assert_called_once()


@pytest.mark.asyncio
async def test_executor_status_tool(mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_executor_status")
    data = result.structured_content
    assert data["status"] == "ok"
    assert "running" in data and "interval" in data


@pytest.mark.asyncio
@patch("promptyoself_mcp_server._get_ctx_scope_key", return_value="scope_test")
async def test_set_and_get_scoped_default_agent(_mock_scope, mcp_in_memory_client):
    set_res = await mcp_in_memory_client.call_tool(
        "promptyoself_set_scoped_default_agent", {"agent_id": "agt_scoped"}
    )
    assert set_res.structured_content["status"] == "success"

    get_res = await mcp_in_memory_client.call_tool("promptyoself_get_scoped_default_agent")
    assert get_res.structured_content["status"] == "ok"
    assert get_res.structured_content["agent_id"] == "agt_scoped"


@pytest.mark.asyncio
async def test_set_default_agent_tool(mcp_in_memory_client, monkeypatch):
    monkeypatch.delenv("LETTA_AGENT_ID", raising=False)
    res = await mcp_in_memory_client.call_tool(
        "promptyoself_set_default_agent", {"agent_id": "agt_def"}
    )
    assert res.structured_content["status"] == "success"
    assert os.getenv("LETTA_AGENT_ID") == "agt_def"


@pytest.mark.asyncio
async def test_inference_diagnostics_tool(mcp_in_memory_client, monkeypatch):
    monkeypatch.setenv("LETTA_AGENT_ID", "agt_env")
    res = await mcp_in_memory_client.call_tool("promptyoself_inference_diagnostics")
    data = res.structured_content
    assert data["status"] == "ok"
    assert data["inferred_agent_id"] == "agt_env"


@pytest.mark.asyncio
async def test_promptyoself_upload_missing_env(mcp_in_memory_client, monkeypatch):
    monkeypatch.delenv("LETTA_API_KEY", raising=False)
    monkeypatch.delenv("LETTA_SERVER_PASSWORD", raising=False)
    res = await mcp_in_memory_client.call_tool(
        "promptyoself_upload", {"source_code": "def tool(): pass"}
    )
    assert "error" in res.structured_content
    assert "Missing LETTA_API_KEY" in res.structured_content["error"]


@pytest.mark.asyncio
@patch("promptyoself_mcp_server._upload_tool", return_value={"status": "success", "tool_id": "tid_1"})
async def test_promptyoself_upload_success(mock_upload, mcp_in_memory_client, monkeypatch):
    monkeypatch.setenv("LETTA_SERVER_PASSWORD", "pw")
    res = await mcp_in_memory_client.call_tool(
        "promptyoself_upload", {"source_code": "def tool(): pass", "description": "d"}
    )
    assert res.structured_content["status"] == "success"
    mock_upload.assert_called_once()

