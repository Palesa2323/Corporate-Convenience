"""AI activity audit logging for Corporate Convenience.

This module owns the audit-log table and records the output of the AI
classification / response workflow. It does not perform bias detection.
"""

import json
from datetime import datetime, timezone

from backend.database import get_connection


REVIEW_STATUSES = ("Pending", "Reviewed", "Flagged")


def _now():
    return datetime.now(timezone.utc).isoformat()


def init_audit_table():
    """Create the audit table without changing the existing database module."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS ai_audit_logs (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL REFERENCES tickets(ticket_id),
                response_id INTEGER REFERENCES responses(response_id),
                employee_id TEXT REFERENCES employees(employee_id),
                department TEXT,
                ai_classification TEXT,
                ai_response TEXT NOT NULL,
                risk_findings TEXT NOT NULL DEFAULT '[]',
                review_status TEXT NOT NULL DEFAULT 'Pending',
                transparency_note TEXT,
                created_at TEXT NOT NULL,
                reviewed_by TEXT REFERENCES employees(employee_id),
                reviewed_at TEXT
            )
        """)
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_ai_audit_ticket "
            "ON ai_audit_logs(ticket_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_ai_audit_created "
            "ON ai_audit_logs(created_at)"
        )


def log_ai_activity(ticket_id, ai_response, department=None,
                    ai_classification=None, risk_findings=None,
                    response_id=None, employee_id=None,
                    transparency_note=None):
    """Save one AI event and return its new audit ID.

    risk_findings may be a list of strings/dictionaries or a dictionary
    returned by the project's separate bias/risk detector.
    """
    if not ticket_id:
        raise ValueError("ticket_id is required")
    if not isinstance(ai_response, str) or not ai_response.strip():
        raise ValueError("ai_response must be a non-empty string")

    init_audit_table()
    findings_json = json.dumps(risk_findings or [], ensure_ascii=False,
                               default=str)

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO ai_audit_logs (
                ticket_id, response_id, employee_id, department,
                ai_classification, ai_response, risk_findings,
                review_status, transparency_note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
        """, (
            int(ticket_id), response_id, employee_id, department,
            ai_classification, ai_response.strip(), findings_json,
            transparency_note or "AI-generated content. Human review is required.",
            _now()
        ))
        return cursor.lastrowid


def get_audit_logs(ticket_id=None, department=None, limit=100):
    """Return audit records, optionally filtered by ticket or department."""
    init_audit_table()
    try:
        limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        limit = 100

    conditions = []
    values = []
    if ticket_id is not None:
        conditions.append("a.ticket_id = ?")
        values.append(int(ticket_id))
    if department:
        conditions.append("a.department = ?")
        values.append(department)

    where_sql = " WHERE " + " AND ".join(conditions) if conditions else ""
    with get_connection() as connection:
        rows = connection.execute(f"""
            SELECT a.*, t.ticket_number, t.subject
            FROM ai_audit_logs AS a
            JOIN tickets AS t ON t.ticket_id = a.ticket_id
            {where_sql}
            ORDER BY a.created_at DESC
            LIMIT ?
        """, (*values, limit)).fetchall()

    results = []
    for row in rows:
        item = dict(row)
        try:
            item["risk_findings"] = json.loads(item.get("risk_findings") or "[]")
        except (TypeError, json.JSONDecodeError):
            item["risk_findings"] = []
        results.append(item)
    return results


def update_review_status(audit_id, review_status, reviewed_by):
    """Mark an audit entry Reviewed or Flagged and record who reviewed it."""
    if review_status not in REVIEW_STATUSES:
        raise ValueError("Review status must be Pending, Reviewed or Flagged.")
    if review_status == "Pending":
        raise ValueError("A review action must be Reviewed or Flagged.")

    init_audit_table()
    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE ai_audit_logs
            SET review_status = ?, reviewed_by = ?, reviewed_at = ?
            WHERE audit_id = ?
        """, (review_status, reviewed_by, _now(), int(audit_id)))
        return cursor.rowcount > 0


# Ensure the table exists when this module is first imported.
init_audit_table()
