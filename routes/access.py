"""Small access-control helpers shared by privileged routes."""
from functools import wraps
from flask import abort, jsonify, request, session


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") == "admin":
            return view(*args, **kwargs)
        if request.path.startswith("/api/"):
            return jsonify({"status": "error", "message": "Administrator access required."}), 403
        abort(403)
    return wrapped
