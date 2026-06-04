import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email

app = Flask(__name__)
app.secret_key = "spendly-dev-secret"  # TODO: load from env var in production

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name or len(name) > 100:
        return render_template("register.html", error="Please enter your full name."), 400
    if not email:
        return render_template("register.html", error="Please enter your email address."), 400
    confirm_password = request.form.get("confirm_password", "")

    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters."), 400
    if password != confirm_password:
        return render_template("register.html", error="Passwords do not match."), 400

    try:
        create_user(name, email, generate_password_hash(password))
    except sqlite3.IntegrityError:
        return render_template("register.html", error="An account with that email already exists."), 400

    flash("Account created — please sign in.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password."), 400

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been signed out.")
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "member_since": "May 2026",
        "initials": "DU",
    }
    stats = {
        "total_spent": "$388.25",
        "transaction_count": 8,
        "top_category": "Bills",
        "top_category_amount": "$120.00",
    }
    transactions = [
        {"date": "May 25, 2026", "description": "Restaurant dinner",  "category": "Food",          "amount": "$60.00"},
        {"date": "May 21, 2026", "description": "Miscellaneous",       "category": "Other",         "amount": "$15.75"},
        {"date": "May 18, 2026", "description": "New shoes",           "category": "Shopping",      "amount": "$80.00"},
        {"date": "May 14, 2026", "description": "Movie tickets",       "category": "Entertainment", "amount": "$25.00"},
        {"date": "May 10, 2026", "description": "Pharmacy",            "category": "Health",        "amount": "$30.00"},
        {"date": "May 08, 2026", "description": "Electricity bill",    "category": "Bills",         "amount": "$120.00"},
        {"date": "May 05, 2026", "description": "Bus pass top-up",     "category": "Transport",     "amount": "$12.00"},
        {"date": "May 02, 2026", "description": "Grocery run",         "category": "Food",          "amount": "$45.50"},
    ]
    categories = [
        {"name": "Bills",         "amount": "$120.00", "pct": 31},
        {"name": "Food",          "amount": "$105.50", "pct": 27},
        {"name": "Shopping",      "amount": "$80.00",  "pct": 21},
        {"name": "Health",        "amount": "$30.00",  "pct": 8},
        {"name": "Entertainment", "amount": "$25.00",  "pct": 6},
        {"name": "Other",         "amount": "$15.75",  "pct": 4},
        {"name": "Transport",     "amount": "$12.00",  "pct": 3},
    ]
    return render_template("profile.html", user=user, stats=stats,
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


if __name__ == "__main__":
    app.run(debug=True, port=5001)
