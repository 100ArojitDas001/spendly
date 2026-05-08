from flask import Flask, render_template, session, redirect, url_for, request
from database.db import get_db, init_db, seed_db, get_user_by_email, verify_password

app = Flask(__name__)
app.secret_key = "dev-secret-key"


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register")
def register():
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

    user = {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "initials": "DU",
        "member_since": "May 2026",
    }
    stats = {
        "total_spent": "$338.25",
        "transaction_count": 8,
        "top_category": "Bills",
    }
    transactions = [
        {"date": "May 08", "description": "Miscellaneous",    "category": "Other",         "amount": "$10.00"},
        {"date": "May 07", "description": "Grocery top-up",   "category": "Food",          "amount": "$15.75"},
        {"date": "May 06", "description": "Clothing",         "category": "Shopping",      "amount": "$80.00"},
        {"date": "May 05", "description": "Movie tickets",    "category": "Entertainment", "amount": "$25.00"},
        {"date": "May 04", "description": "Pharmacy",         "category": "Health",        "amount": "$30.00"},
        {"date": "May 03", "description": "Electricity bill", "category": "Bills",         "amount": "$120.00"},
        {"date": "May 02", "description": "Monthly bus pass", "category": "Transport",     "amount": "$45.00"},
        {"date": "May 01", "description": "Lunch at cafe",    "category": "Food",          "amount": "$12.50"},
    ]
    categories = [
        {"name": "Bills",         "amount": "$120.00", "pct": 36},
        {"name": "Shopping",      "amount": "$80.00",  "pct": 24},
        {"name": "Transport",     "amount": "$45.00",  "pct": 13},
        {"name": "Health",        "amount": "$30.00",  "pct": 9},
        {"name": "Entertainment", "amount": "$25.00",  "pct": 7},
        {"name": "Food",          "amount": "$28.25",  "pct": 8},
        {"name": "Other",         "amount": "$10.00",  "pct": 3},
    ]
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
