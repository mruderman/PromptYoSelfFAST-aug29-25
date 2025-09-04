import pytest
from unittest.mock import patch, MagicMock

from promptyoself import cli


@pytest.mark.unit
def test_cli_upload_tool_missing_auth(monkeypatch):
    monkeypatch.delenv("LETTA_API_KEY", raising=False)
    monkeypatch.delenv("LETTA_SERVER_PASSWORD", raising=False)

    res = cli.upload_tool({"source_code": "def f(): pass", "description": "d"})
    assert "error" in res
    assert "Missing LETTA_API_KEY or LETTA_SERVER_PASSWORD" in res["error"]


@pytest.mark.unit
def test_cli_upload_tool_success(monkeypatch):
    class DummyResp:
        def __init__(self):
            self.id = "tid_x"
            self.name = "tool_name"

    class DummyTools:
        def upsert(self, source_code, description=None):
            assert "def f():" in source_code
            return DummyResp()

    class DummyLetta:
        def __init__(self, token=None, base_url=None):
            self.tools = DummyTools()

    monkeypatch.setenv("LETTA_SERVER_PASSWORD", "pw")

    with patch("letta_client.Letta", DummyLetta):
        res = cli.upload_tool({"source_code": "def f(): pass", "description": "d"})

    assert res["status"] == "success"
    assert res["tool_id"] == "tid_x"
    assert res["name"] == "tool_name"
