import pytest
from datetime import datetime

import promptyoself.db as db


class _CommitErrorSession:
    def __init__(self):
        self.rollback_called = False
        self.closed = False
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        raise RuntimeError("commit boom")

    def refresh(self, _obj):
        pass

    def rollback(self):
        self.rollback_called = True

    def close(self):
        self.closed = True


class _QueryError:
    def __init__(self, exc):
        self.exc = exc

    # Allow chain .filter(...).order_by(...).all() etc. but raise early
    def filter(self, *args, **kwargs):
        raise self.exc

    def order_by(self, *args, **kwargs):
        raise self.exc

    def count(self):
        raise self.exc

    def first(self):
        raise self.exc

    def all(self):
        raise self.exc


class _QueryErrorSession:
    def __init__(self, exc):
        self.exc = exc
        self.closed = False

    def query(self, *args, **kwargs):
        return _QueryError(self.exc)

    def commit(self):
        pass

    def close(self):
        self.closed = True


@pytest.mark.unit
def test_add_schedule_commit_failure(monkeypatch):
    fake = _CommitErrorSession()
    monkeypatch.setattr(db, "get_session", lambda: fake)

    with pytest.raises(RuntimeError, match="commit boom"):
        db.add_schedule(
            agent_id="a",
            prompt_text="p",
            schedule_type="once",
            schedule_value="t",
            next_run=datetime.utcnow(),
        )

    assert fake.rollback_called is True
    assert fake.closed is True


@pytest.mark.unit
def test_list_schedules_query_failure(monkeypatch):
    exc = RuntimeError("query boom")
    fake = _QueryErrorSession(exc)
    monkeypatch.setattr(db, "get_session", lambda: fake)

    with pytest.raises(RuntimeError, match="query boom"):
        db.list_schedules()
    assert fake.closed is True


@pytest.mark.unit
def test_get_due_schedules_query_failure(monkeypatch):
    exc = RuntimeError("query boom")
    fake = _QueryErrorSession(exc)
    monkeypatch.setattr(db, "get_session", lambda: fake)

    with pytest.raises(RuntimeError, match="query boom"):
        db.get_due_schedules()
    assert fake.closed is True

