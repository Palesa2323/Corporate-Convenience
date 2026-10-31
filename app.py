
from flask import (
    Flask, jsonify, render_template, request,
    Response, session
)

from dotenv import load_dotenv
import os

from backend.authy import (
    register_employee,
    authenticate_employee
)
from backend.database import (
    init_db,
    save_ticket,
    get_all_tickets,
    update_ticket_status,
)
from backend.classifier import predict_department
import csv
import io
import re

from pathlib import Path

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


def row_to_dict(row):
    """Convert a database row to a regular dictionary."""
    if hasattr(row, "keys"):
        return {key: row[key] for key in row.keys()}
    if isinstance(row, dict):
        return row
    return {}


def extract_field(message, field):
    """Extract a labelled field from the stored ticket message."""
    pattern = rf"^{re.escape(field)}:\s*(.*)$"
    for line in str(message or "").splitlines():
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def normalize_ticket(row):
    """Adapt existing database rows to the dashboard's expected format."""
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
    description = data.get("description") or extract_field(message, "Description")

    if not description:
        description = message

    return {
        "id": ticket_id,
        "ticket_number": f"CC-{ticket_id}" if ticket_id is not None else "CC-New",
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


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    employee_id = str(data.get("employee_id", "")).strip()
    password = str(data.get("password", ""))

    try:
        register_employee(employee_id, password)

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

    employee = authenticate_employee(employee_id, password)

    if employee is None:
        return jsonify({
            "error": "Invalid employee ID or password."
        }), 401

    session.clear()

    session["employee_id"] = employee["employee_id"]
    session["role"] = employee["role"]

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
            "role": session["role"]
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
    rows = get_all_tickets()
    tickets = [normalize_ticket(row) for row in rows]
    return jsonify({"tickets": tickets})


@app.route("/api/tickets", methods=["POST"])
def create_ticket():
    data = request.get_json(silent=True) or {}

    requester = str(data.get("requester", "")).strip()
    employee_department = str(data.get("employee_department", "")).strip()
    subject = str(data.get("subject", "")).strip()
    description = str(data.get("description", "")).strip()

    if not all([requester, employee_department, subject, description]):
        return jsonify({
            "error": "Please complete every ticket field."
        }), 400

    full_message = (
        f"Requester: {requester}\n"
        f"Employee department: {employee_department}\n"
        f"Subject: {subject}\n"
        f"Description: {description}"
    )

    try:
        assigned_department = predict_department(full_message)
        save_ticket(full_message, assigned_department)

        rows = get_all_tickets()
        tickets = [normalize_ticket(row) for row in rows]

        # Return the latest saved ticket so the frontend can update immediately.
        ticket = tickets[-1] if tickets else {
            "id": None,
            "ticket_number": "CC-New",
            "requester": requester,
            "employee_department": employee_department,
            "subject": subject,
            "description": description,
            "department": assigned_department or "Unassigned",
            "status": "Open",
            "created_at": "",
        }

        return jsonify({"ticket": ticket}), 201

    except Exception as error:
        app.logger.exception("Unable to create ticket")
        return jsonify({
            "error": f"Unable to create ticket: {error}"
        }), 500


@app.route("/api/tickets/<int:ticket_id>", methods=["PATCH"])
def change_ticket_status(ticket_id):
    data = request.get_json(silent=True) or {}
    status = str(data.get("status", "")).strip().title()

    allowed_statuses = {"Open", "In Progress", "Resolved"}
    if status not in allowed_statuses:
        return jsonify({"error": "Invalid ticket status."}), 400

    try:
        update_ticket_status(ticket_id, status)
        rows = get_all_tickets()

        for row in rows:
            ticket = normalize_ticket(row)
            if str(ticket["id"]) == str(ticket_id):
                ticket["status"] = status
                return jsonify({"ticket": ticket})

        return jsonify({"message": "Status updated."})

    except Exception as error:
        app.logger.exception("Unable to update ticket status")
        return jsonify({
            "error": f"Unable to update status: {error}"
        }), 500


@app.route("/api/tickets/export", methods=["GET"])
def export_tickets():
    rows = get_all_tickets()
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

    writer = csv.DictWriter(output, fieldnames=fields)
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


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
