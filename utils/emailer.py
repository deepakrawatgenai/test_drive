import os
import threading
import smtplib
from email.mime.text import MIMEText

def send_email(to_email: str, content: str):
    host = os.getenv('SMTP_HOST')
    port = int(os.getenv('SMTP_PORT','587'))
    user = os.getenv('SMTP_USER')
    password = os.getenv('SMTP_PASSWORD')
    if not (host and user and password):
        print('SMTP not configured. Email content:\n', content)
        return False

    msg = MIMEText(content)
    msg['Subject'] = content.splitlines()[0].replace('Subject:','').strip()
    msg['From'] = user
    msg['To'] = to_email

    try:
        s = smtplib.SMTP(host, port)
        s.starttls()
        s.login(user, password)
        s.sendmail(user, [to_email], msg.as_string())
        s.quit()
        return True
    except Exception as e:
        print("Email send error:", e)
        return False

def send_email_bg(to_email: str, content: str):
    t = threading.Thread(target=send_email, args=(to_email,content), daemon=True)
    t.start()
