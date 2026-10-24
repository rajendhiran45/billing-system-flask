from extensions import mysql


def list_customers():
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT id, name, phone, email, address, loyalty_points, loyalty_lifetime_points, created_at FROM customers ORDER BY name")
        return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
    finally:
        cur.close()


def get_customer(customer_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT id, name, phone, email, address, loyalty_points, loyalty_lifetime_points FROM customers WHERE id=%s", (customer_id,))
        row = cur.fetchone()
        return dict(zip([c[0] for c in cur.description], row)) if row else None
    finally:
        cur.close()


def save_customer(customer_id, name, phone, email, address):
    cur = mysql.connection.cursor()
    try:
        if customer_id:
            cur.execute("UPDATE customers SET name=%s, phone=%s, email=%s, address=%s WHERE id=%s", (name, phone or None, email or None, address or None, customer_id))
        else:
            cur.execute("INSERT INTO customers(name, phone, email, address) VALUES(%s,%s,%s,%s)", (name, phone or None, email or None, address or None))
        mysql.connection.commit()
        return cur.lastrowid if not customer_id else customer_id
    except Exception:
        mysql.connection.rollback()
        raise
    finally:
        cur.close()
