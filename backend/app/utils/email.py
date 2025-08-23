# backend/app/utils/email.py
import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
project_root = Path(__file__).resolve().parents[3]
load_dotenv(dotenv_path=project_root / ".env")

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM = os.getenv("SENDGRID_FROM")  # verified sender email

def send_alert_email(to_email: str, subject: str, content: str) -> bool:
    if not SENDGRID_API_KEY or not SENDGRID_FROM:
        logger.warning("SendGrid not configured; cannot send email.")
        return False

    url = "https://api.sendgrid.com/v3/mail/send"
    body = {
        "personalizations": [{"to": [{"email": to_email}], "subject": subject}],
        "from": {"email": SENDGRID_FROM},
        "content": [{"type": "text/plain", "value": content}],
    }
    headers = {"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"}
    try:
        r = requests.post(url, json=body, headers=headers, timeout=10)
        if r.status_code in (200, 202):
            return True
        logger.warning("SendGrid returned %s: %s", r.status_code, r.text)
        return False
    except Exception as e:
        logger.exception("SendGrid request failed: %s", e)
        return False
