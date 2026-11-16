"""SMTP email delivery and logging for Corporate Convenience.

Configure SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD and
EMAIL_FROM in the application's environment. Use a test mailbox/provider
while developing; never commit real credentials to GitHub.
"""

import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone

from backend.database import get_connection


def _now():
    return datetime.now(timezone.utc).isoformat()


def _record_email(ticket_id, response_id, email_type, recipient,
                  success, error=None):
    """Write delivery outcome to the existing email_log table."""
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO email_log (
                ticket_id, response_id, email_type, recipient,
                success, error, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ticket_id, response_id, email_type, recipient,
              1 if success else 0, error, _now()))


def send_email(recipient, subject, text_body, html_body=None,
               ticket_id=None, response_id=None, email_type="General"):
    """Send an email and record success/failure in email_log.

    ticket_id is required because the existing email_log schema links every
    notification to a ticket.
    """
    if not ticket_id:
        raise ValueError("ticket_id is required for email audit logging")
    if not recipient:
        _record_email(ticket_id, response_id, email_type, recipient,
                      False, "Recipient email address is missing.")
        return False

    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("EMAIL_FROM") or username
    port = int(os.getenv("SMTP_PORT", "587"))

    if not host or not sender:
        error = "SMTP_HOST and EMAIL_FROM (or SMTP_USERNAME) must be configured."
        _record_email(ticket_id, response_id, email_type, recipient, False, error)
        return False

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text_body or "")
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.ehlo()
            if os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}:
                smtp.starttls()
                smtp.ehlo()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
        _record_email(ticket_id, response_id, email_type, recipient, True)
        return True
    except Exception as error:
        _record_email(ticket_id, response_id, email_type, recipient,
                      False, str(error)[:1000])
        return False


def send_template_email(recipient, template, ticket_id, email_type,
                        response_id=None):
    """Send a template dictionary returned by email_templates.py."""
    return send_email(
        recipient=recipient,
        subject=template["subject"],
        text_body=template.get("text", ""),
        html_body=template.get("html"),
        ticket_id=ticket_id,
        response_id=response_id,
        email_type=email_type
    )
