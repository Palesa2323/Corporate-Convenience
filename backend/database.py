
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

# Store the database in the same folder as this file.
# Store the database in the main project folder.
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "tickets.db"

def get_connection():
    """Create a connection to the SQLite database."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    """Create the required database tables if they do not exist."""

    with get_connection() as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                department TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open'
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (
                    role IN ('Employee', 'Support Staff', 'Admin')
                )
            )
        """)

        # Add employee ownership to existing tickets.
        ticket_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(tickets)"
            ).fetchall()
        }

        if "employee_id" not in ticket_columns:
            connection.execute("""
                ALTER TABLE tickets
                ADD COLUMN employee_id TEXT
                REFERENCES employees(employee_id)
            """)


def save_ticket(message, department):
    """Save a ticket and return its complete record."""
    message = message.strip()

    department_map = {
        "HR": "HR",
        "IT": "IT",
        "FINANCE": "Finance",
        "OPERATIONS": "Operations",
    }

    if not message:
        raise ValueError("Ticket message cannot be empty.")

    department_key = department.strip().upper()

    if department_key not in department_map:
        raise ValueError("Invalid department.")

    department = department_map[department_key]
    created_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO tickets (
                message, department, created_at, status
            )
            VALUES (?, ?, ?, ?)
        """, (message, department, created_at, "Open"))

        ticket_id = cursor.lastrowid

    return get_ticket(ticket_id)

def save_employee_ticket(message, department, employee_id):
    """Save a ticket linked to the employee who submitted it."""

    if not employee_id or not employee_id.strip():
        raise ValueError("Employee ID is required.")

    message = message.strip()

    department_map = {
        "HR": "HR",
        "IT": "IT",
        "FINANCE": "Finance",
        "OPERATIONS": "Operations",
    }

    if not message:
        raise ValueError("Ticket message cannot be empty.")

    department_key = department.strip().upper()

    if department_key not in department_map:
        raise ValueError("Invalid department.")

    department = department_map[department_key]
    created_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO tickets (
                message, department, created_at, status, employee_id
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            message,
            department,
            created_at,
            "Open",
            employee_id.strip()
        ))

        ticket_id = cursor.lastrowid

    return get_ticket(ticket_id)


def get_ticket(ticket_id):
    """Retrieve a ticket using its ID."""
    with get_connection() as connection:
        row = connection.execute("""
            SELECT ticket_id, message, department, created_at,
                   status, employee_id
            FROM tickets
            WHERE ticket_id = ?
        """, (ticket_id,)).fetchone()

    return dict(row) if row else None


def get_all_tickets():
    """Retrieve all tickets, newest first."""
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT ticket_id, message, department, created_at,
                   status, employee_id
            FROM tickets
            ORDER BY ticket_id DESC
        """).fetchall()

    return [dict(row) for row in rows]


def get_employee_tickets(employee_id):
    """Retrieve tickets submitted by a specific employee."""

    if not employee_id or not employee_id.strip():
        raise ValueError("Employee ID is required.")

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT ticket_id, message, department, created_at,
                   status, employee_id
            FROM tickets
            WHERE employee_id = ?
            ORDER BY ticket_id DESC
        """, (employee_id.strip(),)).fetchall()

    return [dict(row) for row in rows]

def update_ticket_status(ticket_id, status):
    """Update a ticket's status."""
    allowed_statuses = {"Open", "In Progress", "Resolved"}

    if status not in allowed_statuses:
        raise ValueError("Invalid ticket status.")

    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE tickets
            SET status = ?
            WHERE ticket_id = ?
        """, (status, ticket_id))

    return cursor.rowcount > 0


# Ensure the database tables exist when this module is imported.
init_db()
