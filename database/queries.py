from database.db import get_db
from datetime import datetime


def is_valid_date(value):
    if not value:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _validate_range(start_date, end_date):
    """Returns (start_valid, end_valid), or None if the range should match nothing."""
    start_valid = is_valid_date(start_date)
    end_valid = is_valid_date(end_date)

    if (start_date and not start_valid) or (end_date and not end_valid):
        return None
    if start_valid and end_valid and start_date > end_date:
        return None
    return start_valid, end_valid


def _date_range_clause(user_id, start_valid, end_valid, start_date, end_date):
    clause = " WHERE user_id = ?"
    params = [user_id]
    if start_valid:
        clause += " AND date >= ?"
        params.append(start_date)
    if end_valid:
        clause += " AND date <= ?"
        params.append(end_date)
    return clause, params


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        words = row["name"].split()
        initials = (words[0][0] + words[-1][0]).upper() if len(words) >= 2 else words[0][0].upper()
        dt = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
        return {
            "name": row["name"],
            "email": row["email"],
            "member_since": dt.strftime("%B %Y"),
            "initials": initials,
        }
    finally:
        conn.close()


def get_summary_stats(user_id, start_date=None, end_date=None):
    empty_stats = {"total_spent": "₹0.00", "transaction_count": 0,
                    "top_category": "—", "top_category_amount": "₹0.00"}
    validity = _validate_range(start_date, end_date)
    if validity is None:
        return empty_stats
    start_valid, end_valid = validity

    conn = get_db()
    try:
        where_clause, params = _date_range_clause(user_id, start_valid, end_valid, start_date, end_date)

        totals = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt FROM expenses" + where_clause,
            params,
        ).fetchone()
        top = conn.execute(
            "SELECT category, SUM(amount) AS cat_total FROM expenses" + where_clause +
            " GROUP BY category ORDER BY cat_total DESC LIMIT 1",
            params,
        ).fetchone()
        if top is None:
            return empty_stats
        return {
            "total_spent": "₹{:.2f}".format(totals["total"]),
            "transaction_count": totals["cnt"],
            "top_category": top["category"],
            "top_category_amount": "₹{:.2f}".format(top["cat_total"]),
        }
    finally:
        conn.close()


def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    validity = _validate_range(start_date, end_date)
    if validity is None:
        return []
    start_valid, end_valid = validity

    conn = get_db()
    try:
        where_clause, params = _date_range_clause(user_id, start_valid, end_valid, start_date, end_date)

        sql = "SELECT id, date, description, category, amount FROM expenses" + where_clause
        sql += " ORDER BY date DESC, id DESC"

        date_filter_active = start_valid or end_valid
        if not date_filter_active:
            sql += " LIMIT ?"
            params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        result = []
        for row in rows:
            dt = datetime.strptime(row["date"], "%Y-%m-%d")
            result.append({
                "id": row["id"],
                "date": dt.strftime("%B %d, %Y"),
                "description": row["description"] or "",
                "category": row["category"],
                "amount": "₹{:.2f}".format(row["amount"]),
            })
        return result
    finally:
        conn.close()


def get_category_breakdown(user_id, start_date=None, end_date=None):
    validity = _validate_range(start_date, end_date)
    if validity is None:
        return []
    start_valid, end_valid = validity

    conn = get_db()
    try:
        where_clause, params = _date_range_clause(user_id, start_valid, end_valid, start_date, end_date)

        rows = conn.execute(
            "SELECT category, SUM(amount) AS cat_total FROM expenses" + where_clause +
            " GROUP BY category ORDER BY cat_total DESC",
            params,
        ).fetchall()
        if not rows:
            return []
        grand_total = sum(row["cat_total"] for row in rows)
        result = [
            {
                "name": row["category"],
                "amount": "₹{:.2f}".format(row["cat_total"]),
                "pct": int(row["cat_total"] / grand_total * 100),
            }
            for row in rows
        ]
        result[0]["pct"] += 100 - sum(item["pct"] for item in result)
        return result
    finally:
        conn.close()
