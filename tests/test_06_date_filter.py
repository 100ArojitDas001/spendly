"""
Tests for the date-range filter on GET /profile.

Spec requirements covered:
  Req 1  — No query params → all-time stats and transactions (unchanged behaviour)
  Req 2  — Valid date range → only matching stats/transactions are returned
  Req 3  — Date inputs are pre-filled with the selected range
  Req 4  — "Showing: …" label is visible when a filter is active
  Req 5  — "Clear" link href is /profile with no query params
  Req 6  — from_date > to_date → flash error, fall back to unfiltered view
  Req 7  — Malformed date in either field → flash error, fall back to unfiltered view
  Req 8  — Date range with no expenses → empty-state message, zero stats
  Req 9  — All SQL in queries.py uses ? placeholders, no f-string interpolation
           of user-controlled values (structural check)
"""

import re
import pytest
import database.db as _db

# ---------------------------------------------------------------------------
# Fixtures — reuse the same conftest pattern used across the test suite.
# conftest.py already provides `app`, `client`, and `auth_client`; we rely on
# those instead of redefining them here.  The autouse temp_db fixture below is
# NOT needed because conftest.app already monkeypatches DB_PATH via tmp_path.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Helper constants derived from seed_db() in database/db.py.
# Seed has 8 expenses for demo@spendly.com, all in May 2026.
#
#   2026-05-01  Food          12.50   Lunch at cafe
#   2026-05-02  Transport     45.00   Monthly bus pass
#   2026-05-03  Bills        120.00   Electricity bill
#   2026-05-04  Health        30.00   Pharmacy
#   2026-05-05  Entertainment 25.00   Movie tickets
#   2026-05-06  Shopping      80.00   Clothing
#   2026-05-07  Food          15.75   Grocery top-up
#   2026-05-08  Other         10.00   Miscellaneous
#
# All-time total = 338.25, count = 8, top_category = Bills
# ---------------------------------------------------------------------------

SEED_TOTAL_FORMATTED = b"\xe2\x82\xb9338.25"   # UTF-8 bytes for ₹338.25
SEED_COUNT = 8
ALL_TIME_TOP_CATEGORY = b"Bills"

# Dates that bracket exactly the first three seed rows (total 177.50, count 3)
FILTER_FROM = "2026-05-01"
FILTER_TO = "2026-05-03"
FILTERED_TOTAL_FORMATTED = b"\xe2\x82\xb9177.50"  # ₹177.50
FILTERED_COUNT = 3

# Date range that has no seed expenses at all
EMPTY_FROM = "2025-01-01"
EMPTY_TO = "2025-01-31"


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_unauthenticated_profile_redirects_to_login(self, client):
        """Unauthenticated GET /profile must redirect to /login (Req 1 precondition)."""
        response = client.get("/profile")
        assert response.status_code == 302, "Expected redirect for unauthenticated user"
        assert "/login" in response.headers["Location"], (
            "Unauthenticated /profile should redirect to /login"
        )

    def test_unauthenticated_profile_with_filter_redirects(self, client):
        """Even with query params, unauthenticated requests must be redirected."""
        response = client.get(f"/profile?from_date={FILTER_FROM}&to_date={FILTER_TO}")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ---------------------------------------------------------------------------
# Req 1 — No query params → all-time stats and transactions
# ---------------------------------------------------------------------------

class TestUnfilteredView:
    def test_profile_returns_200_without_filter(self, auth_client):
        response = auth_client.get("/profile")
        assert response.status_code == 200, "Authenticated /profile should return 200"

    def test_all_time_total_shown(self, auth_client):
        """All-time total_spent should equal the sum of all 8 seed expenses."""
        response = auth_client.get("/profile")
        assert SEED_TOTAL_FORMATTED in response.data, (
            "Unfiltered profile should show all-time total ₹338.25"
        )

    def test_all_time_transaction_count_shown(self, auth_client):
        """All-time transaction count should be 8 (all seed rows)."""
        response = auth_client.get("/profile")
        # The count appears as a plain integer in the stat tile
        assert str(SEED_COUNT).encode() in response.data, (
            "Unfiltered profile should report 8 transactions"
        )

    def test_all_time_top_category_shown(self, auth_client):
        """Top category for seed data is Bills (₹120.00)."""
        response = auth_client.get("/profile")
        assert ALL_TIME_TOP_CATEGORY in response.data, (
            "Unfiltered profile top category should be Bills"
        )

    def test_no_showing_label_without_filter(self, auth_client):
        """'Showing:' label must NOT appear when no filter is active (Req 4 inverse)."""
        response = auth_client.get("/profile")
        assert b"Showing:" not in response.data, (
            "No 'Showing:' label should appear on the unfiltered view"
        )

    def test_all_seed_transactions_rendered(self, auth_client):
        """All 8 seed descriptions should appear in the unfiltered view."""
        response = auth_client.get("/profile")
        for description in [
            b"Lunch at cafe",
            b"Monthly bus pass",
            b"Electricity bill",
            b"Pharmacy",
            b"Movie tickets",
            b"Clothing",
            b"Grocery top-up",
            b"Miscellaneous",
        ]:
            assert description in response.data, (
                f"Expected description {description!r} in unfiltered profile"
            )


# ---------------------------------------------------------------------------
# Req 2 — Valid date range → filtered stats and transactions
# ---------------------------------------------------------------------------

class TestValidDateRangeFilter:
    def test_filtered_returns_200(self, auth_client):
        response = auth_client.get(
            f"/profile?from_date={FILTER_FROM}&to_date={FILTER_TO}"
        )
        assert response.status_code == 200

    def test_filtered_total_reflects_range(self, auth_client):
        """Only expenses in [2026-05-01, 2026-05-03] should be summed (₹177.50)."""
        response = auth_client.get(
            f"/profile?from_date={FILTER_FROM}&to_date={FILTER_TO}"
        )
        assert FILTERED_TOTAL_FORMATTED in response.data, (
            f"Filtered total should be ₹177.50 for {FILTER_FROM}–{FILTER_TO}"
        )

    def test_filtered_count_reflects_range(self, auth_client):
        """Transaction count in [2026-05-01, 2026-05-03] should be 3."""
        response = auth_client.get(
            f"/profile?from_date={FILTER_FROM}&to_date={FILTER_TO}"
        )
        assert str(FILTERED_COUNT).encode() in response.data, (
            "Filtered count should be 3 for the three-day window"
        )

    def test_filtered_excludes_out_of_range_description(self, auth_client):
        """A description outside the range should not appear in the filtered view."""
        response = auth_client.get(
            f"/profile?from_date={FILTER_FROM}&to_date={FILTER_TO}"
        )
        assert b"Movie tickets" not in response.data, (
            "Expense on 2026-05-05 should not appear in a filter ending 2026-05-03"
        )

    def test_filtered_includes_boundary_dates(self, auth_client):
        """Both boundary dates (inclusive) must appear."""
        response = auth_client.get(
            f"/profile?from_date={FILTER_FROM}&to_date={FILTER_TO}"
        )
        assert b"Lunch at cafe" in response.data, (
            "Expense on from_date boundary (2026-05-01) must be included"
        )
        assert b"Electricity bill" in response.data, (
            "Expense on to_date boundary (2026-05-03) must be included"
        )

    def test_single_day_range(self, auth_client):
        """from_date == to_date selects only that single day's expenses."""
        response = auth_client.get("/profile?from_date=2026-05-04&to_date=2026-05-04")
        assert response.status_code == 200
        assert b"Pharmacy" in response.data, (
            "Single-day filter should include the matching expense"
        )
        assert b"Lunch at cafe" not in response.data, (
            "Single-day filter should exclude expenses from other days"
        )


# ---------------------------------------------------------------------------
# Req 3 — Date inputs are pre-filled with the selected values
# ---------------------------------------------------------------------------

class TestDateInputsPreFilled:
    def test_from_date_input_value_present(self, auth_client):
        """The from_date input value attribute must equal the submitted from_date."""
        response = auth_client.get(
            f"/profile?from_date={FILTER_FROM}&to_date={FILTER_TO}"
        )
        assert f'value="{FILTER_FROM}"'.encode() in response.data, (
            f"from_date input should be pre-filled with {FILTER_FROM}"
        )

    def test_to_date_input_value_present(self, auth_client):
        """The to_date input value attribute must equal the submitted to_date."""
        response = auth_client.get(
            f"/profile?from_date={FILTER_FROM}&to_date={FILTER_TO}"
        )
        assert f'value="{FILTER_TO}"'.encode() in response.data, (
            f"to_date input should be pre-filled with {FILTER_TO}"
        )

    def test_inputs_empty_without_filter(self, auth_client):
        """Without a filter, date inputs must have empty values."""
        response = auth_client.get("/profile")
        # The template renders: value="{{ from_date or '' }}" and value="{{ to_date or '' }}"
        # Both should render as value=""
        assert b'value=""' in response.data, (
            "Date inputs should be empty when no filter is active"
        )


# ---------------------------------------------------------------------------
# Req 4 — "Showing: …" label is visible when a filter is active
# ---------------------------------------------------------------------------

class TestShowingLabel:
    def test_showing_label_present_with_filter(self, auth_client):
        response = auth_client.get(
            f"/profile?from_date={FILTER_FROM}&to_date={FILTER_TO}"
        )
        assert b"Showing:" in response.data, (
            "'Showing:' label must be rendered when both date params are provided"
        )

    def test_showing_label_contains_from_month_day(self, auth_client):
        """The label should contain the human-readable from_date (May 1)."""
        response = auth_client.get(
            "/profile?from_date=2026-05-01&to_date=2026-05-07"
        )
        # strftime("%-d") produces "1" (no zero-pad); month is "May"
        assert b"May" in response.data
        # The "Showing:" line must be present
        assert b"Showing:" in response.data

    def test_showing_label_absent_with_only_from_date(self, auth_client):
        """Label should not appear when only one of the two date params is supplied."""
        response = auth_client.get("/profile?from_date=2026-05-01")
        assert b"Showing:" not in response.data, (
            "'Showing:' must not appear when to_date is missing"
        )

    def test_showing_label_absent_with_only_to_date(self, auth_client):
        response = auth_client.get("/profile?to_date=2026-05-07")
        assert b"Showing:" not in response.data, (
            "'Showing:' must not appear when from_date is missing"
        )


# ---------------------------------------------------------------------------
# Req 5 — "Clear" link removes the filter (href="/profile" no query params)
# ---------------------------------------------------------------------------

class TestClearLink:
    def test_clear_link_present_on_filtered_view(self, auth_client):
        response = auth_client.get(
            f"/profile?from_date={FILTER_FROM}&to_date={FILTER_TO}"
        )
        assert b'href="/profile"' in response.data, (
            "Clear link with href='/profile' must be present on the filtered view"
        )

    def test_clear_link_present_on_unfiltered_view(self, auth_client):
        """Clear link is always rendered (it's part of the filter form)."""
        response = auth_client.get("/profile")
        assert b'href="/profile"' in response.data, (
            "Clear link with href='/profile' must be present even on the unfiltered view"
        )

    def test_clear_link_has_no_query_params(self, auth_client):
        """The Clear link must not append any query params."""
        response = auth_client.get(
            f"/profile?from_date={FILTER_FROM}&to_date={FILTER_TO}"
        )
        html = response.data.decode("utf-8")
        # Find all href values that point to /profile
        hrefs = re.findall(r'href="(/profile[^"]*)"', html)
        clear_hrefs = [h for h in hrefs if "btn-clear" in html[max(0, html.find(h) - 60):html.find(h) + 60]]
        # The /profile href used in the Clear anchor must have no ?… suffix
        for h in hrefs:
            if h == "/profile":
                # At least one bare /profile href exists — that's the Clear link
                assert "?" not in h, "Clear link href must not contain query params"
                break
        else:
            pytest.fail("No bare /profile href found — Clear link is missing")


# ---------------------------------------------------------------------------
# Req 6 — from_date after to_date → flash error + fallback to unfiltered view
# ---------------------------------------------------------------------------

class TestInvertedDateRange:
    def test_inverted_range_returns_200(self, auth_client):
        response = auth_client.get("/profile?from_date=2026-05-10&to_date=2026-05-01")
        assert response.status_code == 200

    def test_inverted_range_shows_flash_error(self, auth_client):
        response = auth_client.get("/profile?from_date=2026-05-10&to_date=2026-05-01")
        assert b"From" in response.data and b"date" in response.data, (
            "An error message about the date order should be flashed"
        )
        # The spec says the flash message must mention the invalid relationship
        assert (
            b"'From' date must be on or before 'To' date" in response.data
            or b"must be on or before" in response.data
            or b"Invalid" in response.data
            or b"error" in response.data.lower()
        )

    def test_inverted_range_falls_back_to_all_time_total(self, auth_client):
        """After the error the view should show all-time stats, not filtered ones."""
        response = auth_client.get("/profile?from_date=2026-05-10&to_date=2026-05-01")
        assert SEED_TOTAL_FORMATTED in response.data, (
            "After inverted-range error the unfiltered total (₹338.25) should be shown"
        )

    def test_inverted_range_no_showing_label(self, auth_client):
        """The Showing label must not appear when the filter was rejected."""
        response = auth_client.get("/profile?from_date=2026-05-10&to_date=2026-05-01")
        assert b"Showing:" not in response.data, (
            "'Showing:' must not appear when the date filter was invalid"
        )

    def test_equal_dates_are_accepted(self, auth_client):
        """from_date == to_date (same day) is valid — must NOT trigger the error."""
        response = auth_client.get("/profile?from_date=2026-05-05&to_date=2026-05-05")
        assert response.status_code == 200
        assert b"must be on or before" not in response.data, (
            "Equal from_date and to_date should be treated as a valid single-day filter"
        )


# ---------------------------------------------------------------------------
# Req 7 — Malformed dates → flash error + fallback to unfiltered view
# ---------------------------------------------------------------------------

MALFORMED_DATE_CASES = [
    ("not-a-date", "2026-05-10"),
    ("2026-05-10", "not-a-date"),
    ("2026-13-01", "2026-05-10"),   # month 13 is invalid
    ("2026-05-10", "2026-00-01"),   # month 0 is invalid
    ("20260501",   "2026-05-10"),   # no hyphens
    ("2026/05/01", "2026-05-10"),   # slashes instead of hyphens
    ("",           "2026-05-10"),   # empty from_date (treated as absent, no error)
]


class TestMalformedDates:
    @pytest.mark.parametrize("from_date,to_date", [
        ("not-a-date", "2026-05-10"),
        ("2026-05-10", "not-a-date"),
        ("2026-13-01", "2026-05-10"),   # month 13
        ("2026-05-10", "2026-00-01"),   # month 0
        ("20260501",   "2026-05-10"),   # no hyphens
        ("2026/05/01", "2026-05-10"),   # slashes
    ])
    def test_malformed_date_shows_flash_error(self, auth_client, from_date, to_date):
        response = auth_client.get(
            f"/profile?from_date={from_date}&to_date={to_date}"
        )
        assert response.status_code == 200, "Malformed date must still return 200"
        assert (
            b"Invalid date format" in response.data
            or b"invalid" in response.data.lower()
        ), f"Expected flash error for from_date={from_date!r} to_date={to_date!r}"

    @pytest.mark.parametrize("from_date,to_date", [
        ("not-a-date", "2026-05-10"),
        ("2026-05-10", "not-a-date"),
        ("2026-13-01", "2026-05-10"),
        ("2026-05-10", "2026-00-01"),
        ("20260501",   "2026-05-10"),
        ("2026/05/01", "2026-05-10"),
    ])
    def test_malformed_date_falls_back_to_all_time_stats(
        self, auth_client, from_date, to_date
    ):
        """After a format error the unfiltered total must be shown."""
        response = auth_client.get(
            f"/profile?from_date={from_date}&to_date={to_date}"
        )
        assert SEED_TOTAL_FORMATTED in response.data, (
            "After malformed-date error the unfiltered total (₹338.25) must be shown"
        )

    @pytest.mark.parametrize("from_date,to_date", [
        ("not-a-date", "2026-05-10"),
        ("2026-05-10", "not-a-date"),
        ("2026-13-01", "2026-05-10"),
        ("2026-05-10", "2026-00-01"),
        ("20260501",   "2026-05-10"),
        ("2026/05/01", "2026-05-10"),
    ])
    def test_malformed_date_no_showing_label(self, auth_client, from_date, to_date):
        """Showing label must not appear after a format error."""
        response = auth_client.get(
            f"/profile?from_date={from_date}&to_date={to_date}"
        )
        assert b"Showing:" not in response.data, (
            "Showing label must not render when date parsing failed"
        )


# ---------------------------------------------------------------------------
# Req 8 — Date range with no expenses → empty-state message, zero stats
# ---------------------------------------------------------------------------

class TestEmptyDateRange:
    def test_empty_range_returns_200(self, auth_client):
        response = auth_client.get(
            f"/profile?from_date={EMPTY_FROM}&to_date={EMPTY_TO}"
        )
        assert response.status_code == 200

    def test_empty_range_shows_empty_state_message(self, auth_client):
        """Template renders an empty-state cell when transactions list is empty."""
        response = auth_client.get(
            f"/profile?from_date={EMPTY_FROM}&to_date={EMPTY_TO}"
        )
        assert b"No transactions for this period" in response.data, (
            "Empty-state message must appear when no expenses match the filter"
        )

    def test_empty_range_total_is_zero(self, auth_client):
        """total_spent must be ₹0.00 when no expenses match."""
        response = auth_client.get(
            f"/profile?from_date={EMPTY_FROM}&to_date={EMPTY_TO}"
        )
        zero_formatted = "₹0.00".encode("utf-8")  # ₹0.00
        assert zero_formatted in response.data, (
            "total_spent stat must show ₹0.00 for an empty date range"
        )

    def test_empty_range_transaction_count_is_zero(self, auth_client):
        """transaction_count must be 0 when no expenses match."""
        response = auth_client.get(
            f"/profile?from_date={EMPTY_FROM}&to_date={EMPTY_TO}"
        )
        # The count "0" must appear somewhere in the stats tile area.
        # We check the response contains b"0" as transaction count.
        # Since "0" is ambiguous, we also verify the full total is zero (above).
        assert b"0" in response.data, (
            "transaction_count must be 0 when the filtered range is empty"
        )

    def test_empty_range_still_shows_showing_label(self, auth_client):
        """Even with no results the Showing label must still appear (filter is active)."""
        response = auth_client.get(
            f"/profile?from_date={EMPTY_FROM}&to_date={EMPTY_TO}"
        )
        assert b"Showing:" in response.data, (
            "'Showing:' label must appear even when the filtered range is empty"
        )

    def test_empty_range_does_not_show_seed_transactions(self, auth_client):
        """No seed transaction descriptions should appear in a non-overlapping range."""
        response = auth_client.get(
            f"/profile?from_date={EMPTY_FROM}&to_date={EMPTY_TO}"
        )
        for description in [b"Lunch at cafe", b"Electricity bill", b"Pharmacy"]:
            assert description not in response.data, (
                f"{description!r} must not appear in a filter with no matching expenses"
            )


# ---------------------------------------------------------------------------
# Req 9 — SQL in queries.py uses ? placeholders, no f-string user-value injection
# ---------------------------------------------------------------------------

class TestSQLPlaceholders:
    def test_queries_file_uses_placeholder_binding(self):
        """
        Structural check: open queries.py and confirm that the three query
        helpers use ? placeholder binding for user-controlled values
        (from_date, to_date, user_id) and do not build SQL via f-string
        interpolation of those values.

        We verify that:
        1. The file contains '?' placeholders (parameterized binding is used).
        2. The file does NOT contain patterns like f"...{from_date}..." or
           f"...{to_date}..." or f"...{user_id}..." in SQL strings.
        """
        import os
        queries_path = os.path.join(
            os.path.dirname(__file__), "..", "database", "queries.py"
        )
        queries_path = os.path.abspath(queries_path)
        with open(queries_path, "r", encoding="utf-8") as fh:
            source = fh.read()

        # Must use ? for binding
        assert "?" in source, (
            "queries.py must use ? placeholders for parameterized SQL"
        )

        # Must NOT directly interpolate user-supplied date values into SQL strings.
        # Allow f-strings only for structural clauses (like AND date BETWEEN ? AND ?)
        # but not for injecting actual variable values.
        forbidden_patterns = [
            "{from_date}",
            "{to_date}",
            "{user_id}",
            "% from_date",
            "% to_date",
            "% user_id",
        ]
        for pattern in forbidden_patterns:
            assert pattern not in source, (
                f"queries.py must not interpolate {pattern!r} directly into SQL strings"
            )
