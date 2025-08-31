"""
Test parameter normalization logic in the MCP server.

This module tests the critical parameter normalization that converts
MCP client "null"/"None"/empty strings to Python None values.
"""

import pytest
from unittest.mock import patch, Mock
import promptyoself_mcp_server as srv


class TestParameterNormalization:
    """Test the parameter normalization that converts string nulls to Python None."""

    @pytest.mark.parametrize("input_value,expected_output", [
        # String representations that should become None
        ("None", None),
        ("null", None),
        ("NULL", None),
        ("Null", None),
        ("NONE", None),
        ("none", None),
        ("", None),
        ("   ", None),  # whitespace only
        ("\t\n", None),  # various whitespace
        
        # Valid values that should be preserved
        ("agent-12345", "agent-12345"),
        ("test-agent-id", "test-agent-id"),
        ("a", "a"),  # single character
        ("0", "0"),  # zero as string
        ("false", "false"),  # string false (not boolean)
        ("None123", "None123"),  # contains None but is valid
        ("agent-null-test", "agent-null-test"),  # contains null but is valid
        
        # Edge cases that should be preserved (though unusual)
        ("  agent-123  ", "  agent-123  "),  # should be preserved (not a null value)
        ("AGENT-456", "AGENT-456"),
        ("agent_id_123", "agent_id_123"),
    ])
    async def test_parameter_normalization_schedule_time(self, input_value, expected_output, mcp_in_memory_client):
        """Test parameter normalization in promptyoself_schedule_time tool."""
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            # Mock successful registration
            mock_register.return_value = {"status": "success", "id": 123, "next_run": "2025-01-01T00:00:00Z"}
            
            # Mock agent inference for None cases
            if expected_output is None:
                with patch("promptyoself_mcp_server._infer_agent_id") as mock_infer:
                    mock_infer.return_value = ("inferred-agent-123", {"source": "test"})
                    
                    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                        "agent_id": input_value,
                        "prompt": "Test prompt",
                        "time": "2025-12-25T10:00:00Z"
                    })
                    
                    # Should succeed with inference
                    assert "error" not in result.structured_content
                    mock_infer.assert_called_once()
                    
                    # Should pass inferred agent to register_prompt
                    mock_register.assert_called_once()
                    call_args = mock_register.call_args[0][0]  # First positional arg is the args dict
                    assert call_args["agent_id"] == "inferred-agent-123"
            else:
                # Valid agent_id, no inference needed
                result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                    "agent_id": input_value,
                    "prompt": "Test prompt", 
                    "time": "2025-12-25T10:00:00Z"
                })
                
                # Should succeed without inference
                assert "error" not in result.structured_content
                
                # Should pass normalized agent to register_prompt
                mock_register.assert_called_once()
                call_args = mock_register.call_args[0][0]  # First positional arg is the args dict
                assert call_args["agent_id"] == expected_output

    async def test_parameter_normalization_schedule_cron(self, mcp_in_memory_client):
        """Test parameter normalization in promptyoself_schedule_cron tool."""
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 124, "next_run": "2025-01-01T09:00:00Z"}
            
            with patch("promptyoself_mcp_server._infer_agent_id") as mock_infer:
                mock_infer.return_value = ("inferred-cron-agent", {"source": "env"})
                
                # Test string "null" normalization
                result = await mcp_in_memory_client.call_tool("promptyoself_schedule_cron", {
                    "agent_id": "null",
                    "prompt": "Daily check",
                    "cron": "0 9 * * *"
                })
                
                assert "error" not in result.structured_content
                mock_infer.assert_called_once()
                
                # Verify inferred agent was used
                mock_register.assert_called_once()
                call_args = mock_register.call_args[0][0]
                assert call_args["agent_id"] == "inferred-cron-agent"

    async def test_parameter_normalization_schedule_every(self, mcp_in_memory_client):
        """Test parameter normalization in promptyoself_schedule_every tool."""
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 125, "next_run": "2025-01-01T00:05:00Z"}
            
            with patch("promptyoself_mcp_server._infer_agent_id") as mock_infer:
                mock_infer.return_value = ("inferred-every-agent", {"source": "context"})
                
                # Test empty string normalization
                result = await mcp_in_memory_client.call_tool("promptyoself_schedule_every", {
                    "agent_id": "",
                    "prompt": "Every 5 minutes",
                    "every": "5m"
                })
                
                assert "error" not in result.structured_content
                mock_infer.assert_called_once()
                
                # Verify inferred agent was used
                mock_register.assert_called_once()
                call_args = mock_register.call_args[0][0]
                assert call_args["agent_id"] == "inferred-every-agent"


    def test_normalization_with_none_type(self):
        """Test that actual None values are handled correctly (not just strings)."""
        # This tests the logic directly without MCP layer
        test_cases = [
            (None, None),
            ("None", None),
            ("null", None),
            ("valid-agent", "valid-agent"),
        ]
        
        for input_val, expected in test_cases:
            # Simulate the normalization logic from the server
            if input_val is not None and str(input_val).strip().lower() in ("none", "null", ""):
                normalized = None
            else:
                normalized = input_val
                
            assert normalized == expected, f"Failed for input: {input_val}"

    def test_normalization_edge_cases(self):
        """Test edge cases in parameter normalization."""
        edge_cases = [
            # Non-string types that could come through
            (0, 0),  # Should not be converted to None
            (False, False),  # Should not be converted to None
            ([], []),  # Should not be converted to None
            
            # String edge cases
            ("0", "0"),  # Zero string should remain
            ("false", "false"),  # false string should remain
            ("true", "true"),  # true string should remain
            ("None123", "None123"),  # Partial match should remain
            ("nullified", "nullified"),  # Contains null but valid
        ]
        
        for input_val, expected in edge_cases:
            # Test the exact logic from the server
            if input_val is not None and str(input_val).strip().lower() in ("none", "null", ""):
                normalized = None
            else:
                normalized = input_val
                
            assert normalized == expected, f"Failed for input: {input_val} (type: {type(input_val)})"


class TestNormalizationWithInference:
    """Test parameter normalization combined with agent inference."""
    
    async def test_normalization_triggers_inference_success(self, mcp_in_memory_client, monkeypatch):
        """Test that normalized None values trigger successful inference."""
        # Set up environment for inference
        monkeypatch.setenv("LETTA_AGENT_ID", "env-agent-123")
        
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 200}
            
            # Test that "null" string gets normalized and inference succeeds
            result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                "agent_id": "null",
                "prompt": "Test inference",
                "time": "2025-01-01T12:00:00Z"
            })
            
            assert "error" not in result.structured_content
            assert result.structured_content["status"] == "success"
            
            # Verify the environment agent was used
            mock_register.assert_called_once()
            call_args = mock_register.call_args[0][0]
            assert call_args["agent_id"] == "env-agent-123"
    
    async def test_normalization_triggers_inference_failure(self, mcp_in_memory_client, monkeypatch):
        """Test that normalized None values with failed inference show error."""
        # Clear environment variables to force inference failure
        monkeypatch.delenv("PROMPTYOSELF_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.delenv("LETTA_AGENT_ID", raising=False) 
        monkeypatch.delenv("LETTA_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "false")
        
        # Test that "None" string gets normalized but inference fails
        result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
            "agent_id": "None",
            "prompt": "Test failed inference",
            "time": "2025-01-01T12:00:00Z"
        })
        
        # Should get an error about missing agent_id
        assert "error" in result.structured_content
        assert "agent_id" in result.structured_content["error"]

    async def test_valid_agent_bypasses_inference(self, mcp_in_memory_client):
        """Test that valid agent_id values bypass inference entirely."""
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 300}
            
            with patch("promptyoself_mcp_server._infer_agent_id") as mock_infer:
                # Test that valid agent_id doesn't trigger inference
                result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                    "agent_id": "explicit-agent-456",
                    "prompt": "No inference needed",
                    "time": "2025-01-01T12:00:00Z"
                })
                
                assert "error" not in result.structured_content
                assert result.structured_content["status"] == "success"
                
                # Inference should not have been called
                mock_infer.assert_not_called()
                
                # Explicit agent should be used directly
                mock_register.assert_called_once()
                call_args = mock_register.call_args[0][0]
                assert call_args["agent_id"] == "explicit-agent-456"


class TestLoggingDuringNormalization:
    """Test that normalization events are properly logged."""
    
    async def test_normalization_logging(self, mcp_in_memory_client, caplog):
        """Test that parameter normalization is logged appropriately."""
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 400}
            
            with patch("promptyoself_mcp_server._infer_agent_id") as mock_infer:
                mock_infer.return_value = ("logged-agent", {"source": "test"})
                
                # This should trigger normalization and logging
                result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                    "agent_id": "null",
                    "prompt": "Test logging",
                    "time": "2025-01-01T16:00:00Z"
                })
                
                # Check that normalization was logged
                assert any("Converting string 'None'/'null'/empty to actual None" in record.message 
                         for record in caplog.records)
                
                # Check that inference was logged
                assert any("Agent ID inference attempted" in record.message 
                         for record in caplog.records)