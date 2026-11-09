"""Database layer: employee accounts, tickets, response history and privacy."""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

from werkzeug.security import generate_password_hash, check_password_hash


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "tickets.db"

DEPARTMENTS = ("IT", "HR", "Finance", "Operations")
ROLES = ("Employee", "Support Staff", "Admin")
STATUSES = ("Open", "In Progress", "Resolved")
RESPONSE_STATUSES = ("Draft", "Sent")
PRIORITIES = ("Low", "Medium", "High", "Urgent")
MIN_PASSWORD_LENGTH = 8


# --------------------------------------------------------------------------
# Connection
# --------------------------------------------------------------------------

@contextmanager
def get_connection():
    """Create and safely close a SQLite connection."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Schema
# --------------------------------------------------------------------------

def _add_column_if_missing(connection, table, column, definition):
    existing = {
        row["name"]
        for row in connection.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    }

    if column not in existing:
        connection.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def init_db():
    """Create tables and upgrade older databases."""
    with get_connection() as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT,
                email TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_number TEXT,
                subject TEXT NOT NULL DEFAULT '',
                message TEXT NOT NULL,
                department TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'Medium',
                created_at TEXT NOT NULL,
                updated_at TEXT,
                status TEXT NOT NULL DEFAULT 'Open',
                employee_id TEXT REFERENCES employees(employee_id)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                response_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL REFERENCES tickets(ticket_id),
                tone TEXT,
                draft_text TEXT,
                final_text TEXT,
                status TEXT NOT NULL DEFAULT 'Draft',
                response_type TEXT NOT NULL DEFAULT 'Reply',
                ai_generated INTEGER NOT NULL DEFAULT 0,
                created_by TEXT REFERENCES employees(employee_id),
                sent_by TEXT REFERENCES employees(employee_id),
                created_at TEXT NOT NULL,
                sent_at TEXT
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS email_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL REFERENCES tickets(ticket_id),
                response_id INTEGER REFERENCES responses(response_id),
                email_type TEXT NOT NULL,
                recipient TEXT,
                success INTEGER NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Upgrade older database versions.
        _add_column_if_missing(connection, "employees", "department", "TEXT")
        _add_column_if_missing(connection, "employees", "email", "TEXT")
        _add_column_if_missing(
            connection, "employees", "is_active",
            "INTEGER NOT NULL DEFAULT 1"
        )

        _add_column_if_missing(connection, "tickets", "ticket_number", "TEXT")
        _add_column_if_missing(
            connection, "tickets", "subject",
            "TEXT NOT NULL DEFAULT ''"
        )
        _add_column_if_missing(
            connection, "tickets", "priority",
            "TEXT NOT NULL DEFAULT 'Medium'"
        )
        _add_column_if_missing(connection, "tickets", "updated_at", "TEXT")
        _add_column_if_missing(
            connection, "tickets", "employee_id",
            "TEXT REFERENCES employees(employee_id)"
        )

        # Responses: 'Acknowledgement' rows are sent to the employee at
        # once; 'Reply' rows start as a Draft until support staff send them.
        _add_column_if_missing(
            connection, "responses", "response_type",
            "TEXT NOT NULL DEFAULT 'Reply'"
        )
        _add_column_if_missing(
            connection, "responses", "ai_generated",
            "INTEGER NOT NULL DEFAULT 0"
        )

        connection.execute("""
            UPDATE tickets
            SET ticket_number = printf('TKT-%06d', ticket_id)
            WHERE ticket_number IS NULL
        """)

        connection.execute("""
            UPDATE tickets
            SET priority = 'Medium'
            WHERE priority = 'Normal'
        """)

        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_tickets_number
            ON tickets(ticket_number)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_tickets_department
            ON tickets(department)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_tickets_employee
            ON tickets(employee_id)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_responses_ticket
            ON responses(ticket_id)
        """)


# --------------------------------------------------------------------------
# Validation helpers
# --------------------------------------------------------------------------

def _clean_id(employee_id):
    if not employee_id or not str(employee_id).strip():
        raise ValueError("Employee ID is required.")
    return str(employee_id).strip()


def _clean_department(department, required=True):
    if department is None or not str(department).strip():
        if required:
            raise ValueError("Department is required.")
        return None

    department = str(department).strip()

    for valid in DEPARTMENTS:
        if department.lower() == valid.lower():
            return valid

    raise ValueError("Invalid department.")


def _clean_priority(priority):
    priority = str(priority or "Medium").strip().lower()

    for valid in PRIORITIES:
        if priority == valid.lower():
            return valid

    raise ValueError("Invalid priority.")


def _clean_email(email, required=False):
    if not email or not str(email).strip():
        if required:
            raise ValueError("Email address is required.")
        return None

    email = str(email).strip().lower()
    local, separator, domain = email.partition("@")

    if not separator or not local or "." not in domain or " " in email:
        raise ValueError("Invalid email address.")

    return email


def _check_password_rules(password):
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )


# --------------------------------------------------------------------------
# Employee accounts
# --------------------------------------------------------------------------

_PUBLIC_EMPLOYEE_COLUMNS = """
    employee_id, role, department, email, is_active
"""


def get_employee(employee_id):
    """Retrieve an employee without exposing their password hash."""
    employee_id = _clean_id(employee_id)

    with get_connection() as connection:
        row = connection.execute("""
            SELECT employee_id, role, department, email, is_active
            FROM employees
            WHERE employee_id = ?
        """, (employee_id,)).fetchone()

    return dict(row) if row else None


def verify_login(employee_id, password):
    """Verify credentials and return the employee account."""
    if not employee_id or not password:
        return None

    with get_connection() as connection:
        row = connection.execute("""
            SELECT employee_id, password_hash, role,
                   department, email, is_active
            FROM employees
            WHERE employee_id = ?
        """, (str(employee_id).strip(),)).fetchone()

    if not row or not row["is_active"]:
        return None

    if not check_password_hash(row["password_hash"], password):
        return None

    return {
        key: row[key]
        for key in (
            "employee_id", "role", "department", "email", "is_active"
        )
    }


def _trusted_user(user):
    """Always retrieve the user's current permissions from the database."""
    if not isinstance(user, dict) or not user.get("employee_id"):
        raise PermissionError("Authentication required.")

    current = get_employee(user["employee_id"])

    if not current or not current["is_active"]:
        raise PermissionError("Account not found or deactivated.")

    return current


def _require_admin(user):
    current = _trusted_user(user)

    if current["role"] != "Admin":
        raise PermissionError("Administrator access required.")

    return current


def _validate_account(role, department):
    if role not in ROLES:
        raise ValueError("Invalid role.")

    department = _clean_department(department, required=False)

    if role == "Support Staff" and not department:
        raise ValueError("Support Staff must have a department.")

    if role == "Admin":
        return None

    return department


def _insert_employee(employee_id, password, role, department=None, email=None):
    employee_id = _clean_id(employee_id)
    _check_password_rules(password)

    department = _validate_account(role, department)
    email = _clean_email(email)

    try:
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO employees (
                    employee_id, password_hash, role, department, email
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                employee_id,
                generate_password_hash(password),
                role,
                department,
                email
            ))

    except sqlite3.IntegrityError:
        raise ValueError("Employee ID or email already exists.")

    return get_employee(employee_id)


def create_employee(acting_user, employee_id, password, role,
                    department=None, email=None):
    """Admin only: create an employee account."""
    _require_admin(acting_user)
    return _insert_employee(employee_id, password, role, department, email)


def register_employee_public(employee_id, password, department=None):
    """Public registration for standard employees."""
    return _insert_employee(employee_id, password, role="Employee", department=department)


def update_employee(acting_user, employee_id, role=None, department=None,
                    email=None, is_active=None):
    """Admin only: update an employee account."""
    _require_admin(acting_user)

    target = get_employee(employee_id)
    if not target:
        raise ValueError("Employee not found.")

    new_role = role if role is not None else target["role"]
    new_department = (
        department if department is not None
        else target["department"]
    )
    new_department = _validate_account(new_role, new_department)

    new_email = (
        _clean_email(email) if email is not None
        else target["email"]
    )
    new_active = (
        int(bool(is_active)) if is_active is not None
        else target["is_active"]
    )

    if target["role"] == "Admin" and (
        not new_active or new_role != "Admin"
    ):
        if _count_active_admins() <= 1:
            raise ValueError("Cannot remove the last active Admin.")

    try:
        with get_connection() as connection:
            connection.execute("""
                UPDATE employees
                SET role = ?, department = ?, email = ?, is_active = ?
                WHERE employee_id = ?
            """, (
                new_role, new_department, new_email,
                new_active, target["employee_id"]
            ))

    except sqlite3.IntegrityError:
        raise ValueError("Email already in use.")

    return get_employee(target["employee_id"])


def reset_password(acting_user, employee_id, new_password):
    """Admin only: reset an employee password."""
    _require_admin(acting_user)
    _check_password_rules(new_password)

    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE employees
            SET password_hash = ?
            WHERE employee_id = ?
        """, (generate_password_hash(new_password), employee_id))

    if cursor.rowcount == 0:
        raise ValueError("Employee not found.")

    return True


def change_own_password(user, old_password, new_password):
    """Allow a user to change their own password."""
    current = _trusted_user(user)

    if not verify_login(current["employee_id"], old_password):
        raise PermissionError("Current password is incorrect.")

    _check_password_rules(new_password)

    with get_connection() as connection:
        connection.execute("""
            UPDATE employees
            SET password_hash = ?
            WHERE employee_id = ?
        """, (
            generate_password_hash(new_password),
            current["employee_id"]
        ))

    return True


def list_employees(acting_user, role=None, department=None):
    """Admin only: retrieve employee accounts."""
    _require_admin(acting_user)

    query = f"SELECT {_PUBLIC_EMPLOYEE_COLUMNS} FROM employees WHERE 1=1"
    params = []

    if role:
        if role not in ROLES:
            raise ValueError("Invalid role.")
        query += " AND role = ?"
        params.append(role)

    if department:
        query += " AND department = ?"
        params.append(_clean_department(department))

    query += " ORDER BY employee_id"

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    return [dict(row) for row in rows]


def _count_active_admins():
    with get_connection() as connection:
        return connection.execute("""
            SELECT COUNT(*)
            FROM employees
            WHERE role = 'Admin' AND is_active = 1
        """).fetchone()[0]


# --------------------------------------------------------------------------
# Tickets: creation & retrieval
# --------------------------------------------------------------------------

_TICKET_SELECT = """
    SELECT t.ticket_id, t.ticket_number, t.subject, t.message,
           t.department, t.priority, t.status, t.created_at,
           t.updated_at, t.employee_id, e.email AS employee_email
    FROM tickets t
    LEFT JOIN employees e ON e.employee_id = t.employee_id
"""


def _insert_ticket(message, department, employee_id,
                   subject="", priority="Medium"):
    message = (message or "").strip()
    subject = (subject or "").strip()

    if not message:
        raise ValueError("Ticket message cannot be empty.")

    department = _clean_department(department)
    priority = _clean_priority(priority)

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO tickets (
                subject, message, department, priority,
                created_at, status, employee_id
            )
            VALUES (?, ?, ?, ?, ?, 'Open', ?)
        """, (
            subject, message, department, priority,
            _now(), employee_id
        ))

        ticket_id = cursor.lastrowid

        connection.execute("""
            UPDATE tickets
            SET ticket_number = ?
            WHERE ticket_id = ?
        """, (f"TKT-{ticket_id:06d}", ticket_id))

    return ticket_id


def save_employee_ticket(user, message, department,
                         subject="", priority="Medium"):
    """Save a ticket for the authenticated employee."""
    current = _trusted_user(user)

    if current["role"] != "Employee":
        raise PermissionError("Only employees can submit tickets.")

    ticket_id = _insert_ticket(
        message,
        department,
        current["employee_id"],
        subject,
        priority
    )

    return get_ticket(user, ticket_id)


def get_employee_tickets(user):
    """Employees can retrieve only their own tickets."""
    current = _trusted_user(user)

    if current["role"] != "Employee":
        raise PermissionError("Employee access required.")

    with get_connection() as connection:
        rows = connection.execute(
            _TICKET_SELECT + """
                WHERE t.employee_id = ?
                ORDER BY t.ticket_id DESC
            """,
            (current["employee_id"],)
        ).fetchall()

    return [dict(row) for row in rows]


def get_department_tickets(user, department=None):
    """Support Staff can retrieve tickets from their own department."""
    current = _trusted_user(user)

    if current["role"] != "Support Staff":
        raise PermissionError("Support Staff access required.")

    own_department = current["department"]

    if not own_department:
        raise PermissionError("No department assigned.")

    if department is not None:
        requested_department = _clean_department(department)
        if requested_department != own_department:
            raise PermissionError("Access to this department is denied.")

    with get_connection() as connection:
        rows = connection.execute(
            _TICKET_SELECT + """
                WHERE t.department = ?
                ORDER BY t.ticket_id DESC
            """,
            (own_department,)
        ).fetchall()

    return [dict(row) for row in rows]


def get_all_tickets(user):
    """Admins can retrieve all tickets."""
    _require_admin(user)

    with get_connection() as connection:
        rows = connection.execute(
            _TICKET_SELECT + """
                ORDER BY t.ticket_id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_ticket(user, ticket_id):
    """Retrieve one ticket only if the user has permission to see it."""
    current = _trusted_user(user)

    with get_connection() as connection:
        row = connection.execute(
            _TICKET_SELECT + """
                WHERE t.ticket_id = ?
            """,
            (ticket_id,)
        ).fetchone()

    if not row:
        return None

    ticket = dict(row)

    if current["role"] == "Employee":
        if ticket["employee_id"] != current["employee_id"]:
            raise PermissionError("You cannot access this ticket.")

    elif current["role"] == "Support Staff":
        if ticket["department"] != current["department"]:
            raise PermissionError("You cannot access this ticket.")

    elif current["role"] != "Admin":
        raise PermissionError("Access denied.")

    return ticket


def update_ticket_status(user, ticket_id, status):
    """Update a ticket status with role and department checks."""
    current = _trusted_user(user)

    if current["role"] not in {"Support Staff", "Admin"}:
        raise PermissionError("You cannot update tickets.")

    status = str(status or "").strip().title()

    if status not in STATUSES:
        raise ValueError("Invalid ticket status.")

    ticket = get_ticket(user, ticket_id)
    if ticket is None:
        return False

    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE tickets
            SET status = ?, updated_at = ?
            WHERE ticket_id = ?
        """, (status, _now(), ticket_id))

    return cursor.rowcount > 0


# --------------------------------------------------------------------------
# Responses: acknowledgement, AI draft and staff-approved replies
# --------------------------------------------------------------------------

_RESPONSE_SELECT = """
    SELECT response_id, ticket_id, response_type, tone, draft_text,
           final_text, status, ai_generated, created_by, sent_by,
           created_at, sent_at
    FROM responses
"""


def _with_text(item):
    """Add a single `text` field: the sent text, otherwise the draft."""
    item["text"] = item.get("final_text") or item.get("draft_text") or ""
    return item


def _employee_view(item):
    """What an employee is allowed to see of a response."""
    return {
        "response_id": item["response_id"],
        "response_type": item["response_type"],
        "text": item["final_text"],
        "sent_at": item["sent_at"],
    }


def save_ticket_responses(user, ticket_id, acknowledgement, draft_text=None,
                          tone=None, ai_generated=False):
    """
    Store the automatic responses for a new ticket.

    - The acknowledgement is marked Sent straight away.
    - The AI reply is stored as a Draft and stays hidden from the
      employee until support staff review and send it.
    """
    # get_ticket enforces that this user is allowed to see the ticket.
    ticket = get_ticket(user, ticket_id)

    if ticket is None:
        raise ValueError("Ticket not found.")

    now = _now()

    with get_connection() as connection:

        if acknowledgement and str(acknowledgement).strip():
            connection.execute("""
                INSERT INTO responses (
                    ticket_id, tone, draft_text, final_text, status,
                    response_type, ai_generated, created_at, sent_at
                )
                VALUES (?, ?, ?, ?, 'Sent', 'Acknowledgement', 0, ?, ?)
            """, (
                ticket_id, tone, acknowledgement, acknowledgement,
                now, now
            ))

        if draft_text and str(draft_text).strip():
            connection.execute("""
                INSERT INTO responses (
                    ticket_id, tone, draft_text, status,
                    response_type, ai_generated, created_at
                )
                VALUES (?, ?, ?, 'Draft', 'Reply', ?, ?)
            """, (
                ticket_id, tone, draft_text,
                1 if ai_generated else 0, now
            ))


def get_ticket_responses(user, ticket_id):
    """
    Return the responses on a ticket.

    Employees only see responses that have been Sent, and only the
    final text. Support Staff and Admins also see drafts.
    """
    current = _trusted_user(user)

    # get_ticket enforces the ownership / department rules.
    ticket = get_ticket(user, ticket_id)

    if ticket is None:
        return None

    query = _RESPONSE_SELECT + " WHERE ticket_id = ?"

    if current["role"] == "Employee":
        query += " AND status = 'Sent'"

    query += " ORDER BY response_id"

    with get_connection() as connection:
        rows = connection.execute(query, (ticket_id,)).fetchall()

    if current["role"] == "Employee":
        return [_employee_view(dict(row)) for row in rows]

    return [_with_text(dict(row)) for row in rows]


def _staff_user(user):
    """Return the current user if they are Support Staff or an Admin."""
    current = _trusted_user(user)

    if current["role"] not in {"Support Staff", "Admin"}:
        raise PermissionError("Support Staff access required.")

    return current


def save_draft(user, ticket_id, draft_text, tone, ai_generated=False):
    """
    Support Staff / Admin: store an AI (or template) draft for a ticket.

    Any earlier unsent draft on the ticket is replaced, so each ticket
    has at most one draft waiting at a time.
    """
    current = _staff_user(user)

    # Department check for Support Staff happens inside get_ticket.
    ticket = get_ticket(user, ticket_id)

    if ticket is None:
        return None

    draft_text = (draft_text or "").strip()

    if not draft_text:
        raise ValueError("Draft text cannot be empty.")

    with get_connection() as connection:
        connection.execute("""
            DELETE FROM responses
            WHERE ticket_id = ?
              AND response_type = 'Reply'
              AND status = 'Draft'
        """, (ticket_id,))

        cursor = connection.execute("""
            INSERT INTO responses (
                ticket_id, tone, draft_text, status, response_type,
                ai_generated, created_by, created_at
            )
            VALUES (?, ?, ?, 'Draft', 'Reply', ?, ?, ?)
        """, (
            ticket_id, tone, draft_text,
            1 if ai_generated else 0,
            current["employee_id"], _now()
        ))

        row = connection.execute(
            _RESPONSE_SELECT + " WHERE response_id = ?",
            (cursor.lastrowid,)
        ).fetchone()

    return _with_text(dict(row))


def send_response(user, ticket_id, final_text, response_id=None):
    """
    Support Staff / Admin: send a reply to the employee.

    - With response_id: the (possibly edited) draft is marked Sent.
    - Without it: a brand new reply, typed by staff, is sent.

    The employee then sees it under their ticket.
    """
    current = _staff_user(user)

    # Department check for Support Staff happens inside get_ticket.
    ticket = get_ticket(user, ticket_id)

    if ticket is None:
        return None

    final_text = (final_text or "").strip()

    if not final_text:
        raise ValueError("Reply text cannot be empty.")

    now = _now()

    with get_connection() as connection:

        if response_id is not None:
            cursor = connection.execute("""
                UPDATE responses
                SET final_text = ?, status = 'Sent', sent_by = ?, sent_at = ?
                WHERE response_id = ?
                  AND ticket_id = ?
                  AND response_type = 'Reply'
                  AND status = 'Draft'
            """, (
                final_text, current["employee_id"], now,
                response_id, ticket_id
            ))

            if cursor.rowcount == 0:
                raise ValueError("Draft not found, or it was already sent.")

            new_id = response_id

        else:
            cursor = connection.execute("""
                INSERT INTO responses (
                    ticket_id, final_text, status, response_type,
                    ai_generated, created_by, sent_by, created_at, sent_at
                )
                VALUES (?, ?, 'Sent', 'Reply', 0, ?, ?, ?, ?)
            """, (
                ticket_id, final_text, current["employee_id"],
                current["employee_id"], now, now
            ))

            new_id = cursor.lastrowid

        row = connection.execute(
            _RESPONSE_SELECT + " WHERE response_id = ?",
            (new_id,)
        ).fetchone()

    return _with_text(dict(row))


def get_responses_for_tickets(user, ticket_ids):
    """
    Return {ticket_id: [responses]} for a list of tickets, so a dashboard
    can show each ticket's replies underneath it.

    Employees only get their own tickets' Sent responses (text only).
    Support Staff get their department's, including drafts.
    Admins get everything.
    """
    current = _trusted_user(user)
    ticket_ids = [int(t) for t in ticket_ids]

    if not ticket_ids:
        return {}

    placeholders = ",".join("?" for _ in ticket_ids)
    params = list(ticket_ids)

    query = f"""
        SELECT r.response_id, r.ticket_id, r.response_type, r.tone,
               r.draft_text, r.final_text, r.status, r.ai_generated,
               r.created_by, r.sent_by, r.created_at, r.sent_at
        FROM responses r
        JOIN tickets t ON t.ticket_id = r.ticket_id
        WHERE r.ticket_id IN ({placeholders})
    """

    if current["role"] == "Employee":
        query += " AND t.employee_id = ? AND r.status = 'Sent'"
        params.append(current["employee_id"])

    elif current["role"] == "Support Staff":
        query += " AND t.department = ?"
        params.append(current["department"])

    elif current["role"] != "Admin":
        raise PermissionError("Access denied.")

    query += " ORDER BY r.response_id"

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    grouped = {}

    for row in rows:
        item = dict(row)

        if current["role"] == "Employee":
            item = _employee_view(item)
        else:
            item = _with_text(item)

        grouped.setdefault(row["ticket_id"], []).append(item)

    return grouped


# Initialize database on import
init_db()