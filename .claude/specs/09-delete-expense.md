# Spec: Delete Expense

## Overview
This feature replaces the `GET /expenses/<id>/delete` stub with a real delete flow, letting a logged-in user remove one of their own expenses. It follows the same GET-renders-form / POST-performs-action pattern already used by `add_expense` and `edit_expense`: a `GET` shows a confirmation page with the expense's details, and a `POST` actually deletes the row. This avoids destroying data on a plain `GET` request. It also adds a "Delete" link next to the existing "Edit" link on each transaction row on the profile page.

## Depends on
- Step 1 (database setup) — `expenses` table and `get_db()`
- Step 4/5 (profile page) — `profile.html` transactions table, `get_recent_transactions()` (already returns `id` per transaction since Step 8)
- Step 8 (edit expense) — `get_expense_by_id()`, the GET/POST-on-one-view pattern, and the ownership-check (404/403) pattern in `edit_expense()`

## Routes
- `GET /expenses/<int:id>/delete` — render a confirmation page showing the expense's date, category, amount, and description — logged-in
- `POST /expenses/<int:id>/delete` — delete the expense, then redirect to `/profile` — logged-in

Both methods are handled by one `delete_expense(id)` view, replacing the current stub (same pattern as `edit_expense`). The `GET` must only display the confirmation page and must never delete the row itself — only the `POST` deletes.

Access rules (identical to `edit_expense`):
- Redirect to `/login` if `session.get("user_id")` is not set.
- `abort(404)` if no expense with that `id` exists.
- `abort(403)` if the expense exists but its `user_id` does not match `session["user_id"]` — applies to both `GET` and `POST`.

## Database changes
No schema changes. The `expenses` table already has everything needed.

One new function in `database/db.py`:
- `delete_expense_by_id(expense_id)` — parameterized `DELETE FROM expenses WHERE id = ?`, commits, closes the connection. Follows the same open/execute/commit/close pattern as `insert_expense()` and `update_expense()`.

**Naming note:** do not call this function `delete_expense` — that name collides with the `delete_expense(id)` route function in `app.py` and would shadow the import. Use `delete_expense_by_id`.

Fetching the expense for the confirmation page and the ownership check reuses the existing `get_expense_by_id()` — no new read function needed.

## Templates
- **Create:** `templates/delete_expense.html` — same `.auth-section` / `.auth-card` structure as `add_expense.html` / `edit_expense.html`, but read-only:
  - Title: "Delete expense" / subtitle: "This action cannot be undone"
  - Shows the expense's date, category, amount, and description as plain text (not form inputs)
  - A `<form method="POST" action="{{ url_for('delete_expense', id=expense_id) }}">` containing only a submit button: "Delete expense" (styled with the new `.btn-danger` class)
  - A "Cancel" link back to `url_for('profile')`
- **Modify:** `templates/profile.html` — add a "Delete" link next to the existing "Edit" link in each row's `.txn-actions` cell, pointing to `url_for('delete_expense', id=txn.id)`.

## Files to change
- `app.py` — replace the `delete_expense` stub with a full `GET`/`POST` implementation modeled on `edit_expense`
- `database/db.py` — add `delete_expense_by_id()`
- `templates/profile.html` — add a "Delete" link per transaction row
- `static/css/profile.css` — add a `.txn-delete-link` style next to the existing `.txn-edit-link` (same layout, use `var(--danger)` for the hover color)
- `static/css/style.css` — add a `.btn-danger` style next to the existing `.btn-submit` (use `var(--danger)` / `var(--danger-light)`, both already defined in `:root`)

## Files to create
- `templates/delete_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only (`?` placeholders) — never f-strings in SQL
- Passwords hashed with werkzeug (n/a to this feature, no password handling here)
- Ownership check is mandatory: `abort(403)` if `expense["user_id"] != session["user_id"]`; `abort(404)` if the expense doesn't exist — checked before rendering the `GET` confirmation page and before processing the `POST`
- `GET` never deletes anything — only `POST` calls `delete_expense_by_id()`
- On success, `flash("Expense deleted.")` and redirect to `url_for("profile")`
- Use CSS variables — never hardcode hex values; reuse `--danger` / `--danger-light` already defined in `style.css`
- All templates extend `base.html`
- Never hardcode URLs — use `url_for()` everywhere, including the new profile delete link
- DB logic stays in `database/db.py`, never inline in routes
- Name the new DB function `delete_expense_by_id`, not `delete_expense`, to avoid shadowing the route function of the same name

## Definition of done
- [ ] Visiting `/expenses/<id>/delete` (GET) for an expense you own, while logged in, shows a confirmation page with that expense's date, category, amount, and description
- [ ] Visiting `/expenses/<id>/delete` (GET) does not delete the row — refreshing the page or navigating away leaves the expense intact
- [ ] Visiting `/expenses/<id>/delete` while logged out redirects to `/login`
- [ ] Visiting `/expenses/<id>/delete` for an `id` that doesn't exist returns a 404
- [ ] Visiting `/expenses/<id>/delete` for an expense owned by a different user returns a 403
- [ ] Submitting the confirmation form (POST) deletes the row from the database and redirects to `/profile` with a flash message "Expense deleted."
- [ ] POSTing to `/expenses/<id>/delete` for an expense owned by a different user returns a 403 and does not delete it
- [ ] After deletion, the expense no longer appears in the profile page's transactions table or category breakdown
- [ ] The profile page's transactions table shows a "Delete" link for each transaction that navigates to the correct `/expenses/<id>/delete` URL
- [ ] No hardcoded URLs exist in the new/modified templates — all use `url_for()`
- [ ] No raw string responses remain for the delete route
- [ ] All new SQL queries use `?` parameterization
