import pytest
import tempfile
import os
import database.db as _db
from database.db import init_db, seed_db
from database.queries import get_recent_transactions


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", str(db_file))
    init_db()
    seed_db()


def _get_seed_user_id():
    conn = _db.get_db()
    row = conn.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)).fetchone()
    conn.close()
    return row["id"]


def test_returns_list_of_dicts():
    uid = _get_seed_user_id()
    result = get_recent_transactions(uid)
    assert isinstance(result, list)
    assert len(result) == 8


def test_newest_first():
    uid = _get_seed_user_id()
    result = get_recent_transactions(uid)
    assert result[0]["date"] == "May 08"
    assert result[-1]["date"] == "May 01"


def test_dict_keys():
    uid = _get_seed_user_id()
    result = get_recent_transactions(uid)
    for tx in result:
        assert "date" in tx
        assert "description" in tx
        assert "category" in tx
        assert "amount" in tx


def test_amount_uses_rupee_symbol():
    uid = _get_seed_user_id()
    result = get_recent_transactions(uid)
    for tx in result:
        assert "₹" in tx["amount"]


def test_empty_for_nonexistent_user():
    result = get_recent_transactions(99999)
    assert result == []


def test_limit_parameter():
    uid = _get_seed_user_id()
    result = get_recent_transactions(uid, limit=3)
    assert len(result) == 3
