import math
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email, insert_expense, get_expense_by_id, update_expense
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown, is_valid_date

app = Flask(__name__)
app.secret_key = "spendly-dev-secret"  # TODO: load from env var in production

EXPENSE_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
MAX_EXPENSE_AMOUNT = 1_000_000

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

    user = get_user_by_id(session["user_id"])
    if user is None:
        abort(404)

    start_date = request.args.get("start_date", "").strip() or None
    end_date = request.args.get("end_date", "").strip() or None

    stats = get_summary_stats(session["user_id"], start_date=start_date, end_date=end_date)
    transactions = get_recent_transactions(
        session["user_id"], start_date=start_date, end_date=end_date
    )
    categories = get_category_breakdown(session["user_id"], start_date=start_date, end_date=end_date)
    return render_template(
        "profile.html", user=user, stats=stats,
        transactions=transactions, categories=categories,
        start_date=start_date or "", end_date=end_date or "",
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "GET":
        today = datetime.now().strftime("%Y-%m-%d")
        return render_template(
            "add_expense.html",
            categories=EXPENSE_CATEGORIES,
            amount="", category="", date=today, description="",
        )

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    form_values = {
        "categories": EXPENSE_CATEGORIES,
        "amount": amount_raw,
        "category": category,
        "date": date,
        "description": description,
    }

    try:
        amount = float(amount_raw)
    except ValueError:
        return render_template(
            "add_expense.html", error="Please enter a valid amount.", **form_values
        ), 400
    if not math.isfinite(amount) or amount <= 0 or amount > MAX_EXPENSE_AMOUNT:
        return render_template(
            "add_expense.html", error="Amount must be a positive number up to ₹1,000,000.", **form_values
        ), 400

    if category not in EXPENSE_CATEGORIES:
        return render_template(
            "add_expense.html", error="Please choose a valid category.", **form_values
        ), 400

    if not is_valid_date(date):
        return render_template(
            "add_expense.html", error="Please enter a valid date.", **form_values
        ), 400

    insert_expense(session["user_id"], amount, category, date, description or None)

    flash("Expense added.")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(id)
    if expense is None:
        abort(404)
    if expense["user_id"] != session["user_id"]:
        abort(403)

    if request.method == "GET":
        return render_template(
            "edit_expense.html",
            expense_id=id,
            categories=EXPENSE_CATEGORIES,
            amount=expense["amount"], category=expense["category"],
            date=expense["date"], description=expense["description"] or "",
        )

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    form_values = {
        "expense_id": id,
        "categories": EXPENSE_CATEGORIES,
        "amount": amount_raw,
        "category": category,
        "date": date,
        "description": description,
    }

    try:
        amount = float(amount_raw)
    except ValueError:
        return render_template(
            "edit_expense.html", error="Please enter a valid amount.", **form_values
        ), 400
    if not math.isfinite(amount) or amount <= 0 or amount > MAX_EXPENSE_AMOUNT:
        return render_template(
            "edit_expense.html", error="Amount must be a positive number up to ₹1,000,000.", **form_values
        ), 400

    if category not in EXPENSE_CATEGORIES:
        return render_template(
            "edit_expense.html", error="Please choose a valid category.", **form_values
        ), 400

    if not is_valid_date(date):
        return render_template(
            "edit_expense.html", error="Please enter a valid date.", **form_values
        ), 400

    update_expense(id, amount, category, date, description or None)

    flash("Expense updated.")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
