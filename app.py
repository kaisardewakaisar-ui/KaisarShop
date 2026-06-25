import sqlite3
import os
import re
import random
import string
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import config
from mailer import kirim_email_otp

DB_PATH = os.path.join(config.BASE_DIR, 'kaisarshop.db')
UPLOAD_DIR = os.path.join(config.BASE_DIR, 'static', 'uploads')
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'webp'}
MAX_IMAGE_SIZE = 4 * 1024 * 1024

if config.SUPABASE_URL and config.SUPABASE_KEY:
    from supabase import create_client, Client
    supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
else:
    supabase = None

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = MAX_IMAGE_SIZE
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

TRANSLATIONS = {
    'id': {
        'nav_catalog': 'Katalog Tools', 'nav_my_orders': 'Pesanan Saya', 'nav_login': 'Masuk',
        'nav_register': 'Daftar', 'nav_logout': 'Keluar', 'nav_admin_dashboard': 'Dasbor Admin',
        'nav_admin_products': 'Kelola Tools', 'nav_admin_orders': 'Pesanan Masuk', 'nav_admin_buyers': 'Daftar Pembeli',
        'footer_text': 'KaisarShop — Platform Perdagangan Tools Hacking',
        'home_eyebrow': 'Katalog Tools Hacking', 'home_title': 'Tools Hacking Siap Pakai',
        'home_desc': 'Jelajahi koleksi tools hacking premium',
        'search_placeholder': 'Cari tools...', 'all_categories': 'Semua Kategori', 'btn_search': 'Cari',
        'no_products': 'Tidak ada tools yang cocok dengan pencarian Anda.',
        'no_image': 'Tidak ada gambar', 'price_label': 'Harga Tools',
        'btn_buy': 'Beli Tools', 'login_to_buy': 'untuk membeli tools ini.',
        'login_link': 'Masuk',
    },
    'en': {
        'nav_catalog': 'Tools Catalog', 'nav_my_orders': 'My Orders', 'nav_login': 'Sign In',
        'nav_register': 'Register', 'nav_logout': 'Logout', 'nav_admin_dashboard': 'Admin Dashboard',
        'nav_admin_products': 'Manage Tools', 'nav_admin_orders': 'Incoming Orders', 'nav_admin_buyers': 'Buyers List',
        'footer_text': 'KaisarShop@Hacking Tools Marketplace',
        'home_eyebrow': 'Hacking Tools Catalog', 'home_title': 'Ready to Use Hacking Tools',
        'home_desc': 'Browse our premium hacking tools collection.',
        'search_placeholder': 'Search tools...', 'all_categories': 'All Categories', 'btn_search': 'Search',
        'no_products': 'No tools match your search.',
        'no_image': 'No image', 'price_label': 'Tools Price',
        'btn_buy': 'Buy Tools', 'login_to_buy': 'to purchase this tool.',
        'login_link': 'Sign in',
    }
}

CATEGORY_LABELS = {
    'id': {
        'Ransomware': 'Ransomware',
        'crypter': 'Crypter',
        'malware': 'Malware',
        'exploiter': 'Exploiter',
        'crackedsoftware': 'Cracked Software',
        'osint': 'OSINT',
        'other': 'Lainnya'
    },
    'en': {
        'Ransomware': 'Ransomware',
        'crypter': 'Crypter',
        'malware': 'Malware',
        'exploiter': 'Exploiter',
        'crackedsoftware': 'Cracked Software',
        'osint': 'OSINT',
        'other': 'Other'
    }
}

ORDER_STATUS_LABELS = {
    'id': {'menunggu_pembayaran': 'Menunggu Pembayaran', 'menunggu_konfirmasi': 'Menunggu Konfirmasi Admin (≤24 jam)',
           'disetujui': 'Disetujui', 'ditolak': 'Ditolak'},
    'en': {'menunggu_pembayaran': 'Awaiting Payment', 'menunggu_konfirmasi': 'Awaiting Admin Confirmation (≤24h)',
           'disetujui': 'Approved', 'ditolak': 'Rejected'}
}

def get_db():
    if 'db' not in g:
        if config.DATABASE_URL and config.DATABASE_URL.startswith('postgres'):
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(config.DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
            conn.autocommit = False
            g.db = conn
            g.db_type = 'postgres'
        else:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys = ON')
            g.db = conn
            g.db_type = 'sqlite'
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        if exception and g.get('db_type') == 'postgres':
            db.rollback()
        db.close()

def init_db():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Cek jika menggunakan PostgreSQL (Supabase)
    if config.DATABASE_URL and config.DATABASE_URL.startswith('postgres'):
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                full_name TEXT NOT NULL,
                company TEXT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'pembeli',
                email_verified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_otp (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                pending_user_data TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                short_desc TEXT NOT NULL,
                full_desc TEXT NOT NULL,
                price_usd REAL NOT NULL,
                image_filename TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                product_id INTEGER NOT NULL REFERENCES products(id),
                price_usd REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'menunggu_pembayaran',
                paid_marked_at TEXT,
                review_deadline TEXT,
                decided_at TEXT,
                admin_note TEXT,
                created_at TEXT NOT NULL
            );
        """)
        db.commit()
    else:
        # Jika menggunakan SQLite lokal
        db = sqlite3.connect(DB_PATH)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                company TEXT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'pembeli',
                email_verified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS email_otp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                pending_user_data TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                short_desc TEXT NOT NULL,
                full_desc TEXT NOT NULL,
                price_usd REAL NOT NULL,
                image_filename TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                price_usd REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'menunggu_pembayaran',
                paid_marked_at TEXT,
                review_deadline TEXT,
                decided_at TEXT,
                admin_note TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            );
        ''')
        db.commit()
        db.close()

    # Buat akun admin jika belum ada
    if config.ADMIN_USERNAME and config.ADMIN_PASSWORD:
        db = get_db()
        existing_admin = db.execute('SELECT id FROM users WHERE role = "admin"').fetchone()
        if existing_admin is None:
            db.execute(
                'INSERT INTO users (full_name, company, username, email, password_hash, role, email_verified, created_at) VALUES (?,?,?,?,?,?,?,?)',
                ('Administrator', 'KaisarShop', config.ADMIN_USERNAME, f'{config.ADMIN_USERNAME}@kaisarshop.local',
                 generate_password_hash(config.ADMIN_PASSWORD), 'admin', 1, datetime.now().isoformat())
            )
            db.commit()

    # Seed produk awal (jika kosong)
    db = get_db()
    cur = db.execute('SELECT COUNT(*) FROM products')
    if cur.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        products = [
            ('Venom Crypter FUD', 'crypter', 'Fully Undetectable crypter with advanced obfuscation and persistence.', 'A premium crypter designed to bypass all major antivirus detection including Windows Defender, Kaspersky, and Bitdefender. Features polymorphic code engine, process injection, startup persistence, and encrypted payload delivery. Supports .exe, .dll, .bat output formats. Silent execution with anti-sandbox and anti-VM detection built-in.', 499.0, None, 1, now),
            ('DarkStealer RAT v3', 'malware', 'Remote Access Trojan with keylogger, screen capture, and reverse proxy.', 'Advanced RAT with full remote control capabilities. Features include live keylogging, screen monitoring, webcam access, file browser, password harvesting from browsers and crypto wallets, reverse SOCKS5 proxy, and encrypted C2 communication. Lightweight client with only 50KB payload size.', 299.0, None, 1, now)
        ]
        for p in products:
            db.execute('INSERT INTO products (name, category, short_desc, full_desc, price_usd, image_filename, is_active, created_at) VALUES (?,?,?,?,?,?,?,?)', p)
        db.commit()

def get_lang():
    lang = session.get('lang', 'id')
    return lang if lang in ('id', 'en') else 'id'

def t(key):
    return TRANSLATIONS[get_lang()].get(key, key)

def category_label(cat_key):
    return CATEGORY_LABELS[get_lang()].get(cat_key, cat_key)

def status_label(status_key):
    return ORDER_STATUS_LABELS[get_lang()].get(status_key, status_key)

@app.context_processor
def inject_globals():
    return {
        'current_user': {
            'id': session.get('user_id'),
            'full_name': session.get('full_name'),
            'role': session.get('role'),
        },
        'lang': get_lang(),
        't': t,
        'category_label': category_label,
        'status_label': status_label,
        'admin_login_path': config.ADMIN_LOGIN_PATH,
    }

@app.route('/set-lang/<lang_code>')
def set_lang(lang_code):
    if lang_code in ('id', 'en'):
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('index'))

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan masuk untuk mengakses halaman ini. / Please sign in to continue.', 'error')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped

def buyer_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get('role') != 'pembeli':
            abort(403)
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get('role') != 'admin':
            abort(404)
        return view(*args, **kwargs)
    return wrapped

def validasi_username(username):
    return bool(re.fullmatch(r'[a-zA-Z0-9_]{3,32}', username or ''))

def validasi_email(email):
    return bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email or ''))

def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXT

def simpan_gambar_produk(file_storage):
    if not file_storage or file_storage.filename == '':
        return None
    if not allowed_image(file_storage.filename):
        flash('Format gambar tidak didukung. / Unsupported image format.', 'error')
        return None
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    safe_name = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}.{ext}"
    
    if supabase:
        file_content = file_storage.read()
        try:
            res = supabase.storage.from_(config.SUPABASE_BUCKET).upload(
                path=safe_name,
                file=file_content,
                file_options={"content-type": file_storage.mimetype}
            )
            if hasattr(res, 'error') and res.error:
                flash(f'Gagal upload ke Supabase: {res.error}', 'error')
                return None
            public_url = supabase.storage.from_(config.SUPABASE_BUCKET).get_public_url(safe_name)
            return public_url
        except Exception as e:
            flash(f'Exception saat upload ke Supabase: {str(e)}', 'error')
            return None
    else:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_storage.seek(0)
        file_storage.save(os.path.join(UPLOAD_DIR, safe_name))
        return safe_name

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "script-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    return response

@app.route('/')
def index():
    db = get_db()
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    query = 'SELECT * FROM products WHERE is_active = 1'
    params = []
    if q:
        query += ' AND (name LIKE ? OR short_desc LIKE ?)'
        params.extend([f'%{q}%', f'%{q}%'])
    if category:
        query += ' AND category = ?'
        params.append(category)
    query += ' ORDER BY created_at DESC'
    products = db.execute(query, params).fetchall()
    return render_template('index.html', products=products, categories=config.CATEGORY_KEYS, q=q, selected_category=category)

@app.route('/produk/<int:product_id>')
def product_detail(product_id):
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ? AND is_active = 1', (product_id,)).fetchone()
    if product is None:
        flash('Produk tidak ditemukan. / Product not found.', 'error')
        return redirect(url_for('index'))
    active_order = None
    if session.get('role') == 'pembeli':
        active_order = db.execute('SELECT * FROM orders WHERE user_id = ? AND product_id = ? AND status != "ditolak" ORDER BY created_at DESC LIMIT 1', (session['user_id'], product_id)).fetchone()
    return render_template('product_detail.html', product=product, active_order=active_order, wallet_sol=config.WALLET_SOL, wallet_eth=config.WALLET_ETH)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        company = request.form.get('company', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        if not full_name or not username or not password or not email:
            flash('Semua kolom wajib diisi. / All fields are required.', 'error')
            return redirect(url_for('register'))
        if not validasi_username(username):
            flash('Username tidak valid (huruf/angka/underscore, 3-32 karakter). / Invalid username.', 'error')
            return redirect(url_for('register'))
        if not validasi_email(email):
            flash('Format email tidak valid. / Invalid email format.', 'error')
            return redirect(url_for('register'))
        if len(password) < 8:
            flash('Kata sandi minimal 8 karakter. / Password must be at least 8 characters.', 'error')
            return redirect(url_for('register'))
        if password != confirm:
            flash('Konfirmasi kata sandi tidak cocok. / Password confirmation does not match.', 'error')
            return redirect(url_for('register'))
        db = get_db()
        if db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone():
            flash('Username sudah digunakan. / Username already taken.', 'error')
            return redirect(url_for('register'))
        if db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone():
            flash('Email sudah terdaftar. / Email already registered.', 'error')
            return redirect(url_for('register'))
        import json
        pending_data = json.dumps({'full_name': full_name, 'company': company, 'username': username, 'email': email, 'password_hash': generate_password_hash(password)})
        otp_code = generate_otp()
        now = datetime.now()
        expires = now + timedelta(minutes=config.OTP_EXPIRE_MINUTES)
        db.execute('DELETE FROM email_otp WHERE email = ?', (email,))
        db.execute('INSERT INTO email_otp (email, otp_code, pending_user_data, attempts, expires_at, created_at) VALUES (?,?,?,0,?,?)', (email, otp_code, pending_data, expires.isoformat(), now.isoformat()))
        db.commit()
        success, error = kirim_email_otp(email, otp_code, get_lang())
        if not success:
            flash(f'Gagal mengirim email OTP: {error}', 'error')
            return redirect(url_for('register'))
        session['pending_otp_email'] = email
        flash('Kode verifikasi telah dikirim ke email Anda. / Verification code sent to your email.', 'success')
        return redirect(url_for('verify_otp'))
    return render_template('register.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = session.get('pending_otp_email')
    if not email:
        flash('Tidak ada proses verifikasi yang aktif. / No active verification process.', 'error')
        return redirect(url_for('register'))
    if request.method == 'POST':
        entered_code = request.form.get('otp_code', '').strip()
        db = get_db()
        otp_row = db.execute('SELECT * FROM email_otp WHERE email = ?', (email,)).fetchone()
        if otp_row is None:
            flash('Sesi verifikasi tidak ditemukan, silakan daftar ulang. / Verification session not found.', 'error')
            return redirect(url_for('register'))
        if datetime.now() > datetime.fromisoformat(otp_row['expires_at']):
            db.execute('DELETE FROM email_otp WHERE email = ?', (email,))
            db.commit()
            flash('Kode OTP sudah kedaluwarsa. / OTP code expired.', 'error')
            return redirect(url_for('register'))
        if otp_row['attempts'] >= config.OTP_MAX_ATTEMPTS:
            db.execute('DELETE FROM email_otp WHERE email = ?', (email,))
            db.commit()
            flash('Terlalu banyak percobaan gagal. Silakan daftar ulang. / Too many failed attempts.', 'error')
            return redirect(url_for('register'))
        if entered_code != otp_row['otp_code']:
            db.execute('UPDATE email_otp SET attempts = attempts + 1 WHERE email = ?', (email,))
            db.commit()
            sisa = config.OTP_MAX_ATTEMPTS - (otp_row['attempts'] + 1)
            flash(f'Kode OTP salah. Sisa percobaan: {sisa}. / Incorrect code. Attempts left: {sisa}.', 'error')
            return redirect(url_for('verify_otp'))
        import json
        data = json.loads(otp_row['pending_user_data'])
        db.execute('INSERT INTO users (full_name, company, username, email, password_hash, role, email_verified, created_at) VALUES (?,?,?,?,?,?,1,?)', (data['full_name'], data['company'], data['username'], data['email'], data['password_hash'], 'pembeli', datetime.now().isoformat()))
        db.execute('DELETE FROM email_otp WHERE email = ?', (email,))
        db.commit()
        session.pop('pending_otp_email', None)
        flash('Email berhasil diverifikasi. Silakan masuk. / Email verified successfully. Please sign in.', 'success')
        return redirect(url_for('login'))
    return render_template('verify_otp.html', email=email)

@app.route('/resend-otp')
def resend_otp():
    email = session.get('pending_otp_email')
    if not email:
        return redirect(url_for('register'))
    db = get_db()
    otp_row = db.execute('SELECT pending_user_data FROM email_otp WHERE email = ?', (email,)).fetchone()
    if otp_row is None:
        flash('Sesi verifikasi tidak ditemukan. / Verification session not found.', 'error')
        return redirect(url_for('register'))
    otp_code = generate_otp()
    now = datetime.now()
    expires = now + timedelta(minutes=config.OTP_EXPIRE_MINUTES)
    db.execute('UPDATE email_otp SET otp_code = ?, attempts = 0, expires_at = ? WHERE email = ?', (otp_code, expires.isoformat(), email))
    db.commit()
    success, error = kirim_email_otp(email, otp_code, get_lang())
    if success:
        flash('Kode baru telah dikirim. / New code sent.', 'success')
    else:
        flash(f'Gagal mengirim ulang: {error}', 'error')
    return redirect(url_for('verify_otp'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND role = "pembeli"', (username,)).fetchone()
        if user is None or not check_password_hash(user['password_hash'], password):
            flash('Username atau kata sandi salah. / Incorrect username or password.', 'error')
            return redirect(url_for('login'))
        if not user['email_verified']:
            flash('Email belum diverifikasi. / Email not verified yet.', 'error')
            return redirect(url_for('login'))
        session.clear()
        session['user_id'] = user['id']
        session['full_name'] = user['full_name']
        session['role'] = user['role']
        flash(f'Selamat datang, {user["full_name"]}. / Welcome, {user["full_name"]}.', 'success')
        return redirect(url_for('my_orders'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah keluar. / You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route(f'/{config.ADMIN_LOGIN_PATH}', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND role = "admin"', (username,)).fetchone()
        if user is None or not check_password_hash(user['password_hash'], password):
            flash('Kredensial tidak valid.', 'error')
            return redirect(url_for('admin_login'))
        session.clear()
        session['user_id'] = user['id']
        session['full_name'] = user['full_name']
        session['role'] = user['role']
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route('/produk/<int:product_id>/beli', methods=['POST'])
@login_required
@buyer_required
def buy_product(product_id):
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ? AND is_active = 1', (product_id,)).fetchone()
    if product is None:
        flash('Produk tidak ditemukan. / Product not found.', 'error')
        return redirect(url_for('index'))
    existing = db.execute('SELECT id FROM orders WHERE user_id = ? AND product_id = ? AND status != "ditolak"', (session['user_id'], product_id)).fetchone()
    if existing:
        flash('Anda sudah memiliki pesanan aktif untuk produk ini. / You already have an active order for this product.', 'error')
        return redirect(url_for('order_detail', order_id=existing['id']))
    db.execute('INSERT INTO orders (user_id, product_id, price_usd, status, created_at) VALUES (?,?,?,?,?)', (session['user_id'], product_id, product['price_usd'], 'menunggu_pembayaran', datetime.now().isoformat()))
    db.commit()
    order_id = db.execute('SELECT last_insert_rowid() AS id').fetchone()['id']
    return redirect(url_for('order_detail', order_id=order_id))

@app.route('/pesanan/<int:order_id>')
@login_required
@buyer_required
def order_detail(order_id):
    db = get_db()
    order = db.execute('SELECT orders.*, products.name AS product_name, products.image_filename FROM orders JOIN products ON orders.product_id = products.id WHERE orders.id = ? AND orders.user_id = ?', (order_id, session['user_id'])).fetchone()
    if order is None:
        flash('Pesanan tidak ditemukan. / Order not found.', 'error')
        return redirect(url_for('my_orders'))
    sisa_jam = None
    if order['status'] == 'menunggu_konfirmasi' and order['review_deadline']:
        deadline = datetime.fromisoformat(order['review_deadline'])
        delta = deadline - datetime.now()
        sisa_jam = max(delta.total_seconds() / 3600, 0)
    return render_template('order_detail.html', order=order, wallet_sol=config.WALLET_SOL, wallet_eth=config.WALLET_ETH, sisa_jam=sisa_jam, telegram_url=config.TELEGRAM_VERIFY_URL)

@app.route('/pesanan/<int:order_id>/sudah-bayar', methods=['POST'])
@login_required
@buyer_required
def mark_paid(order_id):
    db = get_db()
    order = db.execute('SELECT * FROM orders WHERE id = ? AND user_id = ?', (order_id, session['user_id'])).fetchone()
    if order is None:
        flash('Pesanan tidak ditemukan. / Order not found.', 'error')
        return redirect(url_for('my_orders'))
    if order['status'] != 'menunggu_pembayaran':
        flash('Pesanan ini sudah diproses sebelumnya. / This order has already been processed.', 'error')
        return redirect(url_for('order_detail', order_id=order_id))
    now = datetime.now()
    deadline = now + timedelta(hours=config.PAYMENT_REVIEW_HOURS)
    db.execute('UPDATE orders SET status = "menunggu_konfirmasi", paid_marked_at = ?, review_deadline = ? WHERE id = ?', (now.isoformat(), deadline.isoformat(), order_id))
    db.commit()
    flash('Konfirmasi pembayaran diterima. Admin akan meninjau dalam 24 jam. / Payment confirmation received. Admin will review within 24 hours.', 'success')
    return redirect(url_for('order_detail', order_id=order_id))

@app.route('/pesanan-saya')
@login_required
@buyer_required
def my_orders():
    db = get_db()
    orders = db.execute('SELECT orders.*, products.name AS product_name, products.image_filename FROM orders JOIN products ON orders.product_id = products.id WHERE orders.user_id = ? ORDER BY orders.created_at DESC', (session['user_id'],)).fetchall()
    return render_template('my_orders.html', orders=orders)

@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    total_produk = db.execute('SELECT COUNT(*) FROM products WHERE is_active = 1').fetchone()[0]
    total_pesanan = db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    menunggu = db.execute('SELECT COUNT(*) FROM orders WHERE status = "menunggu_konfirmasi"').fetchone()[0]
    disetujui = db.execute('SELECT COUNT(*) FROM orders WHERE status = "disetujui"').fetchone()[0]
    total_pembeli = db.execute('SELECT COUNT(*) FROM users WHERE role = "pembeli"').fetchone()[0]
    pesanan_terbaru = db.execute('SELECT orders.*, products.name AS product_name, users.full_name, users.email FROM orders JOIN products ON orders.product_id = products.id JOIN users ON orders.user_id = users.id ORDER BY orders.created_at DESC LIMIT 10').fetchall()
    return render_template('admin_dashboard.html', total_produk=total_produk, total_pesanan=total_pesanan, menunggu=menunggu, disetujui=disetujui, total_pembeli=total_pembeli, pesanan_terbaru=pesanan_terbaru)

@app.route('/admin/produk')
@admin_required
def admin_products():
    db = get_db()
    products = db.execute('SELECT * FROM products ORDER BY created_at DESC').fetchall()
    return render_template('admin_products.html', products=products)

def ambil_data_produk():
    nama = request.form.get('name', '').strip()
    kategori = request.form.get('category', '').strip()
    short_desc = request.form.get('short_desc', '').strip()
    full_desc = request.form.get('full_desc', '').strip()
    try:
        harga = float(request.form.get('price_usd') or 0)
    except ValueError:
        harga = 0.0
    errors = []
    if not nama or len(nama) > 150:
        errors.append('Nama produk wajib diisi (maks 150 karakter). / Product name required (max 150 chars).')
    if kategori not in config.CATEGORY_KEYS:
        errors.append('Kategori tidak valid. / Invalid category.')
    if not short_desc or len(short_desc) > 200:
        errors.append('Deskripsi singkat wajib diisi (maks 200 karakter). / Short description required.')
    if not full_desc:
        errors.append('Deskripsi lengkap wajib diisi. / Full description required.')
    if harga <= 0:
        errors.append('Harga harus lebih dari 0. / Price must be greater than 0.')
    return {'name': nama, 'category': kategori, 'short_desc': short_desc, 'full_desc': full_desc, 'price_usd': harga}, errors

@app.route('/admin/produk/tambah', methods=['GET', 'POST'])
@admin_required
def admin_product_add():
    if request.method == 'POST':
        data, errors = ambil_data_produk()
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('admin_product_form.html', product=None, categories=config.CATEGORY_KEYS)
        image_filename = simpan_gambar_produk(request.files.get('image'))
        db = get_db()
        db.execute('INSERT INTO products (name, category, short_desc, full_desc, price_usd, image_filename, is_active, created_at) VALUES (?,?,?,?,?,?,1,?)', (data['name'], data['category'], data['short_desc'], data['full_desc'], data['price_usd'], image_filename, datetime.now().isoformat()))
        db.commit()
        flash('Produk berhasil ditambahkan. / Product added successfully.', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', product=None, categories=config.CATEGORY_KEYS)

@app.route('/admin/produk/<int:product_id>/ubah', methods=['GET', 'POST'])
@admin_required
def admin_product_edit(product_id):
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if product is None:
        flash('Produk tidak ditemukan. / Product not found.', 'error')
        return redirect(url_for('admin_products'))
    if request.method == 'POST':
        data, errors = ambil_data_produk()
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('admin_product_form.html', product=product, categories=config.CATEGORY_KEYS)
        image_filename = product['image_filename']
        new_image = simpan_gambar_produk(request.files.get('image'))
        if new_image:
            image_filename = new_image
        db.execute('UPDATE products SET name=?, category=?, short_desc=?, full_desc=?, price_usd=?, image_filename=? WHERE id=?', (data['name'], data['category'], data['short_desc'], data['full_desc'], data['price_usd'], image_filename, product_id))
        db.commit()
        flash('Produk berhasil diperbarui. / Product updated successfully.', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', product=product, categories=config.CATEGORY_KEYS)

@app.route('/admin/produk/<int:product_id>/hapus', methods=['POST'])
@admin_required
def admin_product_delete(product_id):
    db = get_db()
    db.execute('UPDATE products SET is_active = 0 WHERE id = ?', (product_id,))
    db.commit()
    flash('Produk berhasil dinonaktifkan. / Product deactivated.', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/pesanan')
@admin_required
def admin_orders():
    db = get_db()
    status_filter = request.args.get('status', '')
    query = 'SELECT orders.*, products.name AS product_name, users.full_name, users.email, users.company FROM orders JOIN products ON orders.product_id = products.id JOIN users ON orders.user_id = users.id'
    params = []
    if status_filter:
        query += ' WHERE orders.status = ?'
        params.append(status_filter)
    query += ' ORDER BY orders.created_at DESC'
    orders = db.execute(query, params).fetchall()
    return render_template('admin_orders.html', orders=orders, status_filter=status_filter)

@app.route('/admin/pesanan/<int:order_id>/putuskan', methods=['POST'])
@admin_required
def admin_decide_order(order_id):
    db = get_db()
    order = db.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if order is None:
        flash('Pesanan tidak ditemukan. / Order not found.', 'error')
        return redirect(url_for('admin_orders'))
    decision = request.form.get('decision', '')
    admin_note = request.form.get('admin_note', '').strip()
    if decision not in ('disetujui', 'ditolak'):
        flash('Keputusan tidak valid. / Invalid decision.', 'error')
        return redirect(url_for('admin_orders'))
    db.execute('UPDATE orders SET status = ?, admin_note = ?, decided_at = ? WHERE id = ?', (decision, admin_note, datetime.now().isoformat(), order_id))
    db.commit()
    flash(f'Pesanan telah ditandai sebagai "{decision}". / Order marked as "{decision}".', 'success')
    return redirect(url_for('admin_orders'))

@app.route('/admin/pembeli')
@admin_required
def admin_buyers():
    db = get_db()
    buyers = db.execute('SELECT users.*, (SELECT COUNT(*) FROM orders WHERE orders.user_id = users.id) AS total_pesanan, (SELECT COUNT(*) FROM orders WHERE orders.user_id = users.id AND status = "disetujui") AS total_disetujui FROM users WHERE role = "pembeli" ORDER BY full_name ASC').fetchall()
    return render_template('admin_buyers.html', buyers=buyers)

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, message='Akses ditolak. / Access denied.'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message='Halaman tidak ditemukan. / Page not found.'), 404

@app.errorhandler(413)
def too_large(e):
    return render_template('error.html', code=413, message='Ukuran file terlalu besar (maks 4MB). / File too large (max 4MB).'), 413

if __name__ == '__main__':
    app.run(debug=False, port=5000)
