import math
import sqlite3
from datetime import datetime

from flask import Flask, render_template, session, redirect, url_for, request, abort, flash

from database.db import get_db, init_db, seed_db, get_user_by_email, verify_password, create_user, create_expense
from database.queries import get_recent_transactions, get_user_by_id, get_summary_stats, get_category_breakdown

app = Flask(__name__)
app.secret_key = "dev-secret-key"

EXPENSE_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not all([name, email, password, confirm]):
            flash("All fields are required.")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.")
            return render_template("register.html")
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            flash("Email already registered.")
            return render_template("register.html")
        flash("Account created! Please sign in.")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = get_user_by_email(email)
        if user and verify_password(user, password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("profile"))
        flash("Invalid email or password.")
        return render_template("login.html")
    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    user = get_user_by_id(user_id)
    if user is None:
        abort(404)

    from_date = request.args.get("from_date", "").strip() or None
    to_date = request.args.get("to_date", "").strip() or None

    from_dt = to_dt = None
    if from_date or to_date:
        try:
            if from_date:
                from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            if to_date:
                to_dt = datetime.strptime(to_date, "%Y-%m-%d")
        except ValueError:
            flash("Invalid date format. Please use the date picker.")
            from_date = to_date = None
            from_dt = to_dt = None

    if from_date and to_date and from_date > to_date:
        flash("'From' date must be on or before 'To' date.")
        from_date = to_date = None
        from_dt = to_dt = None

    from_display = from_dt.strftime("%b %-d") if from_dt else None
    to_display = to_dt.strftime("%b %-d") if to_dt else None

    raw = get_summary_stats(user_id, from_date=from_date, to_date=to_date)
    stats = {
        "total_spent":       f"₹{raw['total_spent']:.2f}",
        "transaction_count": raw["transaction_count"],
        "top_category":      raw["top_category"],
    }
    transactions = get_recent_transactions(user_id, from_date=from_date, to_date=to_date)
    categories = get_category_breakdown(user_id, from_date=from_date, to_date=to_date)
    return render_template("profile.html",
                           user=user, stats=stats,
                           transactions=transactions, categories=categories,
                           from_date=from_date, to_date=to_date,
                           from_display=from_display, to_display=to_display)


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    def _render_form():
        return render_template("add_expense.html", categories=EXPENSE_CATEGORIES,
                               today=datetime.today().strftime("%Y-%m-%d"))

    if request.method == "POST":
        amount_raw = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        date = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip()

        try:
            amount = float(amount_raw)
        except ValueError:
            abort(400)

        if not math.isfinite(amount):
            abort(400)

        if amount <= 0:
            flash("Amount must be greater than zero.")
            return _render_form()

        if not date:
            flash("Date is required.")
            return _render_form()

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            flash("Date must be in YYYY-MM-DD format.")
            return _render_form()

        if category not in EXPENSE_CATEGORIES:
            abort(400)

        create_expense(session["user_id"], amount, category, date, description)
        return redirect(url_for("profile"))

    return _render_form()


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
