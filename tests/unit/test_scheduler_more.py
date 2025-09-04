import pytest
from unittest.mock import patch
from promptyoself import scheduler
from promptyoself.db import UnifiedReminder


@pytest.mark.unit
def test_calculate_next_run_for_schedule_unknown_type():
    r = UnifiedReminder(id=1, agent_id='a', message='m', schedule_type="weird", active=True)
    with pytest.raises(ValueError, match="Unknown schedule type"):
        scheduler.calculate_next_run_for_schedule(r)


@pytest.mark.unit
def test_scheduler_execute_job_logs_on_exception(caplog):
    with patch("promptyoself.scheduler.execute_due_prompts", side_effect=RuntimeError("job boom")):
        s = scheduler.PromptScheduler(interval_seconds=1)
        with caplog.at_level("ERROR"):
            s._execute_job()  # should not raise
        assert any("job boom" in rec.message for rec in caplog.records)

