import pytest
from unittest.mock import MagicMock, patch, ANY
from promptyoself import letta_api
import datetime

# The agent ID provided by the user
TEST_AGENT_ID = "agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"

class MockAgent:
    def __init__(self, id, name, created_at=None, last_updated=None):
        self.id = id
        self.name = name
        self.created_at = created_at or datetime.datetime.now()
        self.last_updated = last_updated or datetime.datetime.now()

@pytest.fixture(autouse=True)
def reset_letta_client_singleton():
    """Reset the client before and after each test."""
    letta_api._letta_client = None
    yield
    letta_api._letta_client = None

@pytest.fixture
def mock_letta():
    """Fixture to mock the Letta class."""
    with patch('promptyoself.letta_api.Letta', autospec=True) as mock_letta_class:
        yield mock_letta_class

@pytest.fixture
def mock_client(mock_letta):
    """Fixture to provide a mocked Letta client instance."""
    mock_client_instance = MagicMock()
    mock_letta.return_value = mock_client_instance
    return mock_client_instance

@pytest.mark.unit
def test_get_letta_client_initialization(mock_letta, monkeypatch):
    """Test that _get_letta_client initializes the client correctly."""
    monkeypatch.setenv("LETTA_SERVER_PASSWORD", "test_password")

    client = letta_api._get_letta_client()

    mock_letta.assert_called_once_with(token="test_password", base_url=ANY)
    assert client is not None

@pytest.mark.unit
def test_get_letta_client_singleton(mock_letta, monkeypatch):
    """Test that _get_letta_client returns a singleton instance."""
    monkeypatch.setenv("LETTA_SERVER_PASSWORD", "test_password")

    client1 = letta_api._get_letta_client()
    client2 = letta_api._get_letta_client()

    mock_letta.assert_called_once()
    assert client1 is client2

@pytest.mark.unit
def test_test_letta_connection_success(mock_client):
    """Test test_letta_connection on success."""
    mock_client.agents.list.return_value = [1, 2, 3] # Return a list of 3 agents
    result = letta_api.test_letta_connection()

    assert result["status"] == "success"
    assert "successful" in result["message"]
    assert result["agent_count"] == 3
    mock_client.agents.list.assert_called_once()

@pytest.mark.unit
def test_test_letta_connection_failure(mock_client):
    """Test test_letta_connection on failure."""
    mock_client.agents.list.side_effect = Exception("Connection Error")
    result = letta_api.test_letta_connection()

    assert result["status"] == "error"
    assert "Failed to connect" in result["message"]

@pytest.mark.unit
def test_list_available_agents_success(mock_client):
    """Test listing available agents on success."""
    mock_agent = MockAgent(id=TEST_AGENT_ID, name="Test Agent")
    mock_client.agents.list.return_value = [mock_agent]
    result = letta_api.list_available_agents()

    assert result["status"] == "success"
    assert len(result["agents"]) == 1
    assert result["agents"][0]["id"] == TEST_AGENT_ID

@pytest.mark.unit
def test_list_available_agents_failure(mock_client):
    """Test listing available agents on failure."""
    mock_client.agents.list.side_effect = Exception("API Error")
    result = letta_api.list_available_agents()

    assert result["status"] == "error"
    assert "Failed to list agents" in result["message"]

@pytest.mark.unit
def test_validate_agent_exists_success(mock_client):
    """Test validating an agent that exists."""
    mock_agent = MockAgent(id=TEST_AGENT_ID, name="Test Agent")
    mock_client.agents.list.return_value = [mock_agent]
    result = letta_api.validate_agent_exists(TEST_AGENT_ID)

    assert result["status"] == "success"
    assert result["exists"] is True

@pytest.mark.unit
def test_validate_agent_exists_not_found(mock_client):
    """Test validating an agent that does not exist."""
    mock_client.agents.list.return_value = []
    result = letta_api.validate_agent_exists("agent-does-not-exist")

    assert result["status"] == "error"
    assert result["exists"] is False
    assert "not found" in result["message"]

@pytest.mark.unit
def test_validate_agent_exists_failure(mock_client):
    """Test agent validation when the API call fails."""
    mock_client.agents.list.side_effect = Exception("API Error")
    result = letta_api.validate_agent_exists(TEST_AGENT_ID)

    assert result["status"] == "error"
    assert "Failed to validate agent" in result["message"]

@pytest.mark.unit
@patch('time.sleep', return_value=None)
def test_send_prompt_to_agent_success(mock_sleep, mock_client):
    """Test sending a prompt successfully on the first try."""
    success = letta_api.send_prompt_to_agent(TEST_AGENT_ID, "Test prompt")

    assert success is True
    mock_client.agents.messages.create.assert_called_once()

@pytest.mark.unit
@patch('time.sleep', return_value=None)
def test_send_prompt_to_agent_retry_and_succeed(mock_sleep, mock_client):
    """Test that send_prompt_to_agent retries on failure and then succeeds."""
    mock_client.agents.messages.create.side_effect = [Exception("Attempt 1 fails"), MagicMock()]
    success = letta_api.send_prompt_to_agent(TEST_AGENT_ID, "Test prompt")

    assert success is True
    assert mock_client.agents.messages.create.call_count == 2
    mock_sleep.assert_called_once()

@pytest.mark.unit
@patch('time.sleep', return_value=None)
def test_send_prompt_to_agent_all_failures(mock_sleep, mock_client):
    """Test send_prompt_to_agent when all retries fail."""
    mock_client.agents.messages.create.side_effect = Exception("Persistent failure")
    success = letta_api.send_prompt_to_agent(TEST_AGENT_ID, "Test prompt", max_retries=3)

    assert success is False
    assert mock_client.agents.messages.create.call_count == 3

@pytest.mark.unit
@patch('time.sleep', return_value=None)
def test_send_prompt_to_agent_chatml_fallback(mock_sleep, mock_client):
    """Test the ChatML bug detection and streaming fallback."""
    chatml_error = Exception("'description' blah ChatMLInnerMonologueWrapper")
    mock_client.agents.messages.create.side_effect = chatml_error

    success = letta_api.send_prompt_to_agent(TEST_AGENT_ID, "Test prompt")

    assert success is True
    mock_client.agents.messages.create.assert_called_once()
    mock_client.agents.messages.create_stream.assert_called_once()

@pytest.mark.unit
def test_send_prompt_to_agent_with_detailed_logging_success(mock_client):
    """Test the detailed logging sender on success."""
    result = letta_api.send_prompt_to_agent_with_detailed_logging(TEST_AGENT_ID, "Test")

    assert result["success"] is True
    assert len(result["attempts"]) == 1
    assert result["attempts"][0]["method"] == "standard"
    mock_client.agents.messages.create.assert_called_once()

@pytest.mark.unit
@patch('time.sleep', return_value=None)
def test_send_prompt_to_agent_with_detailed_logging_fallback(mock_sleep, mock_client):
    """Test the detailed logging sender with fallback to streaming."""
    chatml_error = Exception("'description' blah ChatMLInnerMonologueWrapper")
    mock_client.agents.messages.create.side_effect = chatml_error

    result = letta_api.send_prompt_to_agent_with_detailed_logging(TEST_AGENT_ID, "Test")

    assert result["success"] is True
    assert len(result["attempts"]) == 2
    assert result["attempts"][0]["method"] == "standard"
    assert result["attempts"][1]["method"] == "streaming"
    mock_client.agents.messages.create.assert_called_once()
    mock_client.agents.messages.create_stream.assert_called_once()
