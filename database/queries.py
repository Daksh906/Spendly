from database.db import get_db
from datetime import datetime


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


def get_summary_stats(user_id):
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        top = conn.execute(
            """
            SELECT category, SUM(amount) AS cat_total
            FROM expenses WHERE user_id = ?
            GROUP BY category ORDER BY cat_total DESC LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        if top is None:
            return {"total_spent": "₹0.00", "transaction_count": 0,
                    "top_category": "—", "top_category_amount": "₹0.00"}
        return {
            "total_spent": "₹{:.2f}".format(totals["total"]),
            "transaction_count": totals["cnt"],
            "top_category": top["category"],
            "top_category_amount": "₹{:.2f}".format(top["cat_total"]),
        }
    finally:
        conn.close()


def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT date, description, category, amount
            FROM expenses
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        result = []
        for row in rows:
            dt = datetime.strptime(row["date"], "%Y-%m-%d")
            result.append({
                "date": dt.strftime("%B %d, %Y"),
                "description": row["description"] or "",
                "category": row["category"],
                "amount": "₹{:.2f}".format(row["amount"]),
            })
        return result
    finally:
        conn.close()


def get_category_breakdown(user_id):
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT category, SUM(amount) AS cat_total
            FROM expenses WHERE user_id = ?
            GROUP BY category ORDER BY cat_total DESC
            """,
            (user_id,),
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
