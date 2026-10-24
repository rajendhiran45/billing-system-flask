"""Database helpers for user authentication."""
from extensions import mysql


def ensure_users_table():
    """Create the users table if it does not exist yet."""
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(80) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'cashier',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        mysql.connection.commit()
    finally:
        cur.close()


def count_users():
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM users")
        row = cur.fetchone()
        return int(row[0]) if row else 0
    finally:
        cur.close()


def get_user_by_username(username):
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "SELECT id, username, password_hash, role FROM users WHERE username = %s LIMIT 1",
            (username,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {"id": row[0], "username": row[1], "password_hash": row[2], "role": row[3]}
    finally:
        cur.close()


def create_user(username, password_hash, role="cashier"):
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            (username, password_hash, role),
        )
        mysql.connection.commit()
        return int(cur.lastrowid)
    except Exception:
        mysql.connection.rollback()
        raise
    finally:
        cur.close()
