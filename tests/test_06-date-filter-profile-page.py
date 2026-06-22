import pytest
from app import app
from database.db import get_db
from database.queries import get_recent_transactions, get_summary_stats, get_category_breakdown


# Fixtures mirror tests/test_backend_connection.py conventions: real sqlite
# file DB via get_db(), seeded demo user (demo@spendly.com / demo123), and a
# throwaway "empty" user with no expenses for empty-state coverage.

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def seed_user_id():
    conn = get_db()
    row = conn.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)).fetchone()
    conn.close()
    return row["id"]


@pytest.fixture
def empty_user_id():
    conn = get_db()
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Test Empty Filter", "empty-filter@test.com", "x"),
    )
    conn.commit()
    uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    yield uid
    conn2 = get_db()
    conn2.execute("DELETE FROM users WHERE id = ?", (uid,))
    conn2.commit()
    conn2.close()


def login(client, user_id, user_name="Demo User"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = user_name


# Seed data (from database/db.py seed_db()), for reference in assertions:
#   2026-05-02  Food           45.50   Grocery run
#   2026-05-05  Transport      12.00   Bus pass top-up
#   2026-05-08  Bills          120.00  Electricity bill
#   2026-05-10  Health         30.00   Pharmacy
#   2026-05-14  Entertainment  25.00   Movie tickets
#   2026-05-18  Shopping       80.00   New shoes
#   2026-05-21  Other          15.75   Miscellaneous
#   2026-05-25  Food           60.00   Restaurant dinner


# ── Unit-level: get_recent_transactions() ──────────────────────────────────

class TestGetRecentTransactionsDateFilter:

    def test_unfiltered_behaves_as_before(self, seed_user_id):
        txns = get_recent_transactions(seed_user_id)
        assert len(txns) == 8, "Expected all 8 seeded transactions with no filter applied"
        assert txns[0]["date"] == "May 25, 2026", "Expected newest-first ordering"
        assert txns[-1]["date"] == "May 02, 2026"

    def test_unfiltered_respects_limit_cap(self, seed_user_id):
        txns = get_recent_transactions(seed_user_id, limit=3)
        assert len(txns) == 3, "Expected default LIMIT behavior preserved when no filter is active"

    def test_filtered_range_returns_only_matching_transactions(self, seed_user_id):
        txns = get_recent_transactions(seed_user_id, start_date="2026-05-05", end_date="2026-05-18")
        dates = [t["date"] for t in txns]
        assert dates == ["May 18, 2026", "May 14, 2026", "May 10, 2026", "May 08, 2026", "May 05, 2026"], (
            "Expected only transactions within [2026-05-05, 2026-05-18], newest first"
        )

    def test_filtered_range_excludes_out_of_range_rows(self, seed_user_id):
        txns = get_recent_transactions(seed_user_id, start_date="2026-05-05", end_date="2026-05-18")
        descriptions = {t["description"] for t in txns}
        assert "Grocery run" not in descriptions, "2026-05-02 row is before start_date and must be excluded"
        assert "Restaurant dinner" not in descriptions, "2026-05-25 row is after end_date and must be excluded"

    def test_filtered_range_bypasses_limit_cap(self, seed_user_id):
        txns = get_recent_transactions(
            seed_user_id, limit=2, start_date="2026-01-01", end_date="2026-12-31"
        )
        assert len(txns) == 8, "All 8 in-range rows must be returned; LIMIT must not apply when filter is active"

    def test_only_start_date_supplied_returns_on_or_after(self, seed_user_id):
        txns = get_recent_transactions(seed_user_id, start_date="2026-05-18")
        dates = [t["date"] for t in txns]
        assert dates == ["May 25, 2026", "May 21, 2026", "May 18, 2026"], (
            "Expected all transactions on/after 2026-05-18, newest first"
        )

    def test_only_end_date_supplied_returns_on_or_before(self, seed_user_id):
        txns = get_recent_transactions(seed_user_id, end_date="2026-05-08")
        dates = [t["date"] for t in txns]
        assert dates == ["May 08, 2026", "May 05, 2026", "May 02, 2026"], (
            "Expected all transactions on/before 2026-05-08, newest first"
        )

    def test_range_matching_zero_expenses_returns_empty_list(self, seed_user_id):
        txns = get_recent_transactions(seed_user_id, start_date="2099-01-01", end_date="2099-12-31")
        assert txns == [], "Date range with no matching expenses must return an empty list"

    def test_reversed_range_returns_empty_not_error(self, seed_user_id):
        txns = get_recent_transactions(seed_user_id, start_date="2026-05-20", end_date="2026-05-01")
        assert txns == [], "Reversed date range must yield an empty result, not an exception"

    @pytest.mark.parametrize("start_date,end_date", [
        ("not-a-date", None),
        (None, "not-a-date"),
        ("not-a-date", "also-not-a-date"),
        ("2026-13-40", None),
    ])
    def test_malformed_date_strings_return_empty_not_error(self, seed_user_id, start_date, end_date):
        txns = get_recent_transactions(seed_user_id, start_date=start_date, end_date=end_date)
        assert txns == [], (
            f"Malformed date input (start_date={start_date!r}, end_date={end_date!r}) "
            "must be treated as a filter matching nothing, not raise"
        )

    def test_both_dates_blank_strings_behaves_unfiltered(self, seed_user_id):
        txns = get_recent_transactions(seed_user_id, start_date="", end_date="")
        assert len(txns) == 8, "Blank-string dates should behave the same as no filter at all"

    def test_filtered_range_no_expenses_for_user(self, empty_user_id):
        txns = get_recent_transactions(empty_user_id, start_date="2026-01-01", end_date="2026-12-31")
        assert txns == [], "A user with no expenses must return an empty list even with a valid range"

    def test_filter_results_shape_unchanged(self, seed_user_id):
        txns = get_recent_transactions(seed_user_id, start_date="2026-05-05", end_date="2026-05-18")
        assert len(txns) > 0
        for t in txns:
            assert {"date", "description", "category", "amount"} <= t.keys()
            assert t["amount"].startswith("₹"), "Currency must continue to display with the rupee symbol"


# ── Integration-level: GET /profile with query params ──────────────────────

class TestProfileRouteDateFilter:

    def test_profile_unauthenticated_redirects_to_login(self, client):
        resp = client.get("/profile?start_date=2026-05-01&end_date=2026-05-10")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"], "Unauthenticated request must redirect to /login"

    def test_no_query_params_behaves_as_before(self, client, seed_user_id):
        login(client, seed_user_id)
        resp = client.get("/profile")
        assert resp.status_code == 200
        body = resp.data.decode()
        assert "May 25, 2026" in body
        assert "May 02, 2026" in body
        assert body.index("May 25, 2026") < body.index("May 02, 2026"), "Expected newest-first ordering"

    def test_no_query_params_filter_inputs_blank(self, client, seed_user_id):
        login(client, seed_user_id)
        body = client.get("/profile").data.decode()
        assert 'id="start_date"' in body and 'id="end_date"' in body
        assert 'name="start_date"' in body
        assert 'value=""' in body, "Filter inputs must be blank when no query params are supplied"

    def test_filtered_range_returns_only_matching_transactions(self, client, seed_user_id):
        login(client, seed_user_id)
        resp = client.get("/profile?start_date=2026-05-01&end_date=2026-05-10")
        assert resp.status_code == 200
        body = resp.data.decode()
        assert "Grocery run" in body
        assert "Bus pass top-up" in body
        assert "Electricity bill" in body
        assert "Pharmacy" in body
        assert "Movie tickets" not in body, "2026-05-14 is outside the requested range"
        assert "New shoes" not in body, "2026-05-18 is outside the requested range"
        assert "Restaurant dinner" not in body, "2026-05-25 is outside the requested range"

    def test_filtered_range_newest_first_ordering(self, client, seed_user_id):
        login(client, seed_user_id)
        body = client.get("/profile?start_date=2026-05-01&end_date=2026-05-10").data.decode()
        assert body.index("Pharmacy") < body.index("Electricity bill") < body.index("Bus pass top-up") < body.index("Grocery run")

    def test_filtered_range_inputs_prepopulated(self, client, seed_user_id):
        login(client, seed_user_id)
        body = client.get("/profile?start_date=2026-05-01&end_date=2026-05-10").data.decode()
        assert 'value="2026-05-01"' in body, "start_date input must be pre-populated with the query param value"
        assert 'value="2026-05-10"' in body, "end_date input must be pre-populated with the query param value"

    def test_only_start_date_query_param(self, client, seed_user_id):
        login(client, seed_user_id)
        body = client.get("/profile?start_date=2026-05-18").data.decode()
        assert "New shoes" in body
        assert "Miscellaneous" in body
        assert "Restaurant dinner" in body
        assert "Grocery run" not in body, "2026-05-02 is before start_date and must be excluded"
        assert 'value="2026-05-18"' in body

    def test_only_end_date_query_param(self, client, seed_user_id):
        login(client, seed_user_id)
        body = client.get("/profile?end_date=2026-05-08").data.decode()
        assert "Grocery run" in body
        assert "Bus pass top-up" in body
        assert "Electricity bill" in body
        assert "Pharmacy" not in body, "2026-05-10 is after end_date and must be excluded"
        assert 'value="2026-05-08"' in body

    def test_range_matching_zero_expenses_shows_empty_state(self, client, seed_user_id):
        login(client, seed_user_id)
        resp = client.get("/profile?start_date=2099-01-01&end_date=2099-12-31")
        assert resp.status_code == 200
        body = resp.data.decode()
        assert "No transactions found in this date range." in body
        assert "<table" not in body, "Empty filtered result must not render an empty table"

    def test_reversed_range_no_error_shows_empty_state(self, client, seed_user_id):
        login(client, seed_user_id)
        resp = client.get("/profile?start_date=2026-05-20&end_date=2026-05-01")
        assert resp.status_code == 200, "Reversed date range must not produce a server error"
        assert "No transactions found in this date range." in resp.data.decode()

    @pytest.mark.parametrize("query_string", [
        "start_date=not-a-date",
        "end_date=not-a-date",
        "start_date=not-a-date&end_date=also-not-a-date",
        "start_date=2026-13-40",
        "start_date=' OR '1'='1",
        "start_date=<script>alert(1)</script>",
    ])
    def test_malformed_or_malicious_date_input_no_error(self, client, seed_user_id, query_string):
        login(client, seed_user_id)
        resp = client.get(f"/profile?{query_string}")
        assert resp.status_code == 200, f"Malformed input ({query_string}) must not cause a 500 error"
        assert "No transactions found in this date range." in resp.data.decode()

    def test_empty_user_with_filter_shows_empty_state_not_error(self, client, empty_user_id):
        login(client, empty_user_id, user_name="Test Empty Filter")
        resp = client.get("/profile?start_date=2026-01-01&end_date=2026-12-31")
        assert resp.status_code == 200
        assert "No transactions found in this date range." in resp.data.decode()

    def test_clear_filter_restores_default_view(self, client, seed_user_id):
        login(client, seed_user_id)
        filtered_body = client.get("/profile?start_date=2026-05-01&end_date=2026-05-10").data.decode()
        assert "Movie tickets" not in filtered_body

        cleared_resp = client.get("/profile")
        assert cleared_resp.status_code == 200
        cleared_body = cleared_resp.data.decode()
        assert "May 25, 2026" in cleared_body, "Clearing the filter must restore the newest-10 default view"
        assert 'value=""' in cleared_body, "Filter inputs must be blank again after clearing"

    def test_currency_symbol_present_in_filtered_results(self, client, seed_user_id):
        login(client, seed_user_id)
        body = client.get("/profile?start_date=2026-05-01&end_date=2026-05-10").data.decode()
        assert "₹" in body, "Currency must continue to display with the rupee symbol when filtered"


# ── Unit-level: get_summary_stats() / get_category_breakdown() date filter ──

class TestSummaryStatsAndBreakdownDateFilter:

    def test_summary_stats_unfiltered_unchanged(self, seed_user_id):
        stats = get_summary_stats(seed_user_id)
        assert stats["total_spent"] == "₹388.25"
        assert stats["transaction_count"] == 8
        assert stats["top_category"] == "Bills"

    def test_summary_stats_filtered_range(self, seed_user_id):
        stats = get_summary_stats(seed_user_id, start_date="2026-05-01", end_date="2026-05-10")
        assert stats["total_spent"] == "₹207.50", "45.50 + 12.00 + 120.00 + 30.00 within range"
        assert stats["transaction_count"] == 4
        assert stats["top_category"] == "Bills"
        assert stats["top_category_amount"] == "₹120.00"

    def test_summary_stats_only_start_date(self, seed_user_id):
        stats = get_summary_stats(seed_user_id, start_date="2026-05-18")
        assert stats["total_spent"] == "₹155.75", "80.00 + 15.75 + 60.00 on/after 2026-05-18"
        assert stats["transaction_count"] == 3
        assert stats["top_category"] == "Shopping"

    def test_summary_stats_only_end_date(self, seed_user_id):
        stats = get_summary_stats(seed_user_id, end_date="2026-05-08")
        assert stats["total_spent"] == "₹177.50", "45.50 + 12.00 + 120.00 on/before 2026-05-08"
        assert stats["transaction_count"] == 3
        assert stats["top_category"] == "Bills"

    def test_summary_stats_zero_match_range_returns_zeros(self, seed_user_id):
        stats = get_summary_stats(seed_user_id, start_date="2099-01-01", end_date="2099-12-31")
        assert stats == {"total_spent": "₹0.00", "transaction_count": 0,
                          "top_category": "—", "top_category_amount": "₹0.00"}

    def test_summary_stats_reversed_range_returns_zeros(self, seed_user_id):
        stats = get_summary_stats(seed_user_id, start_date="2026-05-20", end_date="2026-05-01")
        assert stats["transaction_count"] == 0
        assert stats["top_category"] == "—"

    def test_summary_stats_malformed_date_returns_zeros(self, seed_user_id):
        stats = get_summary_stats(seed_user_id, start_date="not-a-date")
        assert stats["transaction_count"] == 0
        assert stats["top_category"] == "—"

    def test_category_breakdown_filtered_range(self, seed_user_id):
        cats = get_category_breakdown(seed_user_id, start_date="2026-05-01", end_date="2026-05-10")
        names = {c["name"] for c in cats}
        assert names == {"Food", "Transport", "Bills", "Health"}
        assert cats[0]["name"] == "Bills", "Highest-amount category must sort first"
        assert sum(c["pct"] for c in cats) == 100

    def test_category_breakdown_zero_match_range_returns_empty(self, seed_user_id):
        cats = get_category_breakdown(seed_user_id, start_date="2099-01-01", end_date="2099-12-31")
        assert cats == []

    def test_category_breakdown_reversed_range_returns_empty(self, seed_user_id):
        cats = get_category_breakdown(seed_user_id, start_date="2026-05-20", end_date="2026-05-01")
        assert cats == []

    def test_category_breakdown_malformed_date_returns_empty(self, seed_user_id):
        cats = get_category_breakdown(seed_user_id, end_date="not-a-date")
        assert cats == []

    def test_summary_stats_no_expenses_for_user_with_valid_range(self, empty_user_id):
        stats = get_summary_stats(empty_user_id, start_date="2026-01-01", end_date="2026-12-31")
        assert stats["transaction_count"] == 0
        assert stats["top_category"] == "—"


# ── Integration-level: GET /profile stats + breakdown reflect the filter ───

class TestProfileRouteStatsAndBreakdownDateFilter:

    def test_filtered_range_updates_total_and_count(self, client, seed_user_id):
        login(client, seed_user_id)
        body = client.get("/profile?start_date=2026-05-01&end_date=2026-05-10").data.decode()
        assert "₹207.50" in body
        assert ">4<" in body, "Transaction count stat must reflect the filtered range, not the all-time count of 8"

    def test_filtered_range_updates_top_category(self, client, seed_user_id):
        login(client, seed_user_id)
        body = client.get("/profile?start_date=2026-05-18&end_date=2026-05-25").data.decode()
        assert "Shopping" in body
        assert "₹80.00" in body

    def test_filtered_range_breakdown_excludes_out_of_range_categories(self, client, seed_user_id):
        login(client, seed_user_id)
        body = client.get("/profile?start_date=2026-05-01&end_date=2026-05-10").data.decode()
        assert "Bills" in body
        assert "Entertainment" not in body, "Entertainment (2026-05-14) is outside the requested range"
        assert "Shopping" not in body, "Shopping (2026-05-18) is outside the requested range"

    def test_zero_match_range_shows_empty_stats_and_breakdown(self, client, seed_user_id):
        login(client, seed_user_id)
        body = client.get("/profile?start_date=2099-01-01&end_date=2099-12-31").data.decode()
        assert "₹0.00" in body
        assert "No category data for this date range." in body

    def test_reversed_range_shows_empty_stats_and_breakdown_no_error(self, client, seed_user_id):
        login(client, seed_user_id)
        resp = client.get("/profile?start_date=2026-05-20&end_date=2026-05-01")
        assert resp.status_code == 200
        body = resp.data.decode()
        assert "No category data for this date range." in body
        assert "—" in body, "Top category must fall back to the em-dash placeholder"

    def test_clear_filter_restores_unfiltered_stats(self, client, seed_user_id):
        login(client, seed_user_id)
        client.get("/profile?start_date=2026-05-01&end_date=2026-05-10")
        body = client.get("/profile").data.decode()
        assert "₹388.25" in body, "Clearing the filter must restore the all-time total"