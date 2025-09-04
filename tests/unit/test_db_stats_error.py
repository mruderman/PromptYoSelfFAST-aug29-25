import pytest
import promptyoself.db as db


class _BadSession:
    def query(self, *args, **kwargs):
        raise RuntimeError("query bad")
    def close(self):
        pass


@pytest.mark.unit
def test_get_database_stats_error(monkeypatch):
    monkeypatch.setattr(db, "get_session", lambda: _BadSession())
    stats = db.get_database_stats()
    assert "error" in stats and "query bad" in stats["error"]

