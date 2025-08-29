from unittest import mock
import pytest
from promptyoself.cli import register_prompt, list_prompts, cancel_prompt, test_connection, list_agents, execute_prompts, upload_tool

@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("LETTA_API_KEY", "test-api-key")

@mock.patch("promptyoself.cli.validate_agent_exists")
@mock.patch("promptyoself.cli.send_prompt_to_agent")
def test_register_prompt_valid_arguments(mock_validate, mock_send, mock_env_vars):
    register_prompt("agent-123", "Test prompt", "--time", "2025-01-01T12:00:00", "--max-repetitions", "5")
    mock_validate.assert_called_once_with("agent-123")
    mock_send.assert_called_once()

@mock.patch("promptyoself.cli.validate_agent_exists")
@mock.patch("promptyoself.cli.send_prompt_to_agent")
def test_register_prompt_interval_schedule(mock_validate, mock_send, mock_env_vars):
    register_prompt("agent-123", "Test prompt", "--interval", "5m", "--start-at", "now")
    mock_validate.assert_called_once_with("agent-123")
    mock_send.assert_called_once()

@mock.patch("promptyoself.cli.validate_agent_exists")
@mock.patch("promptyoself.cli.send_prompt_to_agent")
def test_register_prompt_cron_expression(mock_validate, mock_send, mock_env_vars):
    register_prompt("agent-123", "Test prompt", "--cron", "* * * * *", "--start-at", "now")
    mock_validate.assert_called_once_with("agent-123")
    mock_send.assert_called_once()

@mock.patch("promptyoself.cli.validate_agent_exists")
@mock.patch("promptyoself.cli.send_prompt_to_agent")
def test_register_prompt_validation(mock_validate, mock_send, mock_env_vars):
    with pytest.raises(ValueError):
        register_prompt("", "Test prompt", "--time", "2025-01-01T12:00:00")
    mock_validate.assert_not_called()
    mock_send.assert_not_called()

@mock.patch("promptyoself.cli.validate_agent_exists")
@mock.patch("promptyoself.cli.send_prompt_to_agent")
def test_register_prompt_invalid_time_format(mock_validate, mock_send, mock_env_vars):
    with pytest.raises(ValueError):
        register_prompt("agent-123", "Test prompt", "--time", "invalid-date")
    mock_validate.assert_not_called()
    mock_send.assert_not_called()

@mock.patch("promptyoself.cli.validate_agent_exists")
@mock.patch("promptyoself.cli.send_prompt_to_agent")
def test_register_prompt_invalid_interval_format(mock_validate, mock_send, mock_env_vars):
    with pytest.raises(ValueError):
        register_prompt("agent-123", "Test prompt", "--interval", "invalid-interval")
    mock_validate.assert_not_called()
    mock_send.assert_not_called()

@mock.patch("promptyoself.cli.list_schedules")
def test_list_prompts(mock_list, mock_env_vars):
    mock_list.return_value = [{"id": 1, "agent_id": "agent-123", "prompt_text": "Test"}]
    result = list_prompts()
    assert len(result) == 1
    assert result[0]["agent_id"] == "agent-123"

@mock.patch("promptyoself.cli.list_schedules")
def test_list_prompts_agent_filter(mock_list, mock_env_vars):
    mock_list.return_value = [{"id": 1, "agent_id": "agent-123", "prompt_text": "Test"}]
    result = list_prompts(agent_id="agent-123")
    assert len(result) == 1
    assert result[0]["agent_id"] == "agent-123"

@mock.patch("promptyoself.cli.cancel_schedule")
def test_cancel_prompt(mock_cancel, mock_env_vars):
    cancel_prompt(123)
    mock_cancel.assert_called_once_with(123)

@mock.patch("promptyoself.cli.cancel_schedule")
def test_cancel_prompt_nonexistent(mock_cancel, mock_env_vars):
    mock_cancel.return_value = False
    result = cancel_prompt(999)
    assert not result

@mock.patch("promptyoself.cli.test_connection")
def test_test_connection(mock_test, mock_env_vars):
    mock_test.return_value = {"connected": True}
    result = test_connection()
    assert result["connected"]

@mock.patch("promptyoself.cli.list_agents")
def test_list_agents(mock_list, mock_env_vars):
    mock_list.return_value = [{"id": "agent-1", "name": "Test Agent"}]
    result = list_agents()
    assert len(result) == 1
    assert result[0]["name"] == "Test Agent"

@mock.patch("promptyoself.cli.execute_prompts")
def test_execute_prompts(mock_execute, mock_env_vars):
    mock_execute.return_value = [{"id": 1, "delivered": True}]
    result = execute_prompts(mode="single")
    assert result[0]["delivered"]

@mock.patch("promptyoself.cli.execute_prompts")
def test_execute_prompts_loop(mock_execute, mock_env_vars):
    mock_execute.return_value = [{"id": 1, "delivered": True}]
    result = execute_prompts(mode="loop", interval=60)
    assert result[0]["delivered"]

@mock.patch("promptyoself.cli.upload_tool")
def test_upload_tool(mock_upload, mock_env_vars):
    mock_upload.return_value = {"status": "success"}
    result = upload_tool("source.py", "Test tool")
    assert result["status"] == "success"

@mock.patch("promptyoself.cli.upload_tool")
def test_upload_tool_missing_authentication(mock_upload, mock_env_vars):
    mock_upload.return_value = {"error": "Authentication required"}
    result = upload_tool("source.py", "Test tool")
    assert "error" in result