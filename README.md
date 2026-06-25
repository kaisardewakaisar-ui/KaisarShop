# KaisarShop — Platform Lisensi Software

Tema hitam/ungu/putih. OTP via email. Admin URL tersembunyi. Bayar crypto. Redirect Telegram setelah disetujui.

---

## Cara Menjalankan Lokal

```bash
pip install -r requirements.txt
cp .env.example .env   # lalu isi nilai di .env
python app.py
```

Buka `http://127.0.0.1:5000`

---

## Cara Masuk sebagai Admin

Login admin **tidak ada di navigasi publik** dan tidak bisa ditebak dari URL biasa.

URL login admin ditentukan oleh variabel `ADMIN_LOGIN_PATH` di file `.env` Anda.

**Contoh:** jika di `.env` Anda mengisi:
```
ADMIN_LOGIN_PATH=rahasiasaya99
```
Maka URL login admin adalah:
```
http://127.0.0.1:5000/rahasiasaya99
```
Di Vercel/Railway, ganti `127.0.0.1:5000` dengan domain Anda.

Tidak ada link ke URL ini dari halaman manapun di situs publik. Simpan URL ini hanya untuk diri sendiri.

---

## Konfigurasi OTP Email (Gmail)

1. Buka `myaccount.google.com/apppasswords`
2. Buat App Password baru untuk "Mail"
3. Isi di `.env`:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=email-anda@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx   (16 digit App Password)
SMTP_FROM_NAME=KaisarShop
SMTP_FROM_EMAIL=email-anda@gmail.com
```

Tanpa konfigurasi SMTP, OTP otomatis tercetak di terminal (mode testing).

---

## Deploy ke GitHub

```bash
git init
git add .
git commit -m "initial"
git remote add origin https://github.com/USERNAME/kaisarshop.git
git push -u origin main
```

File `.env` dan `kaisarshop.db` tidak ter-commit karena ada di `.gitignore`.

---

## Deploy ke Vercel

Vercel tidak mendukung SQLite persisten. Gunakan **Supabase** (PostgreSQL gratis) sebagai database.

### Langkah-langkah:

**1. Buat database di Supabase**
- Buka `supabase.com` → New Project
- Setelah project dibuat, buka **Settings → Database → Connection String**
- Pilih mode "URI" dan salin connection string-nya (format: `postgresql://postgres:PASSWORD@HOST:5432/postgres`)

**2. Push ke GitHub** (ikuti langkah di atas)

**3. Deploy ke Vercel**
- Buka `vercel.com` → Add New Project → Import dari GitHub
- Pilih repo kaisarshop
- Di bagian **Environment Variables**, tambahkan semua variabel dari `.env` Anda:
  - `SECRET_KEY`
  - `ADMIN_USERNAME`
  - `ADMIN_PASSWORD`
  - `ADMIN_LOGIN_PATH`
  - `DATABASE_URL` (connection string Supabase)
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_NAME`
  - `TELEGRAM_VERIFY_URL`
- Klik Deploy

Vercel otomatis detect `vercel.json` dan build Flask app.

**Catatan upload foto produk di Vercel:**
Vercel filesystem bersifat read-only, jadi foto yang diupload admin tidak persisten antar deploy. Untuk solusi permanen, integrasikan dengan Cloudinary atau Supabase Storage (opsional, tidak termasuk dalam versi ini).

---

## Alternatif: Deploy ke Railway (paling mudah, SQLite tetap jalan)

- Buka `railway.app` → New Project → Deploy from GitHub Repo
- Pilih repo kaisarshop
- Tambahkan environment variables di Railway dashboard
- Railway otomatis jalankan Flask + SQLite tanpa konfigurasi tambahan
- SQLite persisten di Railway (berbeda dengan Vercel)

---

## Alur Transaksi

1. User daftar → kode OTP dikirim ke email → user masukkan kode → akun aktif
2. User login → lihat katalog → klik **Beli Sekarang**
3. Halaman pesanan tampil dengan alamat dompet Solana & Ethereum
4. User transfer → klik **Saya Sudah Bayar**
5. Halaman polling otomatis setiap 15 detik
6. Admin buka `URL_ADMIN_ANDA/admin/pesanan` → klik **Approve**
7. Halaman user **otomatis** berubah dan redirect ke `t.me/Darkness_Lock` dalam 2.5 detik
