from flask import Flask
from extensions import mysql
from config import Config
from routes.products import product_bp 
from routes.billing import billing_bp
from flask import render_template


app=Flask(__name__)
app.config.from_object(Config)
print("MYSQL_DB from app:", app.config.get('MYSQL_DB'))
mysql.init_app(app)
@app.route('/')
def home():
    return render_template('base.html')


app.register_blueprint(product_bp)
app.register_blueprint(billing_bp)


if __name__ == '__main__':
    app.run(debug=True)