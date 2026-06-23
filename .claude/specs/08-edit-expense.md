# Spec: Edit Expense

## Overview
This feature replaces the `GET /expenses/<id>/edit` stub with a real edit flow, letting a logged-in user update an existing expense's amount, category, date, and description. It mirrors the add-expense flow from Step 7 — same form layout and validation rules — but pre-fills the form with the expense's current values and updates the row instead of inserting a new one. This also adds an "Edit" link to each transaction row on the profile page, since no UI currently exposes a way to reach this route.

## Depends on
- Step 1 (database setup) — `expenses` table and `get_db()`
- Step 4/5 (profile page) — `profile.html` transactions table, `get_recent_transactions()`
- Step 7 (add expense) — `EXPENSE_CATEGORIES`, `MAX_EXPENSE_AMOUNT`, `is_valid_date()`, and the form/validation pattern in `add_expense()`

## Routes
- `GET /expenses/<int:id>/edit` — render the edit form pre-filled with the expense's current values — logged-in
- `POST /expenses/<int:id>/edit` — validate and update the expense, then redirect to `/profile` — logged-in

Both methods are handled by one `edit_expense(id)` view, replacing the current stub (same pattern as `add_expense`).

Access rules:
- Redirect to `/login` if `session.get("user_id")` is not set (same as `add_expense`).
- `abort(404)` if no expense with that `id` exists.
- `abort(403)` if the expense exists but its `user_id` does not match `session["user_id"]` — a user must never be able to view or edit another user's expense.

## Database changes
No schema changes. The `expenses` table (defined in `database/db.py`) already has the columns needed: `id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

Two new functions are needed in `database/db.py` (no existing function covers fetching a single raw expense row or updating one):

- `get_expense_by_id(expense_id)` — `SELECT * FROM expenses WHERE id = ?`, returns the row (or `None`) via `get_db()`, parameterized query.
- `update_expense(expense_id, amount, category, date, description)` — parameterized `UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ?`, commits, closes the connection.

Both functions follow the existing `insert_expense()` pattern: open connection via `get_db()`, execute parameterized query, commit, close.

## Templates
- **Create:** `templates/edit_expense.html` — copy the structure of `templates/add_expense.html` (`.auth-section` / `.auth-card` / `.form-group` / `.form-input` pattern), with these differences:
  - Title: "Edit expense" / subtitle: "Update this transaction"
  - Form `action="{{ url_for('edit_expense', id=expense_id) }}"`, `method="POST"`
  - Submit button text: "Update expense"
  - Cancel link still points to `url_for('profile')`
  - All fields pre-filled from the expense being edited (amount, category, date, description), same as the re-render-on-error pattern already used in `add_expense`
- **Modify:** `templates/profile.html` — add an "Edit" link/icon to each row in the transactions table (`.txn-table`), pointing to `url_for('edit_expense', id=txn.id)`. This requires `get_recent_transactions()` to also return the expense `id` for each transaction (currently it only returns formatted display fields — `date`, `description`, `category`, `amount` — not `id`).

## Files to change
- `app.py` — replace the `edit_expense` stub with a full `GET`/`POST` implementation modeled on `add_expense`
- `database/db.py` — add `get_expense_by_id()` and `update_expense()`
- `database/queries.py` — add `id` to the dict returned by `get_recent_transactions()` so the profile page can link to the edit route
- `templates/profile.html` — add an edit link/icon per transaction row

## Files to create
- `templates/edit_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only (`?` placeholders) — never f-strings in SQL
- Use the same validation rules as `add_expense`: amount must be a finite positive float ≤ `MAX_EXPENSE_AMOUNT`, category must be in `EXPENSE_CATEGORIES`, date must pass `is_valid_date()`
- On validation failure, re-render `edit_expense.html` with the submitted (not original) values and an error message, with a 400 status — same pattern as `add_expense`
- On success, `flash("Expense updated.")` and redirect to `url_for("profile")`
- Ownership check is mandatory: `abort(403)` if `expense["user_id"] != session["user_id"]`; `abort(404)` if the expense doesn't exist
- Use CSS variables — never hardcode hex values; reuse existing `.auth-section` / `.form-input` classes from `style.css`, no new CSS file needed
- All templates extend `base.html`
- Never hardcode URLs — use `url_for()` everywhere, including the new profile edit links
- DB logic stays in `database/db.py` / `database/queries.py`, never inline in routes

## Definition of done
- [ ] Visiting `/expenses/<id>/edit` for an expense you own (while logged in) shows a form pre-filled with that expense's amount, category, date, and description
- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`
- [ ] Visiting `/expenses/<id>/edit` for an `id` that doesn't exist returns a 404
- [ ] Visiting `/expenses/<id>/edit` for an expense owned by a different user returns a 403
- [ ] Submitting the form with a valid amount/category/date/description updates the row in the database and redirects to `/profile` with a flash message "Expense updated."
- [ ] Submitting an invalid amount (non-numeric, zero, negative, or over the max) re-renders the form with an error and the submitted values, without changing the database
- [ ] Submitting an invalid category re-renders the form with an error, without changing the database
- [ ] Submitting an invalid date re-renders the form with an error, without changing the database
- [ ] The profile page's transactions table shows an "Edit" link for each transaction that navigates to the correct `/expenses/<id>/edit` URL
- [ ] No hardcoded URLs exist in the new/modified templates — all use `url_for()`
- [ ] No raw string responses remain for the edit route
- [ ] All new SQL queries use `?` parameterization
