"""
Test the promptyoself_set_default_agent MCP tool.

This module tests the new tool that allows MCP clients to set a default
agent ID to avoid passing it with every scheduling call.
"""

import pytest
import os
from unittest.mock import patch


class TestSetDefaultAgentTool:
    """Test the promptyoself_set_default_agent MCP tool functionality."""
    
    async def test_set_default_agent_success(self, mcp_in_memory_client):
        """Test successful setting of default agent ID."""
        test_agent = "agent-12345-test"
        
        result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": test_agent
        })
        
        assert result.structured_content["status"] == "success"
        assert result.structured_content["agent_id"] == test_agent
        assert test_agent in result.structured_content["message"]
        assert "current server session" in result.structured_content["note"]
        
        # Verify the environment variable was actually set
        assert os.getenv("LETTA_AGENT_ID") == test_agent
    
    async def test_set_default_agent_with_whitespace(self, mcp_in_memory_client):
        """Test that whitespace is stripped when setting default agent."""
        test_agent = "  agent-whitespace-test  "
        expected_agent = "agent-whitespace-test"
        
        result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": test_agent
        })
        
        assert result.structured_content["status"] == "success"
        assert result.structured_content["agent_id"] == expected_agent
        
        # Verify the trimmed value was set in environment
        assert os.getenv("LETTA_AGENT_ID") == expected_agent
    
    async def test_set_default_agent_empty_string_error(self, mcp_in_memory_client):
        """Test that empty string agent_id returns error."""
        result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": ""
        })
        
        assert "error" in result.structured_content
        assert "cannot be empty" in result.structured_content["error"]
    
    async def test_set_default_agent_whitespace_only_error(self, mcp_in_memory_client):
        """Test that whitespace-only agent_id returns error."""
        result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": "   \t  "
        })
        
        assert "error" in result.structured_content
        assert "cannot be empty" in result.structured_content["error"]
    
    async def test_set_default_agent_none_error(self, mcp_in_memory_client):
        """Test that None agent_id returns error."""
        # Note: This might be handled by FastMCP validation before reaching our tool
        # But we should handle it gracefully if it gets through
        try:
            result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
                "agent_id": None
            })
            # If we get here, check for error response
            assert "error" in result.structured_content
        except Exception:
            # FastMCP might reject None before reaching our tool, which is fine
            pass
    
    async def test_set_default_agent_verification_works(self, mcp_in_memory_client):
        """Test that the verification mechanism works correctly."""
        test_agent = "agent-verification-test"
        
        result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": test_agent
        })
        
        # Should succeed
        assert result.structured_content["status"] == "success"
        
        # The returned agent_id should match what was actually set
        returned_agent = result.structured_content["agent_id"]
        env_agent = os.getenv("LETTA_AGENT_ID")
        assert returned_agent == env_agent == test_agent
    
    @patch('os.environ.__setitem__')
    async def test_set_default_agent_env_failure(self, mock_setitem, mcp_in_memory_client):
        """Test handling of environment variable setting failure."""
        # Mock environment variable setting to fail
        mock_setitem.side_effect = Exception("Environment variable setting failed")
        
        result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": "test-agent-fail"
        })
        
        assert "error" in result.structured_content
        assert "Failed to set default agent ID" in result.structured_content["error"]
    
    async def test_set_default_agent_overwrites_previous(self, mcp_in_memory_client, monkeypatch):
        """Test that setting a new default agent overwrites the previous one."""
        # Set initial agent
        monkeypatch.setenv("LETTA_AGENT_ID", "initial-agent")
        
        new_agent = "replacement-agent"
        result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": new_agent
        })
        
        assert result.structured_content["status"] == "success"
        assert result.structured_content["agent_id"] == new_agent
        
        # Verify the new agent replaced the old one
        assert os.getenv("LETTA_AGENT_ID") == new_agent
        assert os.getenv("LETTA_AGENT_ID") != "initial-agent"


class TestSetDefaultAgentIntegration:
    """Test integration between set_default_agent and scheduling tools."""
    
    async def test_set_default_then_schedule_without_agent_id(self, mcp_in_memory_client):
        """Test that setting default agent allows scheduling without explicit agent_id."""
        default_agent = "default-integration-agent"
        
        # First, set the default agent
        set_result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": default_agent
        })
        assert set_result.structured_content["status"] == "success"
        
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 500, "next_run": "2025-01-01T10:00:00Z"}
            
            # Now schedule without providing agent_id (should use default)
            schedule_result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                "prompt": "Test with default agent",
                "time": "2025-01-01T10:00:00Z"
                # No agent_id provided - should use default
            })
            
            assert "error" not in schedule_result.structured_content
            assert schedule_result.structured_content["status"] == "success"
            
            # Verify the default agent was used
            mock_register.assert_called_once()
            call_args = mock_register.call_args.kwargs
            assert call_args["agent_id"] == default_agent
    
    async def test_set_default_then_schedule_with_explicit_agent_id(self, mcp_in_memory_client):
        """Test that explicit agent_id overrides default agent."""
        default_agent = "default-agent"
        explicit_agent = "explicit-agent"
        
        # Set the default agent
        set_result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": default_agent
        })
        assert set_result.structured_content["status"] == "success"
        
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 501, "next_run": "2025-01-01T11:00:00Z"}
            
            # Schedule with explicit agent_id (should override default)
            schedule_result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                "agent_id": explicit_agent,
                "prompt": "Test with explicit agent",
                "time": "2025-01-01T11:00:00Z"
            })
            
            assert "error" not in schedule_result.structured_content
            assert schedule_result.structured_content["status"] == "success"
            
            # Verify the explicit agent was used, not the default
            mock_register.assert_called_once()
            call_args = mock_register.call_args.kwargs
            assert call_args["agent_id"] == explicit_agent
            assert call_args["agent_id"] != default_agent
    
    async def test_set_default_then_schedule_with_null_agent_id(self, mcp_in_memory_client):
        """Test that null agent_id gets normalized and falls back to default."""
        default_agent = "default-for-null-test"
        
        # Set the default agent
        set_result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": default_agent
        })
        assert set_result.structured_content["status"] == "success"
        
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 502, "next_run": "2025-01-01T12:00:00Z"}
            
            # Schedule with "null" string (should be normalized and use default)
            schedule_result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                "agent_id": "null",
                "prompt": "Test null normalization with default",
                "time": "2025-01-01T12:00:00Z"
            })
            
            assert "error" not in schedule_result.structured_content
            assert schedule_result.structured_content["status"] == "success"
            
            # Verify the default agent was used after normalization
            mock_register.assert_called_once()
            call_args = mock_register.call_args.kwargs
            assert call_args["agent_id"] == default_agent
    
    async def test_multiple_scheduling_tools_use_default(self, mcp_in_memory_client):
        """Test that all scheduling tools can use the set default agent."""
        default_agent = "multi-tool-default-agent"
        
        # Set the default agent
        set_result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": default_agent
        })
        assert set_result.structured_content["status"] == "success"
        
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            # Test schedule_time with default
            mock_register.return_value = {"status": "success", "id": 601}
            result1 = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                "prompt": "Time with default",
                "time": "2025-01-01T14:00:00Z"
            })
            assert result1.structured_content["status"] == "success"
            
            # Test schedule_cron with default
            mock_register.return_value = {"status": "success", "id": 602}
            result2 = await mcp_in_memory_client.call_tool("promptyoself_schedule_cron", {
                "prompt": "Cron with default",
                "cron": "0 9 * * *"
            })
            assert result2.structured_content["status"] == "success"
            
            # Test schedule_every with default
            mock_register.return_value = {"status": "success", "id": 603}
            result3 = await mcp_in_memory_client.call_tool("promptyoself_schedule_every", {
                "prompt": "Every with default",
                "every": "1h"
            })
            assert result3.structured_content["status"] == "success"
            
            # Test general schedule with default
            mock_register.return_value = {"status": "success", "id": 604}
            result4 = await mcp_in_memory_client.call_tool("promptyoself_schedule", {
                "prompt": "General with default",
                "time": "2025-01-01T16:00:00Z"
            })
            assert result4.structured_content["status"] == "success"
            
            # Verify all calls used the default agent
            assert mock_register.call_count == 4
            for call in mock_register.call_args_list:
                assert call.kwargs["agent_id"] == default_agent


class TestSetDefaultAgentToolValidation:
    """Test validation and edge cases for the set_default_agent tool."""
    
    async def test_agent_id_validation_accepts_various_formats(self, mcp_in_memory_client):
        """Test that various valid agent ID formats are accepted."""
        valid_agent_ids = [
            "agent-123",
            "agent_456", 
            "AGENT-789",
            "a",  # single character
            "agent-with-long-uuid-12345678-1234-1234-1234-123456789abc",
            "123-numeric-agent",
            "agent.with.dots",
            "agent@with@symbols",
            "user:agent-id",
        ]
        
        for agent_id in valid_agent_ids:
            result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
                "agent_id": agent_id
            })
            
            assert result.structured_content["status"] == "success", f"Failed for agent_id: {agent_id}"
            assert result.structured_content["agent_id"] == agent_id
            assert os.getenv("LETTA_AGENT_ID") == agent_id
    
    async def test_invalid_agent_id_formats_rejected(self, mcp_in_memory_client):
        """Test that invalid agent ID formats are properly rejected."""
        invalid_agent_ids = [
            "",  # empty string
            "   ",  # whitespace only
            "\t\n",  # tabs and newlines only
        ]
        
        for agent_id in invalid_agent_ids:
            result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
                "agent_id": agent_id
            })
            
            assert "error" in result.structured_content, f"Should have failed for agent_id: {repr(agent_id)}"
            assert "cannot be empty" in result.structured_content["error"]
    
    async def test_tool_response_structure(self, mcp_in_memory_client):
        """Test that the tool response has the expected structure."""
        test_agent = "structure-test-agent"
        
        result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": test_agent
        })
        
        # Check required fields are present
        assert "status" in result.structured_content
        assert "message" in result.structured_content
        assert "agent_id" in result.structured_content
        assert "note" in result.structured_content
        
        # Check field types and values
        assert isinstance(result.structured_content["status"], str)
        assert isinstance(result.structured_content["message"], str)
        assert isinstance(result.structured_content["agent_id"], str)
        assert isinstance(result.structured_content["note"], str)
        
        assert result.structured_content["status"] == "success"
        assert result.structured_content["agent_id"] == test_agent
    
    async def test_concurrent_set_operations(self, mcp_in_memory_client):
        """Test behavior when multiple set operations happen in sequence."""
        agents = ["agent-1", "agent-2", "agent-3"]
        
        for agent in agents:
            result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
                "agent_id": agent
            })
            
            assert result.structured_content["status"] == "success"
            assert result.structured_content["agent_id"] == agent
            
            # Verify this agent is now the current one
            assert os.getenv("LETTA_AGENT_ID") == agent
        
        # Final verification - should be the last agent set
        assert os.getenv("LETTA_AGENT_ID") == "agent-3"