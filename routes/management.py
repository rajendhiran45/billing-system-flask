import csv
from io import StringIO
from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from models.admin_model import list_users, set_user_role
from models.analytics_model import dashboard_data, forecast_products, low_stock_products, report_rows
from models.customer_model import list_customers, save_customer
from models.audit_model import log_action, recent_actions
from models.user_model import create_user, get_user_by_username
from routes.access import admin_required

management_bp = Blueprint("management", __name__)


@management_bp.route("/dashboard")
@admin_required
def dashboard():
    return render_template("dashboard.html", data=dashboard_data(), low_stock=low_stock_products(current_app.config["LOW_STOCK_THRESHOLD"]))


@management_bp.route("/inventory-alerts")
@admin_required
def inventory_alerts():
    threshold = current_app.config["LOW_STOCK_THRESHOLD"]
    return render_template("inventory_alerts.html", items=low_stock_products(threshold), threshold=threshold)


@management_bp.route("/forecast")
@admin_required
def forecast():
    return render_template("forecast.html", items=forecast_products())


@management_bp.route("/customers", methods=["GET", "POST"])
@admin_required
def customers():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Customer name is required.", "error")
        else:
            try:
                save_customer(request.form.get("customer_id", type=int), name, request.form.get("phone", "").strip(), request.form.get("email", "").strip(), request.form.get("address", "").strip())
                log_action(session.get("user_id"), "customer_saved", "customer", request.form.get("customer_id", type=int), {"name": name})
                from extensions import mysql
                mysql.connection.commit()
                flash("Customer saved.", "success")
            except Exception:
                current_app.logger.exception("Customer save failed")
                flash("Could not save customer. Phone numbers must be unique.", "error")
        return redirect(url_for("management.customers"))
    return render_template("customers.html", customers=list_customers())


@management_bp.route("/reports")
@admin_required
def reports():
    start, end = request.args.get("start"), request.args.get("end")
    return render_template("reports.html", rows=report_rows(start, end), start=start or "", end=end or "")


@management_bp.route("/reports/export.csv")
@admin_required
def export_reports():
    rows = report_rows(request.args.get("start"), request.args.get("end"))
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Bill ID", "Created at", "Customer", "Cashier", "Payment method", "Subtotal", "GST", "Total"])
    for row in rows:
        writer.writerow([row["id"], row["created_at"], row["customer_name"] or "Walk-in", row["cashier"] or "", row["payment_method"], row["subtotal"], row["gst_amount"], row["total"]])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=sales-report.csv"})


@management_bp.route("/admin/users", methods=["GET", "POST"])
@admin_required
def users():
    if request.method == "POST":
        username, password = request.form.get("username", "").strip(), request.form.get("password", "")
        role = request.form.get("role", "cashier")
        if role not in {"admin", "cashier"} or len(username) < 3 or len(password) < 10:
            flash("Use a 3+ character username and a 10+ character password.", "error")
        elif get_user_by_username(username):
            flash("That username is already in use.", "error")
        else:
            create_user(username, generate_password_hash(password), role)
            log_action(session.get("user_id"), "user_created", "user", None, {"username": username, "role": role})
            from extensions import mysql
            mysql.connection.commit()
            flash("Team member added.", "success")
        return redirect(url_for("management.users"))
    return render_template("users.html", users=list_users())


@management_bp.route("/admin/users/<int:user_id>/role", methods=["POST"])
@admin_required
def update_user_role(user_id):
    role = request.form.get("role")
    if role not in {"admin", "cashier"}:
        flash("Invalid role.", "error")
    elif user_id == session.get("user_id") and role != "admin":
        flash("You cannot remove your own administrator access.", "error")
    elif set_user_role(user_id, role):
        flash("Role updated.", "success")
    return redirect(url_for("management.users"))


@management_bp.route("/audit-log")
@admin_required
def audit_log():
    return render_template("audit_log.html", actions=recent_actions())

