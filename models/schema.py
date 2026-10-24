"""Idempotent schema upgrades for installations created before the admin features."""
from extensions import mysql


def _column_exists(cur, table, column):
    cur.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_schema = DATABASE() "
        "AND table_name = %s AND column_name = %s", (table, column)
    )
    return cur.fetchone() is not None


def ensure_application_schema():
    """Create additive tables/columns. Existing product and bill data is retained."""
    cur = mysql.connection.cursor()
    try:
        # Role is added separately so a database made by an older app version upgrades safely.
        if not _column_exists(cur, "users", "role"):
            cur.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'cashier'")
        cur.execute("UPDATE users SET role = 'admin' WHERE role NOT IN ('admin', 'cashier') OR role IS NULL")
        cur.execute("UPDATE users SET role = 'admin' WHERE id = (SELECT first_user.id FROM (SELECT MIN(id) AS id FROM users) AS first_user) AND role = 'cashier'")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                phone VARCHAR(30) NULL,
                email VARCHAR(120) NULL,
                address VARCHAR(255) NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_customer_phone (phone)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        if not _column_exists(cur, "bills", "customer_id"):
            cur.execute("ALTER TABLE bills ADD COLUMN customer_id BIGINT UNSIGNED NULL")
        if not _column_exists(cur, "bills", "cashier_id"):
            cur.execute("ALTER TABLE bills ADD COLUMN cashier_id BIGINT UNSIGNED NULL")
        # New checkout fields are additive: existing invoices remain valid.
        for column, definition in (
            ("discount_amount", "DECIMAL(12,2) NOT NULL DEFAULT 0"),
            ("loyalty_points_earned", "INT NOT NULL DEFAULT 0"),
            ("loyalty_points_redeemed", "INT NOT NULL DEFAULT 0"),
        ):
            if not _column_exists(cur, "bills", column):
                cur.execute(f"ALTER TABLE bills ADD COLUMN {column} {definition}")
        for column, definition in (
            ("loyalty_points", "INT NOT NULL DEFAULT 0"),
            ("loyalty_lifetime_points", "INT NOT NULL DEFAULT 0"),
        ):
            if not _column_exists(cur, "customers", column):
                cur.execute(f"ALTER TABLE customers ADD COLUMN {column} {definition}")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bill_payments (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                bill_id BIGINT UNSIGNED NOT NULL,
                method VARCHAR(20) NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_bill_payments_bill (bill_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT UNSIGNED NULL,
                action VARCHAR(80) NOT NULL,
                entity_type VARCHAR(50) NOT NULL,
                entity_id BIGINT UNSIGNED NULL,
                details JSON NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_audit_created (created_at), INDEX idx_audit_entity (entity_type, entity_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_alerts (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                product_id BIGINT UNSIGNED NOT NULL,
                stock_at_alert INT NOT NULL,
                resolved_at TIMESTAMP NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_alert_product_open (product_id, resolved_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
        raise
    finally:
        cur.close()
