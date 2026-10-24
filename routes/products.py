from flask import Blueprint, jsonify, request, redirect, url_for, flash, session
from flask import render_template, current_app
from werkzeug.utils import secure_filename
import uuid

import cloudinary
import cloudinary.uploader

from models.product_model import (
    get_all_products,
    add_product,
    update_product,
    delete_product,
)
from routes.access import admin_required
from models.audit_model import log_action
from extensions import mysql


product_bp = Blueprint("product", __name__)

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def upload_product_image(image):
    """Upload an image to Cloudinary and return its permanent HTTPS URL."""
    safe_name = secure_filename(image.filename or "")

    if "." not in safe_name:
        raise ValueError("Choose a JPG, JPEG, PNG, or WEBP image.")

    extension = safe_name.rsplit(".", 1)[1].lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Choose a JPG, JPEG, PNG, or WEBP image.")

    cloud_name = current_app.config.get("CLOUDINARY_CLOUD_NAME")
    api_key = current_app.config.get("CLOUDINARY_API_KEY")
    api_secret = current_app.config.get("CLOUDINARY_API_SECRET")

    if not all([cloud_name, api_key, api_secret]):
        raise RuntimeError("Cloudinary is not configured on the server.")

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )

    result = cloudinary.uploader.upload(
        image,
        folder="billora/products",
        public_id=str(uuid.uuid4()),
        resource_type="image",
        overwrite=False,
    )

    return result["secure_url"]


@product_bp.route("/products")
@admin_required
def fetch_products():
    products = get_all_products()

    return render_template(
        "products.html",
        products=products,
        low_stock_threshold=current_app.config.get("LOW_STOCK_THRESHOLD", 5),
    )


@product_bp.route("/api/products/add", methods=["POST"])
@admin_required
def add_product_route():
    try:
        name = request.form.get("name")
        price = request.form.get("price")
        gst_percent = request.form.get("gst_percent")
        stock = request.form.get("stock")

        if not name or not price:
            flash("Name and Price are required", "error")
            return redirect(url_for("product.fetch_products"))

        price = float(price)
        gst_percent = float(gst_percent) if gst_percent else 0
        stock = int(stock) if stock else 0

        if price <= 0 or stock < 0 or not 0 <= gst_percent <= 100:
            flash(
                "Enter a positive price, non-negative stock, and GST between 0 and 100.",
                "error",
            )
            return redirect(url_for("product.fetch_products"))

        image = request.files.get("image")
        image_path = None

        if image and image.filename:
            image_path = upload_product_image(image)

        success = add_product(name, price, gst_percent, stock, image_path)

        if success:
            log_action(
                session.get("user_id"),
                "product_created",
                "product",
                None,
                {"name": name, "stock": stock},
            )
            mysql.connection.commit()
            flash("Product added successfully!", "success")
        else:
            flash("Failed to add product", "error")

        return redirect(url_for("product.fetch_products"))

    except Exception as error:
        flash(str(error), "error")
        return redirect(url_for("product.fetch_products"))


@product_bp.route("/api/products/edit/<int:product_id>", methods=["PUT"])
@admin_required
def update_product_route(product_id):
    try:
        name = request.form.get("name")
        price = request.form.get("price")
        gst_percent = request.form.get("gst_percent")
        stock = request.form.get("stock")

        if price is None:
            return jsonify({"error": "Price required"}), 400

        price = float(price)
        gst_percent = float(gst_percent) if gst_percent else 0
        stock = int(stock) if stock else 0

        if price <= 0 or stock < 0 or not 0 <= gst_percent <= 100:
            return jsonify({
                "status": "error",
                "message": "Enter a positive price, non-negative stock, and GST between 0 and 100.",
            }), 400

        image = request.files.get("image")
        image_path = None

        if image and image.filename:
            image_path = upload_product_image(image)

        success = update_product(
            product_id,
            name,
            price,
            gst_percent,
            stock,
            image_path,
        )

        if success:
            log_action(
                session.get("user_id"),
                "product_updated",
                "product",
                product_id,
                {"name": name, "stock": stock},
            )
            mysql.connection.commit()
            return jsonify({
                "status": "success",
                "message": "Product updated",
            }), 200

        return jsonify({
            "status": "error",
            "message": "Update failed",
        }), 500

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error),
        }), 500


@product_bp.route("/api/products/delete/<int:product_id>", methods=["DELETE"])
@admin_required
def delete_product_route(product_id):
    try:
        success = delete_product(product_id)

        if success:
            log_action(
                session.get("user_id"),
                "product_archived",
                "product",
                product_id,
            )
            mysql.connection.commit()
            return jsonify({
                "status": "success",
                "message": "Product deleted",
            }), 200

        return jsonify({
            "status": "error",
            "message": "Delete failed",
        }), 500

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error),
        }), 500