from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
import os

def generate_bill_pdf(bill_data, bill_id):
    folder = "static/bills"
    os.makedirs(folder, exist_ok=True)

    file_path = f"{folder}/bill_{bill_id}.pdf"

    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    y = height - 40


    c.setFont("Helvetica-Bold", 18)
    c.drawString(200, y, "RAJ STORE")

    y -= 25
    c.setFont("Helvetica", 10)
    c.drawString(200, y, "Kulithalai, Karur")

   
    y -= 40
    c.drawString(50, y, f"Bill ID: {bill_id}")
    c.drawString(400, y, f"Date: {datetime.now().strftime('%d-%m-%Y')}")

    
    y -= 30
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Item")
    c.drawString(200, y, "Qty")
    c.drawString(260, y, "Price")
    c.drawString(330, y, "GST")
    c.drawString(420, y, "Total")

    y -= 10
    c.line(50, y, 550, y)

    c.setFont("Helvetica", 10)
    y -= 20

    for item in bill_data["items"]:
        c.drawString(50, y, item["product_name"])
        c.drawString(200, y, str(item["quantity"]))
        c.drawString(260, y, f"{item['unit_price']}")
        c.drawString(330, y, f"{item['gst_percent']}%")
        c.drawString(420, y, f"{item['line_total']}")

        y -= 20

  
    y -= 20
    c.line(50, y, 550, y)

    y -= 20
    c.drawString(350, y, f"Subtotal: Rs.{bill_data['subtotal']}")
    y -= 15
    c.drawString(350, y, f"GST: Rs.{bill_data['total_gst']}")
    y -= 15
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, y, f"Total: Rs.{bill_data['total_amount']}")

   
    y -= 40
    c.setFont("Helvetica", 10)
    c.drawString(200, y, "Thank you! Visit again ")

    c.save()

    return file_path