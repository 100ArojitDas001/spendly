import sqlite3
from flask import Flask, render_template, session, redirect, url_for, request, abort, flash
from database.db import get_db, init_db, seed_db, get_user_by_email, verify_password, create_user
from database.queries import get_recent_transactions, get_user_by_id, get_summary_stats, get_category_breakdown

app = Flask(__name__)
app.secret_key = "dev-secret-key"


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
        return render_template("login.html", error="Invalid email or password.")
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

    raw = get_summary_stats(user_id)
    stats = {
        "total_spent":       f"₹{raw['total_spent']:.2f}",
        "transaction_count": raw["transaction_count"],
        "top_category":      raw["top_category"],
    }
    transactions = get_recent_transactions(user_id)
    categories = get_category_breakdown(user_id)
    return render_template("profile.html",
                           user=user, stats=stats,
                           transactions=transactions, categories=categories)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


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
