"""
Integration tests for agent_id handling in MCP tools.

This module tests the complete integration of parameter normalization,
agent_id inference, and MCP tool functionality for real-world scenarios.
"""

import pytest
import os
from unittest.mock import patch, Mock


TEST_AGENT = "agent-integration-test-12345"


class TestMCPAgentIdScenarios:
    """Test real-world MCP client scenarios for agent_id handling."""
    
    async def test_mcp_client_sends_null_string_scenario(self, mcp_in_memory_client, monkeypatch):
        """Test the exact failing scenario: MCP client sends agent_id: 'null'."""
        # Set up environment so inference can succeed
        monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
        
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 1001, "next_run": "2025-01-01T10:00:00Z"}
            
            # This is the exact scenario that was failing
            result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                "agent_id": "null",  # MCP client sends string "null" 
                "prompt": "MCP client null test",
                "time": "2025-12-25T10:00:00Z"
            })
            
            # Should succeed with fallback to environment
            assert "error" not in result.structured_content
            assert result.structured_content["status"] == "success"
            assert result.structured_content["id"] == 1001
            
            # Should have used the environment agent
            mock_register.assert_called_once()
            call_args = mock_register.call_args.args[0]
            assert call_args["agent_id"] == TEST_AGENT
    
    async def test_mcp_client_sends_none_string_scenario(self, mcp_in_memory_client):
        """Test MCP client sending agent_id: 'None' (Python None as string)."""
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 1002}
            
            with patch("promptyoself_mcp_server._infer_agent_id") as mock_infer:
                mock_infer.return_value = ("inferred-from-none", {"source": "context"})
                
                result = await mcp_in_memory_client.call_tool("promptyoself_schedule_cron", {
                    "agent_id": "None",  # Python None as string
                    "prompt": "MCP client None test",
                    "cron": "0 9 * * *"
                })
                
                assert "error" not in result.structured_content
                assert result.structured_content["status"] == "success"
                
                # Should have triggered inference
                mock_infer.assert_called_once()
                mock_register.assert_called_once()
                call_args = mock_register.call_args.args[0]
                assert call_args["agent_id"] == "inferred-from-none"
    
    async def test_mcp_client_sends_empty_string_scenario(self, mcp_in_memory_client, monkeypatch):
        """Test MCP client sending agent_id: '' (empty string)."""
        # Use environment fallback
        monkeypatch.setenv("PROMPTYOSELF_DEFAULT_AGENT_ID", TEST_AGENT)
        
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 1003}
            
            result = await mcp_in_memory_client.call_tool("promptyoself_schedule_every", {
                "agent_id": "",  # Empty string
                "prompt": "MCP client empty test",
                "every": "30m"
            })
            
            assert "error" not in result.structured_content
            assert result.structured_content["status"] == "success"
            
            # Should have used environment variable
            mock_register.assert_called_once()
            call_args = mock_register.call_args.args[0]
            assert call_args["agent_id"] == TEST_AGENT
    
    async def test_mcp_client_omits_agent_id_scenario(self, mcp_in_memory_client, monkeypatch):
        """Test MCP client omitting agent_id entirely (gets None by default)."""
        monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
        
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 1004}
            
            # Don't provide agent_id at all
            result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                "prompt": "MCP client omitted agent_id test",
                "time": "2025-01-02T14:00:00Z"
            })
            
            assert "error" not in result.structured_content
            assert result.structured_content["status"] == "success"
            
            # Should have used environment fallback
            mock_register.assert_called_once()
            call_args = mock_register.call_args.args[0]
            assert call_args["agent_id"] == TEST_AGENT
    
    async def test_mcp_client_whitespace_variations(self, mcp_in_memory_client, monkeypatch):
        """Test various whitespace-only agent_id values."""
        monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
        
        whitespace_variants = [
            "   ",      # spaces
            "\t\t",     # tabs  
            "\n\n",     # newlines
            " \t \n ",  # mixed whitespace
        ]
        
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 1005}
            
            for i, whitespace_agent in enumerate(whitespace_variants):
                mock_register.reset_mock()
                
                result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                    "agent_id": whitespace_agent,
                    "prompt": f"Whitespace test {i}",
                    "time": "2025-01-03T10:00:00Z"
                })
                
                # Should succeed with environment fallback
                assert "error" not in result.structured_content, f"Failed for whitespace: {repr(whitespace_agent)}"
                assert result.structured_content["status"] == "success"
                
                # Should have used environment agent
                mock_register.assert_called_once()
                call_args = mock_register.call_args.args[0]
                assert call_args["agent_id"] == TEST_AGENT
    
    async def test_mcp_client_mixed_case_null_variants(self, mcp_in_memory_client, monkeypatch):
        """Test different case variations of null/none strings."""
        monkeypatch.setenv("LETTA_AGENT_ID", TEST_AGENT)
        
        null_variants = [
            "null",
            "NULL", 
            "Null",
            "none",
            "NONE",
            "None",
        ]
        
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 1006}
            
            for i, null_variant in enumerate(null_variants):
                mock_register.reset_mock()
                
                result = await mcp_in_memory_client.call_tool("promptyoself_schedule_cron", {
                    "agent_id": null_variant,
                    "prompt": f"Null variant test {i}",
                    "cron": "0 */6 * * *"
                })
                
                # Should succeed with environment fallback
                assert "error" not in result.structured_content, f"Failed for null variant: {null_variant}"
                assert result.structured_content["status"] == "success"
                
                # Should have used environment agent
                mock_register.assert_called_once()
                call_args = mock_register.call_args.args[0]
                assert call_args["agent_id"] == TEST_AGENT


class TestMCPClientWithSetDefault:
    """Test MCP client scenarios using set_default_agent tool."""
    
    async def test_set_default_then_use_null_agent_id(self, mcp_in_memory_client):
        """Test setting default agent, then using null agent_id in scheduling."""
        default_agent = "set-default-test-agent"
        
        # First set the default
        set_result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": default_agent
        })
        assert set_result.structured_content["status"] == "success"
        
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 2001}
            
            # Now use "null" - should fall back to the set default
            result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                "agent_id": "null",
                "prompt": "Using null with set default",
                "time": "2025-01-04T09:00:00Z"
            })
            
            assert "error" not in result.structured_content
            assert result.structured_content["status"] == "success"
            
            # Should have used the default agent we set
            mock_register.assert_called_once()
            call_args = mock_register.call_args.args[0]
            assert call_args["agent_id"] == default_agent
    
    async def test_set_default_workflow_all_tools(self, mcp_in_memory_client):
        """Test the complete workflow: set default, then use all scheduling tools with null."""
        default_agent = "workflow-test-agent"
        
        # Set default agent
        set_result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": default_agent
        })
        assert set_result.structured_content["status"] == "success"
        
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            # Test all scheduling tools with "null" agent_id
            tools_and_params = [
                ("promptyoself_schedule_time", {"time": "2025-01-05T10:00:00Z"}),
                ("promptyoself_schedule_cron", {"cron": "0 12 * * *"}),
                ("promptyoself_schedule_every", {"every": "2h"}),
            ]
            
            for tool_name, extra_params in tools_and_params:
                mock_register.reset_mock()
                mock_register.return_value = {"status": "success", "id": 2100}
                
                params = {
                    "agent_id": "null",  # Should use default
                    "prompt": f"Test {tool_name} with default",
                    **extra_params
                }
                
                result = await mcp_in_memory_client.call_tool(tool_name, params)
                
                assert "error" not in result.structured_content, f"Failed for {tool_name}"
                assert result.structured_content["status"] == "success"
                
                # Should have used the default agent
                mock_register.assert_called_once()
                call_args = mock_register.call_args.args[0]
                assert call_args["agent_id"] == default_agent, f"Wrong agent for {tool_name}"
    
    async def test_set_default_then_explicit_agent_override(self, mcp_in_memory_client):
        """Test that explicit agent_id overrides set default."""
        default_agent = "default-override-agent"
        explicit_agent = "explicit-override-agent"
        
        # Set default
        set_result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": default_agent
        })
        assert set_result.structured_content["status"] == "success"
        
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 2200}
            
            # Use explicit agent (should override default)
            result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                "agent_id": explicit_agent,
                "prompt": "Explicit override test",
                "time": "2025-01-06T11:00:00Z"
            })
            
            assert "error" not in result.structured_content
            assert result.structured_content["status"] == "success"
            
            # Should have used explicit agent, not default
            mock_register.assert_called_once()
            call_args = mock_register.call_args.args[0]
            assert call_args["agent_id"] == explicit_agent
            assert call_args["agent_id"] != default_agent


class TestMCPClientErrorScenarios:
    """Test MCP client scenarios that should result in errors."""
    
    async def test_null_agent_id_no_fallback_available(self, mcp_in_memory_client, monkeypatch):
        """Test null agent_id when no fallback mechanisms are available."""
        # Clear all environment variables
        monkeypatch.delenv("PROMPTYOSELF_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.delenv("LETTA_AGENT_ID", raising=False)
        monkeypatch.delenv("LETTA_DEFAULT_AGENT_ID", raising=False)
        
        # Disable single agent fallback
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "false")
        
        result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
            "agent_id": "null",
            "prompt": "Should fail - no fallback",
            "time": "2025-01-07T10:00:00Z"
        })
        
        # Should get an error about missing agent_id
        assert "error" in result.structured_content
        assert "agent_id" in result.structured_content["error"].lower()
    
    async def test_empty_agent_id_no_fallback_available(self, mcp_in_memory_client, monkeypatch):
        """Test empty string agent_id when no fallback mechanisms are available."""
        # Clear all environment variables and disable fallback
        monkeypatch.delenv("PROMPTYOSELF_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.delenv("LETTA_AGENT_ID", raising=False) 
        monkeypatch.delenv("LETTA_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "false")
        
        result = await mcp_in_memory_client.call_tool("promptyoself_schedule_cron", {
            "agent_id": "",
            "prompt": "Should fail - empty with no fallback",
            "cron": "0 8 * * *"
        })
        
        # Should get an error
        assert "error" in result.structured_content
        assert "agent_id" in result.structured_content["error"].lower()
    
    async def test_inference_failure_chain(self, mcp_in_memory_client, monkeypatch):
        """Test the complete inference failure chain."""
        # Set up complete inference failure
        monkeypatch.delenv("PROMPTYOSELF_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.delenv("LETTA_AGENT_ID", raising=False)
        monkeypatch.delenv("LETTA_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "false")
        
        # Mock Context to ensure no context metadata
        with patch("promptyoself_mcp_server._infer_agent_id") as mock_infer:
            mock_infer.return_value = (None, {"source": None, "attempted": True})
            
            result = await mcp_in_memory_client.call_tool("promptyoself_schedule_every", {
                "agent_id": "None",  # Will be normalized to None
                "prompt": "Complete inference failure test",
                "every": "1h"
            })
            
            # Should fail gracefully
            assert "error" in result.structured_content
            assert "agent_id" in result.structured_content["error"].lower()
            
            # Should have attempted inference (called twice: once in tool, once in promptyoself_register)
            assert mock_infer.call_count == 2


class TestMCPClientContextualInference:
    """Test agent_id inference from MCP request context."""
    
    async def test_context_metadata_inference(self, mcp_in_memory_client):
        """Test agent_id inference from request context metadata."""
        context_agent = "context-metadata-agent"
        
        # Mock the context to include agent_id in metadata
        with patch("promptyoself_mcp_server._infer_agent_id") as mock_infer:
            mock_infer.return_value = (context_agent, {"source": "context.metadata", "key": "agent_id"})
            
            with patch("promptyoself_mcp_server._register_prompt") as mock_register:
                mock_register.return_value = {"status": "success", "id": 3001}
                
                result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                    "agent_id": "null",  # Should be normalized and inference triggered
                    "prompt": "Context inference test",
                    "time": "2025-01-08T13:00:00Z"
                })
                
                assert "error" not in result.structured_content
                assert result.structured_content["status"] == "success"
                
                # Should have used context-inferred agent
                mock_register.assert_called_once()
                call_args = mock_register.call_args.args[0]
                assert call_args["agent_id"] == context_agent
    
    async def test_single_agent_fallback_success(self, mcp_in_memory_client, monkeypatch):
        """Test successful single-agent fallback when enabled."""
        # Clear env vars and enable single agent fallback
        monkeypatch.delenv("PROMPTYOSELF_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.delenv("LETTA_AGENT_ID", raising=False)
        monkeypatch.delenv("LETTA_DEFAULT_AGENT_ID", raising=False)
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "true")
        
        fallback_agent = "single-agent-fallback"
        
        with patch("promptyoself_mcp_server._infer_agent_id") as mock_infer:
            mock_infer.return_value = (fallback_agent, {"source": "single-agent-fallback"})
            
            with patch("promptyoself_mcp_server._register_prompt") as mock_register:
                mock_register.return_value = {"status": "success", "id": 3002}
                
                result = await mcp_in_memory_client.call_tool("promptyoself_schedule_cron", {
                    "agent_id": "null",
                    "prompt": "Single agent fallback test",
                    "cron": "0 14 * * *"
                })
                
                assert "error" not in result.structured_content
                assert result.structured_content["status"] == "success"
                
                # Should have used fallback agent
                mock_register.assert_called_once()
                call_args = mock_register.call_args.args[0]
                assert call_args["agent_id"] == fallback_agent


class TestMCPClientRealWorldWorkflows:
    """Test complete real-world MCP client workflows."""
    
    async def test_complete_onboarding_workflow(self, mcp_in_memory_client):
        """Test complete MCP client onboarding: test connection, list agents, set default, schedule."""
        test_agent = "onboarding-workflow-agent"
        
        # Step 1: Test connection
        with patch("promptyoself_mcp_server._test_connection") as mock_test:
            mock_test.return_value = {"status": "success", "message": "Connected"}
            
            test_result = await mcp_in_memory_client.call_tool("promptyoself_test")
            assert test_result.structured_content["status"] == "success"
        
        # Step 2: List agents
        with patch("promptyoself_mcp_server._list_agents") as mock_list_agents:
            mock_list_agents.return_value = {"status": "success", "agents": [{"id": test_agent}]}
            
            agents_result = await mcp_in_memory_client.call_tool("promptyoself_agents")
            assert agents_result.structured_content["status"] == "success"
            assert len(agents_result.structured_content["agents"]) == 1
        
        # Step 3: Set default agent
        default_result = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": test_agent
        })
        assert default_result.structured_content["status"] == "success"
        
        # Step 4: Schedule with null agent_id (should use default)
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 4001}
            
            schedule_result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                "agent_id": "null",  # Should use the set default
                "prompt": "Onboarding workflow complete",
                "time": "2025-01-09T16:00:00Z"
            })
            
            assert "error" not in schedule_result.structured_content
            assert schedule_result.structured_content["status"] == "success"
            
            # Should have used the default agent we set
            mock_register.assert_called_once()
            call_args = mock_register.call_args.args[0]
            assert call_args["agent_id"] == test_agent
    
    async def test_multi_client_simulation(self, mcp_in_memory_client):
        """Test behavior that simulates multiple MCP clients with different defaults."""
        client1_agent = "client-1-agent"
        client2_agent = "client-2-agent"
        
        # Simulate Client 1: Set its default agent
        result1 = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
            "agent_id": client1_agent
        })
        assert result1.structured_content["status"] == "success"
        
        with patch("promptyoself_mcp_server._register_prompt") as mock_register:
            mock_register.return_value = {"status": "success", "id": 4100}
            
            # Client 1 schedules with null (should use its default)
            schedule1 = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                "agent_id": "null",
                "prompt": "Client 1 schedule",
                "time": "2025-01-10T09:00:00Z"
            })
            assert schedule1.structured_content["status"] == "success"
            
            # Verify client 1's agent was used
            mock_register.assert_called_once()
            assert mock_register.call_args.args[0]["agent_id"] == client1_agent
            
            # Simulate Client 2: Change the default (overwrites client 1's)
            result2 = await mcp_in_memory_client.call_tool("promptyoself_set_default_agent", {
                "agent_id": client2_agent
            })
            assert result2.structured_content["status"] == "success"
            
            mock_register.reset_mock()
            mock_register.return_value = {"status": "success", "id": 4101}
            
            # Client 2 schedules with null (should use its default)
            schedule2 = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                "agent_id": "null",
                "prompt": "Client 2 schedule",
                "time": "2025-01-10T10:00:00Z"
            })
            assert schedule2.structured_content["status"] == "success"
            
            # Verify client 2's agent was used (overwrote client 1's)
            mock_register.assert_called_once()
            assert mock_register.call_args.args[0]["agent_id"] == client2_agent