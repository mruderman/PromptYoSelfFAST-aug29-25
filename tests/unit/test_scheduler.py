import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from promptyoself import scheduler
from promptyoself.db import UnifiedReminder

@pytest.mark.unit
def test_calculate_next_run_cron():
    """Test cron next run calculation."""
    base_time = datetime(2025, 1, 1, 12, 0, 0)
    next_run = scheduler.calculate_next_run("* * * * *", base_time=base_time)
    assert next_run == datetime(2025, 1, 1, 12, 1, 0)

@pytest.mark.unit
def test_calculate_next_run_for_schedule_once():
    """Test that 'once' schedules do not calculate a next run."""
    reminder = UnifiedReminder(id=1, agent_id='a', message='m', schedule_type="once", active=True)
    assert scheduler.calculate_next_run_for_schedule(reminder) is None

@pytest.mark.unit
@patch('promptyoself.scheduler.calculate_next_run')
def test_calculate_next_run_for_schedule_cron(mock_calculate_next_run):
    """Test next run calculation for a cron schedule."""
    reminder = UnifiedReminder(id=1, agent_id='a', message='m', schedule_type="cron", schedule_value="* * 1 1 *", active=True)
    scheduler.calculate_next_run_for_schedule(reminder)
    mock_calculate_next_run.assert_called_once_with("* * 1 1 *")


@pytest.mark.unit
def test_calculate_next_run_for_schedule_interval():
    """Test next run calculation for an interval schedule."""
    reminder = UnifiedReminder(id=1, agent_id='a', message='m', schedule_type="interval", schedule_value="15m", active=True)
    now = datetime.utcnow()
    with patch('datetime.datetime') as mock_dt:
        mock_dt.utcnow.return_value = now
        next_run = scheduler.calculate_next_run_for_schedule(reminder)
        assert next_run == now + timedelta(minutes=15)

@pytest.fixture
def mock_db_and_api():
    """Fixture to mock DB and API dependencies for execute_due_prompts."""
    with patch('promptyoself.scheduler.db') as mock_db, \
         patch('promptyoself.scheduler.send_prompt_to_agent') as mock_send:

        mock_session = MagicMock()
        mock_db.get_session.return_value = mock_session

        yield mock_db, mock_send, mock_session

@pytest.mark.unit
def test_execute_due_prompts_once_schedule(mock_db_and_api):
    """Test executing a 'once' schedule."""
    mock_db, mock_send, mock_session = mock_db_and_api
    mock_send.return_value = True

    due_reminder = UnifiedReminder(id=1, agent_id="agent1", message="Test", schedule_type="once", active=True)
    mock_db.get_due_schedules.return_value = [due_reminder]

    results = scheduler.execute_due_prompts()

    assert len(results) == 1
    assert results[0]["delivered"] is True
    mock_send.assert_called_once_with("agent1", "Test")
    assert due_reminder.active is False
    mock_session.commit.assert_called_once()


@pytest.mark.unit
def test_execute_due_prompts_interval_schedule(mock_db_and_api):
    """Test executing an interval schedule."""
    mock_db, mock_send, mock_session = mock_db_and_api
    mock_send.return_value = True

    due_reminder = UnifiedReminder(id=1, agent_id="agent1", message="Test", schedule_type="interval", schedule_value="1h", active=True, repetition_count=0)
    mock_db.get_due_schedules.return_value = [due_reminder]

    with patch('promptyoself.scheduler.calculate_next_run_for_schedule') as mock_calc:
        new_next_run = datetime.utcnow() + timedelta(hours=1)
        mock_calc.return_value = new_next_run

        results = scheduler.execute_due_prompts()

        assert len(results) == 1
        assert results[0]["delivered"] is True
        assert due_reminder.active is True
        assert due_reminder.next_run == new_next_run
        assert due_reminder.repetition_count == 1
        mock_session.commit.assert_called_once()

@pytest.mark.unit
def test_execute_due_prompts_delivery_failure(mock_db_and_api):
    """Test when prompt delivery fails."""
    mock_db, mock_send, mock_session = mock_db_and_api
    mock_send.return_value = False

    due_reminder = UnifiedReminder(id=1, agent_id="agent1", message="Test", schedule_type="once", active=True, next_run=datetime.utcnow())
    mock_db.get_due_schedules.return_value = [due_reminder]

    results = scheduler.execute_due_prompts()

    assert len(results) == 1
    assert results[0]["delivered"] is False
    assert due_reminder.active is True # Should not be deactivated
    mock_session.commit.assert_not_called()

@pytest.mark.unit
def test_execute_due_prompts_max_repetitions(mock_db_and_api):
    """Test that an interval schedule is deactivated after max_repetitions."""
    mock_db, mock_send, mock_session = mock_db_and_api
    mock_send.return_value = True

    due_reminder = UnifiedReminder(
        id=1, agent_id="agent1", message="Test",
        schedule_type="interval", schedule_value="1h", active=True,
        repetition_count=4, max_repetitions=5
    )
    mock_db.get_due_schedules.return_value = [due_reminder]

    results = scheduler.execute_due_prompts()

    assert len(results) == 1
    assert results[0]["delivered"] is True
    assert results[0]["completed"] is True
    assert due_reminder.active is False
    assert due_reminder.repetition_count == 5
    mock_session.commit.assert_called_once()

@pytest.mark.unit
@patch('time.sleep')
@patch('apscheduler.schedulers.blocking.BlockingScheduler')
def test_run_scheduler_loop(mock_scheduler_class, mock_sleep):
    """Test the scheduler loop runs until a KeyboardInterrupt."""
    mock_scheduler_instance = MagicMock()
    mock_scheduler_instance.start.side_effect = KeyboardInterrupt
    mock_scheduler_class.return_value = mock_scheduler_instance

    scheduler.run_scheduler_loop(interval_seconds=10)

    mock_scheduler_instance.add_job.assert_called_once()
    mock_scheduler_instance.start.assert_called_once()
    mock_scheduler_instance.shutdown.assert_called_once()
