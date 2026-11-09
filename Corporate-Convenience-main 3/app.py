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
from datetime import datetime, timedelta, timezone

from backend.database import (
    verify_login,
    register_employee_public,
    save_employee_ticket,
    get_all_tickets,
    get_employee_tickets,
    get_department_tickets,
    get_ticket,
    update_ticket_status,
    save_ticket_responses,
    get_ticket_responses,
    get_responses_for_tickets,
    save_draft,
    send_response,
    create_employee,
    list_employees,
    update_employee,
    reset_password,
    get_connection,
)
from backend.response_generator import (
    classify_ticket,
    generate_response,
)

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


ALLOWED_TONES = {"Formal", "Friendly", "Urgent"}

# The AI code uses "Normal"; the database calls the same level "Medium".
PRIORITY_MAP = {"Normal": "Medium"}

# The six kinds of account. Staff accounts are "Support Staff" with a
# department; the Administrator is the only one who sees every ticket.
ACCOUNT_TYPES = {
    "Employee": ("Employee", None),
    "IT": ("Support Staff", "IT"),
    "Finance": ("Support Staff", "Finance"),
    "HR": ("Support Staff", "HR"),
    "Operations": ("Support Staff", "Operations"),
    "Administrator": ("Admin", None),
}


def account_type_of(role, department):
    """Turn a role + department back into one of the six account types."""
    if role == "Admin":
        return "Administrator"
    if role == "Support Staff":
        return department
    return "Employee"


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
        "priority": data.get("priority") or "Medium",
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

    employee["account_type"] = account_type_of(
        employee["role"], employee["department"]
    )

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
            "department": session.get("department"),
            "account_type": account_type_of(
                session["role"], session.get("department")
            )
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


@app.route("/api/analytics", methods=["GET"])
def ticket_analytics():
    """Return ticket metrics for administrators and department support staff."""
    user = get_logged_in_user()
    if not user:
        return jsonify({"error": "Authentication required."}), 401

    role = session.get("role")
    department = session.get("department")

    if role not in {"Admin", "Support Staff"}:
        return jsonify({"error": "Analytics access is restricted to support staff and administrators."}), 403

    try:
        days = request.args.get("days", default=7, type=int)
        if days not in {7, 30, 90}:
            days = 7

        if role == "Admin":
            rows = get_all_tickets(user)
        else:
            rows = get_department_tickets(user)

        tickets = [normalize_ticket(row) for row in rows]
        ticket_ids = [ticket["id"] for ticket in tickets if ticket["id"] is not None]

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=days)
        previous_start = period_start - timedelta(days=days)

        def parse_datetime(value):
            if not value:
                return None
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except (TypeError, ValueError):
                return None

        for ticket in tickets:
            ticket["_created"] = parse_datetime(ticket.get("created_at"))

        current = [
            ticket for ticket in tickets
            if ticket["_created"] and ticket["_created"] >= period_start
        ]
        previous = [
            ticket for ticket in tickets
            if ticket["_created"] and previous_start <= ticket["_created"] < period_start
        ]

        # Only a staff-approved Reply counts as a first response.
        # Automatic acknowledgements are deliberately excluded.
        response_rows = []
        if ticket_ids:
            placeholders = ",".join("?" for _ in ticket_ids)
            with get_connection() as connection:
                response_rows = connection.execute(f"""
                    SELECT ticket_id, MIN(sent_at) AS first_response_at
                    FROM responses
                    WHERE ticket_id IN ({placeholders})
                      AND response_type = 'Reply'
                      AND status = 'Sent'
                      AND sent_at IS NOT NULL
                    GROUP BY ticket_id
                """, ticket_ids).fetchall()

        first_response = {
            row["ticket_id"]: parse_datetime(row["first_response_at"])
            for row in response_rows
        }

        response_minutes = []
        response_by_department = {}
        responded_count = 0
        for ticket in current:
            response_at = first_response.get(ticket["id"])
            created_at = ticket["_created"]
            if response_at and created_at and response_at >= created_at:
                minutes = (response_at - created_at).total_seconds() / 60
                response_minutes.append(minutes)
                response_by_department.setdefault(ticket["department"], []).append(minutes)
                responded_count += 1

        def average(values):
            return round(sum(values) / len(values), 1) if values else None

        statuses = {"Open": 0, "In Progress": 0, "Resolved": 0}
        for ticket in current:
            status = ticket["status"]
            statuses[status] = statuses.get(status, 0) + 1

        departments = {}
        for ticket in current:
            name = ticket["department"] or "Unassigned"
            departments[name] = departments.get(name, 0) + 1

        daily = {}
        for offset in range(days - 1, -1, -1):
            date_key = (now.date() - timedelta(days=offset)).isoformat()
            daily[date_key] = 0
        for ticket in current:
            date_key = ticket["_created"].date().isoformat()
            if date_key in daily:
                daily[date_key] += 1

        average_by_department = {
            name: average(values) for name, values in response_by_department.items()
        }

        insights = []
        if current:
            if departments:
                busiest = max(departments, key=departments.get)
                insights.append(
                    f"{busiest} received the most tickets ({departments[busiest]}) in the selected period."
                )
            if statuses.get("Open", 0):
                insights.append(
                    f"{statuses['Open']} ticket(s) are still open and may need attention."
                )
            if average(response_minutes) is not None:
                insights.append(
                    f"The average first staff response time was {average(response_minutes)} minutes, based on {responded_count} ticket(s) with a sent reply."
                )
            else:
                insights.append(
                    "No staff-approved replies were recorded for tickets in this period, so response time cannot yet be calculated."
                )
            if previous:
                change = len(current) - len(previous)
                if change > 0:
                    insights.append(f"Ticket volume increased by {change} compared with the previous {days}-day period.")
                elif change < 0:
                    insights.append(f"Ticket volume decreased by {abs(change)} compared with the previous {days}-day period.")
                else:
                    insights.append(f"Ticket volume stayed the same as the previous {days}-day period.")
        else:
            insights.append("No tickets were submitted during this period.")

        return jsonify({
            "period_days": days,
            "department_scope": department if role == "Support Staff" else "All departments",
            "summary": {
                "total": len(current),
                "open": statuses.get("Open", 0),
                "in_progress": statuses.get("In Progress", 0),
                "resolved": statuses.get("Resolved", 0),
                "average_response_minutes": average(response_minutes),
                "tickets_with_response": responded_count,
                "previous_period_total": len(previous)
            },
            "daily": [{"date": key, "count": value} for key, value in daily.items()],
            "departments": [{"department": key, "count": value} for key, value in sorted(departments.items())],
            "statuses": [{"status": key, "count": value} for key, value in statuses.items()],
            "response_by_department": [
                {"department": key, "minutes": value}
                for key, value in sorted(average_by_department.items())
            ],
            "insights": insights
        }), 200

    except PermissionError as error:
        return jsonify({"error": str(error)}), 403
    except Exception:
        app.logger.exception("Unable to calculate ticket analytics.")
        return jsonify({"error": "Unable to load analytics."}), 500



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

        # Attach each ticket's replies so a dashboard can show them
        # underneath the ticket. Employees only get Sent replies.
        replies = get_responses_for_tickets(
            user, [ticket["id"] for ticket in tickets]
        )

        for ticket in tickets:
            ticket["responses"] = replies.get(ticket["id"], [])

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

    # Routing only looks at what the employee wrote.
    analysis_text = f"{subject}\n{description}"

    try:
        # Route the ticket and build the acknowledgement. This does not
        # call Gemini: the support team generates the AI reply later, in
        # the tone they choose.
        classification = classify_ticket(analysis_text)

        assigned_department = classification["department"]
        priority = PRIORITY_MAP.get(
            classification["priority"], classification["priority"]
        )

        if assigned_department not in {"HR", "IT", "Finance", "Operations"}:
            return jsonify({"error": "Unable to determine the ticket department."}), 422

        user = get_logged_in_user()

        saved_ticket = save_employee_ticket(
            user=user,
            message=full_message,
            department=assigned_department,
            subject=subject,
            priority=priority
        )

        # The employee gets the automatic acknowledgement straight away.
        try:
            save_ticket_responses(
                user,
                saved_ticket["ticket_id"],
                acknowledgement=classification["acknowledgement"]
            )
        except Exception:
            app.logger.exception(
                "Ticket %s was saved but its acknowledgement was not.",
                saved_ticket["ticket_id"]
            )

        ticket = normalize_ticket(saved_ticket)
        ticket["responses"] = get_ticket_responses(
            user, saved_ticket["ticket_id"]
        )

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

    try:
        ticket = get_ticket(user, ticket_id)
    except PermissionError as error:
        return jsonify({"error": str(error)}), 403

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


@app.route("/api/tickets/<int:ticket_id>", methods=["GET"])
def get_ticket_detail(ticket_id):
    """One ticket plus its responses (what the role is allowed to see)."""
    user = get_logged_in_user()

    if not user:
        return jsonify({"error": "Authentication required."}), 401

    try:
        ticket = get_ticket(user, ticket_id)

        if ticket is None:
            return jsonify({"error": "Ticket not found."}), 404

        return jsonify({
            "ticket": normalize_ticket(ticket),
            "responses": get_ticket_responses(user, ticket_id)
        }), 200

    except PermissionError as error:
        return jsonify({"error": str(error)}), 403

    except Exception:
        app.logger.exception("Unable to retrieve ticket")
        return jsonify({"error": "Unable to retrieve the ticket."}), 500


@app.route("/api/tickets/<int:ticket_id>/draft", methods=["POST"])
def create_draft(ticket_id):
    """
    Support Staff / Admin: generate an AI draft reply in the tone they
    choose. Generating again replaces the previous unsent draft.
    """
    user = get_logged_in_user()

    if not user:
        return jsonify({"error": "Authentication required."}), 401

    if session.get("role") not in {"Support Staff", "Admin"}:
        return jsonify({"error": "You are not authorised to draft replies."}), 403

    data = request.get_json(silent=True) or {}
    tone = str(data.get("tone", "")).strip().title()

    if tone not in ALLOWED_TONES:
        return jsonify({
            "error": "Please choose a tone: Formal, Friendly or Urgent."
        }), 400

    try:
        ticket = get_ticket(user, ticket_id)

        if ticket is None:
            return jsonify({"error": "Ticket not found."}), 404

        details = normalize_ticket(ticket)

        text, ai_generated = generate_response(
            message=f"{details['subject']}\n{details['description']}",
            department=details["department"],
            tone=tone,
            priority=details["priority"]
        )

        draft = save_draft(user, ticket_id, text, tone, ai_generated)

        result = {
            "message": "Draft created. Review it, edit it and send it.",
            "response": draft
        }

        if not ai_generated:
            result["warning"] = (
                "Gemini was unavailable, so a template draft was used. "
                "You can try again."
            )

        return jsonify(result), 200

    except PermissionError as error:
        return jsonify({"error": str(error)}), 403

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception:
        app.logger.exception("Unable to create draft")
        return jsonify({"error": "Unable to create the draft."}), 500


@app.route("/api/tickets/<int:ticket_id>/reply", methods=["POST"])
def send_reply(ticket_id):
    """
    Support Staff / Admin: send a reply to the employee. Pass
    response_id to send an (edited) draft, or leave it out to send a
    reply typed from scratch. The employee sees it under their ticket.
    """
    user = get_logged_in_user()

    if not user:
        return jsonify({"error": "Authentication required."}), 401

    if session.get("role") not in {"Support Staff", "Admin"}:
        return jsonify({"error": "You are not authorised to send replies."}), 403

    data = request.get_json(silent=True) or {}
    response_id = data.get("response_id")

    if response_id is not None:
        try:
            response_id = int(response_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid draft."}), 400

    try:
        sent = send_response(
            user, ticket_id, data.get("final_text"),
            response_id=response_id
        )

        if sent is None:
            return jsonify({"error": "Ticket not found."}), 404

        return jsonify({
            "message": "Reply sent to the employee.",
            "response": sent
        }), 200

    except PermissionError as error:
        return jsonify({"error": str(error)}), 403

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception:
        app.logger.exception("Unable to send reply")
        return jsonify({"error": "Unable to send the reply."}), 500


# --------------------------------------------------------------------------
# Administrator: manage the six account types
# --------------------------------------------------------------------------

def admin_only():
    """Return (user, None) for an Admin, or (None, error_response)."""
    user = get_logged_in_user()

    if not user:
        return None, (jsonify({"error": "Authentication required."}), 401)

    if session.get("role") != "Admin":
        return None, (jsonify({"error": "Administrator access required."}), 403)

    return user, None


@app.route("/api/admin/accounts", methods=["GET"])
def admin_list_accounts():
    user, error = admin_only()
    if error:
        return error

    try:
        accounts = list_employees(user)

        for account in accounts:
            account["account_type"] = account_type_of(
                account["role"], account["department"]
            )

        return jsonify({"accounts": accounts}), 200

    except PermissionError as error:
        return jsonify({"error": str(error)}), 403

    except Exception:
        app.logger.exception("Unable to list accounts")
        return jsonify({"error": "Unable to list accounts."}), 500


@app.route("/api/admin/accounts", methods=["POST"])
def admin_create_account():
    user, error = admin_only()
    if error:
        return error

    data = request.get_json(silent=True) or {}
    account_type = str(data.get("account_type", "")).strip()

    # Accept "hr", "HR", "administrator" and so on.
    matches = {name.lower(): name for name in ACCOUNT_TYPES}
    account_type = matches.get(account_type.lower())

    if account_type is None:
        return jsonify({
            "error": "Account type must be one of: "
                     + ", ".join(ACCOUNT_TYPES)
        }), 400

    role, department = ACCOUNT_TYPES[account_type]

    try:
        if role == "Employee":
            department = data.get("department")

        account = create_employee(
            user,
            str(data.get("employee_id", "")).strip(),
            str(data.get("password", "")),
            role,
            department,
            data.get("email")
        )

        account["account_type"] = account_type_of(
            account["role"], account["department"]
        )

        return jsonify({
            "message": "Account created.",
            "account": account
        }), 201

    except PermissionError as error:
        return jsonify({"error": str(error)}), 403

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception:
        app.logger.exception("Unable to create account")
        return jsonify({"error": "Unable to create the account."}), 500


@app.route("/api/admin/accounts/<employee_id>", methods=["PATCH"])
def admin_update_account(employee_id):
    """Deactivate / reactivate an account, set its email or reset its password."""
    user, error = admin_only()
    if error:
        return error

    data = request.get_json(silent=True) or {}

    try:
        account = update_employee(
            user,
            employee_id,
            email=data.get("email"),
            is_active=data.get("is_active")
        )

        if data.get("new_password"):
            reset_password(user, employee_id, str(data["new_password"]))

        account["account_type"] = account_type_of(
            account["role"], account["department"]
        )

        return jsonify({
            "message": "Account updated.",
            "account": account
        }), 200

    except PermissionError as error:
        return jsonify({"error": str(error)}), 403

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception:
        app.logger.exception("Unable to update account")
        return jsonify({"error": "Unable to update the account."}), 500


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