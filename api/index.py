
import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, '..', 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)

DATABASE_URL = os.environ.get("DATABASE_URL")
SQLITE_PATH = "/tmp/shop.db"

def get_connection():
    if DATABASE_URL:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn, "postgres"
    else:
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"

def init_db():
    conn, db_type = get_connection()
    c = conn.cursor()
    if db_type == "postgres":
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            category TEXT,
            package_name TEXT,
            price INTEGER,
            uid TEXT,
            ign TEXT,
            payment_method TEXT,
            trx_id TEXT,
            phone TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TEXT
        )''')
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            package_name TEXT,
            price INTEGER,
            uid TEXT,
            ign TEXT,
            payment_method TEXT,
            trx_id TEXT,
            phone TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TEXT
        )''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    init_db()
    return render_template('index.html')

@app.route('/api/order', methods=['POST'])
def create_order():
    init_db()
    data = request.json
    conn, db_type = get_connection()
    c = conn.cursor()
    placeholder = "%s" if db_type == "postgres" else "?"
    
    query = f'''INSERT INTO orders 
        (category, package_name, price, uid, ign, payment_method, trx_id, phone, created_at)
        VALUES ({', '.join([placeholder]*9)})'''
    
    values = (
        data['category'],
        data['package_name'],
        data['price'],
        data['uid'],
        data['ign'],
        data['payment_method'],
        data['trx_id'],
        data['phone'],
        datetime.now().strftime("%Y-%m-%d %I:%M %p")
    )
    c.execute(query, values)
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "অর্ডার সফলভাবে গ্রহণ করা হয়েছে!"})

@app.route('/api/orders', methods=['GET'])
def get_orders():
    init_db()
    conn, _ = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM orders ORDER BY id DESC")
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/order/<int:order_id>', methods=['PATCH'])
def update_order(order_id):
    init_db()
    data = request.json
    conn, db_type = get_connection()
    c = conn.cursor()
    placeholder = "%s" if db_type == "postgres" else "?"
    c.execute(f"UPDATE orders SET status = {placeholder} WHERE id = {placeholder}", (data['status'], order_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)
