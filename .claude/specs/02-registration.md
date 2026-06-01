# Spec: Registration

## Overview
Implement user registration and login so visitors can create an account and authenticate.
This step wires up the `POST /register` and `POST /login` handlers, adds Flask session
management, and adds the DB helpers that create and look up users. On success the user is shown with a success message and then redirected to the login page. The templates
(`register.html`, `login.html`) already exist — this step makes them functional.

---

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`, `init_db()`)

---

## Routes

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `GET /register` | Already implemented | Renders registration form | Public |
| `POST /register` | **New** — validate input, create user, set session, redirect | Public |
| `GET /login` | Already implemented | Renders login form | Public |
| `POST /login` | **New** — verify credentials, set session, redirect | Public |

---

## Database changes

No new tables or columns. Two new helper functions in `database/db.py`:

- **`create_user(name, email, password_hash)`** — inserts a new row into `users`,
  returns the new row's `id`. Raises `sqlite3.IntegrityError` if the email is already taken.
- **`get_user_by_email(email)`** — returns the full `users` row (as `sqlite3.Row`) or `None`.

---

## Templates

**Modify (no structural changes — only verify these already work):**
- `templates/register.html` — form already POSTs to `/register`; `{{ error }}` block already present
- `templates/login.html` — form already POSTs to `/login`; `{{ error }}` block already present

**No new templates needed.**

---

## Files to change

| File | What changes |
|------|-------------|
| `app.py` | Add `app.secret_key`; add `POST /register` and `POST /login` route handlers; import session, redirect, url_for, request, flash from flask |
| `database/db.py` | Add `create_user()` and `get_user_by_email()` helper functions |
| 'templates/register.html' | wire up form action/method and flash message display |

---

## Files to create

None.

---

## New dependencies

No new pip packages. Uses:
- `flask.session` (built-in Flask)
- `werkzeug.security.generate_password_hash` / `check_password_hash` (already installed)

---

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only — never f-strings or `%` formatting in SQL
- Hash passwords with `werkzeug.security.generate_password_hash` before inserting
- Verify passwords with `werkzeug.security.check_password_hash` — never compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `app.secret_key` must be set before any `session` usage; use a hard-coded dev string
  (e.g. `"spendly-dev-secret"`) — flag in a comment that this must be an env var in production
- Session stores only `user_id` (integer) and `user_name` (string) — nothing else
- After successful registration: set session, redirect to `url_for('login')` — do NOT
  auto-login (keeps the flow simple until Step 3 is done)
- After successful login: set session, redirect to `url_for('landing')` — dashboard
  doesn't exist yet
- Validation rules:
  - `name` — required, strip whitespace, 1–100 chars
  - `email` — required, strip + lowercase
  - `password` — required, minimum 8 characters
- On any validation failure: re-render the same template with `error=<message>`, HTTP 400
- On duplicate email at registration: catch `sqlite3.IntegrityError`, re-render with error
- On invalid credentials at login: generic message ("Invalid email or password") — never
  reveal which field was wrong
- Use `abort(405)` if a non-POST request somehow hits the POST handler (shouldn't happen
  with Flask routing, but be explicit)

---

## Definition of done

- [ ] `POST /register` with valid data creates a new user in the DB (verify with sqlite3 CLI or seed check)
- [ ] Submitting the registration form in the browser redirects to `/login`
- [ ] Registering with a duplicate email shows an error on the form, HTTP 400
- [ ] Registering with a password shorter than 8 characters shows a validation error
- [ ] `POST /login` with correct credentials sets `session['user_id']` and redirects to `/`
- [ ] `POST /login` with wrong password shows "Invalid email or password", HTTP 400
- [ ] `POST /login` with unknown email shows the same generic error, HTTP 400
- [ ] Passwords are stored as hashes — plaintext is never present in the DB
- [ ] Both forms still render correctly on `GET` (no regression)
- [ ] App starts without errors on `python app.py`