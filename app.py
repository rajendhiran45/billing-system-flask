from datetime import timedelta

from flask import Flask, jsonify, redirect, request, session, url_for

from config import Config
from extensions import mysql
from routes.auth import auth_bp
from routes.billing import billing_bp
from routes.products import product_bp
from routes.management import management_bp

app = Flask(__name__)
app.config.from_object(Config)
mysql.init_app(app)

# Keep session lifetime finite. The secret is loaded from the environment in config.py.
app.config.setdefault("PERMANENT_SESSION_LIFETIME", timedelta(hours=8))
app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")

app.register_blueprint(auth_bp)
app.register_blueprint(product_bp)
app.register_blueprint(billing_bp)
app.register_blueprint(management_bp)


@app.before_request
def require_login():
    """Protect application pages and APIs, leaving auth and static routes public."""
    if request.endpoint is None:
        return None

    public_endpoints = {"auth.login", "auth.register", "auth.logout", "static"}
    if request.endpoint in public_endpoints or request.endpoint.startswith("static"):
        return None

    if not session.get("user_id"):
        if request.path.startswith("/api/"):
            return jsonify({"status": "error", "message": "Authentication required"}), 401
        return redirect(url_for("auth.login", next=request.path))

    return None


@app.route("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("billing.billing_page"))
    return redirect(url_for("auth.login"))


if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False))
