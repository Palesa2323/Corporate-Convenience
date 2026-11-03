"""Database layer: employee accounts, tickets, response history, privacy.

Privacy model
-------------
Every function that reads or changes ticket data takes the logged-in `user`
(a dict with at least "employee_id"; usually the Flask session user).
The role and department are ALWAYS re-read from the database, so a
forged or stale session dict cannot grant extra access.

    Employee       -> own tickets only (and only *sent* replies)
    Support Staff  -> tickets of their own department only
    Admin          -> every department

Denied access raises PermissionError (Member 3: return HTTP 403).
Bad input raises ValueError (HTTP 400).
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

from werkzeug.security import generate_password_hash, check_password_hash

# Store the database in the main project folder.
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "tickets.db"

DEPARTMENTS = ("IT", "HR", "Finance", "Operations")
DEPARTMENT_MAP = {name.upper(): name for name in DEPARTMENTS}
ROLES = ("Employee", "Support Staff", "Admin")
STATUSES = ("Open", "In Progress", "Resolved")
PRIORITIES = ("Low", "Medium", "High", "Urgent")
PRIORITY_MAP = {name.upper(): name for name in PRIORITIES}
TONES = ("Formal", "Friendly", "Urgent")
MIN_PASSWORD_LENGTH = 8


# --------------------------------------------------------------------------
# Connection
# --------------------------------------------------------------------------

@contextmanager
def get_connection():
    """Create and safely close a SQLite database connection."""

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
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in existing:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    """Create the tables if missing and upgrade older databases in place."""

    with get_connection() as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (
                    role IN ('Employee', 'Support Staff', 'Admin')
                ),
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
                priority TEXT NOT NULL DEFAULT 'Normal',
                created_at TEXT NOT NULL,
                updated_at TEXT,
                status TEXT NOT NULL DEFAULT 'Open',
                employee_id TEXT REFERENCES employees(employee_id)
            )

        connection.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                response_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL REFERENCES tickets(ticket_id),
                tone TEXT,
                draft_text TEXT,
                final_text TEXT,
                status TEXT NOT NULL DEFAULT 'Draft'
                    CHECK (status IN ('Draft', 'Sent')),
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
                email_type TEXT NOT NULL
                    CHECK (email_type IN ('Confirmation', 'Response')),
                recipient TEXT,
                success INTEGER NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Upgrades for databases created by earlier versions.
        _add_column_if_missing(connection, "employees", "department", "TEXT")
        _add_column_if_missing(connection, "employees", "email", "TEXT")
        _add_column_if_missing(
            connection, "employees", "is_active", "INTEGER NOT NULL DEFAULT 1"
        )
        _add_column_if_missing(connection, "tickets", "ticket_number", "TEXT")
        _add_column_if_missing(
            connection, "tickets", "subject", "TEXT NOT NULL DEFAULT ''"
        )
        _add_column_if_missing(
            connection, "tickets", "priority", "TEXT NOT NULL DEFAULT 'Medium'"
        )
        _add_column_if_missing(connection, "tickets", "updated_at", "TEXT")
        _add_column_if_missing(
            connection, "tickets", "employee_id",
            "TEXT REFERENCES employees(employee_id)"
        )

        connection.execute("""
            UPDATE tickets
            SET ticket_number = printf('TKT-%06d', ticket_id)
            WHERE ticket_number IS NULL
        """)

        if "priority" not in ticket_columns:
            connection.execute("""
                ALTER TABLE tickets
                ADD COLUMN priority TEXT NOT NULL DEFAULT 'Normal'
            """)

        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_tickets_number
            ON tickets(ticket_number)
        """)

        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_employees_email
            ON employees(email)
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
    key = str(department).strip().upper()
    if key not in DEPARTMENT_MAP:
        raise ValueError("Invalid department.")
    return DEPARTMENT_MAP[key]


def _clean_priority(priority):
    key = str(priority or "Medium").strip().upper()
    if key not in PRIORITY_MAP:
        raise ValueError("Invalid priority.")
    return PRIORITY_MAP[key]


def _clean_email(email, required=False):
    if email is None or not str(email).strip():
        if required:
            raise ValueError("Email address is required.")
        return None
    email = str(email).strip().lower()
    local, _, domain = email.partition("@")
    if not local or "." not in domain or " " in email:
        raise ValueError("Invalid email address.")
    return email

def save_employee_ticket(message, department, employee_id, priority="Normal"):
    """Save a ticket linked to the employee who submitted it."""

def _check_password_rules(password):
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )


# --------------------------------------------------------------------------
# Employee accounts
# --------------------------------------------------------------------------

_PUBLIC_EMPLOYEE_COLUMNS = "employee_id, role, department, email, is_active"


def get_employee(employee_id):
    """Retrieve an employee (never includes the password hash)."""

    employee_id = _clean_id(employee_id)

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO tickets (
                message, department, created_at, status,
                employee_id, priority
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            message,
            department,
            created_at,
            "Open",
            employee_id.strip(),
            priority
        ))

    ticket_id = cursor.lastrowid
def verify_login(employee_id, password):
    """Check credentials. Returns the user dict, or None if invalid.

    Deactivated accounts cannot log in. The same None is returned for an
    unknown ID and a wrong password so callers can't reveal which it was.
    """

    if not employee_id or not str(employee_id).strip() or not password:
        return None

    with get_connection() as connection:
        row = connection.execute("""
            SELECT ticket_id, message, department, created_at,
                   status, employee_id, priority
            FROM tickets
            WHERE ticket_id = ?
        """, (ticket_id,)).fetchone()

    if not row or not row["is_active"]:
        return None
    if not check_password_hash(row["password_hash"], password):
        return None

    return {key: row[key] for key in
            ("employee_id", "role", "department", "email", "is_active")}

def get_all_tickets():
    """Retrieve all tickets, newest first."""
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT ticket_id, message, department, created_at,
                   status, employee_id, priority
            FROM tickets
            ORDER BY ticket_id DESC
        """).fetchall()

    return [dict(row) for row in rows]

def _trusted_user(user):
    """Re-read the user from the database; reject unknown/inactive users."""

    if not isinstance(user, dict) or not user.get("employee_id"):
        raise PermissionError("Authentication required.")

    current = get_employee(user["employee_id"])
    if not current or not current["is_active"]:
        raise PermissionError("Account not found or deactivated.")
    return current


def _require_admin(acting_user):
    admin = _trusted_user(acting_user)
    if admin["role"] != "Admin":
        raise PermissionError("Administrator access required.")
    return admin


def _validate_account(role, department):
    if role not in ROLES:
        raise ValueError("Invalid role.")
    if role == "Support Staff" and not department:
        raise ValueError("Support Staff must be assigned a department.")
    if role == "Admin":
        return None
    return department


def _insert_employee(employee_id, password, role, department, email):
    employee_id = _clean_id(employee_id)
    _check_password_rules(password)
    department = _clean_department(department, required=False)
    department = _validate_account(role, department)
    email = _clean_email(email, required=True)

    try:
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO employees
                    (employee_id, password_hash, role, department, email)
                VALUES (?, ?, ?, ?, ?)
            """, (employee_id, generate_password_hash(password),
                  role, department, email))
    except sqlite3.IntegrityError:
        raise ValueError("Employee ID or email already exists.")

    return get_employee(employee_id)


def create_employee(acting_user, employee_id, password, role,
                    department=None, email=None):
    """Admin only. Create an Employee, Support Staff or Admin account."""

    _require_admin(acting_user)
    return _insert_employee(employee_id, password, role, department, email)


def update_employee(acting_user, employee_id, role=None, department=None,
                    email=None, is_active=None):
    """Admin only. Change role, department, email or active status."""

    _require_admin(acting_user)
    target = get_employee(employee_id)
    if not target:
        raise ValueError("Employee not found.")

    new_role = role if role is not None else target["role"]
    new_dept = (_clean_department(department, required=False)
                if department is not None else target["department"])
    new_dept = _validate_account(new_role, new_dept)
    new_email = (_clean_email(email, required=True)
                 if email is not None else target["email"])
    new_active = int(bool(is_active)) if is_active is not None \
        else target["is_active"]

    if (target["role"] == "Admin" and not new_active
            and _count_active_admins() <= 1):
        raise ValueError("Cannot deactivate the last active Admin.")
    if (target["role"] == "Admin" and new_role != "Admin"
            and _count_active_admins() <= 1):
        raise ValueError("Cannot demote the last active Admin.")

    try:
        with get_connection() as connection:
            connection.execute("""
                UPDATE employees
                SET role = ?, department = ?, email = ?, is_active = ?
                WHERE employee_id = ?
            """, (new_role, new_dept, new_email, new_active,
                  target["employee_id"]))
    except sqlite3.IntegrityError:
        raise ValueError("Email already in use.")

    return get_employee(target["employee_id"])


def reset_password(acting_user, employee_id, new_password):
    """Admin only. Replace a user's password (stored hashed)."""

    _require_admin(acting_user)
    _check_password_rules(new_password)

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT ticket_id, message, department, created_at,
                   status, employee_id, priority
            FROM tickets
            WHERE employee_id = ?
            ORDER BY ticket_id DESC
        """, (employee_id.strip(),)).fetchall()

    return [dict(row) for row in rows]


def change_own_password(user, old_password, new_password):
    """Any logged-in user can change their own password."""

    current = _trusted_user(user)
    if not verify_login(current["employee_id"], old_password):
        raise PermissionError("Current password is incorrect.")
    _check_password_rules(new_password)

    with get_connection() as connection:
        connection.execute(
            "UPDATE employees SET password_hash = ? WHERE employee_id = ?",
            (generate_password_hash(new_password), current["employee_id"]),
        )
    return True


def list_employees(acting_user, role=None, department=None):
    """Admin only. List accounts, optionally filtered."""

    _require_admin(acting_user)
    query = f"SELECT {_PUBLIC_EMPLOYEE_COLUMNS} FROM employees WHERE 1=1"
    params = []
    if role:
        query += " AND role = ?"
        params.append(role)
    if department:
        query += " AND department = ?"
        params.append(_clean_department(department))
    query += " ORDER BY employee_id"

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    return [dict(row) for row in rows]
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def _count_active_admins():
    with get_connection() as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM employees "
            "WHERE role = 'Admin' AND is_active = 1"
        ).fetchone()[0]


# --------------------------------------------------------------------------
# Tickets: creation
# --------------------------------------------------------------------------

_TICKET_SELECT = """
    SELECT t.ticket_id, t.ticket_number, t.subject, t.message,
           t.department, t.priority, t.status, t.created_at,
           t.updated_at, t.employee_id, e.email AS employee_email
    FROM tickets t
    LEFT JOIN employees e ON e.employee_id = t.employee_id
"""


def _insert_ticket(message, department, employee_id, subject, priority):
    message = (message or "").strip()
    if not message:
        raise ValueError("Ticket message cannot be empty.")

    department = _clean_department(department)
    priority = _clean_priority(priority)
    subject = (subject or "").strip()
    created_at = _now()

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO tickets (
                subject, message, department, priority,
                created_at, status, employee_id
            )
            VALUES (?, ?, ?, ?, ?, 'Open', ?)
        """, (subject, message, department, priority, created_at, employee_id))

    return cursor.rowcount > 0
def get_department_tickets(department):
    """Retrieve tickets assigned to a specific support department."""
    if not department:
        return []

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM tickets
            WHERE department = ?
            ORDER BY ticket_id DESC
            """,
            (department,)
        ).fetchall()

    return [dict(row) for row in rows]

# Ensure the database tables exist when this module is imported.
init_db()


if __name__ == "__main__":
    made = seed_test_accounts()
    print("Created:", ", ".join(made) if made else "nothing (already seeded)")
    print(f"Test password for all accounts: {TEST_PASSWORD}")
