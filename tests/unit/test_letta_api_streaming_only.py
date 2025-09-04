import pytest
from unittest.mock import patch, MagicMock

from promptyoself import letta_api

TEST_AGENT_ID = "agent-1"


class _StreamOKClient:
    class _Agents:
        class _Messages:
            @staticmethod
            def create_stream(agent_id=None, messages=None):
                # iterable stream
                return [None]

        messages = _Messages()

    agents = _Agents()


class _StreamFailClient:
    class _Agents:
        class _Messages:
            @staticmethod
            def create_stream(agent_id=None, messages=None):
                raise RuntimeError("stream fail")

        messages = _Messages()

    agents = _Agents()


@pytest.mark.unit
def test_streaming_only_success(monkeypatch):
    monkeypatch.setattr(letta_api, "_get_letta_client", lambda: _StreamOKClient())
    ok = letta_api.send_prompt_to_agent_streaming_only(TEST_AGENT_ID, "hi", max_retries=1)
    assert ok is True


@pytest.mark.unit
@patch("time.sleep", return_value=None)
def test_streaming_only_fail_with_backoff(mock_sleep, monkeypatch):
    monkeypatch.setattr(letta_api, "_get_letta_client", lambda: _StreamFailClient())
    ok = letta_api.send_prompt_to_agent_streaming_only(TEST_AGENT_ID, "hi", max_retries=3)
    assert ok is False
    # backoff calls for attempts 0 and 1 (2^0=1, 2^1=2)
    assert mock_sleep.call_count == 2

