# Spec: Add Expense

## Overview
This step turns the `GET /expenses/add` stub into a fully working add-expense flow. A logged-in user fills in a form (amount, category, date, optional description) and submits it; the expense is written to the `expenses` table and the user is redirected back to their profile. This is the first write path for expense data and makes the app useful beyond just viewing seeded records.

## Depends on
- Step 01 — Database setup (`expenses` table must exist)
- Step 02 — Registration (user accounts exist)
- Step 03 — Login / logout (session must be set)
- Step 04/05 — Profile page (redirect destination after save)

## Routes
- `GET /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate and insert the expense, then redirect to `/profile` — logged-in only

## Database changes
No new tables or columns. The `expenses` table already exists with the required fields:
`id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

A new DB helper `create_expense` must be added to `database/db.py`.

## Templates
- **Create:** `templates/add_expense.html` — form page extending `base.html`
- **Modify:** none

## Files to change
- `app.py` — replace the `add_expense` stub with GET+POST logic; import `create_expense`
- `database/db.py` — add `create_expense(user_id, amount, category, date, description)` helper

## Files to create
- `templates/add_expense.html` — add-expense form
- `static/css/add_expense.css` — page-specific styles

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only — never f-strings in SQL
- Redirect to `url_for("profile")` on successful POST
- Unauthenticated requests redirect to `url_for("login")`; do not `abort()`
- Use `abort(400)` for genuinely malformed input (non-numeric amount)
- Amount must be a positive number; validate server-side and re-render with a flash message on failure
- Category must be one of the fixed set: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- Date must be provided and in `YYYY-MM-DD` format; default the `<input type="date">` to today's date
- Description is optional (may be empty string or None)
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- Page-specific styles go in `static/css/add_expense.css`, linked from the template

## Definition of done
- [ ] `GET /expenses/add` without a session redirects to `/login`
- [ ] `GET /expenses/add` with a valid session renders the form
- [ ] Submitting the form with valid data inserts a row in `expenses` and redirects to `/profile`
- [ ] The new expense appears in the transactions list on the profile page
- [ ] Submitting with a missing or non-positive amount re-renders the form with a flash error
- [ ] Submitting with a missing date re-renders the form with a flash error
- [ ] All seven category options are present in the dropdown
- [ ] The date input defaults to today's date