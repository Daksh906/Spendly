re# Spec: Date Filter for Profile Page

## Overview
Step 6 adds a date-range filter to the profile page. Today `/profile` always
shows the 10 most recent transactions, all-time summary stats, and an
all-time category breakdown, with no way to narrow the view. This step lets
a logged-in user filter their transaction history, summary stats (total
spent, transaction count, top category), and category breakdown to a
specific date range using two date inputs, so they can answer questions like
"what did I spend last week" without scrolling through unrelated expenses.
The `expenses.date` column already stores `YYYY-MM-DD` text, so filtering is
a straightforward range comparison in SQL.

## Depends on
- Step 4: Profile page static UI (transaction table markup already exists)
- Step 5: Backend routes for profile page (`get_recent_transactions()` in
  `database/queries.py` already serves the transaction list from the
  database; this step extends it)

## Routes
No new routes. The existing `GET /profile` route is modified to read two
optional query parameters:
- `start_date` (format `YYYY-MM-DD`) — lower bound, inclusive
- `end_date` (format `YYYY-MM-DD`) — upper bound, inclusive

Access level: logged-in (unchanged from current `/profile` behavior).

## Database changes
No database changes. `expenses.date` already stores `YYYY-MM-DD` text, which
sorts and compares correctly as a string for range filtering.

## Templates
- **Modify:** `templates/profile.html`
  - Add a filter form above the transaction table with two
    `<input type="date">` fields (`start_date`, `end_date`), an "Apply"
    submit button, and a "Clear filter" link back to `/profile` with no
    query params.
  - Form uses `method="get"` so the filtered URL is shareable/bookmarkable.
  - Pre-populate both inputs with the current `start_date`/`end_date` values
    (if any) so the form reflects the active filter after submit.
  - When the filtered transaction list is empty, render an empty-state
    message in place of the table (e.g. "No transactions found in this date
    range.") instead of an empty `<table>`.
  - When the filtered category breakdown is empty, render a similar
    empty-state message (e.g. "No category data for this date range.")
    instead of an empty breakdown container. The summary stats row always
    renders (it has its own zero-state values, e.g. "₹0.00" / "—").

## Files to change
- `app.py` — in the `profile()` view, read `start_date` and `end_date` from
  `request.args`, pass them through to `get_recent_transactions()`, and pass
  them back into the template context so the form can pre-populate.
- `database/queries.py` — extend
  `get_recent_transactions(user_id, limit=10, start_date=None, end_date=None)`,
  `get_summary_stats(user_id, start_date=None, end_date=None)`, and
  `get_category_breakdown(user_id, start_date=None, end_date=None)`:
  - When `start_date`/`end_date` are provided, add a parameterized
    `AND date >= ?` / `AND date <= ?` clause (only the bounds that are
    actually supplied) to each function's query.
  - `get_recent_transactions`: when any date filter is active, do not apply
    the `LIMIT 10` cap — return every matching row in the range, still
    ordered newest-first.
  - `get_summary_stats`: a zero-match or invalid range returns the same
    zero-state dict already used for a user with no expenses
    (`total_spent: "₹0.00"`, `transaction_count: 0`, `top_category: "—"`,
    `top_category_amount: "₹0.00"`).
  - `get_category_breakdown`: a zero-match or invalid range returns `[]`,
    same as a user with no expenses.
  - When no date filter is supplied, behavior of all three functions is
    unchanged (newest 10 / all-time totals / all-time breakdown).
- `templates/profile.html` — add the filter form and empty-state markup
  described above.
- `static/css/profile.css` — style the new filter form using existing CSS
  variables and the established `.form-group`/`.form-input` patterns; no new
  hardcoded colors.

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format dates into SQL
- Foreign keys PRAGMA is already enabled in `get_db()` — no change needed
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline `<style>` tags
- Filter form must use `method="get"` (not POST) so the range is part of the
  URL
- Malformed or reversed date input (e.g. `start_date` after `end_date`, or an
  unparsable string) must never raise an exception — treat it as a filter
  that matches nothing, not a crash
- Currency must continue to display with the ₹ symbol
- `get_recent_transactions()` continues to call `get_db()` internally and
  close the connection before returning

## Definition of done
- [ ] Visiting `/profile` with no query params behaves exactly as before:
      newest 10 transactions, filter inputs blank
- [ ] Visiting `/profile?start_date=2026-05-01&end_date=2026-05-10` (logged in
      as the seed user) shows only transactions with `date` in that inclusive
      range, newest first, with no `LIMIT 10` cap applied
- [ ] On that same filtered URL, the start/end date inputs are pre-filled
      with `2026-05-01` and `2026-05-10`
- [ ] A date range matching zero expenses shows the empty-state message, not
      an empty table or an error
- [ ] Supplying only `start_date` returns all transactions on/after that date
- [ ] Supplying only `end_date` returns all transactions on/before that date
- [ ] Supplying a `start_date` later than `end_date` returns the empty state,
      not a 500 error
- [ ] The "Clear filter" link returns to `/profile` with no query params and
      restores the default 10-transaction view
- [ ] `database/queries.py` shows only parameterized `?` placeholders in the
      new SQL — no f-strings or string concatenation into the query
- [ ] Visiting a filtered URL updates the Total Spent, Transaction Count,
      and Top Category stats to reflect only the filtered range, not
      all-time totals
- [ ] Visiting a filtered URL updates the category breakdown to only the
      categories present in that range, with percentages still summing to
      100
- [ ] A zero-match range shows the zero-state summary stats (`₹0.00`, `0`,
      `—`) and the category breakdown empty-state message, with no error