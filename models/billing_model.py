from extensions import mysql
from models.audit_model import log_action

def save_bill(bill_data, customer_id=None, cashier_id=None, low_stock_threshold=None, payments=None):
    try:
        cur=mysql.connection.cursor()

        bill_query="""
        INSERT INTO bills(subtotal,gst_amount,total,payment_method,customer_id,cashier_id,discount_amount,loyalty_points_earned,loyalty_points_redeemed)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)"""

        cur.execute(bill_query,
                    (
                        bill_data["subtotal"],
                        bill_data["total_gst"],
                        bill_data["total_amount"],
                        bill_data.get("payment_method","cash"), customer_id, cashier_id,
                        bill_data.get("discount_amount", 0), bill_data.get("loyalty_points_earned", 0), bill_data.get("loyalty_points_redeemed", 0)
                    ))
        
        bill_id=cur.lastrowid

        item_query = """
        INSERT INTO bill_items 
        (bill_id, product_id, product_name, quantity, unit_price, gst_percent, gst_amount, line_total)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        for item in bill_data["items"]:
            cur.execute(
                item_query,
                (
                    bill_id,
                    item["product_id"],
                    item["product_name"],
                    item["quantity"],
                    item["unit_price"],
                    item["gst_percent"],
                    item["gst_amount"],
                    item["line_total"]
                )
            )
            update_stock_query = """
            UPDATE products 
            SET stock = stock - %s 
            WHERE id = %s AND stock >= %s
            """

            cur.execute(update_stock_query, (
                item["quantity"],
                item["product_id"],
                item["quantity"]
            ))

            if cur.rowcount == 0:
                print("Stock not enough")
                mysql.connection.rollback()
                return None
        for payment in payments or []:
            cur.execute("INSERT INTO bill_payments(bill_id, method, amount) VALUES(%s,%s,%s)",
                        (bill_id, payment["method"], payment["amount"]))
        if customer_id:
            cur.execute("""UPDATE customers SET loyalty_points=GREATEST(0, loyalty_points-%s)+%s,
                         loyalty_lifetime_points=loyalty_lifetime_points+%s WHERE id=%s""",
                        (bill_data.get("loyalty_points_redeemed", 0), bill_data.get("loyalty_points_earned", 0), bill_data.get("loyalty_points_earned", 0), customer_id))
        # Keep one open alert per low-stock product. Alerts are resolved if an
        # administrator later restocks the product above the configured limit.
        if low_stock_threshold is not None:
            cur.execute("""
                UPDATE inventory_alerts ia JOIN products p ON p.id=ia.product_id
                SET ia.resolved_at=CURRENT_TIMESTAMP
                WHERE ia.resolved_at IS NULL AND p.stock > %s
            """, (low_stock_threshold,))
            for product_id in {item["product_id"] for item in bill_data["items"]}:
                cur.execute("SELECT stock FROM products WHERE id=%s", (product_id,))
                row = cur.fetchone()
                if row and int(row[0]) <= low_stock_threshold:
                    cur.execute("""
                        INSERT INTO inventory_alerts(product_id, stock_at_alert)
                        SELECT %s, %s FROM DUAL WHERE NOT EXISTS (
                            SELECT 1 FROM inventory_alerts WHERE product_id=%s AND resolved_at IS NULL
                        )
                    """, (product_id, int(row[0]), product_id))

        log_action(cashier_id, "checkout_completed", "bill", bill_id, {
            "total": str(bill_data["total_amount"]), "customer_id": customer_id,
            "payment_count": len(payments or [])
        })
        mysql.connection.commit()
        cur.close()

        return bill_id
        
    except Exception as e:
        print("Error in save_bill:", e)
        return None
        
def get_all_bills():
    try:
        cur = mysql.connection.cursor()

        query = "SELECT id, subtotal, gst_amount, total, payment_method, discount_amount, created_at FROM bills ORDER BY id DESC"
        cur.execute(query)

        rows = cur.fetchall()
        columns = [col[0] for col in cur.description]

        bills = [dict(zip(columns, row)) for row in rows]

        cur.close()
        return bills

    except Exception as e:
        print("Error fetching bills:", e)
        return []
