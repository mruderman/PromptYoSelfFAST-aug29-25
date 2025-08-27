import mock
import pytest
from unittest.mock import patch
from promptyoself.letta_api import (
    _get_letta_client,
    send_prompt_to_agent,
    test_letta_connection,
    list_available_agents,
    validate_agent_exists,
    _try_streaming_fallback,
    send_prompt_to_agent_streaming_only,
    send_prompt_to_agent_with_detailed_logging,
)
from letta_client import Letta

@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("LETTA_API_KEY", "test-api-key")

def test_get_letta_client_valid_api_key(mock_env_vars):
    with patch("os.getenv") as mock_getenv:
        mock_getenv.side_effect = lambda var: {
            "LETTA_API_KEY": "test-api-key",
            "LETTA_SERVER_PASSWORD": None
        }.get(var)
        
        client = _get_letta_client()
        assert isinstance(client, Letta)
        assert client.token == "test-api-key"

def test_get_letta_client_password_auth(mock_env_vars):
    with patch("os.getenv") as mock_getenv:
        mock_getenv.side_effect = lambda var: {
            "LETTA_API_KEY": None,
            "LETTA_SERVER_PASSWORD": "test-password"
        }.get(var)
        
        client = _get_letta_client()
        assert isinstance(client, Letta)
        assert client.token == "test-password"

def test_get_letta_client_dummy_token(mock_env_vars):
    with patch("os.getenv") as mock_getenv:
        mock_getenv.side_effect = lambda var: None
        
        client = _get_letta_client()
        assert isinstance(client, Letta)
        assert client.base_url == "http://localhost:8283"

@mock.patch("promptyoself.letta_api.Letta")
def test_send_prompt_to_agent_success(mock_letta_class, mock_env_vars):
    mock_client = mock_letta_class.return_value
    mock_response = mock.Mock()
    mock_response.status = "success"
    mock_client.tools.upsert.return_value = mock_response
    
    result = send_prompt_to_agent("agent-123", "Test prompt")
    assert result["status"] == "success"
    mock_client.tools.upsert.assert_called_once()

@mock.patch("promptyoself.letta_api.Letta")
def test_send_prompt_to_agent_retry(mock_letta_class, mock_env_vars):
    mock_client = mock_letta_class.return_value
    mock_client.tools.upsert.side_effect = [
        Exception("Network timeout"), 
        Exception("Network timeout"),
        mock.Mock(status="success")
    ]
    
    result = send_prompt_to_agent("agent-123", "Test prompt")
    assert result["status"] == "success"
    assert mock_client.tools.upsert.call_count == 3

@mock.patch("promptyoself.letta_api.Letta")
def test_send_prompt_to_agent_failure(mock_letta_class, mock_env_vars):
    mock_client = mock_letta_class.return_value
    mock_client.tools.upsert.side_effect = Exception("Server down")
    
    result = send_prompt_to_agent("agent-123", "Test prompt")
    assert result["error"] is not None
    assert "Server down" in result["error"]

@mock.patch("promptyoself.letta_api.Letta")
def test_try_streaming_fallback_success(mock_letta_class, mock_env_vars):
    mock_client = mock_letta_class.return_value
    mock_response = mock.Mock()
    mock_response.status = "success"
    mock_client.messages.stream.return_value = mock_response
    
    result = _try_streaming_fallback("agent-123", "Test prompt")
    assert result["status"] == "success"
    mock_client.messages.stream.assert_called_once()

@mock.patch("promptyoself.letta_api.Letta")
def test_send_prompt_to_agent_streaming_only(mock_letta_class, mock_env_vars):
    mock_client = mock_letta_class.return_value
    mock_response = mock.Mock()
    mock_response.status = "success"
    mock_client.messages.stream.return_value = mock_response
    
    result = send_prompt_to_agent_streaming_only("agent-123", "Test prompt")
    assert result["status"] == "success"
    mock_client.messages.stream.assert_called_once()

@mock.patch("promptyoself.letta_api.Letta")
def test_send_prompt_to_agent_with_detailed_logging(mock_letta_class, mock_env_vars):
    mock_client = mock_letta_class.return_value
    mock_response = mock.Mock()
    mock_response.status = "success"
    mock_response.id = "test-tool-id"
    mock_client.tools.upsert.return_value = mock_response
    
    result = send_prompt_to_agent_with_detailed_logging("agent-123", "Test prompt", "Test name", "Test description")
    assert result["status"] == "success"
    assert "test-tool-id" in result["tool_id"]
    mock_client.tools.upsert.assert_called_once()

@mock.patch("promptyoself.letta_api.Letta")
def test_test_letta_connection_success(mock_letta_class, mock_env_vars):
    mock_client = mock_letta_class.return_value
    result = test_letta_connection()
    assert result["connected"] is True
    mock_client.connect.assert_called_once()

@mock.patch("promptyoself.letta_api.Letta")
def test_test_letta_connection_failure(mock_letta_class, mock_env_vars):
    mock_client = mock_letta_class.return_value
    mock_client.connect.side_effect = Exception("Connection refused")
    
    result = test_letta_connection()
    assert result["error"] is not None
    assert "Connection refused" in result["error"]

@mock.patch("promptyoself.letta_api.Letta")
def test_list_available_agents_success(mock_letta_class, mock_env_vars):
    mock_client = mock_letta_class.return_value
    mock_agent1 = mock.Mock(id="agent-1", name="Agent 1")
    mock_agent2 = mock.Mock(id="agent-2", name="Agent 2")
    mock_client.agents.list.return_value = [mock_agent1, mock_agent2]
    
    result = list_available_agents()
    assert len(result) == 2
    assert result[0]["id"] == "agent-1"
    assert result[1]["name"] == "Agent 2"

@mock.patch("promptyoself.letta_api.Letta")
def test_validate_agent_exists_true(mock_letta_class, mock_env_vars):
    mock_client = mock_letta_class.return_value
    mock_agent = mock.Mock(id="valid-agent")
    mock_client.agents.retrieve.return_value = mock_agent
    
    result = validate_agent_exists("valid-agent")
    assert result is True

@mock.patch("promptyoself.letta_api.Letta")
def test_validate_agent_exists_false(mock_letta_class, mock_env_vars):
    mock_client = mock_letta_class.return_value
    mock_client.agents.retrieve.side_effect = Exception("Agent not found")
    
    result = validate_agent_exists("invalid-agent")
    assert result is False