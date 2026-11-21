import os
import json
import time
import secrets
import smtplib
import sqlite3
import urllib.request
import urllib.parse
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, '..', 'templates')
SETTINGS_PATH = os.path.join(BASE_DIR, '..', 'settings.json')

app = Flask(__name__, template_folder=TEMPLATE_DIR)

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
SQLITE_PATH = "/tmp/shop.db"
_db_initialized = False
BD_TZ = timezone(timedelta(hours=6))

def bd_now():
    return datetime.now(BD_TZ)

DEFAULT_CATALOG = {
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
    'GUILD GLORY BOT': [
        {'name': '1 Squad (4 Bots)', 'price': 150, 'old': 180, 'save': 30},
        {'name': '2 Squads (8 Bots)', 'price': 280, 'old': 350, 'save': 70},
        {'name': '3 Squads (12 Bots)', 'price': 420, 'old': 520, 'save': 100},
        {'name': '4 Squads (16 Bots)', 'price': 550, 'old': 700, 'save': 150}
    ],
    'Guild Emote Bot': [
        {'name': 'Guild Glory Bot - 7 Days', 'price': 120, 'old': 150, 'save': 30},
        {'name': 'Guild Glory Bot - 30 Days', 'price': 350, 'old': 400, 'save': 50},
        {'name': 'Emote Bot - 7 Days', 'price': 80, 'old': 100, 'save': 20},
        {'name': 'Emote Bot - 30 Days', 'price': 250, 'old': 300, 'save': 50},
        {'name': 'Guild + Emote Combo (30D)', 'price': 550, 'old': 650, 'save': 100}
    ],
    'FF Like Sell': [
        {'name': '100 Likes (Instant)', 'price': 5, 'old': 10, 'save': 5},
        {'name': '220 Likes (Instant)', 'price': 10, 'old': 15, 'save': 5},
        {'name': 'Daily Like Bot - 30 Days', 'price': 100, 'old': 120, 'save': 20},
        {'name': 'Daily Like Bot - 90 Days', 'price': 300, 'old': 350, 'save': 50},
        {'name': 'Daily Like Bot - 365 Days', 'price': 1000, 'old': 1200, 'save': 200}
    ],
    'Memberships': [
        {'name': 'Weekly Lite', 'price': 35, 'old': 45, 'save': 10},
        {'name': 'Weekly Membership', 'price': 155, 'old': 170, 'save': 15},
        {'name': 'Monthly Membership', 'price': 760, 'old': 800, 'save': 40}
    ],
    'Level Up Pass': [
        {'name': 'Level Up Pass (Full)', 'price': 165, 'old': 180, 'save': 15}
    ],
    'Evo Access': [
        {'name': 'Evo Access - 3 Days', 'price': 65, 'old': 80, 'save': 15},
        {'name': 'Evo Access - 7 Days', 'price': 120, 'old': 140, 'save': 20},
        {'name': 'Evo Access - 30 Days', 'price': 360, 'old': 420, 'save': 60}
    ]
}

def load_file_settings():
    default_settings = {
        "shop_name": "RED TEAM SHOP",
        "ticker_text": "Topup in seconds - Available 24/7! Fast & Trusted",
        "whatsapp_number": "88017XXXXXXXX",
        "admin_password": "1234",
        "today_count_offset": 0,
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "smtp_email": "",
        "smtp_app_password": "",
        "google_client_id": "",
        "ff_api_url": "",
        "ff_api_key": "",
        "ff_api_host": "",
        "notice_enabled": True,
        "notice_title": "🔥 স্বাগতম RED TEAM SHOP-এ!",
        "notice_text": "২৪ ঘণ্টা দ্রুত ডেলিভারি। অর্ডার করার পর ১-৫ মিনিট অপেক্ষা করুন। যেকোনো সমস্যায় Support ট্যাব থেকে মেসেজ দিন।",
        "support_hours": "08:00 AM - 11:00 PM (7 Days)",
        "response_time": "< 5 minutes",
        "payment_methods": [
            {"name": "bKash (Send Money)", "number": "017XXXXXXXX"},
            {"name": "Nagad (Send Money)", "number": "018XXXXXXXX"}
        ]
    }
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                default_settings.update(loaded)
    except Exception:
        pass
    return default_settings

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
            email TEXT,
            password TEXT,
            balance INTEGER DEFAULT 0,
            created_at TEXT
        )''')

        if db_type == "postgres":
            c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT")
        else:
            try:
                c.execute("ALTER TABLE users ADD COLUMN email TEXT")
            except Exception:
                pass

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
            region TEXT DEFAULT 'BD',
            payment_method TEXT,
            trx_id TEXT,
            phone TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TEXT
        )''')

        if db_type == "postgres":
            c.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS region TEXT DEFAULT 'BD'")
        else:
            try:
                c.execute("ALTER TABLE orders ADD COLUMN region TEXT DEFAULT 'BD'")
            except Exception:
                pass

        c.execute('''CREATE TABLE IF NOT EXISTS site_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')

        c.execute(f'''CREATE TABLE IF NOT EXISTS support_reports (
            id {id_col},
            user_id INTEGER DEFAULT 0,
            phone TEXT,
            issue_type TEXT,
            order_id TEXT,
            details TEXT,
            status TEXT DEFAULT 'Open',
            admin_reply TEXT DEFAULT '',
            created_at TEXT
        )''')

        c.execute(f'''CREATE TABLE IF NOT EXISTS password_resets (
            id {id_col},
            email TEXT,
            otp_code TEXT,
            expires_ts BIGINT,
            attempts INTEGER DEFAULT 0,
            used INTEGER DEFAULT 0,
            created_at TEXT
        )''')

        conn.commit()
        _db_initialized = True
    finally:
        conn.close()

def get_db_setting(key, fallback):
    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT value FROM site_settings WHERE key = {p}", (key,))
        row = c.fetchone()
        if row and row['value']:
            return json.loads(row['value'])
    except Exception:
        pass
    finally:
        conn.close()
    return fallback

def save_db_setting(key, value_obj):
    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        val_str = json.dumps(value_obj, ensure_ascii=False)
        c.execute(f'''INSERT INTO site_settings (key, value) VALUES ({p}, {p})
                      ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value''', (key, val_str))
        conn.commit()
    finally:
        conn.close()

def get_config():
    base = load_file_settings()
    saved = get_db_setting('config', {})
    if isinstance(saved, dict):
        base.update(saved)
    return base

def get_catalog():
    cat = get_db_setting('catalog', DEFAULT_CATALOG)
    if 'GUILD GLORY BOT' not in cat:
        cat['GUILD GLORY BOT'] = DEFAULT_CATALOG['GUILD GLORY BOT']
    return cat

def get_public_config():
    cfg = get_config()
    return {
        "shop_name": cfg.get("shop_name", "RED TEAM SHOP"),
        "ticker_text": cfg.get("ticker_text", "Topup in seconds - Available 24/7!"),
        "whatsapp_number": cfg.get("whatsapp_number", ""),
        "google_client_id": (os.environ.get("GOOGLE_CLIENT_ID") or cfg.get("google_client_id") or "").strip(),
        "notice_enabled": bool(cfg.get("notice_enabled", True)),
        "notice_title": cfg.get("notice_title", "🔥 স্বাগতম RED TEAM SHOP-এ!"),
        "notice_text": cfg.get("notice_text", ""),
        "support_hours": cfg.get("support_hours", "08:00 AM - 11:00 PM"),
        "response_time": cfg.get("response_time", "< 5 minutes"),
        "payment_methods": cfg.get("payment_methods", [])
    }

def is_admin_authorized():
    cfg = get_config()
    expected = os.environ.get("ADMIN_PASSWORD") or cfg.get("admin_password", "1234")
    provided = request.headers.get("X-Admin-Password", "")
    return bool(provided) and provided == str(expected)

def get_telegram_creds():
    cfg = get_config()
    token = (os.environ.get("TELEGRAM_BOT_TOKEN") or cfg.get("telegram_bot_token") or "").strip()
    chat_id = (os.environ.get("TELEGRAM_CHAT_ID") or cfg.get("telegram_chat_id") or "").strip()
    return token, chat_id

def tg_api_call(method, payload_dict):
    token, _ = get_telegram_creds()
    if not token:
        return None
    try:
        url = f"https://api.telegram.org/bot{token}/{method}"
        data = json.dumps(payload_dict).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=4) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def send_telegram_alert(message_text, buttons=None):
    token, chat_id = get_telegram_creds()
    if not token or not chat_id:
        return
    payload = {"chat_id": chat_id, "text": message_text}
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    tg_api_call("sendMessage", payload)

def send_otp_email(to_email, otp_code):
    cfg = get_config()
    smtp_email = (os.environ.get("SMTP_EMAIL") or cfg.get("smtp_email") or "").strip()
    smtp_pass = (os.environ.get("SMTP_APP_PASSWORD") or cfg.get("smtp_app_password") or "").replace(" ", "").strip()
    shop_name = str(cfg.get("shop_name", "IMPERIO TOPUP")).strip()
    safe_shop = shop_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    if not smtp_email or not smtp_pass:
        return False, "Admin Settings-এ Gmail SMTP Email ও App Password সেট করা নেই!"

    msg = EmailMessage()
    msg["Subject"] = f"{shop_name} Verification Code"
    msg["From"] = smtp_email
    msg["Reply-To"] = smtp_email
    msg["To"] = to_email
    msg.set_content(
        f"Hello,\n\n"
        f"We received a request to reset your {shop_name} account password.\n"
        f"Your 6-digit verification code is: {otp_code}\n\n"
        f"This code will expire in 10 minutes.\n"
        f"If you did not request this, you can safely ignore this email.\n"
    )
    msg.add_alternative(f"""<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#f4f6f5;padding:20px;color:#111827;">
  <div style="max-width:420px;margin:0 auto;background:#ffffff;border-radius:12px;padding:24px;border:1px solid #e5e7eb;">
    <h2 style="margin:0 0 12px;color:#0d7a4f;">{safe_shop}</h2>
    <p style="font-size:14px;line-height:1.6;">Hello,<br>Use the verification code below to reset your account password:</p>
    <div style="margin:18px 0;padding:14px;background:#ecfdf5;border:1px dashed #0d7a4f;border-radius:10px;text-align:center;font-size:26px;font-weight:bold;letter-spacing:6px;color:#0d7a4f;">
      {otp_code}
    </div>
    <p style="font-size:12px;color:#6b7280;">This code is valid for 10 minutes. If you didn't request this, please ignore this email.</p>
  </div>
</body>
</html>""", subtype="html")

    last_err = ""
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(smtp_email, smtp_pass)
            server.send_message(msg)
        return True, "OK"
    except Exception as e:
        last_err = str(e)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_email, smtp_pass)
            server.send_message(msg)
        return True, "OK"
    except Exception as e2:
        return False, f"Email Error: {e2 or last_err}"

def extract_ff_name(obj, depth=0):
    if depth > 4 or obj is None:
        return ""
    if isinstance(obj, dict):
        priority_keys = ("nickname", "AccountName", "accountName", "player_name", "playerName", "ign", "username", "name")
        lower_map = {str(k).lower(): v for k, v in obj.items()}
        for pk in priority_keys:
            val = lower_map.get(pk.lower())
            if isinstance(val, str):
                clean = val.strip()
                if clean and clean.lower() not in ("true", "false", "ok", "success", "error", "not found", "null", "none"):
                    return clean
        for nested_key in ("basicinfo", "accountinfo", "player", "data", "result", "info"):
            if nested_key in lower_map and isinstance(lower_map[nested_key], (dict, list)):
                found = extract_ff_name(lower_map[nested_key], depth + 1)
                if found:
                    return found
        for v in obj.values():
            if isinstance(v, (dict, list)):
                found = extract_ff_name(v, depth + 1)
                if found:
                    return found
    elif isinstance(obj, list):
        for item in obj[:5]:
            found = extract_ff_name(item, depth + 1)
            if found:
                return found
    return ""

def compute_period_totals(rows, amount_key):
    today = bd_now().date()
    week_start = today - timedelta(days=6)
    month_prefix = today.strftime("%Y-%m")
    year_prefix = today.strftime("%Y")
    week_tot = month_tot = year_tot = all_tot = 0
    for r in rows:
        amt = int(r[amount_key] or 0)
        all_tot += amt
        d_str = str(r['created_at'] or '')[:10]
        if d_str.startswith(year_prefix):
            year_tot += amt
        if d_str.startswith(month_prefix):
            month_tot += amt
        try:
            od = datetime.strptime(d_str, "%Y-%m-%d").date()
            if od >= week_start:
                week_tot += amt
        except Exception:
            pass
    return {"week": week_tot, "month": month_tot, "year": year_tot, "all": all_tot}

def get_account_stats(conn, db_type, user_id=None):
    c = conn.cursor()
    p = "%s" if db_type == "postgres" else "?"
    if user_id is not None:
        c.execute(f"SELECT price, created_at FROM orders WHERE user_id = {p} AND status != 'Cancelled'", (int(user_id),))
        order_rows = c.fetchall()
        c.execute(f"SELECT amount, created_at FROM wallet_requests WHERE user_id = {p} AND status = 'Approved'", (int(user_id),))
        wallet_rows = c.fetchall()
    else:
        c.execute("SELECT price, created_at FROM orders WHERE status != 'Cancelled'")
        order_rows = c.fetchall()
        c.execute("SELECT amount, created_at FROM wallet_requests WHERE status = 'Approved'")
        wallet_rows = c.fetchall()
    return {
        "purchase": compute_period_totals(order_rows, "price"),
        "add_money": compute_period_totals(wallet_rows, "amount")
    }

def mask_uid(uid):
    s = str(uid or '').strip()
    if len(s) <= 4:
        return s[:1] + '**' + s[-1:] if len(s) > 2 else '****'
    return s[:2] + '****' + s[-2:]

def get_live_stats_data():
    cfg = get_config()
    offset = int(cfg.get("today_count_offset", 0) or 0)
    today_prefix = bd_now().strftime("%Y-%m-%d")
    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT COUNT(*) AS cnt FROM orders WHERE created_at LIKE {p}", (today_prefix + '%',))
        actual_today = int(c.fetchone()['cnt'])
        c.execute("SELECT category, package_name, uid, status, created_at FROM orders ORDER BY id DESC LIMIT 12")
        recent = []
        for r in c.fetchall():
            recent.append({
                "category": r['category'],
                "package_name": r['package_name'],
                "masked_uid": mask_uid(r['uid']),
                "status": r['status'],
                "created_at": r['created_at']
            })
        return {
            "today_count": max(0, actual_today + offset),
            "actual_today": actual_today,
            "recent": recent
        }
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
    return render_template(
        'index.html',
        shop_config=get_public_config(),
        catalog=get_catalog(),
        live_stats=get_live_stats_data(),
        auto_admin=False
    )

@app.route('/admin')
def secret_admin():
    init_db()
    return render_template(
        'index.html',
        shop_config=get_public_config(),
        catalog=get_catalog(),
        live_stats=get_live_stats_data(),
        auto_admin=True
    )

@app.route('/api/live-stats', methods=['GET'])
def api_live_stats():
    init_db()
    return jsonify(get_live_stats_data())

@app.route('/api/ff/check-uid', methods=['POST'])
def check_ff_uid():
    init_db()
    data = request.json or {}
    uid = str(data.get('uid', '')).strip()
    region = str(data.get('region', 'BD')).strip() or 'BD'
    if not uid.isdigit() or len(uid) < 6 or len(uid) > 14:
        return jsonify({"success": False, "message": "সঠিক Free Fire UID লিখুন (৬–১৪ ডিজিট)!"}), 400

    cfg = get_config()
    api_url = (os.environ.get("FF_API_URL") or cfg.get("ff_api_url") or "").strip()
    api_key = (os.environ.get("FF_API_KEY") or cfg.get("ff_api_key") or "").strip()
    api_host = (os.environ.get("FF_API_HOST") or cfg.get("ff_api_host") or "").strip()

    if api_url:
        try:
            if "{uid}" in api_url:
                target_url = api_url.replace("{uid}", urllib.parse.quote(uid)).replace("{region}", urllib.parse.quote(region.lower()))
            else:
                sep = "&" if "?" in api_url else "?"
                target_url = f"{api_url}{sep}uid={urllib.parse.quote(uid)}"
            headers = {"User-Agent": "Mozilla/5.0"}
            if api_key and api_host:
                headers["x-rapidapi-key"] = api_key
                headers["x-rapidapi-host"] = api_host
            elif api_key:
                headers["x-api-key"] = api_key
                headers["Authorization"] = f"Bearer {api_key}"
            req = urllib.request.Request(target_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=7) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            found = extract_ff_name(body)
            if found:
                return jsonify({"success": True, "name": found, "source": "api"})
        except Exception:
            pass

    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT ign FROM orders WHERE TRIM(uid) = {p} AND TRIM(COALESCE(ign, '')) != '' ORDER BY id DESC LIMIT 1", (uid,))
        row = c.fetchone()
        if row and row['ign']:
            return jsonify({"success": True, "name": str(row['ign']).strip(), "source": "history"})
    finally:
        conn.close()

    if not api_url:
        return jsonify({"success": False, "not_configured": True, "message": "API যুক্ত নেই — চাইলে নিচে নিজেই নাম লিখতে পারেন।"})
    return jsonify({"success": False, "message": "এই UID-এর গেমের নাম পাওয়া যায়নি!"})

@app.route('/api/register', methods=['POST'])
def register():
    init_db()
    data = request.json or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    if not name or not email or not password:
        return jsonify({"success": False, "message": "নাম, Gmail এবং পাসওয়ার্ড দিন!"}), 400
    if '@' not in email or '.' not in email.split('@')[-1]:
        return jsonify({"success": False, "message": "সঠিক Gmail / Email লিখুন!"}), 400
    if len(password) < 4:
        return jsonify({"success": False, "message": "পাসওয়ার্ড কমপক্ষে ৪ অক্ষরের হতে হবে!"}), 400

    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT id FROM users WHERE LOWER(email) = {p}", (email,))
        if c.fetchone():
            return jsonify({"success": False, "message": "এই Gmail দিয়ে আগেই অ্যাকাউন্ট খোলা আছে!"}), 400

        hashed_pw = generate_password_hash(password)
        now = bd_now().strftime("%Y-%m-%d %I:%M %p")
        c.execute(f"INSERT INTO users (name, phone, email, password, balance, created_at) VALUES ({p}, NULL, {p}, {p}, 0, {p})",
                  (name, email, hashed_pw, now))
        conn.commit()
        c.execute(f"SELECT id, name, phone, email, balance, created_at FROM users WHERE LOWER(email) = {p}", (email,))
        user = dict(c.fetchone())
        return jsonify({"success": True, "user": user})
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    init_db()
    data = request.json or {}
    identifier = (data.get('email') or data.get('phone') or '').strip()
    password = data.get('password', '').strip()
    if not identifier or not password:
        return jsonify({"success": False, "message": "Gmail এবং পাসওয়ার্ড দিন!"}), 400

    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT id, name, phone, email, password, balance, created_at FROM users WHERE LOWER(email) = {p} OR phone = {p}",
                  (identifier.lower(), identifier))
        row = c.fetchone()
        if not row:
            return jsonify({"success": False, "message": "Gmail বা পাসওয়ার্ড ভুল!"}), 401

        stored_pw = row['password'] or ''
        valid = False
        try:
            valid = check_password_hash(stored_pw, password)
        except Exception:
            valid = False

        if not valid and stored_pw == password:
            valid = True
            c.execute(f"UPDATE users SET password = {p} WHERE id = {p}", (generate_password_hash(password), row['id']))
            conn.commit()

        if not valid:
            return jsonify({"success": False, "message": "Gmail বা পাসওয়ার্ড ভুল!"}), 401

        user = {
            "id": row['id'],
            "name": row['name'],
            "phone": row['phone'],
            "email": row['email'],
            "balance": row['balance'],
            "created_at": row['created_at']
        }
        return jsonify({"success": True, "user": user})
    finally:
        conn.close()

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    init_db()
    data = request.json or {}
    credential = str(data.get('credential', '')).strip()
    if not credential:
        return jsonify({"success": False, "message": "Google token পাওয়া যায়নি!"}), 400

    cfg = get_config()
    expected_client_id = (os.environ.get("GOOGLE_CLIENT_ID") or cfg.get("google_client_id") or "").strip()
    if not expected_client_id:
        return jsonify({"success": False, "message": "Admin Settings-এ Google Client ID সেট করা নেই!"}), 400

    try:
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(credential)}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            info = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return jsonify({"success": False, "message": "Google অ্যাকাউন্ট যাচাই করা যায়নি!"}), 401

    if info.get("aud") != expected_client_id:
        return jsonify({"success": False, "message": "Google Client ID মিলছে না!"}), 401
    if str(info.get("email_verified", "")).lower() != "true":
        return jsonify({"success": False, "message": "এই Gmail-টি ভেরিফাইড নয়!"}), 401

    email = str(info.get("email", "")).strip().lower()
    g_name = str(info.get("name", "")).strip() or email.split("@")[0]
    if not email:
        return jsonify({"success": False, "message": "Gmail পাওয়া যায়নি!"}), 400

    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT id, name, phone, email, balance, created_at FROM users WHERE LOWER(email) = {p}", (email,))
        row = c.fetchone()
        if row:
            return jsonify({"success": True, "user": dict(row), "is_new": False})

        random_pw = generate_password_hash(secrets.token_urlsafe(24))
        now = bd_now().strftime("%Y-%m-%d %I:%M %p")
        c.execute(
            f"INSERT INTO users (name, phone, email, password, balance, created_at) VALUES ({p}, NULL, {p}, {p}, 0, {p})",
            (g_name, email, random_pw, now)
        )
        conn.commit()
        c.execute(f"SELECT id, name, phone, email, balance, created_at FROM users WHERE LOWER(email) = {p}", (email,))
        user = dict(c.fetchone())
        return jsonify({"success": True, "user": user, "is_new": True})
    finally:
        conn.close()

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    init_db()
    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT id, name, phone, email, balance, created_at FROM users WHERE id = {p}", (user_id,))
        row = c.fetchone()
        if not row:
            return jsonify({"success": False}), 404
        return jsonify({
            "success": True,
            "user": dict(row),
            "account_stats": get_account_stats(conn, db_type, user_id)
        })
    finally:
        conn.close()

@app.route('/api/user/update-profile', methods=['POST'])
def update_user_profile():
    init_db()
    data = request.json or {}
    user_id = int(data.get('user_id') or 0)
    new_name = str(data.get('name', '')).strip()
    old_pw = str(data.get('old_password', '')).strip()
    new_pw = str(data.get('new_password', '')).strip()

    if user_id <= 0 or not old_pw:
        return jsonify({"success": False, "message": "বর্তমান পাসওয়ার্ড দিন!"}), 400
    if new_pw and len(new_pw) < 4:
        return jsonify({"success": False, "message": "নতুন পাসওয়ার্ড কমপক্ষে ৪ অক্ষরের হতে হবে!"}), 400

    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT id, name, phone, email, password, balance, created_at FROM users WHERE id = {p}", (user_id,))
        row = c.fetchone()
        if not row:
            return jsonify({"success": False, "message": "ইউজার পাওয়া যায়নি!"}), 404

        stored_pw = row['password'] or ''
        valid = False
        try:
            valid = check_password_hash(stored_pw, old_pw)
        except Exception:
            valid = False
        if not valid and stored_pw == old_pw:
            valid = True

        if not valid:
            return jsonify({"success": False, "message": "বর্তমান পাসওয়ার্ড ভুল!"}), 401

        final_name = new_name if new_name else row['name']
        final_pw = generate_password_hash(new_pw) if new_pw else stored_pw
        c.execute(f"UPDATE users SET name = {p}, password = {p} WHERE id = {p}", (final_name, final_pw, user_id))
        conn.commit()
        return jsonify({
            "success": True,
            "message": "প্রোফাইল সফলভাবে আপডেট হয়েছে!",
            "user": {
                "id": row['id'],
                "name": final_name,
                "phone": row['phone'],
                "email": row['email'],
                "balance": row['balance'],
                "created_at": row['created_at']
            }
        })
    finally:
        conn.close()

@app.route('/api/auth/forgot-password/send-otp', methods=['POST'])
def forgot_password_send_otp():
    init_db()
    data = request.json or {}
    email = str(data.get('email', '')).strip().lower()
    if not email or '@' not in email:
        return jsonify({"success": False, "message": "সঠিক Gmail লিখুন!"}), 400

    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT id, name, email FROM users WHERE LOWER(email) = {p}", (email,))
        user = c.fetchone()
        if not user:
            return jsonify({"success": False, "message": "এই Gmail দিয়ে কোনো অ্যাকাউন্ট পাওয়া যায়নি!"}), 404

        now_ts = int(time.time())
        c.execute(f"SELECT expires_ts FROM password_resets WHERE LOWER(email) = {p} AND used = 0 ORDER BY id DESC LIMIT 1", (email,))
        last_otp = c.fetchone()
        if last_otp and (int(last_otp['expires_ts']) - 600) > (now_ts - 60):
            return jsonify({"success": False, "message": "অনুগ্রহ করে ১ মিনিট পর আবার কোড পাঠান!"}), 429

        otp_code = str(secrets.randbelow(900000) + 100000)
        ok, err_msg = send_otp_email(user['email'], otp_code)
        if not ok:
            return jsonify({"success": False, "message": err_msg}), 500

        c.execute(f"UPDATE password_resets SET used = 1 WHERE LOWER(email) = {p} AND used = 0", (email,))
        now_str = bd_now().strftime("%Y-%m-%d %I:%M %p")
        c.execute(
            f"INSERT INTO password_resets (email, otp_code, expires_ts, attempts, used, created_at) VALUES ({p}, {p}, {p}, 0, 0, {p})",
            (email, otp_code, now_ts + 600, now_str)
        )
        conn.commit()
        return jsonify({"success": True, "message": f"{user['email']}-এ ৬ ডিজিটের কোড পাঠানো হয়েছে! (Inbox-এ না পেলে Spam ফোল্ডার চেক করুন)"})
    finally:
        conn.close()

@app.route('/api/auth/forgot-password/reset', methods=['POST'])
def forgot_password_reset():
    init_db()
    data = request.json or {}
    email = str(data.get('email', '')).strip().lower()
    otp = str(data.get('otp', '')).strip()
    new_pw = str(data.get('new_password', '')).strip()

    if not email or not otp or not new_pw:
        return jsonify({"success": False, "message": "Gmail, কোড এবং নতুন পাসওয়ার্ড দিন!"}), 400
    if len(new_pw) < 4:
        return jsonify({"success": False, "message": "নতুন পাসওয়ার্ড কমপক্ষে ৪ অক্ষরের হতে হবে!"}), 400

    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"SELECT * FROM password_resets WHERE LOWER(email) = {p} AND used = 0 ORDER BY id DESC LIMIT 1", (email,))
        row = c.fetchone()
        if not row:
            return jsonify({"success": False, "message": "কোনো সক্রিয় কোড পাওয়া যায়নি! আবার কোড পাঠান।"}), 400

        now_ts = int(time.time())
        if now_ts > int(row['expires_ts']):
            c.execute(f"UPDATE password_resets SET used = 1 WHERE id = {p}", (row['id'],))
            conn.commit()
            return jsonify({"success": False, "message": "কোডটির মেয়াদ শেষ হয়ে গেছে! আবার নতুন কোড নিন।"}), 400

        if int(row['attempts'] or 0) >= 5:
            c.execute(f"UPDATE password_resets SET used = 1 WHERE id = {p}", (row['id'],))
            conn.commit()
            return jsonify({"success": False, "message": "অনেকবার ভুল কোড দিয়েছেন! আবার নতুন কোড নিন।"}), 400

        if otp != str(row['otp_code']):
            c.execute(f"UPDATE password_resets SET attempts = attempts + 1 WHERE id = {p}", (row['id'],))
            conn.commit()
            return jsonify({"success": False, "message": "ভুল কোড দিয়েছেন!"}), 400

        hashed_pw = generate_password_hash(new_pw)
        c.execute(f"UPDATE users SET password = {p} WHERE LOWER(email) = {p}", (hashed_pw, email))
        c.execute(f"UPDATE password_resets SET used = 1 WHERE id = {p}", (row['id'],))
        conn.commit()
        return jsonify({"success": True, "message": "পাসওয়ার্ড সফলভাবে পরিবর্তন হয়েছে!"})
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
        c.execute(f"SELECT id, name, phone, email FROM users WHERE id = {p}", (user_id,))
        user = c.fetchone()
        if not user:
            return jsonify({"success": False, "message": "ইউজার পাওয়া যায়নি!"}), 404

        if is_duplicate_trx(c, db_type, trx_id):
            return jsonify({"success": False, "message": "এই TrxID দিয়ে আগেই রিকোয়েস্ট করা হয়েছে!"}), 400

        contact = user['email'] or user['phone'] or ''
        now = bd_now().strftime("%Y-%m-%d %I:%M %p")
        if db_type == "postgres":
            c.execute(f'''INSERT INTO wallet_requests (user_id, user_name, phone, amount, method, trx_id, created_at)
                          VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}) RETURNING id''',
                      (user['id'], user['name'], contact, amount, method, trx_id, now))
            req_id = c.fetchone()['id']
        else:
            c.execute(f'''INSERT INTO wallet_requests (user_id, user_name, phone, amount, method, trx_id, created_at)
                          VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p})''',
                      (user['id'], user['name'], contact, amount, method, trx_id, now))
            req_id = c.lastrowid
        conn.commit()

        send_telegram_alert(
            f"💰 ADD MONEY REQUEST #{req_id}\n"
            f"User: {user['name']} ({contact})\n"
            f"Amount: ৳{amount}\n"
            f"Method: {method}\n"
            f"TrxID: {trx_id}\n"
            f"Time: {now}",
            buttons=[[
                {"text": "✅ Approve", "callback_data": f"wallet_Approved_{req_id}"},
                {"text": "❌ Reject", "callback_data": f"wallet_Rejected_{req_id}"}
            ]]
        )
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
    region = str(data.get('region', 'BD')).strip()[:10]
    pay_method = str(data.get('payment_method', '')).strip()
    trx_id = str(data.get('trx_id', '')).strip()
    contact_info = str(data.get('phone', '')).strip()

    if not uid:
        return jsonify({"success": False, "message": "দয়া করে Player UID / Guild ID দিন!"}), 400

    catalog = get_catalog()
    cat_items = catalog.get(category, [])
    cat_map = {pkg['name']: pkg for pkg in cat_items}

    raw_items = data.get('items')
    selected_lines = []
    total_price = 0

    if isinstance(raw_items, list) and len(raw_items) > 0:
        merged = {}
        for it in raw_items:
            if not isinstance(it, dict):
                continue
            pname = str(it.get('name', '')).strip()
            try:
                qty = int(it.get('qty', 0))
            except (ValueError, TypeError):
                qty = 0
            if pname not in cat_map or qty <= 0:
                continue
            merged[pname] = merged.get(pname, 0) + qty
            if merged[pname] > 100:
                return jsonify({"success": False, "message": "একবারে সর্বোচ্চ ১০০টি পর্যন্ত নেওয়া যাবে!"}), 400
        for pname, qty in merged.items():
            pkg = cat_map[pname]
            total_price += int(pkg['price']) * qty
            selected_lines.append(f"{pname} x{qty}" if qty > 1 or len(merged) > 1 else pname)
    else:
        matched_pkg = cat_map.get(package_name)
        if matched_pkg:
            total_price = int(matched_pkg['price'])
            selected_lines.append(package_name)

    if not selected_lines or total_price <= 0:
        return jsonify({"success": False, "message": "সঠিক প্যাকেজ ও পরিমাণ সিলেক্ট করুন!"}), 400

    package_name = ", ".join(selected_lines)
    price = total_price

    if pay_method != "Wallet Balance" and (len(trx_id) < 4 or trx_id.upper() == 'WALLET'):
        return jsonify({"success": False, "message": "সঠিক Transaction ID (TrxID) দিন!"}), 400

    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"

        if not contact_info and user_id > 0:
            c.execute(f"SELECT name, email, phone FROM users WHERE id = {p}", (user_id,))
            u_row = c.fetchone()
            if u_row:
                contact_info = u_row['email'] or u_row['phone'] or u_row['name'] or 'User'
        if not contact_info:
            contact_info = "Guest"

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

        now = bd_now().strftime("%Y-%m-%d %I:%M %p")
        if db_type == "postgres":
            query = f'''INSERT INTO orders
                (user_id, category, package_name, price, uid, ign, region, payment_method, trx_id, phone, created_at)
                VALUES ({', '.join([p]*11)}) RETURNING id'''
            c.execute(query, (user_id, category, package_name, price, uid, ign, region, pay_method, trx_id, contact_info, now))
            order_id = c.fetchone()['id']
        else:
            query = f'''INSERT INTO orders
                (user_id, category, package_name, price, uid, ign, region, payment_method, trx_id, phone, created_at)
                VALUES ({', '.join([p]*11)})'''
            c.execute(query, (user_id, category, package_name, price, uid, ign, region, pay_method, trx_id, contact_info, now))
            order_id = c.lastrowid

        conn.commit()

        send_telegram_alert(
            f"🛒 NEW ORDER #{order_id}\n"
            f"Category: {category}\n"
            f"Package: {package_name} (৳{price})\n"
            f"UID / Guild ID: {uid} ({region})\n"
            f"IGN: {ign or 'N/A'}\n"
            f"Payment: {pay_method} | Trx: {trx_id}\n"
            f"Customer: {contact_info}\n"
            f"Time: {now}",
            buttons=[[
                {"text": "✅ Complete", "callback_data": f"order_Completed_{order_id}"},
                {"text": "❌ Cancel", "callback_data": f"order_Cancelled_{order_id}"}
            ]]
        )
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
            id_list = [int(x.strip()) for x in ids_param.split(',')[:50] if x.strip().isdigit()]
            if not id_list:
                return jsonify([])
            placeholders = ', '.join([p] * len(id_list))
            c.execute(f"SELECT * FROM orders WHERE id IN ({placeholders}) ORDER BY id DESC", tuple(id_list))
            return jsonify([dict(row) for row in c.fetchall()])
        return jsonify([])
    finally:
        conn.close()

@app.route('/api/reports', methods=['GET', 'POST'])
def handle_reports():
    init_db()
    if request.method == 'POST':
        data = request.json or {}
        user_id = int(data.get('user_id') or 0)
        phone = str(data.get('phone', '')).strip()
        issue_type = str(data.get('issue_type', '')).strip()
        order_id = str(data.get('order_id', '')).strip()
        details = str(data.get('details', '')).strip()
        if not issue_type or not details:
            return jsonify({"success": False, "message": "সমস্যার ধরন এবং বিবরণ লিখুন!"}), 400

        conn, db_type = get_connection()
        try:
            c = conn.cursor()
            p = "%s" if db_type == "postgres" else "?"
            now = bd_now().strftime("%Y-%m-%d %I:%M %p")
            if db_type == "postgres":
                c.execute(f'''INSERT INTO support_reports (user_id, phone, issue_type, order_id, details, created_at)
                              VALUES ({p}, {p}, {p}, {p}, {p}, {p}) RETURNING id''',
                          (user_id, phone, issue_type, order_id, details, now))
                rep_id = c.fetchone()['id']
            else:
                c.execute(f'''INSERT INTO support_reports (user_id, phone, issue_type, order_id, details, created_at)
                              VALUES ({p}, {p}, {p}, {p}, {p}, {p})''',
                          (user_id, phone, issue_type, order_id, details, now))
                rep_id = c.lastrowid
            conn.commit()

            send_telegram_alert(
                f"📩 NEW SUPPORT REPORT #{rep_id}\n"
                f"Issue: {issue_type}\n"
                f"Order/Trx: {order_id or 'N/A'}\n"
                f"From: {phone}\n"
                f"Details: {details}"
            )
            return jsonify({"success": True, "report_id": rep_id, "message": "আপনার রিপোর্ট জমা দেওয়া হয়েছে!"})
        finally:
            conn.close()
    else:
        user_id = request.args.get('user_id')
        ids_param = request.args.get('ids', '').strip()
        conn, db_type = get_connection()
        try:
            c = conn.cursor()
            p = "%s" if db_type == "postgres" else "?"
            if user_id:
                c.execute(f"SELECT * FROM support_reports WHERE user_id = {p} ORDER BY id DESC", (int(user_id),))
                return jsonify([dict(r) for r in c.fetchall()])
            elif ids_param:
                id_list = [int(x.strip()) for x in ids_param.split(',')[:30] if x.strip().isdigit()]
                if not id_list:
                    return jsonify([])
                placeholders = ', '.join([p] * len(id_list))
                c.execute(f"SELECT * FROM support_reports WHERE id IN ({placeholders}) ORDER BY id DESC", tuple(id_list))
                return jsonify([dict(r) for r in c.fetchall()])
            return jsonify([])
        finally:
            conn.close()

@app.route('/api/telegram/webhook', methods=['POST'])
def telegram_webhook():
    init_db()
    update = request.json or {}
    cb = update.get("callback_query")
    if not cb:
        return jsonify({"ok": True})

    _, expected_chat_id = get_telegram_creds()
    msg = cb.get("message") or {}
    chat_id = str((msg.get("chat") or {}).get("id", ""))
    if not expected_chat_id or chat_id != str(expected_chat_id):
        return jsonify({"ok": True})

    data_str = cb.get("data", "")
    parts = data_str.split("_", 2)
    if len(parts) != 3:
        return jsonify({"ok": True})

    kind, new_status, item_id_str = parts
    if not item_id_str.isdigit():
        return jsonify({"ok": True})
    item_id = int(item_id_str)

    conn, db_type = get_connection()
    result_note = ""
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"

        if kind == "order" and new_status in ("Completed", "Cancelled"):
            c.execute(f"SELECT * FROM orders WHERE id = {p}", (item_id,))
            order_row = c.fetchone()
            if not order_row:
                result_note = "Order পাওয়া যায়নি"
            elif order_row['status'] != 'Pending':
                result_note = f"আগেই {order_row['status']} করা হয়েছে"
            else:
                c.execute(f"UPDATE orders SET status = {p} WHERE id = {p} AND status = 'Pending'", (new_status, item_id))
                if c.rowcount == 1 and new_status == 'Cancelled' and order_row['payment_method'] == 'Wallet Balance' and int(order_row['user_id'] or 0) > 0:
                    c.execute(f"UPDATE users SET balance = balance + {p} WHERE id = {p}",
                              (int(order_row['price']), int(order_row['user_id'])))
                conn.commit()
                result_note = f"Status: {new_status}"

        elif kind == "wallet" and new_status in ("Approved", "Rejected"):
            c.execute(f"SELECT * FROM wallet_requests WHERE id = {p}", (item_id,))
            req_row = c.fetchone()
            if not req_row:
                result_note = "Request পাওয়া যায়নি"
            elif req_row['status'] != 'Pending':
                result_note = f"আগেই {req_row['status']} করা হয়েছে"
            else:
                c.execute(f"UPDATE wallet_requests SET status = {p} WHERE id = {p} AND status = 'Pending'", (new_status, item_id))
                if c.rowcount == 1 and new_status == 'Approved':
                    c.execute(f"UPDATE users SET balance = balance + {p} WHERE id = {p}",
                              (int(req_row['amount']), int(req_row['user_id'])))
                conn.commit()
                result_note = f"Status: {new_status}"
    finally:
        conn.close()

    tg_api_call("answerCallbackQuery", {"callback_query_id": cb["id"], "text": result_note or "Done!"})
    orig_text = msg.get("text", "")
    icon = "✅" if new_status in ("Completed", "Approved") else "❌"
    tg_api_call("editMessageText", {
        "chat_id": chat_id,
        "message_id": msg.get("message_id"),
        "text": f"{orig_text}\n\n{icon} {result_note}",
        "reply_markup": {"inline_keyboard": []}
    })
    return jsonify({"ok": True})

@app.route('/api/admin/telegram/set-webhook', methods=['POST'])
def admin_set_tg_webhook():
    if not is_admin_authorized():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    token, _ = get_telegram_creds()
    if not token:
        return jsonify({"success": False, "message": "আগে Telegram Bot Token সেভ করুন!"}), 400
    base_url = request.url_root.replace("http://", "https://")
    webhook_url = base_url + "api/telegram/webhook"
    res = tg_api_call("setWebhook", {"url": webhook_url})
    if res and res.get("ok"):
        return jsonify({"success": True, "message": "Telegram বাটন সফলভাবে কানেক্ট হয়েছে!"})
    return jsonify({"success": False, "message": "Telegram Webhook সেট করা যায়নি, Token চেক করুন!"}), 400

@app.route('/api/admin/verify', methods=['POST'])
def admin_verify():
    init_db()
    data = request.json or {}
    cfg = get_config()
    expected = os.environ.get("ADMIN_PASSWORD") or cfg.get("admin_password", "1234")
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
        c.execute("SELECT id, name, phone, email, balance, created_at FROM users ORDER BY id DESC LIMIT 150")
        users = [dict(r) for r in c.fetchall()]
        stats = get_live_stats_data()
        shop_stats = get_account_stats(conn, db_type, None)
        return jsonify({
            "success": True,
            "db_type": db_type,
            "total_users": total_users,
            "pending_orders": pending_orders,
            "pending_wallet": pending_wallet,
            "actual_today_orders": stats['actual_today'],
            "displayed_today_orders": stats['today_count'],
            "shop_stats": shop_stats,
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

@app.route('/api/admin/user/balance', methods=['POST'])
def admin_adjust_balance():
    if not is_admin_authorized():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    init_db()
    data = request.json or {}
    user_id = int(data.get('user_id', 0))
    delta = int(data.get('delta', 0))
    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        c.execute(f"UPDATE users SET balance = GREATEST(0, balance + {p}) WHERE id = {p}" if db_type == "postgres"
                  else f"UPDATE users SET balance = MAX(0, balance + {p}) WHERE id = {p}", (delta, user_id))
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()

@app.route('/api/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if not is_admin_authorized():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    init_db()
    if request.method == 'GET':
        return jsonify({"success": True, "config": get_config(), "catalog": get_catalog()})
    else:
        data = request.json or {}
        if 'config' in data:
            current_cfg = get_config()
            new_cfg = data['config']
            if not new_cfg.get('admin_password'):
                new_cfg['admin_password'] = current_cfg.get('admin_password', '1234')
            save_db_setting('config', new_cfg)
        if 'catalog' in data:
            save_db_setting('catalog', data['catalog'])
        return jsonify({"success": True, "message": "সফলভাবে সেভ হয়েছে!"})

@app.route('/api/admin/reports', methods=['GET', 'PATCH'])
def admin_reports():
    if not is_admin_authorized():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    init_db()
    conn, db_type = get_connection()
    try:
        c = conn.cursor()
        p = "%s" if db_type == "postgres" else "?"
        if request.method == 'GET':
            c.execute("SELECT * FROM support_reports ORDER BY id DESC LIMIT 100")
            return jsonify([dict(r) for r in c.fetchall()])
        else:
            data = request.json or {}
            rep_id = int(data.get('id', 0))
            status = data.get('status', 'Resolved')
            reply = str(data.get('admin_reply', '')).strip()
            c.execute(f"UPDATE support_reports SET status = {p}, admin_reply = {p} WHERE id = {p}", (status, reply, rep_id))
            conn.commit()
            return jsonify({"success": True})
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
