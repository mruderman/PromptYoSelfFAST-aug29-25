import mock
import pytest
from sqlalchemy import inspect
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from promptyoself.db import initialize_db, add_schedule, list_schedules, get_schedule, update_schedule, cancel_schedule, get_due_schedules, cleanup_old_schedules, get_database_stats

@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("LETTA_API_KEY", "test-api-key")

@mock.patch("promptyoself.db.SessionLocal")
@mock.patch("promptyoself.db.Base.metadata.create_all")
def test_initialize_db(mock_session_local, mock_create_all, mock_env_vars):
    initialize_db()
    mock_create_all.assert_called_once()
    mock_session_local.assert_called_once()

@mock.patch("promptyoself.db.SessionLocal")
@mock.patch("promptyoself.db.UnifiedReminder")
def test_add_schedule(mock_session_local, mock_unified_reminder, mock_env_vars):
    mock_session = mock_session_local.return_value
    mock_session.add.return_value = None
    mock_session.commit.return_value = None
    
    result = add_schedule("agent-123", "Test prompt", "cron", "* * * * *", datetime(2023, 1, 1))
    assert result is not None
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()

@mock.patch("promptyoself.db.SessionLocal")
@mock.patch("promptyoself.db.UnifiedReminder")
def test_list_schedules(mock_session_local, mock_unified_reminder, mock_env_vars):
    mock_session = mock_session_local.return_value
    mock_query = mock_session.query.return_value
    mock_query.all.return_value = [{"id": 1, "agent_id": "agent-123", "message": "Test"}]
    
    result = list_schedules()
    assert len(result) == 1
    mock_session.query.assert_called_once()

@mock.patch("promptyoself.db.SessionLocal")
@mock.patch("promptyoself.db.UnifiedReminder")
def test_get_schedule(mock_session_local, mock_unified_reminder, mock_env_vars):
    mock_session = mock_session_local.return_value
    mock_query = mock_session.query.return_value
    mock_query.first.return_value = {"id": 1, "agent_id": "agent-123", "message": "Test"}
    
    result = get_schedule(1)
    assert result["id"] == 1
    mock_query.filter.assert_called_once()

@mock.patch("promptyoself.db.SessionLocal")
@mock.patch("promptyoself.db.UnifiedReminder")
def test_update_schedule(mock_session_local, mock_unified_reminder, mock_env_vars):
    mock_session = mock_session_local.return_value
    mock_session.commit.return_value = None
    
    result = update_schedule(1, message="Updated prompt")
    assert result is True
    mock_session.commit.assert_called_once()

@mock.patch("promptyoself.db.SessionLocal")
@mock.patch("promptyoself.db.UnifiedReminder")
def test_cancel_schedule(mock_session_local, mock_unified_reminder, mock_env_vars):
    mock_session = mock_session_local.return_value
    mock_session.commit.return_value = None
    
    result = cancel_schedule(1)
    assert result is True
    mock_session.commit.assert_called_once()

@mock.patch("promptyoself.db.SessionLocal")
@mock.patch("promptyoself.db.UnifiedReminder")
def test_get_due_schedules(mock_session_local, mock_unified_reminder, mock_env_vars):
    mock_session = mock_session_local.return_value
    mock_query = mock_session.query.return_value
    mock_query.all.return_value = [{"id": 1, "agent_id": "agent-123", "message": "Test"}]
    
    result = get_due_schedules()
    assert len(result) == 1
    mock_query.filter.assert_called_once()

@mock.patch("promptyoself.db.SessionLocal")
@mock.patch("promptyoself.db.UnifiedReminder")
def test_cleanup_old_schedules(mock_session_local, mock_unified_reminder, mock_env_vars):
    mock_session = mock_session_local.return_value
    mock_query = mock_session.query.return_value
    mock_query.delete.return_value = 5
    
    result = cleanup_old_schedules(days=30)
    assert result == 5
    mock_query.filter.assert_called_once()

@mock.patch("promptyoself.db.inspect")
def test_get_database_stats(mock_inspect, mock_env_vars):
    mock_inspector = mock_inspect.return_value
    mock_inspector.get_table_names.return_value = ["unified_reminders", "schedules"]
    mock_inspector.get_columns.return_value = [{"name": "id"}, {"name": "message"}]
    
    result = get_database_stats()
    assert "tables" in result
    assert len(result["tables"]) == 2

@mock.patch("promptyoself.db.SessionLocal")
@mock.patch("promptyoself.db.UnifiedReminder")
def test_add_schedule_error(mock_session_local, mock_unified_reminder, mock_env_vars):
    mock_session = mock_session_local.return_value
    mock_session.add.side_effect = SQLAlchemyError("Database error")
    
    with pytest.raises(SQLAlchemyError):
        add_schedule("agent-123", "Test prompt", "cron", "* * * * *", datetime(2023, 1, 1))

@mock.patch("promptyoself.db.SessionLocal")
@mock.patch("promptyoself.db.UnifiedReminder")
def test_list_schedules_error(mock_session_local, mock_unified_reminder, mock_env_vars):
    mock_session = mock_session_local.return_value
    mock_session.query.side_effect = SQLAlchemyError("Database error")
    
    with pytest.raises(SQLAlchemyError):
        list_schedules()

@mock.patch("promptyoself.db.SessionLocal")
@mock.patch("promptyoself.db.UnifiedReminder")
def test_get_due_schedules_error(mock_session_local, mock_unified_reminder, mock_env_vars):
    mock_session = mock_session_local.return_value
    mock_session.query.side_effect = SQLAlchemyError("Database error")
    
    with pytest.raises(SQLAlchemyError):
        get_due_schedules()

@mock.patch("promptyoself.db.SessionLocal")
@mock.patch("promptyoself.db.UnifiedReminder")
def test_cleanup_old_schedules_error(mock_session_local, mock_unified_reminder, mock_env_vars):
    mock_session = mock_session_local.return_value
    mock_session.query.side_effect = SQLAlchemyError("Database error")
    
    with pytest.raises(SQLAlchemyError):
        cleanup_old_schedules(days=30)