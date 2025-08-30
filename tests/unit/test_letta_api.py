import pytest
import os
from promptyoself import letta_api

# The agent ID provided by the user
TEST_AGENT_ID = "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"

@pytest.fixture(scope="function")
def live_letta_server(monkeypatch):
    """Fixture to configure the Letta client for a live server."""
    letta_password = os.environ.get("LETTA_SERVER_PASSWORD")
    if not letta_password:
        pytest.skip("Environment variable LETTA_SERVER_PASSWORD not set. Skipping tests that require live Letta server.")
    monkeypatch.setenv("LETTA_SERVER_PASSWORD", letta_password)
    # Reset the client to ensure it picks up the new env vars
    letta_api._letta_client = None
    yield
    # Clean up
    letta_api._letta_client = None

@pytest.mark.usefixtures("live_letta_server")
def test_test_letta_connection():
    result = letta_api.test_letta_connection()
    assert result["status"] == "success"
    assert "Connection to Letta server successful" in result["message"]

@pytest.mark.usefixtures("live_letta_server")
def test_list_available_agents():
    result = letta_api.list_available_agents()
    assert result["status"] == "success"
    # Check that the test agent is in the list
    assert any(agent["id"] == TEST_AGENT_ID for agent in result["agents"])

@pytest.mark.usefixtures("live_letta_server")
def test_validate_agent_exists_success():
    result = letta_api.validate_agent_exists(TEST_AGENT_ID)
    assert result["status"] == "success"
    assert result["exists"] is True

@pytest.mark.usefixtures("live_letta_server")
def test_validate_agent_exists_failure():
    result = letta_api.validate_agent_exists("agent-does-not-exist")
    assert result["status"] == "error"
    assert result["exists"] is False

@pytest.mark.usefixtures("live_letta_server")
def test_send_prompt_to_agent():
    success = letta_api.send_prompt_to_agent(TEST_AGENT_ID, "Hello from the test suite!")
    assert success is True

@pytest.mark.usefixtures("live_letta_server")
def test_send_prompt_to_agent_streaming_only():
    success = letta_api.send_prompt_to_agent_streaming_only(TEST_AGENT_ID, "Hello from the streaming test!")
    assert success is True

@pytest.mark.usefixtures("live_letta_server")
def test_send_prompt_to_agent_with_detailed_logging():
    result = letta_api.send_prompt_to_agent_with_detailed_logging(TEST_AGENT_ID, "Hello from the detailed logging test!")
    assert result["success"] is True
    assert len(result["attempts"]) > 0
