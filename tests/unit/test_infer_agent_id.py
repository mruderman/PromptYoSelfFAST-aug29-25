import os
import pytest
from unittest.mock import Mock

import promptyoself_mcp_server as srv


class DummyCtx:
    def __init__(self, metadata=None, agent_id_attr=None):
        self.metadata = metadata
        if agent_id_attr:
            self.agent_id = agent_id_attr


TEST_AGENT = "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"


class TestContextMetadataInference:
    """Test agent_id inference from various context metadata formats."""

    def test_infer_from_ctx_metadata_agent_id(self):
        ctx = DummyCtx(metadata={"agent_id": TEST_AGENT})
        agent, debug = srv._infer_agent_id(ctx)
        assert agent == TEST_AGENT
        assert debug.get("source") == "context.metadata"
        assert debug.get("key") == "agent_id"

    def test_infer_from_ctx_metadata_agent_id_variants(self):
        """Test various metadata key formats for agent_id."""
        variants = [
            ("agent_id", TEST_AGENT),
            ("agentId", TEST_AGENT),
            ("letta_agent_id", TEST_AGENT),
            ("caller_agent_id", TEST_AGENT),
        ]
        
        for key, expected in variants:
            ctx = DummyCtx(metadata={key: expected})
            agent, debug = srv._infer_agent_id(ctx)
            assert agent == expected, f"Failed for key: {key}"
            assert debug.get("source") == "context.metadata"
            assert debug.get("key") == key

    def test_infer_from_ctx_nested_agent_id(self):
        ctx = DummyCtx(metadata={"agent": {"id": TEST_AGENT}})
        agent, debug = srv._infer_agent_id(ctx)
        assert agent == TEST_AGENT
        assert debug.get("source") == "context.metadata.nested"
        assert debug.get("key") == "agent.id"

    def test_infer_from_ctx_nested_variants(self):
        """Test various nested metadata structures."""
        nested_variants = [
            ({"agent": {"agent_id": TEST_AGENT}}, "agent.agent_id"),
            ({"agent": {"id": TEST_AGENT}}, "agent.id"),
            ({"agent": {"agentId": TEST_AGENT}}, "agent.agentId"),
            ({"caller": {"agent_id": TEST_AGENT}}, "caller.agent_id"),
            ({"caller": {"id": TEST_AGENT}}, "caller.id"),
            ({"source_agent": {"agent_id": TEST_AGENT}}, "source_agent.agent_id"),
        ]
        
        for metadata, expected_key in nested_variants:
            ctx = DummyCtx(metadata=metadata)
            agent, debug = srv._infer_agent_id(ctx)
            assert agent == TEST_AGENT, f"Failed for metadata: {metadata}"
            assert debug.get("source") == "context.metadata.nested"
            assert debug.get("key") == expected_key

    def test_infer_from_ctx_direct_attribute(self):
        """Test inference from direct context attribute."""
        ctx = DummyCtx(agent_id_attr=TEST_AGENT)
        agent, debug = srv._infer_agent_id(ctx)
        assert agent == TEST_AGENT
        assert debug.get("source") == "context.attr"
        assert debug.get("key") == "agent_id"

    def test_metadata_priority_order(self):
        """Test that direct metadata keys take priority over nested ones."""
        ctx = DummyCtx(metadata={
            "agent_id": TEST_AGENT,  # This should be picked first
            "agent": {"id": "nested-agent-id"}
        })
        agent, debug = srv._infer_agent_id(ctx)
        assert agent == TEST_AGENT
        assert debug.get("source") == "context.metadata"
        assert debug.get("key") == "agent_id"


class TestEdgeCasesAndFailures:
    """Test edge cases and failure scenarios for agent_id inference."""

    def test_null_agent_id_in_metadata(self):
        """Test the specific problem scenario: agent_id is present but null."""
        ctx = DummyCtx(metadata={"agent_id": None})
        agent, debug = srv._infer_agent_id(ctx)
        assert agent is None
        assert debug.get("source") is None

    def test_null_agent_id_in_metadata_with_env_cleanup(self):
        """Test null agent_id with proper environment cleanup."""
        import os
        # Clear all relevant env vars for this test
        for env_var in ["LETTA_AGENT_ID", "PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            if env_var in os.environ:
                del os.environ[env_var]

        ctx = DummyCtx(metadata={"agent_id": None})
        agent, debug = srv._infer_agent_id(ctx)
        assert agent is None
        assert debug.get("source") is None

    def test_empty_string_agent_id_in_metadata(self):
        """Test when agent_id is present but empty string."""
        import os
        # Clear all relevant env vars for this test
        for env_var in ["LETTA_AGENT_ID", "PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            if env_var in os.environ:
                del os.environ[env_var]

        ctx = DummyCtx(metadata={"agent_id": ""})
        agent, debug = srv._infer_agent_id(ctx)
        assert agent is None
        assert debug.get("source") is None

    def test_whitespace_only_agent_id(self):
        """Test when agent_id contains only whitespace."""
        import os
        # Clear all relevant env vars for this test
        for env_var in ["LETTA_AGENT_ID", "PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            if env_var in os.environ:
                del os.environ[env_var]

        ctx = DummyCtx(metadata={"agent_id": "   "})
        agent, debug = srv._infer_agent_id(ctx)
        assert agent is None
        assert debug.get("source") is None

    def test_non_string_agent_id(self):
        """Test when agent_id is not a string."""
        import os
        # Clear all relevant env vars for this test
        for env_var in ["LETTA_AGENT_ID", "PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            if env_var in os.environ:
                del os.environ[env_var]

        test_cases = [123, [], {}, True, 0.5]
        for invalid_value in test_cases:
            ctx = DummyCtx(metadata={"agent_id": invalid_value})
            agent, debug = srv._infer_agent_id(ctx)
            assert agent is None, f"Should reject non-string value: {invalid_value}"
            assert debug.get("source") is None

    def test_metadata_as_non_dict_object(self):
        """Test when metadata is an object that needs to be converted to dict."""
        mock_meta = Mock()
        mock_meta.agent_id = TEST_AGENT
        
        ctx = DummyCtx(metadata=mock_meta)
        agent, debug = srv._infer_agent_id(ctx)
        
        # Should handle conversion via vars(meta) or similar
        # The exact behavior depends on implementation details
        # but it should either work or fail gracefully
        assert agent in (TEST_AGENT, None)

    def test_metadata_conversion_failure(self):
        """Test when metadata can't be converted to dict-like."""
        import os
        # Clear all relevant env vars for this test
        for env_var in ["LETTA_AGENT_ID", "PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            if env_var in os.environ:
                del os.environ[env_var]

        class BadMetadata:
            def __dict__(self):
                raise Exception("Cannot convert to dict")
            def keys(self):
                raise Exception("Cannot get keys")

        ctx = DummyCtx(metadata=BadMetadata())
        agent, debug = srv._infer_agent_id(ctx)
        # Should handle gracefully and not crash
        assert agent is None
        assert debug.get("source") is None

    def test_context_attribute_access_failure(self):
        """Test when accessing context attributes raises exceptions."""
        import os
        # Clear all relevant env vars for this test
        for env_var in ["LETTA_AGENT_ID", "PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            if env_var in os.environ:
                del os.environ[env_var]

        class BadContext:
            @property
            def metadata(self):
                raise AttributeError("Cannot access metadata")

            @property
            def agent_id(self):
                raise AttributeError("Cannot access agent_id")

        ctx = BadContext()
        agent, debug = srv._infer_agent_id(ctx)
        # Should handle gracefully and not crash
        assert agent is None
        assert debug.get("source") is None
        # Should have empty metadata keys since access failed
        assert debug.get("context_metadata_keys") == []
        # Should have checked env vars
        assert "env_checked" in debug
        assert debug["env_checked"]["PROMPTYOSELF_DEFAULT_AGENT_ID"] is False


class TestEnvironmentVariableInference:
    """Test agent_id inference from environment variables."""

    def test_infer_from_env_priority_order(self, monkeypatch):
        """Test that environment variables are checked in priority order."""
        # Clear all env vars first
        for env_var in ["PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            monkeypatch.delenv(env_var, raising=False)
        
        # Test PROMPTYOSELF_DEFAULT_AGENT_ID (highest priority)
        monkeypatch.setenv("PROMPTYOSELF_DEFAULT_AGENT_ID", "priority-1")
        monkeypatch.setenv("LETTA_AGENT_ID", "priority-2")
        monkeypatch.setenv("LETTA_DEFAULT_AGENT_ID", "priority-3")
        
        agent, debug = srv._infer_agent_id(None)
        assert agent == "priority-1"
        assert debug.get("source") == "env"
        assert debug.get("key") == "PROMPTYOSELF_DEFAULT_AGENT_ID"

    def test_infer_from_env_letta_agent_id(self, monkeypatch):
        """Test LETTA_AGENT_ID when higher priority not set."""
        monkeypatch.delenv("PROMPTYOSELF_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.delenv("LETTA_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
        
        agent, debug = srv._infer_agent_id(None)
        assert agent == TEST_AGENT
        assert debug.get("source") == "env"
        assert debug.get("key") == "LETTA_AGENT_ID"

    def test_infer_from_env_letta_default_agent_id(self, monkeypatch):
        """Test LETTA_DEFAULT_AGENT_ID (lowest priority)."""
        monkeypatch.delenv("PROMPTYOSELF_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.delenv("LETTA_AGENT_ID", raising=False)
        monkeypatch.setenv("LETTA_DEFAULT_AGENT_ID", TEST_AGENT)
        
        agent, debug = srv._infer_agent_id(None)
        assert agent == TEST_AGENT
        assert debug.get("source") == "env"
        assert debug.get("key") == "LETTA_DEFAULT_AGENT_ID"

    def test_env_whitespace_handling(self, monkeypatch):
        """Test that environment variables with whitespace are handled correctly."""
        # Clear other env vars
        monkeypatch.delenv("PROMPTYOSELF_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.delenv("LETTA_DEFAULT_AGENT_ID", raising=False)
        
        # Test with leading/trailing whitespace
        monkeypatch.setenv("LETTA_AGENT_ID", f"  {TEST_AGENT}  ")
        
        agent, debug = srv._infer_agent_id(None)
        assert agent == TEST_AGENT  # Should be stripped
        assert debug.get("source") == "env"

    def test_env_empty_values(self, monkeypatch):
        """Test that empty environment variable values are ignored."""
        # Clear other env vars
        monkeypatch.delenv("PROMPTYOSELF_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.delenv("LETTA_AGENT_ID", raising=False)
        monkeypatch.delenv("LETTA_DEFAULT_AGENT_ID", raising=False)
        
        # Set empty values
        monkeypatch.setenv("PROMPTYOSELF_DEFAULT_AGENT_ID", "")
        monkeypatch.setenv("LETTA_AGENT_ID", "   ")
        
        agent, debug = srv._infer_agent_id(None)
        assert agent is None
        assert debug.get("source") is None


class TestSingleAgentFallback:
    """Test single-agent fallback mechanism."""

    def test_infer_single_agent_fallback_enabled(self, monkeypatch):
        """Test successful single-agent fallback when enabled."""
        # Clear env variables
        for env_var in ["PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            monkeypatch.delenv(env_var, raising=False)
        
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "true")

        def _fake_list_agents(_args):
            return {"status": "success", "agents": [{"id": TEST_AGENT}]}

        monkeypatch.setattr(srv, "_list_agents", _fake_list_agents)
        agent, debug = srv._infer_agent_id(None)
        assert agent == TEST_AGENT
        assert debug.get("source") == "single-agent-fallback"
        assert debug.get("single_agent_fallback") is True

    def test_single_agent_fallback_disabled(self, monkeypatch):
        """Test that single-agent fallback is disabled by default."""
        # Clear env variables
        for env_var in ["PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            monkeypatch.delenv(env_var, raising=False)
        
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "false")

        def _fake_list_agents(_args):
            return {"status": "success", "agents": [{"id": TEST_AGENT}]}

        monkeypatch.setattr(srv, "_list_agents", _fake_list_agents)
        agent, debug = srv._infer_agent_id(None)
        assert agent is None
        assert debug.get("source") is None
        assert debug.get("single_agent_fallback") is False

    def test_single_agent_fallback_multiple_agents(self, monkeypatch):
        """Test that single-agent fallback fails when multiple agents exist."""
        # Clear env variables
        for env_var in ["PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            monkeypatch.delenv(env_var, raising=False)
        
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "true")

        def _fake_list_agents(_args):
            return {"status": "success", "agents": [
                {"id": "agent-1"}, 
                {"id": "agent-2"}
            ]}

        monkeypatch.setattr(srv, "_list_agents", _fake_list_agents)
        agent, debug = srv._infer_agent_id(None)
        assert agent is None
        assert debug.get("source") is None
        assert debug.get("agents_count") == 2

    def test_single_agent_fallback_no_agents(self, monkeypatch):
        """Test that single-agent fallback fails when no agents exist."""
        # Clear env variables
        for env_var in ["PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            monkeypatch.delenv(env_var, raising=False)
        
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "true")

        def _fake_list_agents(_args):
            return {"status": "success", "agents": []}

        monkeypatch.setattr(srv, "_list_agents", _fake_list_agents)
        agent, debug = srv._infer_agent_id(None)
        assert agent is None
        assert debug.get("source") is None
        assert debug.get("agents_count") == 0

    def test_single_agent_fallback_api_failure(self, monkeypatch):
        """Test that single-agent fallback handles API failures gracefully."""
        # Clear env variables
        for env_var in ["PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            monkeypatch.delenv(env_var, raising=False)
        
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "true")

        def _fake_list_agents(_args):
            return {"status": "error", "message": "Connection failed"}

        monkeypatch.setattr(srv, "_list_agents", _fake_list_agents)
        agent, debug = srv._infer_agent_id(None)
        assert agent is None
        assert debug.get("source") is None

    def test_single_agent_fallback_exception(self, monkeypatch):
        """Test that single-agent fallback handles exceptions gracefully."""
        # Clear env variables
        for env_var in ["PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            monkeypatch.delenv(env_var, raising=False)
        
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "true")

        def _fake_list_agents(_args):
            raise Exception("Unexpected error")

        monkeypatch.setattr(srv, "_list_agents", _fake_list_agents)
        agent, debug = srv._infer_agent_id(None)
        assert agent is None
        assert debug.get("source") is None


class TestDebugInformation:
    """Test debug information returned by _infer_agent_id."""

    def test_debug_context_metadata_keys(self):
        """Test that debug info includes context metadata keys."""
        large_metadata = {
            "agent_id": TEST_AGENT,
            "session_id": "session-123",
            "timestamp": "2025-01-01T00:00:00Z",
            "client_version": "1.0.0",
            "other_field": "value"
        }
        ctx = DummyCtx(metadata=large_metadata)
        agent, debug = srv._infer_agent_id(ctx)
        
        assert agent == TEST_AGENT
        assert "context_metadata_keys" in debug
        # Should include some keys (limited to 20 for safety)
        keys = debug["context_metadata_keys"]
        assert isinstance(keys, list)
        assert "agent_id" in keys

    def test_debug_env_checked(self, monkeypatch):
        """Test that debug info shows which env vars were checked."""
        # Clear all env vars
        for env_var in ["PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            monkeypatch.delenv(env_var, raising=False)
        
        # Set one env var
        monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
        
        agent, debug = srv._infer_agent_id(None)
        
        assert agent == TEST_AGENT
        assert "env_checked" in debug
        env_checked = debug["env_checked"]
        assert env_checked["PROMPTYOSELF_DEFAULT_AGENT_ID"] is False
        assert env_checked["LETTA_AGENT_ID"] is True
        assert env_checked["LETTA_DEFAULT_AGENT_ID"] is False

    def test_debug_complete_failure(self, monkeypatch):
        """Test debug info when all inference methods fail."""
        # Clear all env vars and disable fallback
        for env_var in ["PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            monkeypatch.delenv(env_var, raising=False)
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "false")

        agent, debug = srv._infer_agent_id(None)
        
        assert agent is None
        assert debug.get("source") is None
        assert "env_checked" in debug
        assert debug.get("single_agent_fallback") is False


class TestRequestContextMetadataInference:
    """Test agent_id inference from request_context metadata (Letta-style)."""

    def test_request_context_metadata_agent_id(self):
        """Test inference from request_context.metadata.agent_id."""
        class MockRequestContext:
            def __init__(self, agent_id):
                self.metadata = {"agent_id": agent_id}

        class MockContext:
            def __init__(self, agent_id):
                self.request_context = MockRequestContext(agent_id)

        ctx = MockContext(TEST_AGENT)
        agent, debug = srv._infer_agent_id(ctx)
        assert agent == TEST_AGENT
        assert debug.get("source") == "context.request_context.metadata"
        assert debug.get("key") == "agent_id"

    def test_request_context_nested_agent_id(self):
        """Test inference from request_context.metadata.agent.id."""
        class MockRequestContext:
            def __init__(self):
                self.metadata = {"agent": {"id": TEST_AGENT}}

        class MockContext:
            def __init__(self):
                self.request_context = MockRequestContext()

        ctx = MockContext()
        agent, debug = srv._infer_agent_id(ctx)
        assert agent == TEST_AGENT
        assert debug.get("source") == "context.request_context.metadata.nested"
        assert debug.get("key") == "agent.id"

    def test_request_context_attr_metadata(self):
        """Test inference from request_context.metadata (attribute access)."""
        class MockRequestContext:
            def __init__(self):
                self.meta = {"agent_id": TEST_AGENT}  # Different attr name

        class MockContext:
            def __init__(self):
                self.request_context = MockRequestContext()

        ctx = MockContext()
        agent, debug = srv._infer_agent_id(ctx)
        assert agent == TEST_AGENT
        assert debug.get("source") == "context.request_context.meta"
        assert debug.get("key") == "agent_id"

    def test_request_context_metadata_priority(self):
        """Test that request_context takes priority over regular context."""
        # Context has agent_id, but request_context should override
        request_ctx_agent = "request-context-agent"

        import os
        # Clear all relevant env vars for this test
        for env_var in ["LETTA_AGENT_ID", "PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            if env_var in os.environ:
                del os.environ[env_var]

        class MockRequestContext:
            def __init__(self):
                self.metadata = {"agent_id": request_ctx_agent}

        class MockContext:
            def __init__(self):
                self.request_context = MockRequestContext()
                self.metadata = {"agent_id": "regular-context-agent"}  # Should be ignored

        ctx = MockContext()
        agent, debug = srv._infer_agent_id(ctx)
        assert agent == request_ctx_agent
        assert debug.get("source") == "context.request_context.metadata"
        assert debug.get("key") == "agent_id"


def test_infer_none_when_unavailable(monkeypatch):
    """Legacy test - ensure backward compatibility."""
    # Clear env and disable fallback
    monkeypatch.delenv("PROMPTYOSELF_DEFAULT_AGENT_ID", raising=False)
    monkeypatch.delenv("LETTA_AGENT_ID", raising=False)
    monkeypatch.delenv("LETTA_DEFAULT_AGENT_ID", raising=False)
    monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "false")

    agent, debug = srv._infer_agent_id(None)
    assert agent is None
    assert debug.get("source") is None
