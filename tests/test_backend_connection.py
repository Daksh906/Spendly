import pytest
from app import app
from database.db import get_db
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

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
        ("Test Empty", "empty@test.com", "x"),
    )
    conn.commit()
    uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    yield uid
    conn2 = get_db()
    conn2.execute("DELETE FROM users WHERE id = ?", (uid,))
    conn2.commit()
    conn2.close()


# ── get_user_by_id ────────────────────────────────────────────────────────────

def test_get_user_by_id_returns_correct_fields(seed_user_id):
    user = get_user_by_id(seed_user_id)
    assert user is not None
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert user["initials"] == "DU"
    parts = user["member_since"].split()
    assert len(parts) == 2 and parts[1].isdigit()


def test_get_user_by_id_nonexistent_returns_none():
    assert get_user_by_id(999999) is None


# ── get_summary_stats ─────────────────────────────────────────────────────────

def test_get_summary_stats_with_expenses(seed_user_id):
    stats = get_summary_stats(seed_user_id)
    assert stats["total_spent"] == "₹388.25"
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"
    assert stats["top_category_amount"] == "₹120.00"


def test_get_summary_stats_no_expenses(empty_user_id):
    stats = get_summary_stats(empty_user_id)
    assert stats["total_spent"] == "₹0.00"
    assert stats["transaction_count"] == 0
    assert stats["top_category"] == "—"


# ── get_recent_transactions ───────────────────────────────────────────────────

def test_get_recent_transactions_count_and_shape(seed_user_id):
    txns = get_recent_transactions(seed_user_id)
    assert len(txns) == 8
    for t in txns:
        assert {"date", "description", "category", "amount"} <= t.keys()
        assert t["amount"].startswith("₹")


def test_get_recent_transactions_newest_first(seed_user_id):
    txns = get_recent_transactions(seed_user_id)
    assert txns[0]["date"] == "May 25, 2026"
    assert txns[-1]["date"] == "May 02, 2026"


def test_get_recent_transactions_limit(seed_user_id):
    assert len(get_recent_transactions(seed_user_id, limit=3)) == 3


def test_get_recent_transactions_no_expenses(empty_user_id):
    assert get_recent_transactions(empty_user_id) == []


# ── get_category_breakdown ────────────────────────────────────────────────────

def test_get_category_breakdown_seven_categories(seed_user_id):
    cats = get_category_breakdown(seed_user_id)
    assert len(cats) == 7
    for c in cats:
        assert {"name", "amount", "pct"} <= c.keys()
        assert isinstance(c["pct"], int)
        assert c["amount"].startswith("₹")


def test_get_category_breakdown_pct_sums_to_100(seed_user_id):
    cats = get_category_breakdown(seed_user_id)
    assert sum(c["pct"] for c in cats) == 100


def test_get_category_breakdown_sorted_by_amount(seed_user_id):
    cats = get_category_breakdown(seed_user_id)
    assert cats[0]["name"] == "Bills"


def test_get_category_breakdown_no_expenses(empty_user_id):
    assert get_category_breakdown(empty_user_id) == []


# ── Route: GET /profile ───────────────────────────────────────────────────────

def test_profile_unauthenticated_redirects(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_authenticated_200(client, seed_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"
    assert client.get("/profile").status_code == 200


def test_profile_shows_real_user(client, seed_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"
    body = client.get("/profile").data.decode()
    assert "Demo User" in body
    assert "demo@spendly.com" in body


def test_profile_shows_rupee_symbol(client, seed_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"
    assert "₹" in client.get("/profile").data.decode()


def test_profile_correct_total_spent(client, seed_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"
    assert "₹388.25" in client.get("/profile").data.decode()


def test_profile_top_category(client, seed_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"
    assert "Bills" in client.get("/profile").data.decode()


def test_profile_transactions_newest_first(client, seed_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"
    body = client.get("/profile").data.decode()
    assert body.index("May 25, 2026") < body.index("May 02, 2026")


def test_profile_all_seven_categories(client, seed_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"
    body = client.get("/profile").data.decode()
    for cat in ["Bills", "Food", "Shopping", "Health", "Entertainment", "Transport", "Other"]:
        assert cat in body


def test_profile_empty_user_no_errors(client, empty_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = empty_user_id
        sess["user_name"] = "Test Empty"
    resp = client.get("/profile")
    assert resp.status_code == 200
    assert "₹0.00" in resp.data.decode()
