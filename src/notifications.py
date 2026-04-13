"""Notification dispatch — email and webhook channels for call summaries."""

import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

import httpx

logger = logging.getLogger(__name__)


def send_notification(
    summary: str,
    caller_name: str,
    action_required: bool,
) -> dict[str, bool]:
    """Send call summary via configured channels.

    Returns dict indicating which channels succeeded.
    Skips unconfigured channels without error.
    """
    results = {
        "email": _send_email(summary, caller_name, action_required),
        "webhook": _send_webhook(summary, caller_name, action_required),
    }
    return results


def _send_email(summary: str, caller_name: str, action_required: bool) -> bool:
    """Send summary via SMTP. Returns False if not configured or on failure."""
    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    to_addr = os.environ.get("NOTIFICATION_EMAIL_TO")
    from_addr = os.environ.get("NOTIFICATION_EMAIL_FROM", user or "")

    if not all([host, user, password, to_addr]):
        return False

    aktion = "Ja" if action_required else "Nein"
    body = (
        f"Anrufzusammenfassung\n"
        f"====================\n"
        f"Anrufer: {caller_name}\n"
        f"Aktion erforderlich: {aktion}\n\n"
        f"{summary}"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"Anruf von {caller_name}" + (" — Aktion erforderlich" if action_required else "")
    msg["From"] = from_addr
    msg["To"] = to_addr

    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send email notification")
        return False


def _send_webhook(summary: str, caller_name: str, action_required: bool) -> bool:
    """POST summary to webhook URL. Returns False if not configured or on failure."""
    url = os.environ.get("NOTIFICATION_WEBHOOK_URL")
    if not url:
        return False

    payload = {
        "caller_name": caller_name,
        "summary": summary,
        "action_required": action_required,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        response = httpx.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception:
        logger.exception("Failed to send webhook notification")
        return False
