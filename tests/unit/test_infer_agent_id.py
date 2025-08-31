import os
import pytest

import promptyoself_mcp_server as srv


class DummyCtx:
    def __init__(self, metadata=None, agent_id_attr=None):
        self.metadata = metadata
        if agent_id_attr:
            self.agent_id = agent_id_attr


TEST_AGENT = "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"


def test_infer_from_ctx_metadata_agent_id():
    ctx = DummyCtx(metadata={"agent_id": TEST_AGENT})
    agent, debug = srv._infer_agent_id(ctx)
    assert agent == TEST_AGENT
    assert debug.get("source") in ("context.metadata", "context.attr", "context.metadata.nested")


def test_infer_from_ctx_nested_agent_id():
    ctx = DummyCtx(metadata={"agent": {"id": TEST_AGENT}})
    agent, debug = srv._infer_agent_id(ctx)
    assert agent == TEST_AGENT
    assert debug.get("source") == "context.metadata.nested"


def test_infer_from_env(monkeypatch):
    monkeypatch.delenv("PROMPTYOSELF_DEFAULT_AGENT_ID", raising=False)
    monkeypatch.delenv("LETTA_DEFAULT_AGENT_ID", raising=False)
    monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
    agent, debug = srv._infer_agent_id(None)
    assert agent == TEST_AGENT
    assert debug.get("source") == "env"
    assert debug.get("key") == "LETTA_AGENT_ID"


def test_infer_single_agent_fallback(monkeypatch):
    monkeypatch.delenv("PROMPTYOSELF_DEFAULT_AGENT_ID", raising=False)
    monkeypatch.delenv("LETTA_AGENT_ID", raising=False)
    monkeypatch.delenv("LETTA_DEFAULT_AGENT_ID", raising=False)
    monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "true")

    def _fake_list_agents(_args):
        return {"status": "success", "agents": [{"id": TEST_AGENT}]}

    monkeypatch.setattr(srv, "_list_agents", _fake_list_agents)
    agent, debug = srv._infer_agent_id(None)
    assert agent == TEST_AGENT
    assert debug.get("source") == "single-agent-fallback"
    assert debug.get("single_agent_fallback") is True


def test_infer_none_when_unavailable(monkeypatch):
    # Clear env and disable fallback
    monkeypatch.delenv("PROMPTYOSELF_DEFAULT_AGENT_ID", raising=False)
    monkeypatch.delenv("LETTA_AGENT_ID", raising=False)
    monkeypatch.delenv("LETTA_DEFAULT_AGENT_ID", raising=False)
    monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "false")

    agent, debug = srv._infer_agent_id(None)
    assert agent is None
    assert debug.get("source") is None
