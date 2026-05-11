# Spec: Date Filter for Profile Page

## Overview
This feature adds a date-range filter to the profile page so users can narrow
the summary stats, transaction list, and category breakdown to a specific time
window. The filter is driven by query-string parameters (`from_date` and
`to_date`) submitted via a plain HTML form, keeping the implementation
entirely server-side with no JavaScript dependency. All three existing query
helpers are updated to accept optional date bounds, and the profile route
passes those bounds through to each helper and back to the template so the UI
can pre-fill the selected range.

## Depends on
- Step 01 — Database Setup (expenses table with `date` column)
- Step 04 — Profile Page Design (profile.html template)
- Step 05 — Backend Routes for Profile Page (get_summary_stats,
  get_recent_transactions, get_category_breakdown query helpers)

## Routes
- `GET /profile` — existing route, extended to read optional `from_date` and
  `to_date` query-string parameters and pass them to all query helpers —
  logged-in only

No new routes.

## Database changes
No database changes. The existing `expenses.date` column (TEXT, `YYYY-MM-DD`)
is used directly in `WHERE date BETWEEN ? AND ?` clauses.

## Templates
- **Modify:** `templates/profile.html`
  - Add a date-filter form above the stats/transactions section
  - Two `<input type="date">` fields: "From" and "To"
  - A "Filter" submit button and a "Clear" link that resets to the unfiltered view
  - Pre-fill both inputs with the currently active `from_date` / `to_date` values
  - Show a visible label (e.g. "Showing: May 1 – May 11") when a filter is active

## Files to change
- `app.py` — update `profile()` route to read `from_date` and `to_date` from
  `request.args`, validate them, and pass them to all three query helpers and
  to `render_template`
- `database/queries.py` — update `get_summary_stats`, `get_recent_transactions`,
  and `get_category_breakdown` to accept optional `from_date` and `to_date`
  keyword arguments; add `AND date BETWEEN ? AND ?` to each query when both
  are provided
- `templates/profile.html` — add filter form UI (see Templates section)
- `static/css/profile.css` — add styles for the filter form (if this file
  exists; otherwise add a new `static/css/profile.css` imported from
  `profile.html`)

## Files to create
- `static/css/profile.css` — only if it does not already exist; scoped styles
  for the date-filter form

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only — never interpolate dates into SQL strings
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Date validation in the route: if either param is present but malformed
  (not a valid `YYYY-MM-DD` string), flash an error and ignore both params
  rather than passing bad data to the DB layer
- If `from_date` > `to_date`, flash a validation error and render with no
  filter applied
- Query helpers must remain backwards-compatible — `from_date` and `to_date`
  default to `None`; callers that omit them get the existing all-time behaviour
- The "Clear" link must point to `url_for("profile")` with no query params

## Definition of done
- [ ] Visiting `/profile` with no query params shows all-time stats and
      transactions (existing behaviour unchanged)
- [ ] Submitting the filter form with a valid date range reloads the page and
      shows only stats and transactions whose `date` falls within that range
- [ ] Both date inputs are pre-filled with the selected range on the filtered view
- [ ] A "Showing: …" label is visible when a filter is active
- [ ] The "Clear" link removes the filter and restores the all-time view
- [ ] Entering a `from_date` after `to_date` shows a flash error and falls
      back to the unfiltered view
- [ ] Entering a malformed date in either field shows a flash error and falls
      back to the unfiltered view
- [ ] The page renders correctly when the filtered date range contains no
      expenses (stats show zeros, transaction list shows an empty-state message)
- [ ] All SQL queries use `?` placeholders — no f-strings or string
      concatenation in SQL
