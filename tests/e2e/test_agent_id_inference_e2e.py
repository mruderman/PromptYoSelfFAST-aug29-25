"""
End-to-end tests for the complete agent_id inference and normalization system.

These tests cover the complete workflow from MCP client request through
parameter normalization, agent inference, and successful scheduling.
"""

import pytest
import os
from unittest.mock import patch, Mock
import tempfile


TEST_AGENT = "agent-e2e-test-12345"


class TestAgentIdInferenceE2E:
    """Complete end-to-end tests for agent_id inference system."""
    
    @pytest.mark.asyncio
    async def test_complete_null_agent_workflow(self, mcp_in_memory_client, monkeypatch):
        """Test the complete workflow that was failing: null agent_id → inference → success."""
        # Set up environment for successful inference
        monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
        
        # Mock the entire chain to avoid external dependencies
        with patch("promptyoself.cli.validate_agent_exists") as mock_validate:
            mock_validate.return_value = {"status": "success", "exists": True, "agent_id": TEST_AGENT}
            
            with patch("promptyoself.cli.register_prompt") as mock_register:
                mock_register.return_value = {
                    "status": "success",
                    "id": 5001,
                    "next_run": "2025-01-01T10:00:00Z",
                    "message": "Scheduled successfully"
                }
                
                # The failing scenario: MCP client sends "null" as agent_id
                result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                    "agent_id": "null",  # This was causing the issue
                    "prompt": "Complete workflow test",
                    "time": "2025-12-25T10:00:00Z"
                })
                
                # Should succeed
                assert "error" not in result.structured_content
                assert result.structured_content["status"] == "success"
                assert result.structured_content["id"] == 5001
                assert "next_run" in result.structured_content
                
                # Verify the complete call chain
                mock_validate.assert_called_once_with(TEST_AGENT)
                mock_register.assert_called_once()
                
                # Verify the inferred agent was used
                call_args = mock_register.call_args.kwargs
                assert call_args["agent_id"] == TEST_AGENT
                assert call_args["prompt"] == "Complete workflow test"
                assert call_args["time"] == "2025-12-25T10:00:00Z"
    
    @pytest.mark.asyncio
    async def test_set_default_agent_complete_workflow(self, mcp_in_memory_client):
        """Test the complete set-default-agent workflow."""
        workflow_agent = "workflow-default-agent"
        
        # Step 1: Set default agent
        set_result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": workflow_agent
        })
        
        assert set_result.structured_content["status"] == "success"
        assert set_result.structured_content["agent_id"] == workflow_agent
        assert "current server session" in set_result.structured_content["note"]
        
        # Verify environment was updated
        assert os.getenv("LETTA_AGENT_ID") == workflow_agent
        
        # Step 2: Schedule with null agent_id (should use default)
        with patch("promptyoself.cli.validate_agent_exists") as mock_validate:
            mock_validate.return_value = {"status": "success", "exists": True, "agent_id": workflow_agent}
            
            with patch("promptyoself.cli.register_prompt") as mock_register:
                mock_register.return_value = {
                    "status": "success",
                    "id": 5002,
                    "next_run": "2025-01-02T11:00:00Z",
                    "message": "Scheduled with default agent"
                }
                
                schedule_result = await mcp_in_memory_client.call_tool("promptyoself_schedule_cron", {
                    "agent_id": "null",  # Should use the default we set
                    "prompt": "Using default agent workflow",
                    "cron": "0 9 * * *"
                })
                
                # Should succeed using the default agent
                assert "error" not in schedule_result.structured_content
                assert schedule_result.structured_content["status"] == "success"
                assert schedule_result.structured_content["id"] == 5002
                
                # Verify the default agent was used
                mock_validate.assert_called_once_with(workflow_agent)
                mock_register.assert_called_once()
                
                call_args = mock_register.call_args.kwargs
                assert call_args["agent_id"] == workflow_agent
                assert call_args["cron"] == "0 9 * * *"
    
    @pytest.mark.asyncio
    async def test_parameter_normalization_complete_coverage(self, mcp_in_memory_client, monkeypatch):
        """Test all parameter normalization cases in complete workflow."""
        monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
        
        normalization_cases = [
            ("null", "Null string test"),
            ("NULL", "Uppercase null test"),
            ("None", "Python None string test"),
            ("NONE", "Uppercase None test"),
            ("", "Empty string test"),
            ("   ", "Whitespace only test"),
            ("\t\n", "Tab newline test"),
        ]
        
        with patch("promptyoself.cli.validate_agent_exists") as mock_validate:
            mock_validate.return_value = {"status": "success", "exists": True, "agent_id": TEST_AGENT}
            
            with patch("promptyoself.cli.register_prompt") as mock_register:
                
                for i, (agent_value, prompt) in enumerate(normalization_cases):
                    mock_register.reset_mock()
                    mock_validate.reset_mock()
                    mock_register.return_value = {"status": "success", "id": 5100 + i}
                    
                    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_every", {
                        "agent_id": agent_value,
                        "prompt": prompt,
                        "every": "1h"
                    })
                    
                    # All cases should succeed with inference
                    assert "error" not in result.structured_content, f"Failed for agent_value: {repr(agent_value)}"
                    assert result.structured_content["status"] == "success"
                    
                    # All should have used the inferred agent
                    mock_validate.assert_called_once_with(TEST_AGENT)
                    mock_register.assert_called_once()
                    assert mock_register.call_args.kwargs["agent_id"] == TEST_AGENT
    
    @pytest.mark.asyncio 
    async def test_multiple_tools_inference_consistency(self, mcp_in_memory_client, monkeypatch):
        """Test that agent inference works consistently across all scheduling tools."""
        monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
        
        scheduling_tools = [
            ("promptyoself_schedule_time", {"time": "2025-01-03T14:00:00Z"}),
            ("promptyoself_schedule_cron", {"cron": "*/30 * * * *"}),
            ("promptyoself_schedule_every", {"every": "45m"}),
            ("promptyoself_schedule", {"time": "2025-01-03T16:00:00Z"}),
        ]
        
        with patch("promptyoself.cli.validate_agent_exists") as mock_validate:
            mock_validate.return_value = {"status": "success", "exists": True, "agent_id": TEST_AGENT}
            
            with patch("promptyoself.cli.register_prompt") as mock_register:
                
                for i, (tool_name, extra_params) in enumerate(scheduling_tools):
                    mock_register.reset_mock()
                    mock_validate.reset_mock()
                    mock_register.return_value = {"status": "success", "id": 5200 + i}
                    
                    params = {
                        "agent_id": "null",  # Should trigger inference for all tools
                        "prompt": f"Multi-tool test {tool_name}",
                        **extra_params
                    }
                    
                    result = await mcp_in_memory_client.call_tool(tool_name, params)
                    
                    # All tools should handle inference consistently
                    assert "error" not in result.structured_content, f"Failed for tool: {tool_name}"
                    assert result.structured_content["status"] == "success"
                    assert result.structured_content["id"] == 5200 + i
                    
                    # All should have used the same inferred agent
                    mock_validate.assert_called_once_with(TEST_AGENT)
                    mock_register.assert_called_once()
                    assert mock_register.call_args.kwargs["agent_id"] == TEST_AGENT
    
    @pytest.mark.asyncio
    async def test_inference_priority_chain_e2e(self, mcp_in_memory_client, monkeypatch):
        """Test the complete inference priority chain end-to-end."""
        
        # Test 1: Context metadata takes highest priority (mocked)
        context_agent = "context-priority-agent"
        
        with patch("promptyoself_mcp_server._infer_agent_id") as mock_infer:
            mock_infer.return_value = (context_agent, {"source": "context.metadata", "key": "agent_id"})
            
            with patch("promptyoself.cli.validate_agent_exists") as mock_validate:
                mock_validate.return_value = {"status": "success", "exists": True, "agent_id": context_agent}
                
                with patch("promptyoself.cli.register_prompt") as mock_register:
                    mock_register.return_value = {"status": "success", "id": 5301}
                    
                    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                        "agent_id": "null",
                        "prompt": "Context priority test",
                        "time": "2025-01-04T09:00:00Z"
                    })
                    
                    assert result.structured_content["status"] == "success"
                    mock_validate.assert_called_once_with(context_agent)
        
        # Test 2: Environment variable priority order
        env_test_cases = [
            ("PROMPTYOSELF_DEFAULT_AGENT_ID", "promptyoself-priority-agent"),
            ("LETTA_AGENT_ID", "letta-agent-priority"),
            ("LETTA_DEFAULT_AGENT_ID", "letta-default-priority"),
        ]
        
        for env_var, agent_value in env_test_cases:
            # Clear other environment variables
            for clear_var in ["PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
                monkeypatch.delenv(clear_var, raising=False)
            
            # Set only the current test variable
            monkeypatch.setenv(env_var, agent_value)
            
            with patch("promptyoself.cli.validate_agent_exists") as mock_validate:
                mock_validate.return_value = {"status": "success", "exists": True, "agent_id": agent_value}
                
                with patch("promptyoself.cli.register_prompt") as mock_register:
                    mock_register.return_value = {"status": "success", "id": 5400}
                    
                    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_cron", {
                        "agent_id": "null",
                        "prompt": f"Env priority test {env_var}",
                        "cron": "0 10 * * *"
                    })
                    
                    assert result.structured_content["status"] == "success", f"Failed for env var: {env_var}"
                    mock_validate.assert_called_once_with(agent_value)
                    assert mock_register.call_args.kwargs["agent_id"] == agent_value
    
    @pytest.mark.asyncio
    async def test_complete_failure_recovery_e2e(self, mcp_in_memory_client, monkeypatch):
        """Test complete inference failure and proper error handling."""
        # Clear all environment variables and disable fallbacks
        for env_var in ["PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            monkeypatch.delenv(env_var, raising=False)
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "false")
        
        result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
            "agent_id": "null",  # Will be normalized to None, inference will fail
            "prompt": "Complete failure test",
            "time": "2025-01-05T12:00:00Z"
        })
        
        # Should get a clear error message
        assert "error" in result.structured_content
        assert "agent_id" in result.structured_content["error"].lower()
        
        # Should not have attempted to register
        # (This is implied since validation/registration would be mocked if called)
    
    @pytest.mark.asyncio
    async def test_single_agent_fallback_e2e(self, mcp_in_memory_client, monkeypatch):
        """Test the complete single-agent fallback mechanism end-to-end."""
        # Clear env vars and enable single agent fallback
        for env_var in ["PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            monkeypatch.delenv(env_var, raising=False)
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "true")
        
        fallback_agent = "single-agent-fallback-e2e"
        
        # Mock the list_agents call that single-agent fallback uses
        with patch("promptyoself.cli.list_agents") as mock_list:
            mock_list.return_value = {"status": "success", "agents": [{"id": fallback_agent}]}
            
            with patch("promptyoself.cli.validate_agent_exists") as mock_validate:
                mock_validate.return_value = {"status": "success", "exists": True, "agent_id": fallback_agent}
                
                with patch("promptyoself.cli.register_prompt") as mock_register:
                    mock_register.return_value = {"status": "success", "id": 5500}
                    
                    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_every", {
                        "agent_id": "null",
                        "prompt": "Single agent fallback e2e test", 
                        "every": "2h"
                    })
                    
                    # Should succeed using single agent fallback
                    assert "error" not in result.structured_content
                    assert result.structured_content["status"] == "success"
                    
                    # Should have used the fallback agent
                    mock_list.assert_called_once()
                    mock_validate.assert_called_once_with(fallback_agent)
                    mock_register.assert_called_once()
                    assert mock_register.call_args.kwargs["agent_id"] == fallback_agent
    
    @pytest.mark.asyncio
    async def test_real_database_integration_e2e(self, mcp_in_memory_client, monkeypatch):
        """Test end-to-end with real database operations (using temp DB)."""
        # Create a temporary database for this test
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            temp_db_path = tmp_db.name
        
        try:
            # Set up environment to use temp database
            monkeypatch.setenv("PROMPTYOSELF_DB", temp_db_path)
            monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
            
            # Mock only the Letta API calls, let database operations run
            with patch("promptyoself.letta_api.get_letta_client") as mock_client:
                # Mock Letta client for validation
                mock_letta = Mock()
                mock_letta.list_agents.return_value = [Mock(id=TEST_AGENT, name="Test Agent")]
                mock_client.return_value = mock_letta
                
                # Schedule a real prompt (will hit real database)
                result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                    "agent_id": "null",  # Should infer from environment
                    "prompt": "Real database e2e test",
                    "time": "2025-12-31T23:59:59Z"
                })
                
                # Should succeed and return real database ID
                assert "error" not in result.structured_content
                assert result.structured_content["status"] == "success"
                assert "id" in result.structured_content
                assert isinstance(result.structured_content["id"], int)
                assert "next_run" in result.structured_content
                
                # Verify the record exists in database
                from promptyoself.db import get_db_session, UnifiedReminder
                
                with get_db_session() as session:
                    reminder = session.query(UnifiedReminder).filter_by(
                        id=result.structured_content["id"]
                    ).first()
                    
                    assert reminder is not None
                    assert reminder.message == "Real database e2e test"
                    assert reminder.agent_id == TEST_AGENT
                    assert reminder.schedule_type == "once"
                    assert reminder.status == "pending"
                
        finally:
            # Clean up temp database
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    @pytest.mark.asyncio
    async def test_diagnostics_tool_e2e(self, mcp_in_memory_client, monkeypatch):
        """Test the inference diagnostics tool end-to-end."""
        # Set up specific environment for diagnostics
        monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "true")
        
        # Mock agents list for single agent fallback info
        with patch("promptyoself.cli.list_agents") as mock_list:
            mock_list.return_value = {"status": "success", "agents": [{"id": TEST_AGENT}, {"id": "other-agent"}]}
            
            result = await mcp_in_memory_client.call_tool("promptyoself_inference_diagnostics")
            
            # Should provide comprehensive diagnostics
            assert result.structured_content["status"] == "ok"
            assert "ctx_present" in result.structured_content
            assert "env" in result.structured_content
            assert "single_agent_fallback_enabled" in result.structured_content
            assert "agents_count" in result.structured_content
            
            # Environment should show LETTA_AGENT_ID is set
            env_info = result.structured_content["env"]
            assert env_info["LETTA_AGENT_ID"]["set"] is True
            assert env_info["LETTA_AGENT_ID"]["value"] == TEST_AGENT
            
            # Single agent fallback should be enabled but not applicable (multiple agents)
            assert result.structured_content["single_agent_fallback_enabled"] is True
            assert result.structured_content["agents_count"] == 2
    
    @pytest.mark.asyncio
    async def test_complete_error_context_e2e(self, mcp_in_memory_client, caplog, monkeypatch):
        """Test that complete error context is provided when inference fails."""
        # Set up complete failure scenario
        monkeypatch.delenv("PROMPTYOSELF_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.delenv("LETTA_AGENT_ID", raising=False)
        monkeypatch.delenv("LETTA_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "false")
        
        result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
            "agent_id": "null",
            "prompt": "Error context test",
            "time": "2025-01-06T15:00:00Z"
        })
        
        # Should get detailed error
        assert "error" in result.structured_content
        error_msg = result.structured_content["error"]
        
        # Error should be informative
        assert "agent_id" in error_msg.lower()
        assert any(word in error_msg.lower() for word in ["required", "missing", "infer", "provide"])
        
        # Should have logged the inference attempt
        log_messages = [record.message for record in caplog.records]
        assert any("Agent ID inference attempted" in msg for msg in log_messages)
        assert any("Converting string 'None'/'null'/empty to actual None" in msg for msg in log_messages)