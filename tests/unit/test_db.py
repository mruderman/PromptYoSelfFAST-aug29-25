import pytest
import os
from datetime import datetime, timedelta
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from promptyoself import db
from promptyoself.db import UnifiedReminder, PromptSchedule, CLIReminderAdapter

# Fixture for a clean, in-memory database for each test
@pytest.fixture
def session():
    # Use in-memory SQLite database for tests
    os.environ["PROMPTYOSELF_DB"] = ":memory:"
    # Reset any existing database connection and create a new engine
    db.reset_db_connection()
    # Initialize the database with the new engine
    db.initialize_db()
    # Get a session from the new factory
    db_session = db.get_session()
    yield db_session
    db_session.close()
    # Clean up the environment variable
    del os.environ["PROMPTYOSELF_DB"]

def test_initialize_db(session: Session):
    # Check if the tables were created
    inspector = inspect(db.get_engine())
    assert "unified_reminders" in inspector.get_table_names()
    assert "schedules" in inspector.get_table_names()

def test_add_schedule(session: Session):
    # Add a new schedule
    next_run_time = datetime.utcnow() + timedelta(hours=1)
    schedule_id = db.add_schedule(
        agent_id="test_agent",
        prompt_text="Test prompt",
        schedule_type="once",
        schedule_value="2025-01-01T12:00:00",
        next_run=next_run_time,
        max_repetitions=1
    )
    assert isinstance(schedule_id, int)

    # Verify the schedule was added
    reminder = session.query(UnifiedReminder).filter_by(id=schedule_id).one()
    assert reminder.agent_id == "test_agent"
    assert reminder.message == "Test prompt"
    assert reminder.schedule_type == "once"
    assert reminder.next_run == next_run_time
    assert reminder.max_repetitions == 1

def test_list_schedules(session: Session):
    # Add some schedules
    db.add_schedule("agent1", "prompt1", "once", "2025-01-01T12:00:00", datetime.utcnow())
    db.add_schedule("agent1", "prompt2", "cron", "* * * * *", datetime.utcnow())
    db.add_schedule("agent2", "prompt3", "interval", "1h", datetime.utcnow())
    
    # List all schedules
    schedules = db.list_schedules()
    assert len(schedules) == 3
    
    # List schedules for a specific agent
    agent1_schedules = db.list_schedules(agent_id="agent1")
    assert len(agent1_schedules) == 2
    
    # List only active schedules (default)
    active_schedules = db.list_schedules(active_only=True)
    assert len(active_schedules) == 3

def test_get_schedule(session: Session):
    schedule_id = db.add_schedule("agent1", "prompt1", "once", "2025-01-01T12:00:00", datetime.utcnow())
    
    schedule = db.get_schedule(schedule_id)
    assert schedule is not None
    assert schedule["id"] == schedule_id
    assert schedule["agent_id"] == "agent1"
    
    # Test getting a non-existent schedule
    non_existent_schedule = db.get_schedule(999)
    assert non_existent_schedule is None

def test_update_schedule(session: Session):
    schedule_id = db.add_schedule("agent1", "prompt1", "once", "2025-01-01T12:00:00", datetime.utcnow())
    
    # Update the prompt text
    updated = db.update_schedule(schedule_id, prompt_text="Updated prompt")
    assert updated is True
    
    schedule = db.get_schedule(schedule_id)
    assert schedule["prompt_text"] == "Updated prompt"

def test_cancel_schedule(session: Session):
    schedule_id = db.add_schedule("agent1", "prompt1", "once", "2025-01-01T12:00:00", datetime.utcnow())
    
    # Cancel the schedule
    cancelled = db.cancel_schedule(schedule_id)
    assert cancelled is True
    
    schedule = db.get_schedule(schedule_id)
    assert schedule["active"] is False

def test_get_due_schedules(session: Session):
    # Add a due schedule
    db.add_schedule("agent1", "due_prompt", "once", "2025-01-01T12:00:00", datetime.utcnow() - timedelta(minutes=1))
    # Add a future schedule
    db.add_schedule("agent2", "future_prompt", "once", "2025-01-01T12:00:00", datetime.utcnow() + timedelta(minutes=1))
    
    due_schedules = db.get_due_schedules()
    assert len(due_schedules) == 1
    assert due_schedules[0].agent_id == "agent1"

def test_cleanup_old_schedules(session: Session):
    # Add an old, inactive schedule
    old_inactive_time = datetime.utcnow() - timedelta(days=40)
    reminder = CLIReminderAdapter.create_from_cli_args(
        agent_id="test_agent",
        prompt_text="Old prompt",
        schedule_type="once",
        schedule_value="2024-01-01T12:00:00",
        next_run=old_inactive_time
    )
    reminder.active = False
    reminder.created_at = old_inactive_time
    session.add(reminder)
    session.commit()

    # Add a new inactive schedule (should not be deleted)
    new_inactive_time = datetime.utcnow() - timedelta(days=10)
    reminder2 = CLIReminderAdapter.create_from_cli_args(
        agent_id="test_agent_2",
        prompt_text="Newer prompt",
        schedule_type="once",
        schedule_value="2024-01-01T12:00:00",
        next_run=new_inactive_time
    )
    reminder2.active = False
    reminder2.created_at = new_inactive_time
    session.add(reminder2)
    session.commit()

    deleted_count = db.cleanup_old_schedules(days_old=30)
    assert deleted_count == 1

    remaining_reminders = session.query(UnifiedReminder).all()
    assert len(remaining_reminders) == 1
    assert remaining_reminders[0].agent_id == "test_agent_2"

def test_get_database_stats(session: Session):
    db.add_schedule("agent1", "prompt1", "once", "2025-01-01T12:00:00", datetime.utcnow())
    stats = db.get_database_stats()
    assert stats["total_reminders"] == 1
    assert stats["active_reminders"] == 1
    assert stats["cli_reminders"] == 1
    assert "database_size_bytes" in stats

# Additional simple tests to improve coverage
def test_cancel_schedule_nonexistent(session: Session):
    """Test canceling a schedule that doesn't exist."""
    result = db.cancel_schedule(99999)
    assert result is False

def test_get_schedule_nonexistent(session: Session):
    """Test getting a schedule that doesn't exist.""" 
    result = db.get_schedule(99999)
    assert result is None

def test_update_schedule_nonexistent(session: Session):
    """Test updating a schedule that doesn't exist."""
    result = db.update_schedule(99999, prompt_text="New text")
    assert result is False

def test_list_schedules_empty(session: Session):
    """Test listing schedules when database is empty."""
    schedules = db.list_schedules()
    assert schedules == []

def test_get_due_schedules_empty(session: Session):
    """Test getting due schedules when none are due."""
    schedules = db.get_due_schedules()
    assert schedules == []

def test_cleanup_old_schedules_empty(session: Session):
    """Test cleanup when no old schedules exist."""
    deleted_count = db.cleanup_old_schedules(days_old=30)
    assert deleted_count == 0
