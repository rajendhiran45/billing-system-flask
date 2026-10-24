from extensions import mysql


def _rows(query, args=()):
    cur = mysql.connection.cursor()
    try:
        cur.execute(query, args)
        columns = [item[0] for item in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]
    finally:
        cur.close()


def dashboard_data(days=30):
    summary = _rows("""
        SELECT COUNT(*) AS bill_count, COALESCE(SUM(total),0) AS revenue,
               COALESCE(SUM(gst_amount),0) AS gst
        FROM bills WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
    """, (days,))[0]
    daily = _rows("""
        SELECT DATE(created_at) AS day, COUNT(*) AS bills, COALESCE(SUM(total),0) AS revenue
        FROM bills WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        GROUP BY DATE(created_at) ORDER BY day
    """, (days,))
    top_products = _rows("""
        SELECT bi.product_name, SUM(bi.quantity) AS units, SUM(bi.line_total) AS revenue
        FROM bill_items bi JOIN bills b ON b.id=bi.bill_id
        WHERE b.created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        GROUP BY bi.product_id, bi.product_name ORDER BY units DESC LIMIT 5
    """, (days,))
    return {"summary": summary, "daily": daily, "top_products": top_products}


def low_stock_products(threshold):
    return _rows("""
        SELECT p.id, p.name, p.stock, p.price,
          COALESCE(SUM(CASE WHEN b.created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) THEN bi.quantity ELSE 0 END),0) AS units_30d
        FROM products p LEFT JOIN bill_items bi ON bi.product_id=p.id
          LEFT JOIN bills b ON b.id=bi.bill_id
        WHERE p.is_active=TRUE GROUP BY p.id, p.name, p.stock, p.price
        HAVING p.stock <= %s ORDER BY p.stock, units_30d DESC
    """, (threshold,))


def forecast_products(days=30):
    rows = _rows("""
        SELECT p.id, p.name, p.stock, COALESCE(SUM(CASE WHEN b.created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY) THEN bi.quantity ELSE 0 END),0) AS units_sold
        FROM products p LEFT JOIN bill_items bi ON bi.product_id=p.id
          LEFT JOIN bills b ON b.id=bi.bill_id
        WHERE p.is_active=TRUE GROUP BY p.id, p.name, p.stock ORDER BY units_sold DESC
    """, (days,))
    for item in rows:
        average_daily = float(item["units_sold"] or 0) / days
        item["average_daily"] = round(average_daily, 2)
        item["forecast_30d"] = max(0, round(average_daily * 30))
        item["suggested_restock"] = max(0, item["forecast_30d"] - int(item["stock"] or 0))
    return rows


def report_rows(start_date=None, end_date=None):
    filters, args = [], []
    if start_date:
        filters.append("DATE(b.created_at) >= %s"); args.append(start_date)
    if end_date:
        filters.append("DATE(b.created_at) <= %s"); args.append(end_date)
    where = " WHERE " + " AND ".join(filters) if filters else ""
    return _rows("""
        SELECT b.id, b.created_at, b.subtotal, b.gst_amount, b.total, b.payment_method,
               c.name AS customer_name, u.username AS cashier
        FROM bills b LEFT JOIN customers c ON c.id=b.customer_id LEFT JOIN users u ON u.id=b.cashier_id
    """ + where + " ORDER BY b.created_at DESC", tuple(args))
