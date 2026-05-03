from extensions import mysql

def get_all_products():
    try:
        cur=mysql.connection.cursor()
        query="SELECT * FROM products WHERE is_active=TRUE ORDER BY created_at DESC"
        cur.execute(query)

        rows=cur.fetchall()
        print("Rows found:", rows)
        columns=[col[0]for col in cur.description]

        products=[]
        for row in rows:
            product=dict(zip(columns,row))

            product["price"] = float(product["price"])
            product["gst_percent"] = float(product["gst_percent"])
            products.append(product)
        
        cur.close()
        return products
    except Exception as e:
        print("Error in get_all_products:", e)
        return []

def add_product(name,price,gst_percent,stock,image_path):
    try:
        cur=mysql.connection.cursor()
        query="""INSERT INTO products(name,price,gst_percent,stock,image_path,is_active)
        VALUES(%s,%s,%s,%s,%s,TRUE)"""

        cur.execute(query,(name,price,gst_percent,stock,image_path))

        mysql.connection.commit()
        cur.close()
        return True
    
    except Exception as e:
        print("Error in get_all_products:", e)
        return False
    
def update_product(product_id,name,price,gst_percent,stock,image_path=None):
    try:
        cur=mysql.connection.cursor()
        if image_path:
            query="""
            UPDATE products
            SET name=%s,price=%s,gst_percent=%s,stock=%s,image_path=%s
            WHERE id=%s"""

            cur.execute(query,(name,price,gst_percent,stock,image_path,product_id))

        else:
            query="""
            UPDATE products
            SET name=%s,price=%s,gst_percent=%s,stock=%s
            WHERE id=%s"""

            cur.execute(query,(name,price,gst_percent,stock,product_id))

        mysql.connection.commit()
        cur.close()
        return True
    
    except Exception as e:
        print("Error in get_all_products:", e)
        return False
    

def delete_product(product_id):
    try:
        cur=mysql.connection.cursor()

        query="""UPDATE products SET is_active=FALSE WHERE id=%s"""
        cur.execute(query,(product_id,))

        mysql.connection.commit()
        cur.close()
        return True
    
    except Exception as e:
        print("Error in get_all_products:", e)
        return False

