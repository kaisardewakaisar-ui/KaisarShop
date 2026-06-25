import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import config


def kirim_email_otp(to_email, otp_code, lang='id'):
    if not config.SMTP_HOST or not config.SMTP_USERNAME or not config.SMTP_PASSWORD:
        print(f"[DEV MODE] Kode OTP untuk {to_email}: {otp_code}")
        return True, None

    if lang == 'en':
        subject = f"Your KaisarShop verification code: {otp_code}"
        plain_body = (
            f"Hello,\n\n"
            f"Your verification code is: {otp_code}\n"
            f"This code expires in {config.OTP_EXPIRE_MINUTES} minutes.\n\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"— KaisarShop"
        )
        html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#050507;font-family:Inter,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#050507;padding:40px 20px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:#0f0f14;border:1px solid #28242f;border-radius:12px;padding:40px 36px;">
        <tr><td>
          <p style="margin:0 0 4px;font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#9b5cf6;font-weight:600;">// VERIFICATION</p>
          <h1 style="margin:0 0 24px;font-size:22px;color:#f5f3fa;">KaisarShop</h1>
          <p style="color:#8b8696;font-size:15px;margin:0 0 28px;line-height:1.6;">
            Your email verification code:
          </p>
          <div style="background:#16161d;border:1px solid #28242f;border-radius:10px;padding:24px;text-align:center;margin-bottom:28px;">
            <span style="font-size:36px;font-weight:800;letter-spacing:10px;color:#c9a8ff;">{otp_code}</span>
          </div>
          <p style="color:#8b8696;font-size:13px;margin:0 0 8px;">
            This code is valid for <strong style="color:#f5f3fa;">{config.OTP_EXPIRE_MINUTES} minutes</strong>.
            Do not share it with anyone.
          </p>
          <p style="color:#28242f;font-size:12px;margin:24px 0 0;border-top:1px solid #28242f;padding-top:18px;">
            KaisarShop — If you did not request this, ignore this email.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    else:
        subject = f"Kode verifikasi KaisarShop Anda: {otp_code}"
        plain_body = (
            f"Halo,\n\n"
            f"Kode verifikasi Anda adalah: {otp_code}\n"
            f"Kode ini berlaku selama {config.OTP_EXPIRE_MINUTES} menit.\n\n"
            f"Jika Anda tidak meminta ini, abaikan email ini.\n\n"
            f"— KaisarShop"
        )
        html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#050507;font-family:Inter,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#050507;padding:40px 20px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:#0f0f14;border:1px solid #28242f;border-radius:12px;padding:40px 36px;">
        <tr><td>
          <p style="margin:0 0 4px;font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#9b5cf6;font-weight:600;">// VERIFIKASI</p>
          <h1 style="margin:0 0 24px;font-size:22px;color:#f5f3fa;">KaisarShop</h1>
          <p style="color:#8b8696;font-size:15px;margin:0 0 28px;line-height:1.6;">
            Kode verifikasi email Anda:
          </p>
          <div style="background:#16161d;border:1px solid #28242f;border-radius:10px;padding:24px;text-align:center;margin-bottom:28px;">
            <span style="font-size:36px;font-weight:800;letter-spacing:10px;color:#c9a8ff;">{otp_code}</span>
          </div>
          <p style="color:#8b8696;font-size:13px;margin:0 0 8px;">
            Kode ini berlaku selama <strong style="color:#f5f3fa;">{config.OTP_EXPIRE_MINUTES} menit</strong>.
            Jangan bagikan kode ini kepada siapapun.
          </p>
          <p style="color:#28242f;font-size:12px;margin:24px 0 0;border-top:1px solid #28242f;padding-top:18px;">
            KaisarShop &mdash; Jika Anda tidak mendaftar, abaikan email ini.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    from_addr = config.SMTP_FROM_EMAIL or config.SMTP_USERNAME
    msg = MIMEMultipart('alternative')
    msg['From'] = f"{config.SMTP_FROM_NAME} <{from_addr}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg['X-Mailer'] = 'KaisarShop-Mailer/1.0'
    msg.attach(MIMEText(plain_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        context = ssl.create_default_context()
        if config.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, context=context) as server:
                server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                server.sendmail(from_addr, to_email, msg.as_string())
        else:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                server.sendmail(from_addr, to_email, msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)
