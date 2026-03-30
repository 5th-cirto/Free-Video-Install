from __future__ import annotations

import smtplib
from email.message import EmailMessage

from api.config import settings


class EmailServiceError(RuntimeError):
    """Raised when email sending fails or SMTP config is invalid."""


def _require_smtp_config() -> None:
    required = {
        "SMTP_HOST": settings.smtp_host,
        "SMTP_PORT": str(settings.smtp_port),
        "SMTP_USER": settings.smtp_user,
        "SMTP_PASSWORD": settings.smtp_password,
        "SMTP_FROM_EMAIL": settings.smtp_from_email,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise EmailServiceError(f"Missing SMTP config: {', '.join(missing)}")


def send_email(*, to_email: str, subject: str, body: str) -> None:
    _require_smtp_config()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    except Exception as exc:  # noqa: BLE001
        raise EmailServiceError(f"SMTP send failed: {exc}") from exc

