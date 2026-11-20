import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, '..', 'templates')
SETTINGS_PATH = os.path.join(BASE_DIR, '..', 'settings.json')

app = Flask(__name__, template_folder=TEMPLATE_DIR)

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
SQLITE_PATH = "/tmp/shop.db"
_db_initialized = False

CATALOG = {
    'Diamonds': [
        {'name': '25 Diamonds', 'price': 22, 'old': 25, 'save': 3},
        {'name': '50 Diamonds', 'price': 40, 'old': 45, 'save': 5},
        {'name': '115 Diamonds', 'price': 80, 'old': 85, 'save': 5},
        {'name': '240 Diamonds', 'price': 160, 'old': 170, 'save': 10},
        {'name': '355 Diamonds', 'price': 235, 'old': 250, 'save': 15},
        {'name': '610 Diamonds', 'price': 395, 'old': 420, 'save': 25},
        {'name': '1240 Diamonds', 'price': 785, 'old': 840, 'save': 55},
        {'name': '2530 Diamonds', 'price': 1580, 'old': 1680, 'save': 100}
    ],
    'Level Up Pass': [
        {'name': 'Level Up Pass (Full)', 'price': 165, 'old': 180, 'save': 15}
    ],
    'Memberships': [
        {'name': 'Weekly Lite', 'price': 35, 'old': 45, 'save': 10},
        {'name': 'Weekly Membership', 'price': 155, 'old': 170, 'save': 15},
        {'name': 'Monthly Membership', 'price': 760, 'old': 800, 'save': 40}
    ],
    'FF Like Sell': [
        {'name': 'Daily Like Bot - 30 Days', 'price': 100, 'old': 120, 'save': 20},
        {'name': 'Daily Like Bot - 90 Days', 'price': 300, 'old': 350, 'save': 50},
        {'name': 'Daily Like Bot - 365 Days', 'price': 1000, 'old': 1200, 'save': 200}
    ],
    'Guild Emote Bot': [
        {'name': 'Guild Glory Bot - 7 Days', 'price': 120, 'old': 150, 'save': 30},
        {'name': 'Guild Glory Bot - 30 Days', 'price': 350, 'old': 400, 'save': 50},
        {'name': 'Emote Bot - 7 Days', 'price': 80, 'old': 100, 'save': 20},
        {'name': 'Emote Bot - 30 Days', 'price': 250, 'old': 300, 'save': 50},
        {'name': 'Guild + Emote Combo (30D)', 'price': 550, 'old': 650, 'save': 100}
    ],
    'Evo Access': [
        {'name': 'Evo Access - 3 Days', 'price': 65, 'old': 80, 'save': 15},
        {'name': 'Evo Access - 7 Days', 'price': 120, 'old': 140, 'save': 20},
        {'name': 'Evo Access - 30 Days', 'price': 360, 'old': 420, 'save': 60}
    ]
}

def load_settings():
    default_settings = {
        "whatsapp_number": "88017XXXXXXXX",
        "admin_password": "1234",
        "payment_methods": [
            {"name": "bKash (Send Money)", "number": "017XXXXXXXX"},
            {"name": "Nagad (Send Money)", "number": "018XXXXXXXX"}
        ]
    }
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
    except Exception:
        pass
    return default_settings

def get_public_settings():
    s = load_settings()
    return {
        "whatsapp_number": s.get("whatsapp_number", ""),
        "payment_methods": s.get("payment_methods", [])
    }

def is_admin_authorized():
    expected = os.environ.get("ADMIN_PASSWORD") or load_settings().get("admin_password", "1234")
    provided = request.headers.get("X-Admin-Password", "")
    return bool(provided) and provided == str(expected)

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
    global _db_initialized
    if _db_initialized:
        return
    conn, db_type = get_connection()
    try:
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
        _db_initialized = True
    finally:
        conn.close()

def is_duplicate_trx(c, db_type, trx_id):
    p = "%s" if db_type == "postgres" else "?"
    clean_trx = trx_id.strip().lower()
    c.execute(f"SELECT id FROM wallet_requests WHERE LOWER(TRIM(trx_id)) = {p} AND status != 'Rejected'", (clean_trx,))
    if c.fetchone():
        return True
    c.execute(f"SELECT id FROM orders WHERE LOWER(TRIM(trx_id)) = {p} AND payment_method != 'Wallet Balance' AND status != 'Cancelled'", (clean_trx,))
    if c.fetchone():
        return True
    return False

@app.route('/')
def home():
    init_db()
    return render_template('index.html', shop_config=get_public_settings(), catalog=CATALOG)

@app.route('/api/register', methods=['POST'])
def register():
    init_db()
    data = request.json or {}
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()
    if not name or not phone or not password:
        return jsonify({"success": False, "message": "সব তথ্য সঠিকভাবে দিন!"}), 400
    if len(password) < 4:
        return jsonify({"success": False, "message": "পাসওয়ার্ড কমপক্ষে ৪ অক্ষরের হতে হবে!"}), 400

    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT id FROM users WHERE phone = {p}", (phone,))
        if c.fetchone():
            return jsonify({"success": False, "message": "এই নম্বর দিয়ে আগেই অ্যাকাউন্ট খোলা আছে!"}), 400

        hashed_pw = generate_password_hash(password)
        now = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        c.execute(f"INSERT INTO users (name, phone, password, balance, created_at) VALUES ({p}, {p}, {p}, 0, {p})",
                  (name, phone, hashed_pw, now))
        conn.commit()
        c.execute(f"SELECT id, name, phone, balance FROM users WHERE phone = {p}", (phone,))
        user = dict(c.fetchone())
        return jsonify({"success": True, "user": user})
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    init_db()
    data = request.json or {}
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()
    if not phone or not password:
        return jsonify({"success": False, "message": "ফোন নম্বর এবং পাসওয়ার্ড দিন!"}), 400

    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT id, name, phone, password, balance FROM users WHERE phone = {p}", (phone,))
        row = c.fetchone()
        if not row:
            return jsonify({"success": False, "message": "ফোন নম্বর বা পাসওয়ার্ড ভুল!"}), 401

        stored_pw = row['password'] or ''
        valid = False
        try:
            valid = check_password_hash(stored_pw, password)
        except Exception:
            valid = False

        if not valid and stored_pw == password:
            valid = True
            # পুরোনো plain-text পাসওয়ার্ড অটোমেটিক হ্যাশ করা হচ্ছে
            c.execute(f"UPDATE users SET password = {p} WHERE id = {p}", (generate_password_hash(password), row['id']))
            conn.commit()

        if not valid:
            return jsonify({"success": False, "message": "ফোন নম্বর বা পাসওয়ার্ড ভুল!"}), 401

        user = {"id": row['id'], "name": row['name'], "phone": row['phone'], "balance": row['balance']}
        return jsonify({"success": True, "user": user})
    finally:
        conn.close()

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    init_db()
    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT id, name, phone, balance FROM users WHERE id = {p}", (user_id,))
        row = c.fetchone()
        if not row:
            return jsonify({"success": False}), 404
        return jsonify({"success": True, "user": dict(row)})
    finally:
        conn.close()

@app.route('/api/wallet/add', methods=['POST'])
def add_wallet_request():
    init_db()
    data = request.json or {}
    try:
        user_id = int(data.get('user_id', 0))
        amount = int(data.get('amount', 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "সঠিক টাকার পরিমাণ দিন!"}), 400

    method = str(data.get('method', '')).strip()
    trx_id = str(data.get('trx_id', '')).strip()

    if user_id <= 0 or amount <= 0:
        return jsonify({"success": False, "message": "টাকার পরিমাণ ০-এর বেশি হতে হবে!"}), 400
    if not method or len(trx_id) < 4:
        return jsonify({"success": False, "message": "সঠিক পেমেন্ট মাধ্যম এবং TrxID দিন!"}), 400

    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT id, name, phone FROM users WHERE id = {p}", (user_id,))
        user = c.fetchone()
        if not user:
            return jsonify({"success": False, "message": "ইউজার পাওয়া যায়নি!"}), 404

        if is_duplicate_trx(c, db_type, trx_id):
            return jsonify({"success": False, "message": "এই TrxID দিয়ে আগেই রিকোয়েস্ট করা হয়েছে!"}), 400

        now = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        c.execute(f'''INSERT INTO wallet_requests (user_id, user_name, phone, amount, method, trx_id, created_at)
                      VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p})''',
                  (user['id'], user['name'], user['phone'], amount, method, trx_id, now))
        conn.commit()
        return jsonify({"success": True, "message": "Add Money রিকোয়েস্ট পাঠানো হয়েছে! অ্যাডমিন চেক করে ব্যালেন্স যোগ করে দেবেন।"})
    finally:
        conn.close()

@app.route('/api/wallet/requests', methods=['GET'])
def get_wallet_requests():
    init_db()
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify([])
    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT * FROM wallet_requests WHERE user_id = {p} ORDER BY id DESC", (int(user_id),))
        return jsonify([dict(r) for r in c.fetchall()])
    finally:
        conn.close()

@app.route('/api/order', methods=['POST'])
def create_order():
    init_db()
    data = request.json or {}
    try:
        user_id = int(data.get('user_id') or 0)
    except (ValueError, TypeError):
        user_id = 0

    category = str(data.get('category', '')).strip()
    package_name = str(data.get('package_name', '')).strip()
    uid = str(data.get('uid', '')).strip()
    ign = str(data.get('ign', '')).strip()
    pay_method = str(data.get('payment_method', '')).strip()
    trx_id = str(data.get('trx_id', '')).strip()
    phone = str(data.get('phone', '')).strip()

    if not uid or not phone:
        return jsonify({"success": False, "message": "Player UID এবং ফোন নম্বর দিন!"}), 400

    # সার্ভার থেকে আসল দাম যাচাই
    matched_pkg = next((pkg for pkg in CATALOG.get(category, []) if pkg['name'] == package_name), None)
    if not matched_pkg:
        return jsonify({"success": False, "message": "সঠিক প্যাকেজ সিলেক্ট করুন!"}), 400
    price = int(matched_pkg['price'])

    if pay_method != "Wallet Balance" and (len(trx_id) < 4 or trx_id.upper() == 'WALLET'):
        return jsonify({"success": False, "message": "সঠিক Transaction ID (TrxID) দিন!"}), 400

    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"

        if pay_method == "Wallet Balance":
            if user_id <= 0:
                return jsonify({"success": False, "message": "ওয়ালেট দিয়ে পেমেন্ট করতে আগে লগইন করুন!"}), 400
            c.execute(f"UPDATE users SET balance = balance - {p} WHERE id = {p} AND balance >= {p}",
                      (price, user_id, price))
            if c.rowcount != 1:
                conn.rollback()
                return jsonify({"success": False, "message": "আপনার ওয়ালেটে পর্যাপ্ত টাকা নেই! আগে Add Money করুন।"}), 400
            trx_id = "WALLET"
        else:
            if is_duplicate_trx(c, db_type, trx_id):
                return jsonify({"success": False, "message": "এই TrxID দিয়ে আগেই অর্ডার বা রিকোয়েস্ট করা হয়েছে!"}), 400

        now = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        if db_type == "postgres":
            query = f'''INSERT INTO orders
                (user_id, category, package_name, price, uid, ign, payment_method, trx_id, phone, created_at)
                VALUES ({', '.join([p]*10)}) RETURNING id'''
            c.execute(query, (user_id, category, package_name, price, uid, ign, pay_method, trx_id, phone, now))
            order_id = c.fetchone()['id']
        else:
            query = f'''INSERT INTO orders
                (user_id, category, package_name, price, uid, ign, payment_method, trx_id, phone, created_at)
                VALUES ({', '.join([p]*10)})'''
            c.execute(query, (user_id, category, package_name, price, uid, ign, pay_method, trx_id, phone, now))
            order_id = c.lastrowid

        conn.commit()
        return jsonify({"success": True, "order_id": order_id, "message": f"অর্ডার #{order_id} সফলভাবে গ্রহণ করা হয়েছে!"})
    finally:
        conn.close()

@app.route('/api/orders', methods=['GET'])
def get_orders():
    init_db()
    user_id = request.args.get('user_id')
    ids_param = request.args.get('ids', '').strip()

    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        if user_id:
            c.execute(f"SELECT * FROM orders WHERE user_id = {p} ORDER BY id DESC", (int(user_id),))
            return jsonify([dict(row) for row in c.fetchall()])
        elif ids_param:
            id_list = []
            for x in ids_param.split(',')[:50]:
                if x.strip().isdigit():
                    id_list.append(int(x.strip()))
            if not id_list:
                return jsonify([])
            placeholders = ', '.join([p] * len(id_list))
            c.execute(f"SELECT * FROM orders WHERE id IN ({placeholders}) ORDER BY id DESC", tuple(id_list))
            return jsonify([dict(row) for row in c.fetchall()])
        else:
            return jsonify([])
    finally:
        conn.close()

# ---------------- ADMIN ROUTES ----------------

@app.route('/api/admin/verify', methods=['POST'])
def admin_verify():
    data = request.json or {}
    expected = os.environ.get("ADMIN_PASSWORD") or load_settings().get("admin_password", "1234")
    if str(data.get('password', '')) == str(expected):
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "ভুল পাসওয়ার্ড!"}), 401

@app.route('/api/admin/overview', methods=['GET'])
def admin_overview():
    if not is_admin_authorized():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    init_db()
    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) AS cnt FROM users")
        total_users = c.fetchone()['cnt']
        c.execute("SELECT COUNT(*) AS cnt FROM orders WHERE status = 'Pending'")
        pending_orders = c.fetchone()['cnt']
        c.execute("SELECT COUNT(*) AS cnt FROM wallet_requests WHERE status = 'Pending'")
        pending_wallet = c.fetchone()['cnt']
        c.execute("SELECT id, name, phone, balance, created_at FROM users ORDER BY id DESC LIMIT 100")
        users = [dict(r) for r in c.fetchall()]
        return jsonify({
            "success": True,
            "db_type": db_type,
            "total_users": total_users,
            "pending_orders": pending_orders,
            "pending_wallet": pending_wallet,
            "users": users
        })
    finally:
        conn.close()

@app.route('/api/admin/orders', methods=['GET'])
def admin_get_orders():
    if not is_admin_authorized():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    init_db()
    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 200")
        return jsonify([dict(row) for row in c.fetchall()])
    finally:
        conn.close()

@app.route('/api/admin/wallet/requests', methods=['GET'])
def admin_get_wallet_requests():
    if not is_admin_authorized():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    init_db()
    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM wallet_requests ORDER BY id DESC LIMIT 200")
        return jsonify([dict(r) for r in c.fetchall()])
    finally:
        conn.close()

@app.route('/api/order/<int:order_id>', methods=['PATCH'])
def update_order(order_id):
    if not is_admin_authorized():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    init_db()
    data = request.json or {}
    new_status = data.get('status')
    if new_status not in ('Completed', 'Cancelled'):
        return jsonify({"success": False, "message": "Invalid status"}), 400

    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT * FROM orders WHERE id = {p}", (order_id,))
        order_row = c.fetchone()
        if not order_row:
            return jsonify({"success": False, "message": "Order not found"}), 404

        refunded = False
        if order_row['status'] == 'Pending':
            c.execute(f"UPDATE orders SET status = {p} WHERE id = {p} AND status = 'Pending'", (new_status, order_id))
            if c.rowcount == 1 and new_status == 'Cancelled' and order_row['payment_method'] == 'Wallet Balance' and int(order_row['user_id'] or 0) > 0:
                c.execute(f"UPDATE users SET balance = balance + {p} WHERE id = {p}",
                          (int(order_row['price']), int(order_row['user_id'])))
                refunded = True
            conn.commit()
        return jsonify({"success": True, "refunded": refunded})
    finally:
        conn.close()

@app.route('/api/wallet/request/<int:req_id>', methods=['PATCH'])
def update_wallet_request(req_id):
    if not is_admin_authorized():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    init_db()
    data = request.json or {}
    new_status = data.get('status')
    if new_status not in ('Approved', 'Rejected'):
        return jsonify({"success": False, "message": "Invalid status"}), 400

    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT * FROM wallet_requests WHERE id = {p}", (req_id,))
        req_row = c.fetchone()
        if req_row and req_row['status'] == 'Pending':
            c.execute(f"UPDATE wallet_requests SET status = {p} WHERE id = {p} AND status = 'Pending'", (new_status, req_id))
            if c.rowcount == 1 and new_status == 'Approved':
                c.execute(f"UPDATE users SET balance = balance + {p} WHERE id = {p}",
                          (int(req_row['amount']), int(req_row['user_id'])))
            conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
