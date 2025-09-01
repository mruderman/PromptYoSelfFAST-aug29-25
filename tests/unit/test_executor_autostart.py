import os
import types
import pytest


def test_executor_autostart_default_true(monkeypatch):
    import promptyoself_mcp_server as srv

    # Ensure no env explicit disable
    monkeypatch.delenv("PROMPTYOSELF_EXECUTOR_AUTOSTART", raising=False)
    monkeypatch.setenv("PROMPTYOSELF_EXECUTOR_INTERVAL", "5")

    started = {"called": False}

    class FakeProc:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon
        def start(self):
            started["called"] = True

    monkeypatch.setattr("promptyoself_mcp_server._execute_prompts", lambda args: None)
    monkeypatch.setattr("promptyoself_mcp_server._EXECUTOR_PROCESS", None, raising=False)
    monkeypatch.setattr("multiprocessing.Process", FakeProc)

    # Call the internal helper directly
    srv._start_executor_loop_if_enabled()
    assert started["called"] is True


def test_executor_autostart_disabled(monkeypatch):
    import promptyoself_mcp_server as srv

    monkeypatch.setenv("PROMPTYOSELF_EXECUTOR_AUTOSTART", "false")
    started = {"called": False}

    class FakeProc:
        def __init__(self, *a, **k):
            pass
        def start(self):
            started["called"] = True

    monkeypatch.setattr("multiprocessing.Process", FakeProc)
    srv._start_executor_loop_if_enabled()
    assert started["called"] is False


@pytest.mark.asyncio
async def test_executor_status_tool(mcp_in_memory_client, monkeypatch):
    # Fake a running process
    class Alive:
        def is_alive(self):
            return True

    monkeypatch.setenv("PROMPTYOSELF_EXECUTOR_INTERVAL", "42")
    import promptyoself_mcp_server as srv
    srv._EXECUTOR_PROCESS = Alive()

    res = await mcp_in_memory_client.call_tool("promptyoself_executor_status")
    data = res.structured_content
    assert data["status"] == "ok"
    assert data["running"] is True
    assert data["interval"] == 42
