from datetime import datetime
from database.db import get_db


def _date_filter(from_date, to_date):
    if from_date and to_date:
        return "AND date BETWEEN ? AND ?", (from_date, to_date)
    return "", ()


def get_category_breakdown(user_id, from_date=None, to_date=None):
    date_clause, date_params = _date_filter(from_date, to_date)
    conn = get_db()
    rows = conn.execute(
        "SELECT category, SUM(amount) AS total FROM expenses "
        "WHERE user_id = ? " + date_clause + " GROUP BY category ORDER BY total DESC",
        (user_id, *date_params),
    ).fetchall()
    conn.close()
    if not rows:
        return []
    grand = sum(r["total"] for r in rows)
    result = [
        {
            "name":   r["category"],
            "amount": f"₹{r['total']:.2f}",
            "pct":    round(r["total"] / grand * 100),
        }
        for r in rows
    ]
    diff = 100 - sum(c["pct"] for c in result)
    if diff and result:
        result[0]["pct"] += diff
    return result


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    dt = datetime.strptime(row["created_at"][:19], "%Y-%m-%d %H:%M:%S")
    return {
        "name":         row["name"],
        "email":        row["email"],
        "initials":     "".join(w[0].upper() for w in row["name"].split()[:2]),
        "member_since": dt.strftime("%B %Y"),
    }


def get_summary_stats(user_id, from_date=None, to_date=None):
    date_clause, date_params = _date_filter(from_date, to_date)
    conn = get_db()
    agg = conn.execute(
        "SELECT SUM(amount) AS total, COUNT(*) AS cnt FROM expenses WHERE user_id = ? " + date_clause,
        (user_id, *date_params),
    ).fetchone()
    total = agg["total"] or 0.0
    count = agg["cnt"] or 0
    top = conn.execute(
        "SELECT category FROM expenses WHERE user_id = ? " + date_clause + " "
        "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        (user_id, *date_params),
    ).fetchone()
    conn.close()
    return {
        "total_spent":       total,
        "transaction_count": count,
        "top_category":      top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10, from_date=None, to_date=None):
    date_clause, date_params = _date_filter(from_date, to_date)
    conn = get_db()
    rows = conn.execute(
        "SELECT date, description, category, amount "
        "FROM expenses WHERE user_id = ? " + date_clause + " ORDER BY date DESC LIMIT ?",
        (user_id, *date_params, limit),
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        date_obj = datetime.strptime(row["date"], "%Y-%m-%d")
        result.append({
            "date":        date_obj.strftime("%b %d"),
            "description": row["description"],
            "category":    row["category"],
            "amount":      f"₹{row['amount']:.2f}",
        })
    return result
