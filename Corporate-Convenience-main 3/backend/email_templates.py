"""Reusable plain-text and HTML email templates for ticket notifications."""

from html import escape


def _layout(title, body):
    return f"""<!doctype html>
<html lang=\"en\">
<head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>{escape(title)}</title></head>
<body style=\"margin:0;padding:24px;background:#f4f6f8;font-family:Arial,sans-serif;color:#263238;\">
  <div style=\"max-width:600px;margin:0 auto;background:#ffffff;padding:28px;border-radius:8px;\">
    <h2 style=\"margin-top:0;color:#23415c;\">Corporate Convenience</h2>
    {body}
    <p style=\"font-size:12px;color:#687782;margin-top:28px;\">This is an automated notification. Please do not reply to this email.</p>
  </div>
</body></html>"""


def ticket_submitted(ticket_number, subject):
    subject_line = f"Ticket {ticket_number} received"
    text = (f"Your support ticket {ticket_number} has been submitted.\n"
            f"Subject: {subject}\n\nOur team will review it.")
    html = _layout(subject_line, f"<h3>{escape(subject_line)}</h3>"
                   f"<p>We've received your support request.</p>"
                   f"<p><strong>Subject:</strong> {escape(str(subject))}</p>"
                   f"<p>Our team will review it and provide an update.</p>")
    return {"subject": subject_line, "text": text, "html": html}


def ticket_assigned(ticket_number, subject, department):
    subject_line = f"Ticket {ticket_number} assigned"
    text = (f"Ticket {ticket_number} has been assigned to {department}.\n"
            f"Subject: {subject}")
    html = _layout(subject_line, f"<h3>{escape(subject_line)}</h3>"
                   f"<p>Your ticket has been assigned to <strong>{escape(str(department))}</strong>.</p>"
                   f"<p><strong>Subject:</strong> {escape(str(subject))}</p>")
    return {"subject": subject_line, "text": text, "html": html}


def ticket_status_updated(ticket_number, subject, status):
    subject_line = f"Ticket {ticket_number} status update"
    text = (f"Ticket {ticket_number} status: {status}.\n"
            f"Subject: {subject}")
    html = _layout(subject_line, f"<h3>{escape(subject_line)}</h3>"
                   f"<p>The status of your ticket is now <strong>{escape(str(status))}</strong>.</p>"
                   f"<p><strong>Subject:</strong> {escape(str(subject))}</p>")
    return {"subject": subject_line, "text": text, "html": html}


def ticket_reply(ticket_number, subject, reply_text):
    subject_line = f"A response has been added to ticket {ticket_number}"
    text = (f"A response has been added to your ticket.\n"
            f"Ticket: {ticket_number}\nSubject: {subject}\n\n{reply_text}")
    safe_reply = escape(str(reply_text)).replace("\n", "<br>")
    html = _layout(subject_line, f"<h3>{escape(subject_line)}</h3>"
                   f"<p><strong>Subject:</strong> {escape(str(subject))}</p>"
                   f"<div style=\"padding:16px;background:#f4f6f8;border-radius:6px;\">{safe_reply}</div>")
    return {"subject": subject_line, "text": text, "html": html}
