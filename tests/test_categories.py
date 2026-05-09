import pytest
import database.db as _db
from database.db import init_db, seed_db
from database.queries import get_category_breakdown


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


def _make_empty_user():
    conn = _db.get_db()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Empty User", "empty@test.com", "x"),
    )
    uid = cur.lastrowid
    conn.commit()
    conn.close()
    return uid


def test_returns_list():
    uid = _get_seed_user_id()
    result = get_category_breakdown(uid)
    assert isinstance(result, list)


def test_returns_seven_categories():
    uid = _get_seed_user_id()
    result = get_category_breakdown(uid)
    assert len(result) == 7


def test_ordered_by_amount_desc():
    uid = _get_seed_user_id()
    result = get_category_breakdown(uid)
    assert result[0]["name"] == "Bills"
    assert result[-1]["name"] == "Other"


def test_pct_sums_to_100():
    uid = _get_seed_user_id()
    result = get_category_breakdown(uid)
    assert sum(c["pct"] for c in result) == 100


def test_pct_are_integers():
    uid = _get_seed_user_id()
    result = get_category_breakdown(uid)
    for cat in result:
        assert isinstance(cat["pct"], int)


def test_amount_uses_rupee_symbol():
    uid = _get_seed_user_id()
    result = get_category_breakdown(uid)
    for cat in result:
        assert "₹" in cat["amount"]


def test_dict_keys():
    uid = _get_seed_user_id()
    result = get_category_breakdown(uid)
    for cat in result:
        assert "name" in cat
        assert "amount" in cat
        assert "pct" in cat


def test_empty_for_no_expenses():
    uid = _make_empty_user()
    result = get_category_breakdown(uid)
    assert result == []
