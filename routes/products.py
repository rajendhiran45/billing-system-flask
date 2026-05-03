from flask import Blueprint,jsonify,request,redirect,url_for,flash
from models.product_model import get_all_products,add_product,update_product,delete_product
import os
import uuid
from flask import render_template

product_bp=Blueprint('product',__name__)

@product_bp.route('/products')
def fetch_products():
    products=get_all_products()
    return render_template("products.html", products=products)

@product_bp.route('/api/products/add',methods=['POST'])
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
            flash("Product added successfully!", "success")
        else:
            flash("Failed to add product", "error")

        return redirect(url_for('product.fetch_products'))

    except Exception as e:
        flash(str(e), "error")
        return redirect(url_for('product.fetch_products'))

@product_bp.route('/api/products/edit/<int:product_id>', methods=['PUT'])
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
            return jsonify({"status": "success", "message": "Product updated"}), 200
        else:
            return jsonify({"status": "error", "message": "Update failed"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

@product_bp.route('/api/products/delete/<int:product_id>', methods=['DELETE'])
def delete_product_route(product_id):
    try:
        success = delete_product(product_id)

        if success:
            return jsonify({"status": "success", "message": "Product deleted"}), 200
        else:
            return jsonify({"status": "error", "message": "Delete failed"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

