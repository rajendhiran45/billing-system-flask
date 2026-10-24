from extensions import mysql


def list_users():
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT id, username, role, created_at FROM users ORDER BY username")
        return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
    finally:
        cur.close()


def set_user_role(user_id, role):
    cur = mysql.connection.cursor()
    try:
        cur.execute("UPDATE users SET role=%s WHERE id=%s", (role, user_id))
        mysql.connection.commit()
        return cur.rowcount == 1
    finally:
        cur.close()
