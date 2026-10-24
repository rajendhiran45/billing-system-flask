
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import (
    Blueprint,
    current_app,
    request,
    jsonify,
    render_template,
    send_file,
    session,
)

from services.billing_service import calculate_bill
from models.billing_model import save_bill, get_all_bills
from models.product_model import get_all_products
from utils.pdf_generator import generate_bill_pdf
from models.customer_model import get_customer, list_customers, save_customer
from models.audit_model import log_action


billing_bp = Blueprint("billing", __name__)

PAYMENT_METHODS = {"cash", "card", "upi"}
CENT = Decimal("0.01")


def _money(value):
    return Decimal(str(value)).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def _payments(raw_payments, expected_total, split_mode=False):
    """
    Validate payment details.

    Single payment:
        Use the server-calculated final total automatically.

    Split payment:
        Every amount must be valid and the sum must equal the final total.
    """
    expected = _money(expected_total)

    if not expected.is_finite() or expected <= 0:
        raise ValueError("The bill total must be greater than zero.")

    if not isinstance(raw_payments, list) or not raw_payments:
        raise ValueError("Choose a payment method.")

    # A split payment must contain at least two valid payment entries.
    if split_mode and len(raw_payments) < 2:
        raise ValueError(
            "Add at least two payment entries for split payment."
        )

    # For one ordinary payment, the amount is always the final bill total.
    if len(raw_payments) == 1 and not split_mode:
        item = raw_payments[0]

        if not isinstance(item, dict):
            raise ValueError("Invalid payment details.")

        method = str(item.get("method", "")).strip().lower()

        if method not in PAYMENT_METHODS:
            raise ValueError("Choose Cash, UPI, or Card.")

        return [{
            "method": method,
            "amount": expected,
        }]

    cleaned = []
    payment_total = Decimal("0.00")

    for item in raw_payments:
        if not isinstance(item, dict):
            raise ValueError("Invalid payment details.")

        method = str(item.get("method", "")).strip().lower()

        if method not in PAYMENT_METHODS:
            raise ValueError("Choose a valid payment method.")

        try:
            amount = _money(item.get("amount"))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError(
                "Each split payment amount must be valid."
            )

        if not amount.is_finite() or amount <= 0:
            raise ValueError(
                "Each split payment amount must be greater than zero."
            )

        cleaned.append({
            "method": method,
            "amount": amount,
        })
        payment_total += amount

    if _money(payment_total) != expected:
        raise ValueError(
            "Split payment amounts must equal the final bill total."
        )

    return cleaned


@billing_bp.route("/api/customers/quick-create", methods=["POST"])
def quick_create_customer():
    """Allow signed-in cashiers to register a customer during billing."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "Customer details are required."}), 400

    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    email = str(data.get("email", "")).strip()
    address = str(data.get("address", "")).strip()

    if not name:
        return jsonify({"status": "error", "message": "Customer name is required."}), 400

    if len(name) > 120 or len(phone) > 30 or len(email) > 120 or len(address) > 255:
        return jsonify({"status": "error", "message": "One or more customer details are too long."}), 400

    try:
        customer_id = save_customer(None, name, phone, email, address)
        log_action(
            session.get("user_id"),
            "customer_created_at_checkout",
            "customer",
            customer_id,
            {"name": name},
        )
        from extensions import mysql
        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "customer": {
                "id": customer_id,
                "name": name,
                "phone": phone,
                "email": email,
                "address": address,
                "loyalty_points": 0,
                "loyalty_lifetime_points": 0,
            },
        }), 201
    except Exception:
        current_app.logger.exception("Quick customer creation failed")
        return jsonify({
            "status": "error",
            "message": "Could not save customer. Phone numbers must be unique.",
        }), 400

@billing_bp.route("/api/billing/checkout", methods=["POST"])
def checkout():
    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict) or "cart_items" not in data:
            return jsonify({
                "status": "error",
                "message": "Cart items are required.",
            }), 400

        cart_items = data.get("cart_items")

        if not isinstance(cart_items, list) or not cart_items:
            return jsonify({
                "status": "error",
                "message": "Cart must contain at least one product.",
            }), 400

        # Validate the selected customer.
        raw_customer_id = data.get("customer_id")
        customer_id = None
        customer = None

        if raw_customer_id not in (None, ""):
            try:
                customer_id = int(raw_customer_id)
            except (TypeError, ValueError):
                return jsonify({
                    "status": "error",
                    "message": "Invalid customer ID.",
                }), 400

            if customer_id <= 0:
                return jsonify({
                    "status": "error",
                    "message": "Invalid customer ID.",
                }), 400

            customer = get_customer(customer_id)

            if not customer:
                return jsonify({
                    "status": "error",
                    "message": "Selected customer was not found.",
                }), 400

        # Automatic discounts are calculated by billing_service.py.
        # Do not accept a client-provided discount amount as authoritative.
        try:
            requested_points = int(
                data.get("loyalty_points_redeemed", 0) or 0
            )
        except (TypeError, ValueError):
            return jsonify({
                "status": "error",
                "message": "Invalid loyalty points.",
            }), 400

        if requested_points < 0:
            return jsonify({
                "status": "error",
                "message": "Loyalty points cannot be negative.",
            }), 400

        if requested_points and not customer_id:
            return jsonify({
                "status": "error",
                "message": (
                    "Only registered customers can redeem loyalty points."
                ),
            }), 400

        if customer_id:
            available_points = int(customer.get("loyalty_points") or 0)

            if requested_points > available_points:
                return jsonify({
                    "status": "error",
                    "message": (
                        "Customer does not have enough loyalty points."
                    ),
                }), 400

        # The billing service calculates the automatic percentage discount,
        # loyalty redemption, GST, and final amount.
        bill_data = calculate_bill(
            cart_items,
            0,
            requested_points,
        )

        if not bill_data:
            return jsonify({
                "status": "error",
                "message": (
                    "Unable to calculate the bill. "
                    "Check the cart, stock, discount, and loyalty values."
                ),
            }), 400

        if requested_points != bill_data["loyalty_points_redeemed"]:
            return jsonify({
                "status": "error",
                "message": (
                    "Loyalty redemption exceeds the permitted limit. "
                    "Reduce the points and try again."
                ),
            }), 400

        # Support the existing payments array and a single payment method.
        raw_payments = data.get("payments")
        payment_choice = str(
            data.get("payment_method", data.get("payment_mode", ""))
        ).strip().lower()

        split_mode = (
            payment_choice == "split"
            or data.get("payment_mode") == "split"
        )

        if not raw_payments and payment_choice in PAYMENT_METHODS:
            raw_payments = [{
                "method": payment_choice,
                "amount": bill_data["total_amount"],
            }]

        try:
            payments = _payments(
                raw_payments,
                bill_data["total_amount"],
                split_mode=split_mode,
            )
        except ValueError as exc:
            return jsonify({
                "status": "error",
                "message": str(exc),
            }), 400

        bill_data["payment_method"] = (
            payments[0]["method"]
            if len(payments) == 1
            else "split"
        )

        bill_id = save_bill(
            bill_data,
            customer_id=customer_id,
            cashier_id=session.get("user_id"),
            low_stock_threshold=current_app.config.get(
                "LOW_STOCK_THRESHOLD", 5
            ),
            payments=payments,
        )

        if not bill_id:
            return jsonify({
                "status": "error",
                "message": "Failed to save the bill.",
            }), 500

        # Add customer and loyalty details to the PDF receipt.
        bill_data["customer_id"] = customer_id

        if customer:
            points_before = int(customer.get("loyalty_points") or 0)

            bill_data["customer_name"] = customer["name"]
            bill_data["customer_phone"] = customer.get("phone")
            bill_data["loyalty_points_before"] = points_before
            bill_data["loyalty_points_after"] = (
                points_before
                - bill_data["loyalty_points_redeemed"]
                + bill_data["loyalty_points_earned"]
            )
        else:
            bill_data["customer_name"] = "Walk-in Customer"
            bill_data["customer_phone"] = None
            bill_data["loyalty_points_before"] = 0
            bill_data["loyalty_points_after"] = 0

        pdf_path = generate_bill_pdf(bill_data, bill_id)

        return send_file(
            pdf_path,
            as_attachment=False,
            mimetype="application/pdf",
        )

    except Exception:
        logging.exception("Checkout failed")

        return jsonify({
            "status": "error",
            "message": (
                "Unable to complete checkout. "
                "Check the server logs."
            ),
        }), 500


@billing_bp.route("/api/billing/products", methods=["GET"])
def billing_products_api():
    """Return the latest product stock quantities."""
    try:
        products = get_all_products()

        return jsonify({
            "status": "success",
            "products": [
                {
                    "id": product["id"],
                    "name": product["name"],
                    "stock": int(product["stock"] or 0),
                }
                for product in products
            ],
        })

    except Exception:
        logging.exception("Failed to fetch billing products")

        return jsonify({
            "status": "error",
            "message": "Unable to fetch current product stock.",
        }), 500


@billing_bp.route("/billing")
def billing_page():
    products = get_all_products()
    customers = list_customers()

    return render_template(
        "billing.html",
        products=products,
        customers=customers,
    )


@billing_bp.route("/history")
def history_page():
    bills = get_all_bills()
    return render_template("history.html", bills=bills)
