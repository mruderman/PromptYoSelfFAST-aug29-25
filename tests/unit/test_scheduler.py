import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from promptyoself import scheduler, db
from promptyoself.db import UnifiedReminder

@pytest.fixture
def session():
    """Fixture to provide a clean in-memory database session for each test."""
    import os
    os.environ["PROMPTYOSELF_DB"] = ":memory:"
    db.reset_db_connection()
    db.initialize_db()
    db_session = db.get_session()
    yield db_session
    db_session.close()
    del os.environ["PROMPTYOSELF_DB"]

def test_calculate_next_run_cron():
    base_time = datetime(2025, 1, 1, 12, 0, 0)
    next_run = scheduler.calculate_next_run("* * * * *", base_time=base_time)
    assert next_run == datetime(2025, 1, 1, 12, 1, 0)

def test_calculate_next_run_for_schedule_once():
    reminder = UnifiedReminder(schedule_type="once")
    assert scheduler.calculate_next_run_for_schedule(reminder) is None

def test_calculate_next_run_for_schedule_cron():
    reminder = UnifiedReminder(schedule_type="cron", schedule_value="0 0 1 1 *")
    next_run = scheduler.calculate_next_run_for_schedule(reminder)
    assert next_run.day == 1
    assert next_run.month == 1

def test_calculate_next_run_for_schedule_interval():
    reminder = UnifiedReminder(schedule_type="interval", schedule_value="15m")
    next_run = scheduler.calculate_next_run_for_schedule(reminder)
    assert next_run > datetime.utcnow()
    assert (next_run - datetime.utcnow()).total_seconds() < 15 * 60 + 1

@patch("promptyoself.scheduler.send_prompt_to_agent", return_value=True)
def test_execute_due_prompts_once_schedule(mock_send_prompt, session):
    # Add a due "once" schedule
    next_run_time = datetime.utcnow() - timedelta(minutes=1)
    schedule_id = db.add_schedule(
        agent_id="test_agent",
        prompt_text="Test prompt",
        schedule_type="once",
        schedule_value="",
        next_run=next_run_time
    )

    results = scheduler.execute_due_prompts()

    assert len(results) == 1
    assert results[0]["delivered"] is True
    mock_send_prompt.assert_called_once_with("test_agent", "Test prompt")

    # Verify the schedule is now inactive
    updated_schedule = db.get_schedule(schedule_id)
    assert updated_schedule["active"] is False

@patch("promptyoself.scheduler.send_prompt_to_agent", return_value=True)
def test_execute_due_prompts_interval_schedule(mock_send_prompt, session):
    # Add a due "interval" schedule
    next_run_time = datetime.utcnow() - timedelta(minutes=1)
    schedule_id = db.add_schedule(
        agent_id="test_agent",
        prompt_text="Test prompt",
        schedule_type="interval",
        schedule_value="1h",
        next_run=next_run_time
    )

    results = scheduler.execute_due_prompts()

    assert len(results) == 1
    assert results[0]["delivered"] is True

    # Verify the schedule is still active and next_run is updated
    updated_schedule = db.get_schedule(schedule_id)
    assert updated_schedule["active"] is True
    assert datetime.fromisoformat(updated_schedule["next_run"]) > datetime.utcnow()

@patch("promptyoself.scheduler.send_prompt_to_agent", return_value=False)
def test_execute_due_prompts_delivery_failure(mock_send_prompt, session):
    # Add a due schedule
    next_run_time = datetime.utcnow() - timedelta(minutes=1)
    schedule_id = db.add_schedule(
        agent_id="test_agent",
        prompt_text="Test prompt",
        schedule_type="once",
        schedule_value="",
        next_run=next_run_time
    )

    results = scheduler.execute_due_prompts()

    assert len(results) == 1
    assert results[0]["delivered"] is False

    # Verify the schedule is still active and next_run is not changed
    updated_schedule = db.get_schedule(schedule_id)
    assert updated_schedule["active"] is True
    assert datetime.fromisoformat(updated_schedule["next_run"]).timestamp() == pytest.approx(next_run_time.timestamp())

@patch("promptyoself.scheduler.send_prompt_to_agent", return_value=True)
def test_execute_due_prompts_max_repetitions(mock_send_prompt, session):
    # Add a due "interval" schedule with max_repetitions
    next_run_time = datetime.utcnow() - timedelta(minutes=1)
    schedule_id = db.add_schedule(
        agent_id="test_agent",
        prompt_text="Test prompt",
        schedule_type="interval",
        schedule_value="1h",
        next_run=next_run_time,
        max_repetitions=1
    )

    results = scheduler.execute_due_prompts()

    assert len(results) == 1
    assert results[0]["delivered"] is True
    assert results[0]["completed"] is True

    # Verify the schedule is now inactive
    updated_schedule = db.get_schedule(schedule_id)
    assert updated_schedule["active"] is False
