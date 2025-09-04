import pytest
from unittest.mock import patch

from promptyoself import cli


@pytest.mark.unit
def test_cancel_prompt_not_found():
    with patch("promptyoself.cli.cancel_schedule", return_value=False):
        res = cli.cancel_prompt({"id": "123"})
    assert "error" in res and "not found" in res["error"]


@pytest.mark.unit
def test_test_connection_exception():
    with patch("promptyoself.cli.test_letta_connection", side_effect=RuntimeError("boom")):
        res = cli.test_connection({})
    assert "error" in res and "Failed to test connection" in res["error"]


@pytest.mark.unit
def test_list_agents_exception():
    with patch("promptyoself.cli.list_available_agents", side_effect=RuntimeError("boom")):
        res = cli.list_agents({})
    assert "error" in res and "Failed to list agents" in res["error"]

