import pytest
from unittest.mock import patch, MagicMock
from promptyoself import cli
import datetime

@pytest.fixture(autouse=True)
def mock_dependencies():
    """Fixture to mock all external dependencies of the cli module."""
    with patch('promptyoself.cli.add_schedule') as mock_add_schedule, \
         patch('promptyoself.cli.list_schedules') as mock_list_schedules, \
         patch('promptyoself.cli.cancel_schedule') as mock_cancel_schedule, \
         patch('promptyoself.cli.calculate_next_run', return_value=datetime.datetime.now() + datetime.timedelta(hours=1)) as mock_calculate_next_run, \
         patch('promptyoself.cli.execute_due_prompts', return_value=[]) as mock_execute_due_prompts, \
         patch('promptyoself.cli.run_scheduler_loop') as mock_run_scheduler_loop, \
         patch('promptyoself.cli.test_letta_connection', return_value={"status": "success"}) as mock_test_letta_connection, \
         patch('promptyoself.cli.list_available_agents', return_value={"status": "success", "agents": []}) as mock_list_available_agents, \
         patch('promptyoself.cli.validate_agent_exists', return_value={"status": "success", "exists": True}) as mock_validate_agent_exists, \
         patch('promptyoself.cli.upload_tool', return_value={"status": "success"}) as mock_upload_tool:

        mock_add_schedule.return_value = 1 # Example schedule ID
        mock_list_schedules.return_value = [] # Return a JSON serializable list
        mock_cancel_schedule.return_value = True

        yield {
            "add_schedule": mock_add_schedule,
            "list_schedules": mock_list_schedules,
            "cancel_schedule": mock_cancel_schedule,
            "execute_due_prompts": mock_execute_due_prompts,
            "run_scheduler_loop": mock_run_scheduler_loop,
            "validate_agent_exists": mock_validate_agent_exists,
            "upload_tool": mock_upload_tool,
            "calculate_next_run": mock_calculate_next_run
        }

def run_main_with_args(args, expected_exit_code=0):
    """Helper to run the CLI's main function with patched sys.argv."""
    with patch('sys.argv', ['cli.py'] + args):
        with pytest.raises(SystemExit) as e:
            cli.main()
        assert e.value.code == expected_exit_code

@pytest.mark.unit
def test_register_prompt_time(mock_dependencies):
    """Test registering a one-time prompt."""
    future_time = (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat()
    args = ["register", "--agent-id", "test-agent", "--prompt", "Hello", "--time", future_time]
    run_main_with_args(args)
    mock_dependencies["add_schedule"].assert_called_once()
    call_kwargs = mock_dependencies["add_schedule"].call_args[1]
    assert call_kwargs['agent_id'] == 'test-agent'
    assert call_kwargs['schedule_type'] == 'once'

@pytest.mark.unit
def test_register_prompt_cron(mock_dependencies):
    """Test registering a cron prompt."""
    args = ["register", "--agent-id", "test-agent", "--prompt", "Hello", "--cron", "0 0 * * *"]
    run_main_with_args(args)
    mock_dependencies["add_schedule"].assert_called_once()
    call_kwargs = mock_dependencies["add_schedule"].call_args[1]
    assert call_kwargs['schedule_type'] == 'cron'

@pytest.mark.unit
def test_register_prompt_interval(mock_dependencies):
    """Test registering an interval prompt."""
    args = ["register", "--agent-id", "test-agent", "--prompt", "Hello", "--every", "15m"]
    run_main_with_args(args)
    mock_dependencies["add_schedule"].assert_called_once()
    call_kwargs = mock_dependencies["add_schedule"].call_args[1]
    assert call_kwargs['schedule_type'] == 'interval'

@pytest.mark.unit
def test_register_prompt_invalid_agent(mock_dependencies):
    """Test registering a prompt with an invalid agent."""
    mock_dependencies["validate_agent_exists"].return_value = {"status": "error", "exists": False, "message": "Agent not found"}
    future_time = (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat()
    args = ["register", "--agent-id", "invalid-agent", "--prompt", "p", "--time", future_time]
    run_main_with_args(args, expected_exit_code=1)
    mock_dependencies["add_schedule"].assert_not_called()

@pytest.mark.unit
def test_list_schedules(mock_dependencies):
    """Test the list command."""
    run_main_with_args(["list"])
    mock_dependencies["list_schedules"].assert_called_once()

@pytest.mark.unit
def test_cancel_schedule(mock_dependencies):
    """Test the cancel command."""
    run_main_with_args(["cancel", "--id", "1"])
    mock_dependencies["cancel_schedule"].assert_called_once_with(1)

@pytest.mark.unit
def test_execute_schedules_once(mock_dependencies):
    """Test the execute command for a single run."""
    run_main_with_args(["execute"])
    mock_dependencies["execute_due_prompts"].assert_called_once()
    mock_dependencies["run_scheduler_loop"].assert_not_called()

@pytest.mark.unit
def test_execute_schedules_loop(mock_dependencies):
    """Test the execute command in loop mode."""
    run_main_with_args(["execute", "--loop", "--interval", "10"])
    mock_dependencies["run_scheduler_loop"].assert_called_once_with(10)
    mock_dependencies["execute_due_prompts"].assert_not_called()

@pytest.mark.unit
def test_upload_tool(mock_dependencies):
    """Test the upload command."""
    args = ["upload", "--source-code", "def f(): pass"]
    run_main_with_args(args)
    mock_dependencies["upload_tool"].assert_called_once()

# Argparse failure checks
@pytest.mark.unit
def test_argparse_register_missing_args():
    """Test that argparse exits if required args are missing for register."""
    with patch('sys.argv', ['cli.py', 'register', '--prompt', 'p']), pytest.raises(SystemExit) as e:
        cli.main()
    assert e.value.code != 0

@pytest.mark.unit
def test_argparse_no_schedule_option(mock_dependencies):
    """Test for error if no schedule option is provided."""
    run_main_with_args(['register', '--agent-id', 'a', '--prompt', 'p'], expected_exit_code=1)

@pytest.mark.unit
def test_argparse_multiple_schedule_options(mock_dependencies):
    """Test for error if multiple schedule options are provided."""
    run_main_with_args(['register', '--agent-id', 'a', '--prompt', 'p', '--time', 'now', '--cron', '*'], expected_exit_code=1)

@pytest.mark.unit
def test_register_invalid_cron(mock_dependencies):
    """Test registration with an invalid cron string."""
    args = ["register", "--agent-id", "test-agent", "--prompt", "p", "--cron", "invalid cron"]
    run_main_with_args(args, expected_exit_code=1)
    mock_dependencies["add_schedule"].assert_not_called()

@pytest.mark.unit
def test_register_past_time(mock_dependencies):
    """Test registration with a time in the past."""
    past_time = (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat()
    args = ["register", "--agent-id", "test-agent", "--prompt", "p", "--time", past_time]
    run_main_with_args(args, expected_exit_code=1)
    mock_dependencies["add_schedule"].assert_not_called()
