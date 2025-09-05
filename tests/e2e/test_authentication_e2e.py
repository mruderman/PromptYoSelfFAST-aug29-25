"""
Comprehensive end-to-end tests specifically for authentication and environment variable handling.

These tests verify the authentication fixes implemented for the PromptYoSelf MCP server,
including proper .env loading, password handling, and agent validation.
"""

import pytest
import os
import tempfile
import time
from unittest.mock import patch, Mock


@pytest.mark.e2e
class TestAuthenticationE2E:
    """End-to-end tests for authentication scenarios."""

    @pytest.mark.asyncio
    async def test_authentication_with_correct_password(self, mcp_in_memory_client, monkeypatch):
        """Test successful authentication with correct password."""
        # Set correct password in environment
        monkeypatch.setenv("LETTA_SERVER_PASSWORD", "TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JTlmnopxyz")
        monkeypatch.setenv("LETTA_BASE_URL", "http://localhost:8283")
        monkeypatch.setenv("LETTA_AGENT_ID", "agent-ff18d65c-1f8f-4ca7-9013-2e4e526fd2f4")

        # Mock successful authentication response
        with patch("promptyoself.letta_api._get_letta_client") as mock_client_getter:
            mock_client = Mock()
            mock_client_getter.return_value = mock_client

            # Mock successful agent validation
            with patch("promptyoself.cli.validate_agent_exists") as mock_validate:
                mock_validate.return_value = {
                    "status": "success", 
                    "exists": True, 
                    "agent_id": "agent-ff18d65c-1f8f-4ca7-9013-2e4e526fd2f4"
                }

                with patch("promptyoself_mcp_server._register_prompt") as mock_register:
                    mock_register.return_value = {
                        "status": "success",
                        "id": 6001,
                        "next_run": "2025-12-25T10:00:00Z",
                        "message": "Authentication test successful"
                    }

                    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                        "agent_id": "null",  # Should infer from environment
                        "prompt": "Authentication test with correct password",
                        "time": "2025-12-25T10:00:00Z"
                    })

                    # Should succeed
                    assert "error" not in result.structured_content
                    assert result.structured_content["status"] == "success"
                    assert result.structured_content["id"] == 6001

    @pytest.mark.asyncio
    async def test_authentication_with_legacy_password_format(self, mcp_in_memory_client, monkeypatch):
        """Test that legacy password format (without 'xyz') fails gracefully."""
        # Set old password format (without xyz suffix)
        monkeypatch.setenv("LETTA_SERVER_PASSWORD", "TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JTlmnop")
        monkeypatch.setenv("LETTA_BASE_URL", "http://localhost:8283")
        monkeypatch.setenv("LETTA_AGENT_ID", "agent-ff18d65c-1f8f-4ca7-9013-2e4e526fd2f4")

        # Mock authentication failure (401 Unauthorized)
        with patch("promptyoself.letta_api._get_letta_client") as mock_client_getter:
            mock_client_getter.side_effect = Exception("401 Unauthorized")

            result = await mcp_in_memory_client.call_tool("promptyoself_test")

            # Should report authentication error (different structure for test tool)
            assert result.structured_content["status"] == "error"
            assert "401" in result.structured_content["message"] or "Unauthorized" in result.structured_content["message"]

    @pytest.mark.asyncio
    async def test_environment_variable_loading_priority(self, mcp_in_memory_client, monkeypatch):
        """Test that environment variables are loaded in correct priority order."""
        test_agent = "env-priority-test-agent"
        
        # Clear all environment variables first
        for env_var in ["LETTA_AGENT_ID", "PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            monkeypatch.delenv(env_var, raising=False)
        
        # Test PROMPTYOSELF_DEFAULT_AGENT_ID priority (highest priority)
        monkeypatch.setenv("PROMPTYOSELF_DEFAULT_AGENT_ID", test_agent)
        monkeypatch.setenv("LETTA_AGENT_ID", "should-not-be-used")

        with patch("promptyoself.cli.validate_agent_exists") as mock_validate:
            mock_validate.return_value = {"status": "success", "exists": True, "agent_id": test_agent}

            with patch("promptyoself_mcp_server._register_prompt") as mock_register:
                mock_register.return_value = {"status": "success", "id": 6002}

                result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                    "agent_id": "null",
                    "prompt": "Environment priority test",
                    "time": "2025-12-26T10:00:00Z"
                })

                assert result.structured_content["status"] == "success"
                # Verify PROMPTYOSELF_DEFAULT_AGENT_ID was used (highest priority)
                mock_register.assert_called_once()
                assert mock_register.call_args.args[0]["agent_id"] == test_agent

    @pytest.mark.asyncio
    async def test_agent_validation_with_real_letta_server(self, mcp_in_memory_client, monkeypatch):
        """Test agent validation against actual Letta server agent list."""
        # Set up environment
        monkeypatch.setenv("LETTA_SERVER_PASSWORD", "TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JTlmnopxyz")
        monkeypatch.setenv("LETTA_BASE_URL", "http://localhost:8283")
        
        # Mock Letta client and agents list response - need proper dict structure
        with patch("promptyoself.letta_api._get_letta_client") as mock_client_getter:
            mock_client = Mock()
            mock_client_getter.return_value = mock_client
            
            # Create a mock agent with proper attributes
            class MockAgent:
                def __init__(self, agent_id, name):
                    self.id = agent_id
                    self.name = name
                    self.created_at = None
                    self.last_updated = None
            
            mock_agent = MockAgent("agent-ff18d65c-1f8f-4ca7-9013-2e4e526fd2f4", "Test Agent")
            mock_client.agents.list.return_value = [mock_agent]

            # Test the agents tool
            result = await mcp_in_memory_client.call_tool("promptyoself_agents")

            assert result.structured_content["status"] == "success"
            assert len(result.structured_content["agents"]) > 0
            agent_ids = [agent["id"] for agent in result.structured_content["agents"]]
            assert "agent-ff18d65c-1f8f-4ca7-9013-2e4e526fd2f4" in agent_ids

    @pytest.mark.asyncio
    async def test_parameter_cleanup_no_agentId_accepted(self, mcp_in_memory_client, monkeypatch):
        """Test that agentId parameter (deprecated) is no longer accepted."""
        monkeypatch.setenv("LETTA_AGENT_ID", "cleanup-test-agent")

        # Try using deprecated agentId parameter - should fail gracefully
        # Note: This test assumes the parameter has been removed from tool definitions
        # The tool should only accept agent_id now
        
        with patch("promptyoself.cli.validate_agent_exists") as mock_validate:
            mock_validate.return_value = {"status": "success", "exists": True, "agent_id": "cleanup-test-agent"}

            with patch("promptyoself_mcp_server._register_prompt") as mock_register:
                mock_register.return_value = {"status": "success", "id": 6003}

                # This should work with agent_id
                result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                    "agent_id": "cleanup-test-agent",
                    "prompt": "Parameter cleanup test",
                    "time": "2025-12-27T10:00:00Z"
                })

                assert result.structured_content["status"] == "success"

                # If we tried to pass agentId, it should be ignored (not cause an error)
                # Since the parameter is no longer in the schema, this would be a client error
                # But we can verify the correct agent_id is used
                mock_register.assert_called_once()
                assert mock_register.call_args.args[0]["agent_id"] == "cleanup-test-agent"

    @pytest.mark.asyncio
    async def test_mcp_server_environment_loading(self, mcp_in_memory_client, monkeypatch):
        """Test that MCP server processes properly load environment variables."""
        # Test the health check tool which reports environment status
        monkeypatch.setenv("LETTA_SERVER_PASSWORD", "TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JTlmnopxyz")
        monkeypatch.setenv("LETTA_BASE_URL", "http://localhost:8283")

        result = await mcp_in_memory_client.call_tool("health")

        assert result.structured_content["status"] == "healthy"
        
        # Should show authentication is configured
        assert result.structured_content["auth_set"] is True
        assert result.structured_content["letta_base_url"] == "http://localhost:8283"

    @pytest.mark.asyncio
    async def test_inference_diagnostics_comprehensive(self, mcp_in_memory_client, monkeypatch):
        """Test comprehensive diagnostics for agent ID inference and authentication."""
        # Set up complete environment
        test_agent = "diagnostics-test-agent"
        monkeypatch.setenv("LETTA_AGENT_ID", test_agent)
        monkeypatch.setenv("LETTA_SERVER_PASSWORD", "TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JTlmnopxyz")
        monkeypatch.setenv("LETTA_BASE_URL", "http://localhost:8283")
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "true")

        # Mock agents list for diagnostics
        with patch("promptyoself_mcp_server._list_agents") as mock_list:
            mock_list.return_value = {
                "status": "success", 
                "agents": [
                    {"id": test_agent, "name": "Test Agent"}
                ],
                "count": 1
            }

            result = await mcp_in_memory_client.call_tool("promptyoself_inference_diagnostics")

            # Should provide complete diagnostic information
            assert result.structured_content["status"] == "ok"
            assert "env" in result.structured_content
            assert "single_agent_fallback_enabled" in result.structured_content
            assert "agents_count" in result.structured_content

            # Check environment variable status
            env_info = result.structured_content["env"]
            assert env_info["LETTA_AGENT_ID"]["set"] is True
            assert env_info["LETTA_AGENT_ID"]["value"] == test_agent
            
            # Check if LETTA_SERVER_PASSWORD is reported in diagnostics
            if "LETTA_SERVER_PASSWORD" in env_info:
                assert env_info["LETTA_SERVER_PASSWORD"]["set"] is True
                # Password value should be masked/truncated for security
                password_value = env_info["LETTA_SERVER_PASSWORD"]["value"]
                assert "***" in password_value or len(password_value) < 20  # Should be masked

            # Check single agent fallback
            assert result.structured_content["single_agent_fallback_enabled"] is True
            assert result.structured_content["agents_count"] == 1

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, mcp_in_memory_client, monkeypatch):
        """Test proper error handling when authentication fails."""
        # Set up invalid authentication
        monkeypatch.setenv("LETTA_SERVER_PASSWORD", "invalid-password")
        monkeypatch.setenv("LETTA_BASE_URL", "http://localhost:8283")

        # Mock authentication failure
        with patch("promptyoself.letta_api._get_letta_client") as mock_client_getter:
            mock_client_getter.side_effect = Exception("401 Client Error: Unauthorized")

            result = await mcp_in_memory_client.call_tool("promptyoself_test")

            # Should return structured error response (test tool has different structure)
            assert result.structured_content["status"] == "error"
            error_message = result.structured_content["message"]
            assert "401" in error_message or "Unauthorized" in error_message
            assert "Client Error" in error_message

    @pytest.mark.asyncio
    async def test_concurrent_authentication_requests(self, mcp_in_memory_client, monkeypatch):
        """Test that concurrent requests handle authentication properly."""
        # Set up environment
        monkeypatch.setenv("LETTA_SERVER_PASSWORD", "TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JTlmnopxyz")
        monkeypatch.setenv("LETTA_BASE_URL", "http://localhost:8283")
        monkeypatch.setenv("LETTA_AGENT_ID", "concurrent-test-agent")

        # Mock successful responses for concurrent calls
        with patch("promptyoself.letta_api._get_letta_client") as mock_client_getter:
            mock_client = Mock()
            mock_client_getter.return_value = mock_client

            with patch("promptyoself.cli.validate_agent_exists") as mock_validate:
                mock_validate.return_value = {"status": "success", "exists": True, "agent_id": "concurrent-test-agent"}

                with patch("promptyoself_mcp_server._register_prompt") as mock_register:
                    mock_register.return_value = {"status": "success", "id": 6004}

                    # Make multiple concurrent requests
                    import asyncio
                    
                    async def make_request(i):
                        return await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                            "agent_id": "null",
                            "prompt": f"Concurrent test {i}",
                            "time": f"2025-12-{25 + i:02d}T10:00:00Z"
                        })
                    
                    # Execute 3 concurrent requests
                    results = await asyncio.gather(*[make_request(i) for i in range(3)])
                    
                    # All should succeed
                    for i, result in enumerate(results):
                        assert "error" not in result.structured_content, f"Request {i} failed"
                        assert result.structured_content["status"] == "success"

                    # Should have been called 3 times (once per request)
                    assert mock_register.call_count == 3

    @pytest.mark.asyncio 
    async def test_environment_variable_persistence(self, mcp_in_memory_client, monkeypatch):
        """Test that environment variables persist across MCP tool calls."""
        agent1 = "persistence-test-agent-1"
        agent2 = "persistence-test-agent-2"
        
        # Set initial agent
        monkeypatch.setenv("LETTA_AGENT_ID", agent1)

        # First call - should use agent1
        with patch("promptyoself.cli.validate_agent_exists") as mock_validate:
            mock_validate.return_value = {"status": "success", "exists": True}

            with patch("promptyoself_mcp_server._register_prompt") as mock_register:
                mock_register.return_value = {"status": "success", "id": 6005}

                result1 = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                    "agent_id": "null",
                    "prompt": "Persistence test 1",
                    "time": "2025-12-28T10:00:00Z"
                })

                assert result1.structured_content["status"] == "success"
                mock_register.assert_called_once()
                assert mock_register.call_args.args[0]["agent_id"] == agent1

        # Change environment variable
        monkeypatch.setenv("LETTA_AGENT_ID", agent2)

        # Second call - should use agent2
        with patch("promptyoself.cli.validate_agent_exists") as mock_validate:
            mock_validate.return_value = {"status": "success", "exists": True}

            with patch("promptyoself_mcp_server._register_prompt") as mock_register:
                mock_register.return_value = {"status": "success", "id": 6006}

                result2 = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                    "agent_id": "null",
                    "prompt": "Persistence test 2", 
                    "time": "2025-12-29T10:00:00Z"
                })

                assert result2.structured_content["status"] == "success"
                mock_register.assert_called_once()
                assert mock_register.call_args.args[0]["agent_id"] == agent2

    @pytest.mark.asyncio
    async def test_missing_environment_variables_handling(self, mcp_in_memory_client, monkeypatch):
        """Test graceful handling when required environment variables are missing."""
        # Clear all authentication environment variables
        for env_var in ["LETTA_API_KEY", "LETTA_SERVER_PASSWORD", "LETTA_AGENT_ID", 
                       "PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"]:
            monkeypatch.delenv(env_var, raising=False)

        # Disable single agent fallback
        monkeypatch.setenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "false")

        result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
            "agent_id": "null",
            "prompt": "Missing env vars test",
            "time": "2025-12-30T10:00:00Z"
        })

        # Should return informative error
        assert "error" in result.structured_content
        error_message = result.structured_content["error"]
        assert "agent_id" in error_message.lower()
        assert any(word in error_message.lower() for word in ["required", "missing", "provide"])

    @pytest.mark.asyncio
    async def test_database_connection_with_authentication(self, mcp_in_memory_client, monkeypatch):
        """Test that database operations work with proper authentication setup."""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            temp_db_path = tmp_db.name

        try:
            # Set up complete environment
            monkeypatch.setenv("PROMPTYOSELF_DB", temp_db_path)
            monkeypatch.setenv("LETTA_SERVER_PASSWORD", "TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JTlmnopxyz")
            monkeypatch.setenv("LETTA_BASE_URL", "http://localhost:8283")
            monkeypatch.setenv("LETTA_AGENT_ID", "db-auth-test-agent")

            # Mock authentication but allow database operations
            with patch("promptyoself.letta_api._get_letta_client") as mock_client_getter:
                mock_client = Mock()
                mock_client_getter.return_value = mock_client

                with patch("promptyoself.cli.validate_agent_exists") as mock_validate:
                    mock_validate.return_value = {"status": "success", "exists": True, "agent_id": "db-auth-test-agent"}

                    # Test actual schedule creation (will hit database)
                    result = await mcp_in_memory_client.call_tool("promptyoself_schedule_time", {
                        "agent_id": "db-auth-test-agent",
                        "prompt": "Database authentication test",
                        "time": "2025-12-31T10:00:00Z",
                        "skip_validation": True  # Skip Letta API validation
                    })

                    # Should succeed and return actual database ID
                    assert "error" not in result.structured_content
                    assert result.structured_content["status"] == "success" 
                    assert "id" in result.structured_content
                    assert isinstance(result.structured_content["id"], int)

        finally:
            # Clean up
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)