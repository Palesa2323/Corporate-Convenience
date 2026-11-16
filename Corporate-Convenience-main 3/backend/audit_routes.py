"""Flask Blueprint for authorised AI audit-log access."""

from flask import Blueprint, jsonify, request, session

from backend.audit_logger import get_audit_logs, update_review_status
from backend.database import get_connection


audit_bp = Blueprint("audit", __name__)


def _current_user():
    employee_id = session.get("employee_id")
    if not employee_id:
        return None
    with get_connection() as connection:
        row = connection.execute("""
            SELECT employee_id, role, department, is_active
            FROM employees WHERE employee_id = ?
        """, (employee_id,)).fetchone()
    if row is None or not row["is_active"]:
        return None
    return dict(row)


def _can_access_department(user, department):
    if user["role"] == "Admin":
        return True
    if user["role"] == "Support Staff":
        return user.get("department") == department
    return False


@audit_bp.route("/api/audit-logs", methods=["GET"])
def list_ai_audit_logs():
    """Admins see all logs; Support Staff see their own department only."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Authentication required."}), 401
    if user["role"] not in {"Admin", "Support Staff"}:
        return jsonify({"error": "You are not authorised to view AI audit logs."}), 403

    ticket_id = request.args.get("ticket_id", type=int)
    requested_department = request.args.get("department")
    if user["role"] == "Support Staff":
        department = user.get("department")
        if requested_department and requested_department != department:
            return jsonify({"error": "You can only view your department's audit logs."}), 403
    else:
        department = requested_department

    logs = get_audit_logs(
        ticket_id=ticket_id,
        department=department,
        limit=request.args.get("limit", 100)
    )
    return jsonify({"audit_logs": logs, "count": len(logs)}), 200


@audit_bp.route("/api/audit-logs/<int:audit_id>/review", methods=["PATCH"])
def review_ai_audit_log(audit_id):
    """Allow authorised staff to mark a log Reviewed or Flagged."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Authentication required."}), 401
    if user["role"] not in {"Admin", "Support Staff"}:
        return jsonify({"error": "You are not authorised to review AI audit logs."}), 403

    data = request.get_json(silent=True) or {}
    status = data.get("review_status")

    # Verify the record exists and enforce department-level access.
    with get_connection() as connection:
        row = connection.execute(
            "SELECT department FROM ai_audit_logs WHERE audit_id = ?",
            (audit_id,)
        ).fetchone()
    if row is None:
        return jsonify({"error": "Audit record not found."}), 404
    if not _can_access_department(user, row["department"]):
        return jsonify({"error": "You cannot review another department's records."}), 403

    try:
        updated = update_review_status(audit_id, status, user["employee_id"])
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    if not updated:
        return jsonify({"error": "Audit record not found."}), 404
    return jsonify({"message": "Audit record updated.", "review_status": status}), 200
