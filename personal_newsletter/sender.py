"""Deliver newsletters over SMTP (config via environment variables)."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from .models import Subscriber


class SenderConfigError(Exception):
    pass


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SenderConfigError(
            f"Missing {name}. Sending requires SMTP_HOST, SMTP_PORT, SMTP_USER, "
            "SMTP_PASSWORD, and FROM_EMAIL environment variables."
        )
    return value


def send_email(subscriber: Subscriber, subject: str, html_body: str, text_body: str) -> None:
    host = _require_env("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = _require_env("SMTP_USER")
    password = _require_env("SMTP_PASSWORD")
    from_email = _require_env("FROM_EMAIL")

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
