from flask import Blueprint,request,jsonify
from services.billing_service import calculate_bill
from models.billing_model import save_bill,get_all_bills
from flask import render_template,send_file
from models.product_model import get_all_products
from utils.pdf_generator import generate_bill_pdf

billing_bp=Blueprint("billing",__name__)

@billing_bp.route('/api/billing/checkout',methods=['POST'])
def checkout():
    try:
        data=request.json

        if not data or "cart_items" not in data:
            return jsonify({
                    "status": "error",
                    "message": "cart_items required"
                }), 400
        
        cart_items=data.get("cart_items")

        bill_data=calculate_bill(cart_items)

        if not bill_data:

            return jsonify({
                        "status": "error",
                        "message": "Failed to calculate bill"
                    }), 500
        
        bill_id=save_bill(bill_data)

        if not bill_id:
            return jsonify({
                "status": "error",
                "message": "Failed to save bill"
            }), 500

        pdf_path = generate_bill_pdf(bill_data, bill_id)

        return send_file(pdf_path, as_attachment=False)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500       
    
    bill_id = save_bill(bill_data)

    
                
@billing_bp.route('/billing')
def billing_page():
    products = get_all_products()
    return render_template("billing.html", products=products)

@billing_bp.route('/history')
def history_page():
    bills = get_all_bills()
    return render_template("history.html", bills=bills)
