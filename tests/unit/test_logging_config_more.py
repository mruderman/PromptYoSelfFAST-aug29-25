import io
import json
import logging
import os

import pytest

from promptyoself import logging_config as lc


@pytest.mark.unit
def test_structured_formatter_includes_extra_and_exception():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(lc.StructuredFormatter(include_context=True))

    logger = logging.getLogger("structured_test_logger")
    logger.setLevel(logging.DEBUG)
    logger.handlers = [handler]

    # Log with extra fields
    logger.info("hello", extra={"alpha": 1, "beta": "x"})
    # Log an exception to capture 'exception' field
    try:
        raise ValueError("boom")
    except Exception:  # noqa: BLE001
        logger.exception("had error")

    out = stream.getvalue().strip().splitlines()
    first = json.loads(out[0])
    second = json.loads(out[1])

    assert first["message"] == "hello"
    assert "extra" in first and first["extra"]["alpha"] == 1
    assert second["level"] == "ERROR"
    assert "exception" in second


@pytest.mark.unit
def test_configure_logging_env_and_files(tmp_path, monkeypatch):
    # Ensure structured logging and file logging enabled via env
    monkeypatch.setenv("PROMPTYOSELF_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("PROMPTYOSELF_LOG_STRUCTURED", "true")
    monkeypatch.setenv("PROMPTYOSELF_LOG_FILE", "true")
    monkeypatch.setenv("PROMPTYOSELF_LOG_CONSOLE", "false")

    cfg = lc.configure_logging()
    logger = cfg.get_logger("promptyoself.test")

    logger.info("file test info")
    logger.error("file test error")

    info_log = tmp_path / "promptyoself.log"
    err_log = tmp_path / "promptyoself_errors.log"
    # Handlers flush asynchronously; force flush by removing and reconfiguring root handlers if needed
    for h in logging.getLogger().handlers:
        try:
            h.flush()
        except Exception:
            pass

    assert info_log.exists()
    assert err_log.exists()
    assert info_log.read_text().strip() != ""
    assert err_log.read_text().strip() != ""


@pytest.mark.unit
def test_log_letta_operation_failure_and_success(caplog):
    caplog.set_level(logging.DEBUG)
    # Success
    lc.log_letta_operation("send", "agt_x", True, {"k": "v"})
    # Failure
    lc.log_letta_operation("send", "agt_x", False, {"k": "v"})

    text = caplog.text
    assert "Letta send for agent agt_x succeeded" in text
    assert "Letta send for agent agt_x failed" in text


@pytest.mark.unit
def test_performance_timer_exception_branch(caplog):
    caplog.set_level(logging.DEBUG)
    with pytest.raises(RuntimeError):
        with lc.PerformanceTimer("boom", lc.get_logger("x")):
            raise RuntimeError("fail inside")
    assert "Operation 'boom' failed" in caplog.text

