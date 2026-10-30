
from flask import Flask, jsonify, render_template, request, Response
from database import (
    init_db,
    save_ticket,
    get_all_tickets,
    update_ticket_status,
)
from classifier import predict_department
import csv
import io
import re

app = Flask(__name__)


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
