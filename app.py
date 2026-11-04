from flask import (
    Flask, jsonify, render_template, request,
    Response, session
)

from dotenv import load_dotenv
import os
import csv
import io
import re
from pathlib import Path

from backend.database import (
    verify_login,
    register_employee_public,
    save_employee_ticket,
    get_all_tickets,
    get_employee_tickets,
    get_department_tickets,
    get_ticket,
    update_ticket_status,
)
from backend.classifier import predict_department

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env", override=True)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is missing from .env")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False
)


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/")
def home():
    return render_template("index.html")


def row_to_dict(row):
    """Convert a database row to a regular dictionary."""
    if hasattr(row, "keys"):
        return {key: row[key] for key in row.keys()}
    if isinstance(row, dict):
        return row
    return {}


def get_logged_in_user():
    """Get the logged-in user's identity from the Flask session."""
    if "employee_id" not in session:
        return None
    return {
        "employee_id": session["employee_id"]
    }


def extract_field(message, field):
    """Extract a labelled field from the stored ticket message."""
    pattern = rf"^{re.escape(field)}:\s*(.*)$"
    for line in str(message or "").splitlines():
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def normalize_ticket(row):
    """Adapt database ticket rows to the dashboard's expected format."""
    data = row_to_dict(row)

    ticket_id = (
        data.get("ticket_id")
        or data.get("id")
        or data.get("ticketId")
    )

    message = (
        data.get("message")
        or data.get("description")
        or data.get("request")
        or ""
    )

    requester = data.get("requester") or extract_field(message, "Requester")
    employee_department = (
        data.get("employee_department")
        or extract_field(message, "Employee department")
    )
    subject = data.get("subject") or extract_field(message, "Subject")
    description = (
        data.get("description")
        or extract_field(message, "Description")
    )

    if not description:
        description = message

    return {
        "id": ticket_id,
        "ticket_number": data.get("ticket_number") or (
            f"TKT-{ticket_id:06d}" if ticket_id is not None else "TKT-New"
        ),
        "requester": requester or "Not provided",
        "employee_department": employee_department or "Not provided",
        "subject": subject or "Support request",
        "description": description,
        "department": (
            data.get("assigned_department")
            or data.get("department")
            or "Unassigned"
        ),
        "status": str(data.get("status") or "Open").title(),
        "created_at": (
            data.get("created_at")
            or data.get("created")
            or ""
        ),
    }


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    employee_id = str(data.get("employee_id", "")).strip()
    password = str(data.get("password", ""))
    department = data.get("department")

    try:
        register_employee_public(employee_id, password, department)

        return jsonify({
            "message": "Registration successful. You can now log in."
        }), 201

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception:
        app.logger.exception("Registration failed")
        return jsonify({
            "error": "Unable to complete registration."
        }), 500


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    employee_id = str(data.get("employee_id", "")).strip()
    password = str(data.get("password", ""))

    employee = verify_login(employee_id, password)

    if employee is None:
        return jsonify({
            "error": "Invalid employee ID or password."
        }), 401

    session.clear()
    session["employee_id"] = employee["employee_id"]
    session["role"] = employee["role"]
    session["department"] = employee["department"]

    return jsonify({
        "message": "Login successful.",
        "employee": employee
    })


@app.route("/api/session", methods=["GET"])
def check_session():
    if "employee_id" not in session:
        return jsonify({
            "authenticated": False
        }), 401

    return jsonify({
        "authenticated": True,
        "employee": {
            "employee_id": session["employee_id"],
            "role": session["role"],
            "department": session.get("department")
        }
    })


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({
        "message": "Logged out successfully."
    })


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/tickets", methods=["GET"])
def list_tickets():
    user = get_logged_in_user()

    if not user:
        return jsonify({"error": "Authentication required."}), 401

    role = session.get("role")

    try:
        if role == "Employee":
            rows = get_employee_tickets(user)
        elif role == "Support Staff":
            rows = get_department_tickets(user)
        elif role == "Admin":
            rows = get_all_tickets(user)
        else:
            return jsonify({"error": "Access denied."}), 403

        tickets = [normalize_ticket(row) for row in rows]
        return jsonify({"tickets": tickets}), 200

    except PermissionError as error:
        return jsonify({"error": str(error)}), 403

    except Exception:
        app.logger.exception("Failed to retrieve tickets.")
        return jsonify({"error": "Unable to retrieve tickets."}), 500


@app.route("/api/tickets", methods=["POST"])
def create_ticket():
    if "employee_id" not in session:
        return jsonify({"error": "Authentication required."}), 401

    if session.get("role") != "Employee":
        return jsonify({"error": "Only employees can submit tickets."}), 403

    data = request.get_json(silent=True) or {}
    employee_id = session["employee_id"]
    employee_department = session.get("department") or "Not provided"

    subject = str(data.get("subject", "")).strip()
    description = str(data.get("description", "")).strip()

    if not subject or not description:
        return jsonify({"error": "Please provide a subject and description."}), 400

    full_message = (
        f"Requester: {employee_id}\n"
        f"Employee department: {employee_department}\n"
        f"Subject: {subject}\n"
        f"Description: {description}"
    )

    try:
        assigned_department = predict_department(full_message)

        if assigned_department not in {"HR", "IT", "Finance", "Operations"}:
            return jsonify({"error": "Unable to determine the ticket department."}), 422

        saved_ticket = save_employee_ticket(
            user=get_logged_in_user(),
            message=full_message,
            department=assigned_department,
            subject=subject
        )

        ticket = normalize_ticket(saved_ticket)
        return jsonify({
            "message": "Ticket submitted successfully.",
            "ticket": ticket
        }), 201

    except Exception:
        app.logger.exception("Unable to create ticket")
        return jsonify({"error": "Unable to submit your ticket. Please try again."}), 500


@app.route("/api/tickets/<int:ticket_id>", methods=["PATCH"])
def change_ticket_status(ticket_id):
    if "employee_id" not in session:
        return jsonify({"error": "Authentication required."}), 401

    role = session.get("role")
    department = session.get("department")

    if role not in {"Support Staff", "Admin"}:
        return jsonify({"error": "You are not authorised to update tickets."}), 403

    user = get_logged_in_user()
    ticket = get_ticket(user, ticket_id)

    if ticket is None:
        return jsonify({"error": "Ticket not found."}), 404

    if role == "Support Staff":
        if not department or ticket["department"] != department:
            return jsonify({"error": "You cannot update tickets outside your department."}), 403

    data = request.get_json(silent=True) or {}
    status = str(data.get("status", "")).strip().title()

    if status not in {"Open", "In Progress", "Resolved"}:
        return jsonify({"error": "Invalid ticket status."}), 400

    try:
        updated = update_ticket_status(user, ticket_id, status)

        if not updated:
            return jsonify({"error": "Unable to update ticket."}), 500

        updated_ticket = get_ticket(user, ticket_id)
        return jsonify({
            "message": "Ticket status updated successfully.",
            "ticket": normalize_ticket(updated_ticket)
        }), 200

    except Exception:
        app.logger.exception("Unable to update ticket status")
        return jsonify({"error": "Unable to update ticket status."}), 500


@app.route("/api/tickets/export", methods=["GET"])
def export_tickets():
    user = get_logged_in_user()
    if not user:
        return jsonify({"error": "Authentication required."}), 401

    role = session.get("role")
    department = session.get("department")

    try:
        if role == "Admin":
            rows = get_all_tickets(user)
        elif role == "Support Staff":
            if not department:
                return jsonify({"error": "No department assigned."}), 403
            rows = get_department_tickets(user, department)
        elif role == "Employee":
            return jsonify({"error": "Employees are not authorised to export tickets."}), 403
        else:
            return jsonify({"error": "Access denied."}), 403

        tickets = [normalize_ticket(row) for row in rows]
        output = io.StringIO()

        fields = [
            "ticket_number",
            "requester",
            "employee_department",
            "subject",
            "description",
            "department",
            "status",
            "created_at",
        ]

        writer = csv.DictWriter(
            output,
            fieldnames=fields,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(tickets)

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition":
                    "attachment; filename=corporate_convenience_tickets.csv"
            },
        )
    except Exception:
        app.logger.exception("Export failed")
        return jsonify({"error": "Unable to export tickets."}), 500


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)