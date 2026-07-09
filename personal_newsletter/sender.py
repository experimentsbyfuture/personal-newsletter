"""Deliver newsletters by email.

Two backends, picked automatically:
- Resend (https://resend.com) when RESEND_API_KEY is set — one HTTPS call,
  free tier, no SMTP setup. Recommended for the daily GitHub Actions job.
- Plain SMTP otherwise (SMTP_HOST/PORT/USER/PASSWORD).

Both require FROM_EMAIL.
"""

from __future__ import annotations

import json
import os
import smtplib
import urllib.request
from email.message import EmailMessage

from .models import Subscriber

RESEND_URL = "https://api.resend.com/emails"


class SenderConfigError(Exception):
    pass


def _require_env(name: str, hint: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SenderConfigError(f"Missing {name}. {hint}")
    return value


def send_email(subscriber: Subscriber, subject: str, html_body: str, text_body: str) -> None:
    if os.environ.get("RESEND_API_KEY"):
        send_via_resend(subscriber, subject, html_body, text_body)
    else:
        send_via_smtp(subscriber, subject, html_body, text_body)


def send_via_resend(subscriber: Subscriber, subject: str, html_body: str, text_body: str) -> None:
    api_key = os.environ["RESEND_API_KEY"]
    from_email = _require_env(
        "FROM_EMAIL",
        "Set it to a sender verified in your Resend account, "
        'e.g. "Your Newsletter <news@yourdomain.com>".',
    )
    payload = json.dumps(
        {
            "from": from_email,
            "to": [subscriber.email],
            "subject": subject,
            "html": html_body,
            "text": text_body,
        }
    ).encode()
    request = urllib.request.Request(
        RESEND_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status >= 300:
            raise RuntimeError(f"Resend returned {response.status}: {response.read()[:300]!r}")


def send_via_smtp(subscriber: Subscriber, subject: str, html_body: str, text_body: str) -> None:
    hint = (
        "Sending over SMTP requires SMTP_HOST, SMTP_USER, SMTP_PASSWORD, and "
        "FROM_EMAIL (SMTP_PORT defaults to 587). Or set RESEND_API_KEY to use "
        "Resend instead."
    )
    host = _require_env("SMTP_HOST", hint)
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = _require_env("SMTP_USER", hint)
    password = _require_env("SMTP_PASSWORD", hint)
    from_email = _require_env("FROM_EMAIL", hint)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = subscriber.email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
