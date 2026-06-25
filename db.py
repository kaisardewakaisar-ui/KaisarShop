"""
Database abstraction layer.
- Lokal / Railway: pakai SQLite (default)
- Vercel + Supabase: set DATABASE_URL di environment variable
"""
import os
import sqlite3
from flask import g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_SQLITE_PATH = os.path.join(BASE_DIR, 'kaisarshop.db')
DATABASE_URL = os.environ.get('DATABASE_URL', '')

USE_POSTGRES = bool(DATABASE_URL and DATABASE_URL.startswith('postgres'))


def get_db():
    if 'db' not in g:
        if USE_POSTGRES:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
            conn.autocommit = False
            g.db = conn
            g.db_type = 'postgres'
        else:
            conn = sqlite3.connect(DB_SQLITE_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys = ON')
            g.db = conn
            g.db_type = 'sqlite'
    return g.db


def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        if exception and g.get('db_type') == 'postgres':
            db.rollback()
        db.close()


def ph(n=1):
    """
    Placeholder helper.
    SQLite pakai '?', PostgreSQL pakai '%s'.
    ph()   -> '?'  atau  '%s'
    ph(3)  -> '?,?,?'  atau  '%s,%s,%s'
    """
    mark = '%s' if USE_POSTGRES else '?'
    return ','.join([mark] * n)


def execute(db, sql, params=()):
    """Jalankan query dengan placeholder yang sesuai driver."""
    if USE_POSTGRES:
        sql = sql.replace('?', '%s')
        cur = db.cursor()
        cur.execute(sql, params)
        return cur
    else:
        return db.execute(sql, params)


def commit(db):
    if USE_POSTGRES:
        db.commit()
    else:
        db.commit()


def init_schema(db):
    """Buat tabel jika belum ada. Aman dipanggil berkali-kali."""
    if USE_POSTGRES:
        stmts = [
            """CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                full_name TEXT NOT NULL,
                company TEXT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'pembeli',
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS email_otp (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL,
                username TEXT NOT NULL,
                full_name TEXT NOT NULL,
                company TEXT,
                password_hash TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                short_desc TEXT NOT NULL,
                full_desc TEXT NOT NULL,
                price_usd REAL NOT NULL,
                image_filename TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                product_id INTEGER NOT NULL REFERENCES products(id),
                price_usd REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'menunggu_pembayaran',
                admin_note TEXT,
                review_deadline TEXT,
                created_at TEXT NOT NULL,
                decided_at TEXT
            )""",
        ]
        cur = db.cursor()
        for s in stmts:
            cur.execute(s)
        db.commit()
    else:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                company TEXT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'pembeli',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS email_otp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                username TEXT NOT NULL,
                full_name TEXT NOT NULL,
                company TEXT,
                password_hash TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
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
                admin_note TEXT,
                review_deadline TEXT,
                created_at TEXT NOT NULL,
                decided_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
        """)
        db.commit()
