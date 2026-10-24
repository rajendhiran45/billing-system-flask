from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from models.user_model import (
    count_users,
    create_user,
    ensure_users_table,
    get_user_by_username,
)
from models.schema import ensure_application_schema

auth_bp = Blueprint("auth", __name__)


def _database_ready():
    """Prepare the authentication table when an auth page is opened."""
    ensure_users_table()
    ensure_application_schema()


def _safe_next_url(candidate):
    # Only accept local relative paths to avoid open-redirect vulnerabilities.
    if candidate and candidate.startswith("/") and not candidate.startswith("//"):
        return candidate
    return url_for("billing.billing_page")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    try:
        _database_ready()
        if count_users() == 0:
            return redirect(url_for("auth.register"))
    except Exception:
        current_app.logger.exception("Could not prepare the authentication database")
        return render_template(
            "auth/login.html",
            setup_error="Could not connect to the database. Check your Aiven settings and try again.",
        ), 503

    if session.get("user_id"):
        return redirect(url_for("billing.billing_page"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Enter both your username and password.", "error")
            return render_template("auth/login.html"), 400

        try:
            user = get_user_by_username(username)
        except Exception:
            current_app.logger.exception("Login database lookup failed")
            flash("Unable to sign in right now. Please try again.", "error")
            return render_template("auth/login.html"), 503

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html"), 401

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session.permanent = True
        flash("Signed in successfully.", "success")
        return redirect(_safe_next_url(request.args.get("next")))

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    try:
        _database_ready()
        user_count = count_users()
    except Exception:
        current_app.logger.exception("Could not prepare the authentication database")
        return render_template(
            "auth/register.html",
            setup_error="Could not connect to the database. Check your Aiven settings and try again.",
        ), 503

    # Registration is available only for the first account. This prevents
    # unauthenticated visitors from creating additional accounts later.
    if user_count > 0:
        flash("An account already exists. Please sign in.", "info")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(username) < 3 or len(username) > 80:
            flash("Username must be between 3 and 80 characters.", "error")
        elif any(char.isspace() for char in username):
            flash("Username cannot contain spaces.", "error")
        elif len(password) < 10:
            flash("Use a password with at least 10 characters.", "error")
        elif password != confirm_password:
            flash("The passwords do not match.", "error")
        else:
            try:
                create_user(username, generate_password_hash(password), role="admin")
                current_app.logger.info("Initial application account created")
                flash("Account created. Sign in to continue.", "success")
                return redirect(url_for("auth.login"))
            except Exception:
                current_app.logger.exception("Could not create the initial account")
                flash("Could not create the account. Check the database connection and try again.", "error")

    return render_template("auth/register.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))
