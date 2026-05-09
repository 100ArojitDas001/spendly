import pytest
import database.db as _db
from database.db import init_db, seed_db
from database.queries import get_user_by_id, get_summary_stats


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


# --- get_user_by_id ---

def test_get_user_by_id_returns_dict():
    uid = _get_seed_user_id()
    result = get_user_by_id(uid)
    assert isinstance(result, dict)


def test_get_user_by_id_correct_fields():
    uid = _get_seed_user_id()
    result = get_user_by_id(uid)
    assert result["name"] == "Demo User"
    assert result["email"] == "demo@spendly.com"
    assert result["initials"] == "DU"
    assert "member_since" in result


def test_get_user_by_id_member_since_format():
    uid = _get_seed_user_id()
    result = get_user_by_id(uid)
    # Should be "Month YYYY" e.g. "May 2026"
    parts = result["member_since"].split()
    assert len(parts) == 2
    assert parts[1].isdigit()


def test_get_user_by_id_nonexistent():
    result = get_user_by_id(99999)
    assert result is None


# --- get_summary_stats ---

def test_summary_stats_with_expenses():
    uid = _get_seed_user_id()
    result = get_summary_stats(uid)
    assert result["total_spent"] == pytest.approx(338.25)
    assert result["transaction_count"] == 8
    assert result["top_category"] == "Bills"


def test_summary_stats_no_expenses():
    uid = _make_empty_user()
    result = get_summary_stats(uid)
    assert result["total_spent"] == 0
    assert result["transaction_count"] == 0
    assert result["top_category"] == "—"
