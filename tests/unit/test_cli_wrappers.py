import json
import pytest
from unittest.mock import patch

from promptyoself import cli


@pytest.mark.unit
@patch("promptyoself.cli.register_prompt", return_value={"status": "success", "id": 1})
def test_promptyoself_schedule_wrapper(mock_reg):
    out = cli.promptyoself_schedule("agt_x", "p", time="2026-01-01T00:00:00Z")
    data = json.loads(out)
    assert data["status"] == "success"
    mock_reg.assert_called_once()


@pytest.mark.unit
@patch("promptyoself.cli.list_prompts", return_value={"status": "success", "schedules": []})
def test_promptyoself_list_wrapper(mock_list):
    out = cli.promptyoself_list("agt_x", True)
    data = json.loads(out)
    assert data["status"] == "success"
    mock_list.assert_called_once()


@pytest.mark.unit
@patch("promptyoself.cli.cancel_prompt", return_value={"status": "success", "cancelled_id": 3})
def test_promptyoself_cancel_wrapper(mock_cancel):
    out = cli.promptyoself_cancel("3")
    data = json.loads(out)
    assert data["status"] == "success"
    mock_cancel.assert_called_once()


@pytest.mark.unit
@patch("promptyoself.cli.execute_prompts", return_value={"status": "success", "executed": []})
def test_promptyoself_execute_wrapper(mock_exec):
    out = cli.promptyoself_execute(daemon=False, once=True)
    data = json.loads(out)
    assert data["status"] == "success"
    mock_exec.assert_called_once()


@pytest.mark.unit
@patch("promptyoself.cli.test_connection", return_value={"status": "success"})
def test_promptyoself_test_wrapper(mock_test):
    out = cli.promptyoself_test()
    data = json.loads(out)
    assert data["status"] == "success"
    mock_test.assert_called_once()


@pytest.mark.unit
@patch("promptyoself.cli.list_agents", return_value={"status": "success", "agents": []})
def test_promptyoself_agents_wrapper(mock_agents):
    out = cli.promptyoself_agents()
    data = json.loads(out)
    assert data["status"] == "success"
    mock_agents.assert_called_once()


@pytest.mark.unit
@patch("promptyoself.cli.upload_tool", return_value={"status": "success", "tool_id": "tid"})
def test_promptyoself_upload_wrapper(mock_upload):
    out = cli.promptyoself_upload(name=None, description="d", source_code="def t(): pass")
    data = json.loads(out)
    assert data["status"] == "success"
    mock_upload.assert_called_once()

