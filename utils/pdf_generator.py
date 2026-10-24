"""Generate a compact thermal-printer receipt PDF for a completed bill.

The paper width can be configured with RECEIPT_WIDTH_MM=58 or 80 in .env.
All monetary values come from the server-side bill calculation.
"""

import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _money(value):
    """Format a numeric amount consistently without trusting display input."""
    try:
        amount = Decimal(str(value or 0))
    except (InvalidOperation, ValueError, TypeError):
        amount = Decimal("0.00")
    return f"{amount:,.2f}"


def _wrap_text(text, max_chars):
    """Wrap text for a narrow receipt without splitting words unnecessarily."""
    words = str(text or "").split()
    if not words:
        return [""]

    lines = []
    current = words[0]
    for word in words[1:]:
        if len(current) + len(word) + 1 <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            while len(word) > max_chars:
                lines.append(word[:max_chars])
                word = word[max_chars:]
            current = word
    lines.append(current)
    return lines


def generate_bill_pdf(bill_data, bill_id):
    """Create a printer-friendly 58 mm or 80 mm thermal receipt PDF."""
    folder = os.path.join("static", "bills")
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, f"bill_{bill_id}.pdf")

    try:
        paper_width_mm = int(os.getenv("RECEIPT_WIDTH_MM", "58"))
    except (TypeError, ValueError):
        paper_width_mm = 58
    if paper_width_mm not in (58, 80):
        paper_width_mm = 58

    page_width = paper_width_mm * mm
    margin = 4 * mm if paper_width_mm == 58 else 5 * mm
    content_width = page_width - (2 * margin)
    line_height = 3.6 * mm
    now = datetime.now()

    shop_name = os.getenv("SHOP_NAME", "RAJ STORE").strip() or "RAJ STORE"
    shop_address = os.getenv("SHOP_ADDRESS", "Kulithalai, Karur").strip()
    shop_phone = os.getenv("SHOP_PHONE", "").strip()
    shop_gstin = os.getenv("SHOP_GSTIN", "").strip()

    items = bill_data.get("items") or []
    # Estimate height before drawing, so receipts can be printed as one roll.
    estimated_lines = 24 + (len(shop_name) // 20) + (len(items) * 4)
    for item in items:
        estimated_lines += max(0, len(str(item.get("product_name", ""))) // (25 if paper_width_mm == 58 else 38))
    estimated_lines += (len(shop_address) // (25 if paper_width_mm == 58 else 38))
    if shop_phone:
        estimated_lines += 1
    if shop_gstin:
        estimated_lines += 1
    page_height = max(105 * mm, (estimated_lines * line_height) + (18 * mm))

    c = canvas.Canvas(file_path, pagesize=(page_width, page_height), pageCompression=1)
    x_left = margin
    x_right = page_width - margin
    y = page_height - (7 * mm)

    def centered(text, font="Helvetica", size=8):
        nonlocal y
        c.setFont(font, size)
        c.drawCentredString(page_width / 2, y, str(text))
        y -= line_height

    def left(text, font="Helvetica", size=7.5):
        nonlocal y
        c.setFont(font, size)
        c.drawString(x_left, y, str(text))
        y -= line_height

    def rule(char="-"):
        nonlocal y
        c.setFont("Helvetica", 7)
        c.drawCentredString(page_width / 2, y, char * (28 if paper_width_mm == 58 else 42))
        y -= line_height

    def pair(label, value, bold=False, size=7.5):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawString(x_left, y, str(label))
        c.drawRightString(x_right, y, str(value))
        y -= line_height

    centered(shop_name.upper(), "Helvetica-Bold", 11 if paper_width_mm == 58 else 13)
    if shop_address:
        for address_line in _wrap_text(shop_address, 26 if paper_width_mm == 58 else 38):
            centered(address_line, size=7)
    if shop_phone:
        centered(f"Phone: {shop_phone}", size=7)
    if shop_gstin:
        centered(f"GSTIN: {shop_gstin}", size=7)

    rule("=")
    centered("SALES RECEIPT", "Helvetica-Bold", 9)
    pair("Receipt No:", f"{bill_id}", bold=True)
    pair("Date:", now.strftime("%d-%m-%Y"))
    pair("Time:", now.strftime("%I:%M %p"))
    pair("Customer:", str(bill_data.get("customer_name") or "Walk-in Customer")[:24 if paper_width_mm == 58 else 38])
    rule()

    # Compact two-line item layout remains readable on 58 mm paper.
    for item in items:
        name = str(item.get("product_name") or "Item")
        for line in _wrap_text(name, 25 if paper_width_mm == 58 else 38):
            left(line, "Helvetica-Bold", 7.5)
        quantity = int(item.get("quantity") or 0)
        unit_price = _money(item.get("unit_price", 0))
        line_total = _money(item.get("line_total", 0))
        pair(f"{quantity} x {unit_price}", line_total, size=7.5)
        gst_percent = item.get("gst_percent", 0)
        gst_amount = _money(item.get("gst_amount", 0))
        pair(f"  GST {gst_percent}%", gst_amount, size=7)

    rule("-")
    pair("Subtotal", f"Rs. {_money(bill_data.get('subtotal'))}")
    pair("Total GST", f"Rs. {_money(bill_data.get('total_gst'))}")
    if bill_data.get("discount_amount"):
        pair("Discount", f"- Rs. {_money(bill_data.get('discount_amount'))}")
    if bill_data.get("loyalty_points_redeemed"):
        pair(f"Points redeemed ({bill_data.get('loyalty_points_redeemed')})", f"- Rs. {_money(bill_data.get('loyalty_redemption_amount'))}")
    rule("=")
    pair("TOTAL PAYABLE", f"Rs. {_money(bill_data.get('total_amount'))}", bold=True, size=9)
    rule("=")
    pair("Payment:", str(bill_data.get("payment_method") or "Cash").title())
    if bill_data.get("loyalty_points_earned"):
        pair("Points earned:", str(bill_data["loyalty_points_earned"]))
    if bill_data.get("loyalty_points_before") is not None and bill_data.get("customer_id"):
        pair("Points before:", str(bill_data.get("loyalty_points_before", 0)))
        pair("Points balance:", str(bill_data.get("loyalty_points_after", 0)))
    y -= line_height / 2
    centered("Thank you for shopping with us!", "Helvetica-Bold", 7.5)
    centered("Please visit again.", size=7)
    y -= 2 * mm
    centered("*** END OF RECEIPT ***", size=6.5)

    c.showPage()
    c.save()
    return file_path
