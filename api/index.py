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
    id_col = "SERIAL PRIMARY KEY" if db_type == "postgres" else "INTEGER PRIMARY KEY AUTOINCREMENT"

    c.execute(f'''CREATE TABLE IF NOT EXISTS users (
        id {id_col},
        name TEXT,
        phone TEXT UNIQUE,
        password TEXT,
        balance INTEGER DEFAULT 0,
        created_at TEXT
    )''')

    c.execute(f'''CREATE TABLE IF NOT EXISTS wallet_requests (
        id {id_col},
        user_id INTEGER,
        user_name TEXT,
        phone TEXT,
        amount INTEGER,
        method TEXT,
        trx_id TEXT,
        status TEXT DEFAULT 'Pending',
        created_at TEXT
    )''')

    c.execute(f'''CREATE TABLE IF NOT EXISTS orders (
        id {id_col},
        user_id INTEGER DEFAULT 0,
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

@app.route('/api/register', methods=['POST'])
def register():
    init_db()
    data = request.json
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()
    if not name or not phone or not password:
        return jsonify({"success": False, "message": "সব তথ্য সঠিকভাবে দিন!"}), 400

    conn, db_type = get_connection()
    c = conn.cursor()
    p = "%s" if db_type == "postgres" else "?"
    c.execute(f"SELECT id FROM users WHERE phone = {p}", (phone,))
    if c.fetchone():
        conn.close()
        return jsonify({"success": False, "message": "এই নম্বর দিয়ে আগেই অ্যাকাউন্ট খোলা আছে!"}), 400

    now = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    c.execute(f"INSERT INTO users (name, phone, password, balance, created_at) VALUES ({p}, {p}, {p}, 0, {p})",
              (name, phone, password, now))
    conn.commit()
    c.execute(f"SELECT id, name, phone, balance FROM users WHERE phone = {p}", (phone,))
    user = dict(c.fetchone())
    conn.close()
    return jsonify({"success": True, "user": user})

@app.route('/api/login', methods=['POST'])
def login():
    init_db()
    data = request.json
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()

    conn, db_type = get_connection()
    c = conn.cursor()
    p = "%s" if db_type == "postgres" else "?"
    c.execute(f"SELECT id, name, phone, balance FROM users WHERE phone = {p} AND password = {p}", (phone, password))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({"success": False, "message": "ফোন নম্বর বা পাসওয়ার্ড ভুল!"}), 401
    return jsonify({"success": True, "user": dict(row)})

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    init_db()
    conn, db_type = get_connection()
    c = conn.cursor()
    p = "%s" if db_type == "postgres" else "?"
    c.execute(f"SELECT id, name, phone, balance FROM users WHERE id = {p}", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({"success": False}), 404
    return jsonify({"success": True, "user": dict(row)})

@app.route('/api/wallet/add', methods=['POST'])
def add_wallet_request():
    init_db()
    data = request.json
    conn, db_type = get_connection()
    c = conn.cursor()
    p = "%s" if db_type == "postgres" else "?"
    now = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    c.execute(f'''INSERT INTO wallet_requests (user_id, user_name, phone, amount, method, trx_id, created_at)
                  VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p})''',
              (data['user_id'], data['user_name'], data['phone'], int(data['amount']), data['method'], data['trx_id'], now))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Add Money রিকোয়েস্ট পাঠানো হয়েছে! অ্যাডমিন চেক করে ব্যালেন্স যোগ করে দেবেন।"})

@app.route('/api/wallet/requests', methods=['GET'])
def get_wallet_requests():
    init_db()
    user_id = request.args.get('user_id')
    conn, db_type = get_connection()
    c = conn.cursor()
    p = "%s" if db_type == "postgres" else "?"
    if user_id:
        c.execute(f"SELECT * FROM wallet_requests WHERE user_id = {p} ORDER BY id DESC", (int(user_id),))
    else:
        c.execute("SELECT * FROM wallet_requests ORDER BY id DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/wallet/request/<int:req_id>', methods=['PATCH'])
def update_wallet_request(req_id):
    init_db()
    data = request.json
    new_status = data['status']
    conn, db_type = get_connection()
    c = conn.cursor()
    p = "%s" if db_type == "postgres" else "?"
    c.execute(f"SELECT * FROM wallet_requests WHERE id = {p}", (req_id,))
    req_row = c.fetchone()
    if req_row and req_row['status'] == 'Pending':
        c.execute(f"UPDATE wallet_requests SET status = {p} WHERE id = {p}", (new_status, req_id))
        if new_status == 'Approved':
            c.execute(f"UPDATE users SET balance = balance + {p} WHERE id = {p}", (req_row['amount'], req_row['user_id']))
        conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/order', methods=['POST'])
def create_order():
    init_db()
    data = request.json
    user_id = int(data.get('user_id') or 0)
    price = int(data['price'])
    pay_method = data['payment_method']

    conn, db_type = get_connection()
    c = conn.cursor()
    p = "%s" if db_type == "postgres" else "?"

    if pay_method == "Wallet Balance":
        if not user_id:
            conn.close()
            return jsonify({"success": False, "message": "ওয়ালেট দিয়ে পেমেন্ট করতে আগে লগইন করুন!"}), 400
        c.execute(f"SELECT balance FROM users WHERE id = {p}", (user_id,))
        u = c.fetchone()
        if not u or u['balance'] < price:
            conn.close()
            return jsonify({"success": False, "message": "আপনার ওয়ালেটে পর্যাপ্ত টাকা নেই! আগে Add Money করুন।"}), 400
        c.execute(f"UPDATE users SET balance = balance - {p} WHERE id = {p}", (price, user_id))

    now = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    query = f'''INSERT INTO orders 
        (user_id, category, package_name, price, uid, ign, payment_method, trx_id, phone, created_at)
        VALUES ({', '.join([p]*10)})'''
    values = (
        user_id,
        data['category'],
        data['package_name'],
        price,
        data['uid'],
        data.get('ign', ''),
        pay_method,
        data.get('trx_id', 'WALLET'),
        data['phone'],
        now
    )
    c.execute(query, values)
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "অর্ডার সফলভাবে গ্রহণ করা হয়েছে!"})

@app.route('/api/orders', methods=['GET'])
def get_orders():
    init_db()
    user_id = request.args.get('user_id')
    conn, db_type = get_connection()
    c = conn.cursor()
    p = "%s" if db_type == "postgres" else "?"
    if user_id:
        c.execute(f"SELECT * FROM orders WHERE user_id = {p} ORDER BY id DESC", (int(user_id),))
    else:
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
    p = "%s" if db_type == "postgres" else "?"
    c.execute(f"UPDATE orders SET status = {p} WHERE id = {p}", (data['status'], order_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)
