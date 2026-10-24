from flask import Blueprint,jsonify,request,redirect,url_for,flash,session
from models.product_model import get_all_products,add_product,update_product,delete_product
import os
import uuid
from flask import render_template, current_app
from routes.access import admin_required
from models.audit_model import log_action
from extensions import mysql

product_bp=Blueprint('product',__name__)

@product_bp.route('/products')
@admin_required
def fetch_products():
    products=get_all_products()
    return render_template(
        "products.html",
        products=products,
        low_stock_threshold=current_app.config.get("LOW_STOCK_THRESHOLD", 5),
    )

@product_bp.route('/api/products/add',methods=['POST'])
@admin_required
def add_product_route():
    try:
        name = request.form.get('name')
        price = request.form.get('price')
        gst_percent = request.form.get('gst_percent')
        stock = request.form.get('stock')

        if not name or not price:
            flash("Name and Price are required", "error")
            return redirect(url_for('product.fetch_products'))

        price = float(price)
        gst_percent = float(gst_percent) if gst_percent else 0
        stock = int(stock) if stock else 0
        if price <= 0 or stock < 0 or not 0 <= gst_percent <= 100:
            flash("Enter a positive price, non-negative stock, and GST between 0 and 100.", "error")
            return redirect(url_for('product.fetch_products'))

        image = request.files.get('image')
        image_path = None

        if image:
            allowed = {'jpg', 'jpeg', 'png', 'webp'}
            ext = image.filename.rsplit('.', 1)[-1].lower()

            if ext not in allowed:
                flash("Invalid image type", "error")
                return redirect(url_for('product.fetch_products'))

            import uuid, os
            filename = str(uuid.uuid4()) + "." + ext
            upload_folder = "static/uploads/products"
            os.makedirs(upload_folder, exist_ok=True)

            file_path = os.path.join(upload_folder, filename)
            image.save(file_path)

            image_path = f"uploads/products/{filename}"

        success = add_product(name, price, gst_percent, stock, image_path)

        if success:
            log_action(session.get("user_id"), "product_created", "product", None, {"name": name, "stock": stock})
            mysql.connection.commit()
            flash("Product added successfully!", "success")
        else:
            flash("Failed to add product", "error")

        return redirect(url_for('product.fetch_products'))

    except Exception as e:
        flash(str(e), "error")
        return redirect(url_for('product.fetch_products'))

@product_bp.route('/api/products/edit/<int:product_id>', methods=['PUT'])
@admin_required
def update_product_route(product_id):
    try:
        name = request.form.get('name')
        price = request.form.get('price')
        gst_percent = request.form.get('gst_percent')
        stock = request.form.get('stock')

        if price is None:
            return jsonify({"error": "Price required"}), 400
             
        price = float(price)
        gst_percent = float(gst_percent) if gst_percent else 0
        stock = int(stock) if stock else 0
        if price <= 0 or stock < 0 or not 0 <= gst_percent <= 100:
            return jsonify({"status": "error", "message": "Enter a positive price, non-negative stock, and GST between 0 and 100."}), 400

        image = request.files.get('image')
        image_path = None

        if image:
            ext = image.filename.rsplit('.', 1)[-1].lower()
            filename = str(uuid.uuid4()) + "." + ext
            upload_folder = "static/uploads/products"
            os.makedirs(upload_folder, exist_ok=True)

            file_path = os.path.join(upload_folder, filename)
            image.save(file_path)

            image_path = f"uploads/products/{filename}"

        success = update_product(product_id, name, price, gst_percent, stock, image_path)

        if success:
            log_action(session.get("user_id"), "product_updated", "product", product_id, {"name": name, "stock": stock})
            mysql.connection.commit()
            return jsonify({"status": "success", "message": "Product updated"}), 200
        else:
            return jsonify({"status": "error", "message": "Update failed"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

@product_bp.route('/api/products/delete/<int:product_id>', methods=['DELETE'])
@admin_required
def delete_product_route(product_id):
    try:
        success = delete_product(product_id)

        if success:
            log_action(session.get("user_id"), "product_archived", "product", product_id)
            mysql.connection.commit()
            return jsonify({"status": "success", "message": "Product deleted"}), 200
        else:
            return jsonify({"status": "error", "message": "Delete failed"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

