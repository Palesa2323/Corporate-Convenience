
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

# Store the database in the same folder as this file.
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "tickets.db"


def get_connection():
    """Create a connection to the SQLite database."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    """Create the tickets table if it does not exist."""
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


def save_ticket(message, department):
    """Save a ticket and return its complete record."""
    message = message.strip()
    department = department.strip().upper()

    if not message:
        raise ValueError("Ticket message cannot be empty.")

    if department not in {"HR", "IT", "Finance", "Operations"}:
        raise ValueError("Invalid department.")

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


def get_ticket(ticket_id):
    """Retrieve a ticket using its ID."""
    with get_connection() as connection:
        row = connection.execute("""
            SELECT ticket_id, message, department, created_at, status
            FROM tickets
            WHERE ticket_id = ?
        """, (ticket_id,)).fetchone()

    return dict(row) if row else None


def get_all_tickets():
    """Retrieve all tickets, newest first."""
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT ticket_id, message, department, created_at, status
            FROM tickets
            ORDER BY ticket_id DESC
        """).fetchall()

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


# Ensure the database table exists when this module is imported.
init_db()
