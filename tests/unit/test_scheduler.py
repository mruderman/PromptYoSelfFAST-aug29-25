import mock
import pytest
from croniter import croniter
from datetime import datetime, timedelta
from promptyoself.scheduler import calculate_next_run, calculate_next_run_for_schedule, execute_due_prompts, PromptScheduler, run_scheduler_loop

@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("LETTA_API_KEY", "test-api-key")

@mock.patch("promptyoself.scheduler._get_letta_client")
def test_calculate_next_run(mock_client, mock_env_vars):
    result = calculate_next_run("* * * * *", base_time=datetime(2023, 1, 1))
    assert isinstance(result, datetime)

@mock.patch("promptyoself.scheduler._get_letta_client")
def test_calculate_next_run_base_time(mock_client, mock_env_vars):
    result = calculate_next_run("* * * * *", base_time=datetime(2023, 1, 1, 12, 0))
    assert result.hour == 12

@mock.patch("promptyoself.scheduler._get_letta_client")
def test_calculate_next_run_invalid_cron(mock_client, mock_env_vars):
    with pytest.raises(ValueError):
        calculate_next_run("invalid-cron", base_time=datetime(2023, 1, 1))

@mock.patch("promptyoself.scheduler.calculate_next_run")
def test_calculate_next_run_for_schedule_cron(mock_calc, mock_env_vars):
    result = calculate_next_run_for_schedule("agent-123", "cron", "* * * * *", datetime(2023, 1, 1))
    assert isinstance(result, datetime)

@mock.patch("promptyoself.scheduler.calculate_next_run")
def test_calculate_next_run_for_schedule_interval(mock_calc, mock_env_vars):
    result = calculate_next_run_for_schedule("agent-123", "interval", "5m", datetime(2023, 1, 1))
    assert isinstance(result, datetime)

@mock.patch("promptyoself.scheduler.calculate_next_run")
def test_calculate_next_run_for_schedule_one_time(mock_calc, mock_env_vars):
    result = calculate_next_run_for_schedule("agent-123", "one-time", None, datetime(2023, 1, 1))
    assert isinstance(result, datetime)

@mock.patch("promptyoself.scheduler.calculate_next_run")
def test_calculate_next_run_for_schedule_unknown_type(mock_calc, mock_env_vars):
    with pytest.raises(ValueError):
        calculate_next_run_for_schedule("agent-123", "unknown", None, datetime(2023, 1, 1))

@mock.patch("promptyoself.scheduler.execute_due_prompts")
def test_execute_due_prompts_no_results(mock_execute, mock_env_vars):
    mock_execute.return_value = []
    result = execute_due_prompts()
    assert len(result) == 0

@mock.patch("promptyoself.scheduler.execute_due_prompts")
def test_execute_due_prompts_multiple_results(mock_execute, mock_env_vars):
    mock_execute.return_value = [{"id": 1}, {"id": 2}]
    result = execute_due_prompts()
    assert len(result) == 2

@mock.patch("promptyoself.scheduler.execute_due_prompts")
def test_execute_due_prompts_failed_delivery(mock_execute, mock_env_vars):
    mock_execute.side_effect = Exception("Delivery failed")
    with pytest.raises(Exception):
        execute_due_prompts()

class MockPromptScheduler(PromptScheduler):
    def __init__(self):
        super().__init__()
        self.start_called = False
        self.stop_called = False
        self.running = False

    def start(self):
        self.start_called = True
        self.running = True

    def stop(self):
        self.stop_called = True
        self.running = False

@mock.patch("promptyoself.scheduler.PromptScheduler")
def test_prompt_scheduler_start_stop(mock_cls, mock_env_vars):
    scheduler = MockPromptScheduler()
    scheduler.start()
    assert scheduler.start_called
    scheduler.stop()
    assert scheduler.stop_called

@mock.patch("promptyoself.scheduler.PromptScheduler")
@mock.patch("time.sleep")
def test_run_scheduler_loop(mock_cls, mock_sleep, mock_env_vars):
    scheduler = MockPromptScheduler()
    scheduler.run_loop()
    assert scheduler.running
    mock_sleep.assert_called()

@mock.patch("signal.signal")
@mock.patch("sys.exit")
@mock.patch("time.sleep")
def test_run_scheduler_loop_interrupt(mock_signal, mock_exit, mock_sleep, mock_env_vars):
    scheduler = MockPromptScheduler()
    scheduler.run_loop()
    mock_signal.assert_called()
    mock_exit.assert_not_called()
    scheduler.stop()
    mock_exit.assert_called()