import pytest
import logging
from promptyoself import logging_config

def test_get_logger():
    logger = logging_config.get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"

def test_performance_timer(caplog):
    with caplog.at_level(logging.INFO):
        with logging_config.PerformanceTimer("test_op", logging_config.get_logger("test_logger")):
            pass
    assert "Operation 'test_op' completed" in caplog.text
