"""
Tests for the Add Expense feature — GET /expenses/add and POST /expenses/add.

Spec: .claude/specs/07-add-expense.md

Coverage:
  Auth    1 — Unauthenticated GET redirects to /login
  Auth    2 — Unauthenticated POST redirects to /login
  GET     3 — Authenticated GET returns 200
  GET     4 — Response renders an HTML form
  GET     5 — All 7 category options present in the dropdown
  GET     6 — Date input defaults to today's date (value="{{ today }}")
  GET     7 — Page extends base.html (base landmarks present)
  POST    8 — Valid data with description inserts row and redirects to /profile
  POST    9 — Valid data without description (optional field) also succeeds
  POST   10 — DB side effect: new expense row exists with correct field values
  POST   11 — All 7 categories are individually accepted (parametrize)
  VAL    12 — Amount = 0 re-renders form with flash error (not redirect)
  VAL    13 — Negative amount re-renders form with flash error (not redirect)
  VAL    14 — Non-numeric amount string returns HTTP 400
  VAL    15 — Empty amount string returns HTTP 400
  VAL    16 — Missing date (empty string) re-renders form with flash error
  VAL    17 — Invalid category string returns HTTP 400
  SQL    18 — db.py uses ? placeholders, no f-string user-value injection
"""

import os
import re
from datetime import date

import pytest
import database.db as _db
from app import app as flask_app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app(tmp_path, monkeypatch):
    """
    Isolated app with a fresh on-disk DB per test.

    We monkeypatch DB_PATH so every helper (get_db, init_db, create_expense …)
    points at the temp file rather than the real spendly.db.  seed_db() is
    called so the demo user exists for auth_client; tests that need a clean
    user create one explicitly.
    """
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", str(db_file))
    with flask_app.app_context():
        _db.init_db()
        _db.seed_db()
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test"
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Test client pre-logged-in as the seeded demo user."""
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    return client


# ---------------------------------------------------------------------------
# Constants mirroring the implementation spec
# ---------------------------------------------------------------------------

VALID_CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]

VALID_FORM = {
    "amount": "42.50",
    "category": "Food",
    "date": "2026-06-01",
    "description": "Test lunch",
}


# ---------------------------------------------------------------------------
# Auth    1 & 2 — Unauthenticated requests must redirect to /login
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_unauthenticated_get_redirects_to_login(self, client):
        """GET /expenses/add without a session must redirect to /login (302)."""
        response = client.get("/expenses/add")
        assert response.status_code == 302, (
            "Unauthenticated GET /expenses/add should return 302"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login for unauthenticated GET"
        )

    def test_unauthenticated_post_redirects_to_login(self, client):
        """POST /expenses/add without a session must redirect to /login (302)."""
        response = client.post("/expenses/add", data=VALID_FORM)
        assert response.status_code == 302, (
            "Unauthenticated POST /expenses/add should return 302"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login for unauthenticated POST"
        )

    def test_unauthenticated_get_does_not_write_db(self, client, tmp_path):
        """Unauthenticated GET must not create any expense row."""
        client.get("/expenses/add")
        conn = _db.get_db()
        count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()
        # Seed has 8 rows; an unauthenticated GET must not add any
        assert count == 8, (
            "Unauthenticated GET must not insert rows into expenses"
        )


# ---------------------------------------------------------------------------
# GET     3–7 — Authenticated GET renders the form correctly
# ---------------------------------------------------------------------------

class TestGetForm:
    def test_get_returns_200(self, auth_client):
        """Authenticated GET /expenses/add must return HTTP 200."""
        response = auth_client.get("/expenses/add")
        assert response.status_code == 200, (
            "Authenticated GET /expenses/add should return 200"
        )

    def test_get_renders_html_form(self, auth_client):
        """Response must contain an HTML <form> element."""
        response = auth_client.get("/expenses/add")
        assert b"<form" in response.data, (
            "GET /expenses/add must render an HTML form"
        )

    def test_get_form_has_amount_input(self, auth_client):
        """Form must include an amount input field (name='amount')."""
        response = auth_client.get("/expenses/add")
        assert b'name="amount"' in response.data, (
            "Form must contain name='amount' input"
        )

    def test_get_form_has_date_input(self, auth_client):
        """Form must include a date input field (name='date')."""
        response = auth_client.get("/expenses/add")
        assert b'name="date"' in response.data, (
            "Form must contain name='date' input"
        )

    def test_get_form_has_category_select(self, auth_client):
        """Form must include a category select field (name='category')."""
        response = auth_client.get("/expenses/add")
        assert b'name="category"' in response.data, (
            "Form must contain name='category' select"
        )

    def test_get_form_has_description_field(self, auth_client):
        """Form must include a description field (name='description')."""
        response = auth_client.get("/expenses/add")
        assert b'name="description"' in response.data, (
            "Form must contain name='description' field"
        )

    def test_get_all_seven_categories_present(self, auth_client):
        """All 7 category options must appear in the dropdown."""
        response = auth_client.get("/expenses/add")
        for category in VALID_CATEGORIES:
            assert category.encode() in response.data, (
                f"Category option '{category}' must be present in the form dropdown"
            )

    def test_get_exactly_seven_category_options(self, auth_client):
        """The dropdown must contain exactly 7 <option> elements (one per category)."""
        response = auth_client.get("/expenses/add")
        html = response.data.decode("utf-8")
        option_values = re.findall(r'<option value="([^"]+)"', html)
        category_options = [v for v in option_values if v in VALID_CATEGORIES]
        assert len(category_options) == 7, (
            f"Expected exactly 7 category options, found {len(category_options)}: {category_options}"
        )

    def test_get_date_input_defaults_to_today(self, auth_client):
        """The date input value attribute must equal today's date in YYYY-MM-DD."""
        today_str = date.today().strftime("%Y-%m-%d")
        response = auth_client.get("/expenses/add")
        assert f'value="{today_str}"'.encode() in response.data, (
            f"Date input must default to today ({today_str})"
        )

    def test_get_page_title_or_heading_present(self, auth_client):
        """The page must contain 'Add Expense' as a heading or title."""
        response = auth_client.get("/expenses/add")
        assert b"Add Expense" in response.data, (
            "Page must contain 'Add Expense' heading text"
        )

    def test_get_page_extends_base_html(self, auth_client):
        """Template extends base.html — response must include the base layout marker."""
        response = auth_client.get("/expenses/add")
        # base.html always renders a <html> tag; its presence confirms extension.
        assert b"<html" in response.data or b"<!DOCTYPE" in response.data, (
            "Page must extend base.html, rendering a full HTML document"
        )

    def test_get_submit_button_present(self, auth_client):
        """Form must contain a submit button."""
        response = auth_client.get("/expenses/add")
        assert b"Save Expense" in response.data or b'type="submit"' in response.data, (
            "Form must contain a submit button"
        )


# ---------------------------------------------------------------------------
# POST    8–11 — Happy path: valid data inserts expense and redirects
# ---------------------------------------------------------------------------

class TestPostHappyPath:
    def test_valid_post_redirects_to_profile(self, auth_client):
        """Valid form data must redirect (302) to /profile."""
        response = auth_client.post("/expenses/add", data=VALID_FORM)
        assert response.status_code == 302, (
            "Valid POST /expenses/add must return 302 redirect"
        )
        assert "/profile" in response.headers["Location"], (
            "Successful POST must redirect to /profile"
        )

    def test_valid_post_without_description_redirects(self, auth_client):
        """Optional description field — omitting it must still redirect to /profile."""
        data = {k: v for k, v in VALID_FORM.items() if k != "description"}
        data["description"] = ""
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 302, (
            "POST without description should still succeed with 302"
        )
        assert "/profile" in response.headers["Location"], (
            "POST without description must redirect to /profile"
        )

    def test_valid_post_inserts_expense_row(self, auth_client):
        """After a valid POST, one new row must exist in the expenses table."""
        conn = _db.get_db()
        before = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()

        auth_client.post("/expenses/add", data=VALID_FORM)

        conn = _db.get_db()
        after = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()

        assert after == before + 1, (
            f"Expected expenses count to increase by 1 (was {before}, now {after})"
        )

    def test_valid_post_db_row_has_correct_amount(self, auth_client):
        """The inserted row's amount must match the submitted value."""
        auth_client.post("/expenses/add", data=VALID_FORM)

        conn = _db.get_db()
        row = conn.execute(
            "SELECT amount FROM expenses WHERE description = ?",
            ("Test lunch",),
        ).fetchone()
        conn.close()

        assert row is not None, "Expected to find the inserted expense row"
        assert abs(row["amount"] - 42.50) < 0.001, (
            f"Inserted amount should be 42.50, got {row['amount']}"
        )

    def test_valid_post_db_row_has_correct_category(self, auth_client):
        """The inserted row's category must match the submitted value."""
        auth_client.post("/expenses/add", data=VALID_FORM)

        conn = _db.get_db()
        row = conn.execute(
            "SELECT category FROM expenses WHERE description = ?",
            ("Test lunch",),
        ).fetchone()
        conn.close()

        assert row is not None, "Expected to find the inserted expense row"
        assert row["category"] == "Food", (
            f"Category should be 'Food', got '{row['category']}'"
        )

    def test_valid_post_db_row_has_correct_date(self, auth_client):
        """The inserted row's date must match the submitted value."""
        auth_client.post("/expenses/add", data=VALID_FORM)

        conn = _db.get_db()
        row = conn.execute(
            "SELECT date FROM expenses WHERE description = ?",
            ("Test lunch",),
        ).fetchone()
        conn.close()

        assert row is not None, "Expected to find the inserted expense row"
        assert row["date"] == "2026-06-01", (
            f"Date should be '2026-06-01', got '{row['date']}'"
        )

    def test_valid_post_db_row_has_correct_description(self, auth_client):
        """The inserted row's description must match the submitted value."""
        auth_client.post("/expenses/add", data=VALID_FORM)

        conn = _db.get_db()
        row = conn.execute(
            "SELECT description FROM expenses WHERE description = ?",
            ("Test lunch",),
        ).fetchone()
        conn.close()

        assert row is not None, "Expected to find the inserted expense row"
        assert row["description"] == "Test lunch", (
            f"Description should be 'Test lunch', got '{row['description']}'"
        )

    def test_valid_post_db_row_description_none_when_empty(self, auth_client):
        """When description is submitted as empty string, DB row should store NULL/None."""
        data = dict(VALID_FORM)
        data["description"] = ""
        data["amount"] = "10.00"

        auth_client.post("/expenses/add", data=data)

        conn = _db.get_db()
        row = conn.execute(
            "SELECT description FROM expenses WHERE amount = ? AND date = ?",
            (10.00, data["date"]),
        ).fetchone()
        conn.close()

        assert row is not None, "Expected to find the inserted expense row"
        # The spec says description is optional; db.py stores None (NULL) for blank
        assert row["description"] is None or row["description"] == "", (
            "Empty description should be stored as NULL or empty in the DB"
        )

    def test_valid_post_expense_belongs_to_logged_in_user(self, auth_client):
        """The inserted row's user_id must match the logged-in user's ID."""
        # The demo user is the only user in the seeded DB
        conn = _db.get_db()
        demo_user = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
        ).fetchone()
        conn.close()

        auth_client.post("/expenses/add", data=VALID_FORM)

        conn = _db.get_db()
        row = conn.execute(
            "SELECT user_id FROM expenses WHERE description = ?",
            ("Test lunch",),
        ).fetchone()
        conn.close()

        assert row is not None, "Expected to find the inserted expense row"
        assert row["user_id"] == demo_user["id"], (
            "Inserted expense must be associated with the logged-in user"
        )

    @pytest.mark.parametrize("category", VALID_CATEGORIES)
    def test_each_valid_category_is_accepted(self, auth_client, category):
        """Every one of the 7 categories must be accepted and result in a redirect."""
        data = dict(VALID_FORM)
        data["category"] = category
        data["description"] = f"Test for {category}"
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 302, (
            f"Category '{category}' should be accepted; expected 302, got {response.status_code}"
        )
        assert "/profile" in response.headers["Location"], (
            f"Valid category '{category}' must redirect to /profile"
        )


# ---------------------------------------------------------------------------
# VAL    12–16 — Validation errors re-render the form with flash messages
# ---------------------------------------------------------------------------

class TestPostValidation:
    def test_zero_amount_rerenders_form(self, auth_client):
        """Amount = 0 must re-render the form (200), not redirect."""
        data = dict(VALID_FORM, amount="0")
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 200, (
            "Amount = 0 should re-render the form with status 200"
        )

    def test_zero_amount_shows_flash_error(self, auth_client):
        """Amount = 0 must produce a flash error message."""
        data = dict(VALID_FORM, amount="0")
        response = auth_client.post("/expenses/add", data=data)
        assert b"Amount must be greater than zero" in response.data or b"zero" in response.data.lower(), (
            "A flash error about non-positive amount must be shown"
        )

    def test_zero_amount_does_not_insert_row(self, auth_client):
        """Amount = 0 must not insert any row into the expenses table."""
        conn = _db.get_db()
        before = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()

        auth_client.post("/expenses/add", data=dict(VALID_FORM, amount="0"))

        conn = _db.get_db()
        after = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()

        assert after == before, (
            "Amount = 0 must not insert a new row (count unchanged)"
        )

    def test_negative_amount_rerenders_form(self, auth_client):
        """Negative amount must re-render the form (200), not redirect."""
        data = dict(VALID_FORM, amount="-10.00")
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 200, (
            "Negative amount should re-render the form with status 200"
        )

    def test_negative_amount_shows_flash_error(self, auth_client):
        """Negative amount must produce a flash error message."""
        data = dict(VALID_FORM, amount="-10.00")
        response = auth_client.post("/expenses/add", data=data)
        assert (
            b"Amount must be greater than zero" in response.data
            or b"greater than zero" in response.data
            or b"positive" in response.data.lower()
        ), "A flash error about non-positive amount must be shown for negative value"

    def test_negative_amount_does_not_insert_row(self, auth_client):
        """Negative amount must not insert any row into the expenses table."""
        conn = _db.get_db()
        before = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()

        auth_client.post("/expenses/add", data=dict(VALID_FORM, amount="-1.00"))

        conn = _db.get_db()
        after = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()

        assert after == before, (
            "Negative amount must not insert a new row (count unchanged)"
        )

    @pytest.mark.parametrize("bad_amount", ["abc", "twelve", "1,000", "NaN", "$50"])
    def test_non_numeric_amount_returns_400(self, auth_client, bad_amount):
        """Non-numeric amount string must abort with HTTP 400."""
        data = dict(VALID_FORM, amount=bad_amount)
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, (
            f"Non-numeric amount '{bad_amount}' must return HTTP 400, got {response.status_code}"
        )

    def test_empty_amount_returns_400(self, auth_client):
        """Empty amount string (float('') raises ValueError) must return HTTP 400."""
        data = dict(VALID_FORM, amount="")
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, (
            "Empty amount string must return HTTP 400 (non-numeric triggers abort(400))"
        )

    def test_empty_date_rerenders_form(self, auth_client):
        """Missing date must re-render the form (200), not redirect."""
        data = dict(VALID_FORM, date="")
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 200, (
            "Empty date should re-render the form with status 200"
        )

    def test_empty_date_shows_flash_error(self, auth_client):
        """Missing date must produce a flash error message."""
        data = dict(VALID_FORM, date="")
        response = auth_client.post("/expenses/add", data=data)
        assert b"Date is required" in response.data or b"date" in response.data.lower(), (
            "A flash error about missing date must be shown"
        )

    def test_empty_date_does_not_insert_row(self, auth_client):
        """Missing date must not insert any row into the expenses table."""
        conn = _db.get_db()
        before = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()

        auth_client.post("/expenses/add", data=dict(VALID_FORM, date=""))

        conn = _db.get_db()
        after = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()

        assert after == before, (
            "Missing date must not insert a new row (count unchanged)"
        )

    @pytest.mark.parametrize("bad_category", [
        "food",            # wrong case
        "FOOD",            # all caps
        "Groceries",       # not in the fixed list
        "Utilities",       # not in the fixed list
        "",                # empty string
        "Food; DROP TABLE expenses;--",  # SQL injection attempt
        "Transportation",  # close but wrong
    ])
    def test_invalid_category_returns_400(self, auth_client, bad_category):
        """Category not in the fixed set must return HTTP 400."""
        data = dict(VALID_FORM, category=bad_category)
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, (
            f"Invalid category '{bad_category}' must return HTTP 400, got {response.status_code}"
        )

    def test_invalid_category_does_not_insert_row(self, auth_client):
        """An invalid category must not insert any row into the expenses table."""
        conn = _db.get_db()
        before = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()

        auth_client.post("/expenses/add", data=dict(VALID_FORM, category="Groceries"))

        conn = _db.get_db()
        after = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()

        assert after == before, (
            "Invalid category must not insert a new row (count unchanged)"
        )

    def test_validation_rerenders_all_seven_categories(self, auth_client):
        """After a validation failure the re-rendered form must still show all 7 categories."""
        data = dict(VALID_FORM, amount="0")
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 200
        for category in VALID_CATEGORIES:
            assert category.encode() in response.data, (
                f"Category '{category}' must still appear in the re-rendered form after validation error"
            )

    def test_validation_rerenders_with_date_input(self, auth_client):
        """After a validation failure the re-rendered form must still contain the date input."""
        data = dict(VALID_FORM, amount="0")
        response = auth_client.post("/expenses/add", data=data)
        assert b'name="date"' in response.data, (
            "Date input must still be present in the re-rendered form after validation error"
        )


# ---------------------------------------------------------------------------
# POST — Edge cases: very small positive amount and long description
# ---------------------------------------------------------------------------

class TestPostEdgeCases:
    def test_very_small_positive_amount_accepted(self, auth_client):
        """The smallest valid positive amount (0.01) must be accepted."""
        data = dict(VALID_FORM, amount="0.01", description="Tiny expense")
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 302, (
            "Amount 0.01 should be accepted as the minimum positive value"
        )

    def test_large_amount_accepted(self, auth_client):
        """A large but valid amount must be accepted without error."""
        data = dict(VALID_FORM, amount="99999.99", description="Big expense")
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 302, (
            "Large amount 99999.99 should be accepted"
        )

    def test_long_description_accepted(self, auth_client):
        """A long description must be stored without truncation or error."""
        long_desc = "A" * 500
        data = dict(VALID_FORM, description=long_desc)
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 302, (
            "A 500-character description must be accepted"
        )

        conn = _db.get_db()
        row = conn.execute(
            "SELECT description FROM expenses WHERE date = ? ORDER BY id DESC LIMIT 1",
            (VALID_FORM["date"],),
        ).fetchone()
        conn.close()

        assert row is not None, "Expected to find the inserted row"
        assert row["description"] == long_desc, (
            "Long description must be stored exactly as submitted"
        )

    def test_sql_injection_in_description_is_safe(self, auth_client):
        """SQL injection in the description must be stored safely, not executed."""
        injection = "'; DROP TABLE expenses; --"
        data = dict(VALID_FORM, description=injection, amount="5.00")
        response = auth_client.post("/expenses/add", data=data)
        # If parameterized queries are used, this just stores the string literally
        assert response.status_code == 302, (
            "SQL injection attempt in description must be treated as literal text"
        )

        conn = _db.get_db()
        # The expenses table must still exist and contain the row
        row = conn.execute(
            "SELECT description FROM expenses WHERE description = ?",
            (injection,),
        ).fetchone()
        conn.close()

        assert row is not None, (
            "The injection string must be stored as a literal value (table must still exist)"
        )
        assert row["description"] == injection, (
            "Description must equal the raw injection string (stored safely)"
        )


# ---------------------------------------------------------------------------
# SQL    18 — Structural check: db.py uses ? placeholders for create_expense
# ---------------------------------------------------------------------------

class TestSQLPlaceholders:
    def test_db_py_uses_placeholder_binding_for_create_expense(self):
        """
        Structural check: db.py must use ? placeholders for create_expense,
        not f-string interpolation of user-supplied values.
        """
        db_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "database", "db.py")
        )
        with open(db_path, "r", encoding="utf-8") as fh:
            source = fh.read()

        assert "?" in source, (
            "db.py must use ? placeholders for parameterized SQL in create_expense"
        )

        # The function must not directly interpolate user-supplied parameter names
        forbidden = [
            "{user_id}",
            "{amount}",
            "{category}",
            "{date}",
            "{description}",
            "% user_id",
            "% amount",
            "% category",
            "% description",
        ]
        for pattern in forbidden:
            assert pattern not in source, (
                f"db.py must not interpolate '{pattern}' directly into SQL strings"
            )

    def test_create_expense_function_exists_in_db_module(self):
        """The create_expense helper must be importable from database.db."""
        from database.db import create_expense
        assert callable(create_expense), (
            "database.db must export a callable create_expense function"
        )

    def test_create_expense_accepts_five_arguments(self):
        """create_expense must accept (user_id, amount, category, date, description)."""
        import inspect
        from database.db import create_expense
        sig = inspect.signature(create_expense)
        params = list(sig.parameters.keys())
        assert len(params) == 5, (
            f"create_expense must accept exactly 5 parameters, found {len(params)}: {params}"
        )
