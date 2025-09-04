import pytest
from unittest.mock import patch

from promptyoself.letta_api import _try_streaming_fallback
from promptyoself import letta_api


class _StreamFailClient:
    class _Agents:
        class _Messages:
            @staticmethod
            def create_stream(agent_id=None, messages=None):
                raise RuntimeError("fail stream")

        messages = _Messages()

    agents = _Agents()


@pytest.mark.unit
def test_try_streaming_fallback_failure(monkeypatch):
    monkeypatch.setattr(letta_api, "_get_letta_client", lambda: _StreamFailClient())
    ok = _try_streaming_fallback("agent", "msg")
    assert ok is False


@pytest.mark.unit
@patch("time.sleep", return_value=None)
def test_detailed_logging_all_attempts_fail(_mock_sleep, monkeypatch):
    class _FailClient:
        class _Agents:
            class _Messages:
                @staticmethod
                def create(*args, **kwargs):
                    raise RuntimeError("nope")

                @staticmethod
                def create_stream(*args, **kwargs):
                    # not triggered unless message contains chatml error marker
                    raise RuntimeError("nope stream")

            messages = _Messages()

        agents = _Agents()

    monkeypatch.setattr(letta_api, "_get_letta_client", lambda: _FailClient())
    res = letta_api.send_prompt_to_agent_with_detailed_logging("agent", "hi")
    assert res["success"] is False
    assert "All" in res["error"]

