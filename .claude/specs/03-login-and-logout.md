# Spec: Login and Logout

## Overview
Complete the authentication lifecycle by implementing the `GET /logout` route and making
the shared navigation session-aware. After this step, signed-in users see their name and
a "Sign out" link in the nav, while guests see "Sign in" / "Get started". Flash messages
(introduced in Step 02 for registration success) become visible for the first time because
`base.html` gains the flash-message display block. The login POST was already wired up in
Step 02; this step closes the loop so users can both sign in and sign out cleanly.

---

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`)
- Step 02 — Registration (`create_user`, `get_user_by_email`, `POST /login` handler, session keys)

---

## Routes

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `GET /logout` | **Implement stub** — clear session, flash confirmation, redirect to `/login` | Public |

No other new routes.

---

## Database changes

No database changes.

---

## Templates

**Modify:**
- `templates/base.html`
  - Add a flash-message block between the `<nav>` and `<main>` so messages from `flash()` are displayed
  - Replace the static nav links with a session-aware conditional:
    - Logged in (`session.user_id` truthy): show the user's name (read-only, not a link) and a "Sign out" link to `url_for('logout')`
    - Logged out: show existing "Sign in" and "Get started" links unchanged

**No new templates.**

---

## Files to change

| File | What changes |
|------|-------------|
| `app.py` | Implement the `GET /logout` stub: clear session, call `flash()`, redirect to `url_for('login')` |
| `templates/base.html` | Add flash-message display block; make nav links conditional on `session.get('user_id')` |

---

## Files to create

None.

---

## New dependencies

No new pip packages. Uses:
- `flask.session` (built-in Flask — already imported)
- `flask.flash` / `flask.get_flashed_messages` (built-in Flask — already imported)

---

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only (no SQL changes needed here, but the rule stands)
- Passwords hashed with werkzeug (no password logic needed here)
- Use CSS variables — never hardcode hex values in any new CSS
- All templates extend `base.html`
- `session.clear()` is the correct way to sign a user out — do not manually delete individual keys
- The logout route must redirect with `redirect(url_for('login'))` after clearing the session
- Flash the message `"You've been signed out."` on logout
- Flash messages in `base.html` must use `get_flashed_messages()` — loop over all messages and render each
- The flash container must have a distinct CSS class (e.g. `flash-messages`) so it can be styled without inline `<style>` tags — add styles to `static/css/style.css` using existing CSS variables only
- The session-aware nav must use `session.get('user_id')` (not `session['user_id']`) to avoid `KeyError` when no session exists
- Display the logged-in user's name from `session.get('user_name')` — no DB query needed
- Do not add a `login_required` decorator in this step — no protected routes exist yet

---

## Definition of done

- [ ] Visiting `/logout` when logged in clears the session and redirects to `/login`
- [ ] After logout, the nav shows "Sign in" and "Get started" (not the user's name)
- [ ] After logout, a flash message "You've been signed out." appears on the login page
- [ ] After registration (Step 02), the flash message "Account created — please sign in." is now visible on the login page
- [ ] When logged in, the nav shows the user's name and a "Sign out" link — not "Sign in" / "Get started"
- [ ] Clicking "Sign out" in the nav logs the user out and shows the flash message
- [ ] Visiting `/logout` when already logged out does not raise an error (session.clear() is safe on an empty session)
- [ ] No hardcoded URLs in templates — all internal links use `url_for()`
- [ ] App starts without errors on `python app.py`