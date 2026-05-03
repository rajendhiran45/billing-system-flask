from extensions import mysql

def save_bill(bill_data):
    try:
        cur=mysql.connection.cursor()

        bill_query="""
        INSERT INTO bills(subtotal,gst_amount,total,payment_method)
        VALUES(%s,%s,%s,%s)"""

        cur.execute(bill_query,
                    (
                        bill_data["subtotal"],
                        bill_data["total_gst"],
                        bill_data["total_amount"],
                        bill_data.get("payment_method","cash")
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
        mysql.connection.commit()
        cur.close()

        return bill_id
        
    except Exception as e:
        print("Error in save_bill:", e)
        return None
        
def get_all_bills():
    try:
        cur = mysql.connection.cursor()

        query = "SELECT id, subtotal, gst_amount, total, created_at FROM bills ORDER BY id DESC"
        cur.execute(query)

        rows = cur.fetchall()
        columns = [col[0] for col in cur.description]

        bills = [dict(zip(columns, row)) for row in rows]

        cur.close()
        return bills

    except Exception as e:
        print("Error fetching bills:", e)
        return []