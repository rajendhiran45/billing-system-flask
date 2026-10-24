"""Small, write-only audit trail for sensitive business actions."""
import json
from extensions import mysql


def log_action(user_id, action, entity_type, entity_id=None, details=None):
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "INSERT INTO audit_logs(user_id, action, entity_type, entity_id, details) VALUES(%s,%s,%s,%s,%s)",
            (user_id, action, entity_type, entity_id, json.dumps(details or {})),
        )
    finally:
        cur.close()


def recent_actions(limit=100):
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT a.id, a.action, a.entity_type, a.entity_id, a.details, a.created_at,
                   COALESCE(u.username, 'System') AS username
            FROM audit_logs a LEFT JOIN users u ON u.id=a.user_id
            ORDER BY a.created_at DESC, a.id DESC LIMIT %s
        """, (limit,))
        return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
    finally:
        cur.close()
