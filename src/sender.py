# src/sender.py

import os
import smtplib
import socket
from email.message import EmailMessage
import mimetypes

try:
    import dns.resolver
    _HAS_DNSPY = True
except ImportError:
    _HAS_DNSPY = False

def _validate_recipient(to_address):
    domain = to_address.split('@')[-1]
    # MX lookup
    if _HAS_DNSPY:
        try:
            answers = dns.resolver.resolve(domain, 'MX')
            if not answers:
                raise ValueError(f"No MX records for domain '{domain}'")
            return
        except Exception as e:
            raise ValueError(f"MX lookup failed for '{domain}': {e}")
    # Fallback: A/AAAA lookup
    else:
        try:
            socket.getaddrinfo(domain, None)
        except Exception as e:
            raise ValueError(f"DNS lookup failed for '{domain}': {e}")

def send_email(to_address, subject, body, attachments=None):
    # 1) DNS‐based precheck
    _validate_recipient(to_address)

    # 2) Build the EmailMessage
    msg = EmailMessage()
    msg['From']    = os.getenv("SMTP_USERNAME")
    msg['To']      = to_address
    msg['Subject'] = subject
    msg.set_content(body)

    # 3) Attach files if any
    if attachments:
        for path in attachments:
            with open(path, 'rb') as f:
                data = f.read()
            ctype, encoding = mimetypes.guess_type(path)
            if ctype is None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            filename = os.path.basename(path)
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

    # 4) Send and detect immediate SMTP rejects
    with smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT"))) as smtp:
        smtp.starttls()
        smtp.login(os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD"))
        refused = smtp.sendmail(msg['From'], [to_address], msg.as_string())
        if refused:
            # e.g. { 'bad@address.com': (550, b'User unknown') }
            raise smtplib.SMTPRecipientsRefused(refused)
