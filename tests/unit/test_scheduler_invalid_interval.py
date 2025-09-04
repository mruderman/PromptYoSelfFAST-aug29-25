import pytest
from promptyoself import scheduler
from promptyoself.db import UnifiedReminder


@pytest.mark.unit
def test_calculate_next_run_for_schedule_invalid_interval_value():
    # schedule_value '5x' will attempt int('5x') and raise ValueError
    r = UnifiedReminder(id=1, agent_id='a', message='m', schedule_type="interval", schedule_value="5x", active=True)
    with pytest.raises(ValueError):
        scheduler.calculate_next_run_for_schedule(r)

