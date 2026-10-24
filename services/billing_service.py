
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR

from services.gst_service import calculate_gst
from models.product_model import get_product_by_id


CENT = Decimal("0.01")
POINT_VALUE = Decimal("0.10")  # 100 points = ₹10
MAX_LOYALTY_REDEMPTION_RATE = Decimal("0.20")


def money(value):
    return Decimal(str(value or 0)).quantize(
        CENT,
        rounding=ROUND_HALF_UP
    )


def calculate_automatic_discount(subtotal):
    """Return the automatic percentage discount amount and rate."""

    subtotal = money(subtotal)

    if subtotal >= Decimal("5000"):
        percentage = Decimal("15")
    elif subtotal >= Decimal("2000"):
        percentage = Decimal("10")
    elif subtotal >= Decimal("1000"):
        percentage = Decimal("5")
    else:
        percentage = Decimal("0")

    discount_amount = money(
        subtotal * percentage / Decimal("100")
    )

    return discount_amount, percentage


def calculate_bill(cart_items, discount_amount=0, loyalty_points_redeemed=0):
    """
    Calculate a bill using automatic percentage discounts.

    Rules:
    - Under ₹1,000: no automatic discount.
    - ₹1,000 and above: 5% discount.
    - ₹2,000 and above: 10% discount.
    - ₹5,000 and above: 15% discount.
    - Loyalty redemption: 100 points = ₹10.
    - Maximum loyalty redemption: 20% of subtotal after coupon discount.
    - Discounts are applied before GST.

    The discount_amount parameter is retained for compatibility with
    existing callers but is intentionally ignored.
    """

    try:
        if not isinstance(cart_items, list) or not cart_items:
            return None

        items = []
        subtotal = Decimal("0.00")

        # Validate products and calculate subtotal.
        for item in cart_items:
            if not isinstance(item, dict):
                return None

            product_id = item.get("product_id")
            quantity = item.get("quantity")

            if (
                isinstance(quantity, bool)
                or not isinstance(quantity, int)
                or quantity <= 0
            ):
                return None

            product = get_product_by_id(product_id)

            if not product or quantity > int(product["stock"]):
                return None

            price = money(product["price"])
            rate = Decimal(str(product["gst_percent"]))

            if rate < 0:
                return None

            line_subtotal = money(price * quantity)
            subtotal += line_subtotal

            items.append({
                "product_id": product["id"],
                "product_name": product["name"],
                "quantity": quantity,
                "unit_price": float(price),
                "gst_percent": float(rate),
                "gst_amount": 0.0,
                "line_subtotal": float(line_subtotal),
                "line_total": 0.0,
                "discount_allocated": 0.0,
            })

        subtotal = money(subtotal)

        # Automatically calculate percentage discount.
        automatic_discount, discount_percentage = (
            calculate_automatic_discount(subtotal)
        )

        # Loyalty redemption is calculated after the automatic discount.
        eligible_after_discount = money(
            subtotal - automatic_discount
        )

        try:
            points_requested = int(loyalty_points_redeemed or 0)
        except (TypeError, ValueError):
            return None

        if points_requested < 0:
            return None

        # The calling route must also verify that the customer is registered
        # and has enough points. This function alone cannot verify ownership
        # or the customer's current loyalty balance.
        max_redemption = money(
            eligible_after_discount * MAX_LOYALTY_REDEMPTION_RATE
        )

        max_points_by_limit = int(
            (max_redemption / POINT_VALUE).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )

        points_used = min(points_requested, max_points_by_limit)
        redemption = money(Decimal(points_used) * POINT_VALUE)

        total_discount = money(automatic_discount + redemption)
        eligible_net = money(subtotal - total_discount)

        # Allocate discounts proportionally across items before GST.
        ratio = (
            eligible_net / subtotal
            if subtotal > 0
            else Decimal("0")
        )

        gst_total = Decimal("0.00")

        for line in items:
            original_line_subtotal = money(line["line_subtotal"])

            line_base = money(original_line_subtotal * ratio)

            line_gst = money(
                line_base
                * Decimal(str(line["gst_percent"]))
                / Decimal("100")
            )

            line_total = money(line_base + line_gst)

            line["gst_amount"] = float(line_gst)
            line["line_total"] = float(line_total)
            line["discount_allocated"] = float(
                money(original_line_subtotal - line_base)
            )

            gst_total += line_gst

        gst_total = money(gst_total)
        total = money(eligible_net + gst_total)

        # Earn 1 point for each full ₹100 of eligible pre-tax spend.
        earned = int(
            (eligible_net / Decimal("100")).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )

        return {
            "items": items,
            "subtotal": float(subtotal),
            "discount_percentage": float(discount_percentage),
            "discount_amount": float(automatic_discount),
            "loyalty_points_redeemed": points_used,
            "loyalty_redemption_amount": float(redemption),
            "loyalty_points_earned": earned,
            "total_discount": float(total_discount),
            "taxable_amount": float(eligible_net),
            "total_gst": float(gst_total),
            "total_amount": float(total),
        }

    except Exception as exc:
        print("Error in calculate_bill:", repr(exc))
        return None
