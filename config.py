import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except ImportError:
    pass


def env(key, default=None):
    return os.environ.get(key, default)


SECRET_KEY = env('SECRET_KEY') or os.urandom(32).hex()

ADMIN_USERNAME = env('ADMIN_USERNAME', '').strip()
ADMIN_PASSWORD = env('ADMIN_PASSWORD', '').strip()
ADMIN_LOGIN_PATH = env('ADMIN_LOGIN_PATH', 'portal-x9k2m').strip().strip('/')

SMTP_HOST = env('SMTP_HOST', '')
SMTP_PORT = int(env('SMTP_PORT', '587') or 587)
SMTP_USERNAME = env('SMTP_USERNAME', '')
SMTP_PASSWORD = env('SMTP_PASSWORD', '')
SMTP_FROM_NAME = env('SMTP_FROM_NAME', 'KaisarShop')
SMTP_FROM_EMAIL = env('SMTP_FROM_EMAIL', '')

TELEGRAM_VERIFY_URL = env('TELEGRAM_VERIFY_URL', 'https://t.me/Darkness_Lock')

WALLET_SOL = '7FA2U8ibBDRJ8PBLDhtVkByc9b5arB4F5J9H6Sn18NtZ'
WALLET_ETH = '0x85EA9a1cAD3eb169BE581E9482fF864B53BDc734'

OTP_EXPIRE_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
PAYMENT_REVIEW_HOURS = 24

CATEGORY_KEYS = ['Ransomware','crypter', 'malware', 'exploiter', 'crackedsoftware', 'osint', 'other']

