import pytest
from unittest.mock import patch
from datetime import datetime, timedelta

from promptyoself import cli


@pytest.mark.unit
def test_register_prompt_time_with_utc_suffix_future():
    """Covers _normalize_iso path for ' UTC' suffix and isoparse branch."""
    future_time = (datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S UTC")
    args = {
        "agent_id": "test-agent",
        "prompt": "Hello",
        "time": future_time,
        "skip_validation": True,
    }
    with patch("promptyoself.cli.add_schedule", return_value=42):
        result = cli.register_prompt(args)
    assert result.get("status") == "success"
    # Ensure the returned next_run is parseable and in the future
    from dateutil import parser as date_parser
    nr = date_parser.isoparse(result["next_run"])  # should include timezone (+00:00)
    now_ref = datetime.now(tz=nr.tzinfo)
    assert nr > now_ref


@pytest.mark.unit
def test_register_prompt_time_fallback_parse_future():
    """Covers fallback dateutil.parse branch when isoparse fails."""
    # Use a non-ISO but common format
    future_time = (datetime.utcnow() + timedelta(days=400)).strftime("%B %d, %Y %H:%M:%S")
    args = {
        "agent_id": "test-agent",
        "prompt": "Hello",
        "time": future_time,
        "skip_validation": True,
    }
    with patch("promptyoself.cli.add_schedule", return_value=43):
        result = cli.register_prompt(args)
    assert result.get("status") == "success"


@pytest.mark.unit
def test_register_prompt_every_30s_and_1h():
    """Covers interval parsing branches for 's' and 'h' suffixes."""
    # 30 seconds
    args_30s = {
        "agent_id": "a",
        "prompt": "p",
        "every": "30s",
        "skip_validation": True,
    }
    with patch("promptyoself.cli.add_schedule", return_value=1) as add1:
        res1 = cli.register_prompt(args_30s)
        assert res1.get("status") == "success"
        call_kwargs = add1.call_args.kwargs
        assert call_kwargs["schedule_type"] == "interval"

    # 1 hour
    args_1h = {
        "agent_id": "a",
        "prompt": "p",
        "every": "1h",
        "skip_validation": True,
    }
    with patch("promptyoself.cli.add_schedule", return_value=2) as add2:
        res2 = cli.register_prompt(args_1h)
        assert res2.get("status") == "success"
        call_kwargs = add2.call_args.kwargs
        assert call_kwargs["schedule_type"] == "interval"


@pytest.mark.unit
def test_register_prompt_interval_start_at_fallback_parse():
    """Covers start_at fallback parse branch in interval scheduling."""
    start_at = (datetime.utcnow() + timedelta(days=10)).strftime("%B %d, %Y %H:%M:%S")
    args = {
        "agent_id": "a",
        "prompt": "p",
        "every": "10m",
        "start_at": start_at,
        "skip_validation": True,
    }
    with patch("promptyoself.cli.add_schedule", return_value=3):
        res = cli.register_prompt(args)
    assert res.get("status") == "success"


@pytest.mark.unit
def test_register_prompt_invalid_max_repetitions_non_integer():
    args = {
        "agent_id": "a",
        "prompt": "p",
        "every": "10m",
        "max_repetitions": "not-a-number",
        "skip_validation": True,
    }
    res = cli.register_prompt(args)
    assert "error" in res and "valid integer" in res["error"]


@pytest.mark.unit
def test_register_prompt_invalid_max_repetitions_negative():
    args = {
        "agent_id": "a",
        "prompt": "p",
        "every": "10m",
        "max_repetitions": -5,
        "skip_validation": True,
    }
    res = cli.register_prompt(args)
    assert "error" in res and "positive integer" in res["error"]


@pytest.mark.unit
def test_list_prompts_error_handling():
    with patch("promptyoself.cli.list_schedules", side_effect=RuntimeError("db error")):
        res = cli.list_prompts({"agent_id": "a"})
    assert "error" in res and "Failed to list prompts" in res["error"]


@pytest.mark.unit
def test_cancel_prompt_missing_and_invalid_id():
    # Missing id
    res1 = cli.cancel_prompt({})
    assert "error" in res1 and "Missing required argument" in res1["error"]

    # Invalid format
    res2 = cli.cancel_prompt({"id": "abc"})
    assert "error" in res2 and "must be a number" in res2["error"]


@pytest.mark.unit
def test_execute_prompts_loop_invalid_interval():
    res = cli.execute_prompts({"loop": True, "interval": "abc"})
    assert "error" in res and "must be a number" in res["error"]
