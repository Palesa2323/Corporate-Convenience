
import hashlib
import hmac
import secrets
import sqlite3

from backend.database import get_connection


def hash_password(password):
    """Hash a password using PBKDF2 with a random salt."""
    if not password:
        raise ValueError("Password cannot be empty.")

    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        600_000
    )

    return f"{salt.hex()}:{password_hash.hex()}"


def verify_password(password, stored_hash):
    """Verify a password against its stored hash."""
    try:
        salt_hex, hash_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            600_000
        )

        return hmac.compare_digest(actual_hash, expected_hash)

    except (ValueError, AttributeError):
        return False


def register_employee(employee_id, password, role="Employee"):
    """Register a new employee account."""

    if not employee_id or not employee_id.strip():
        raise ValueError("Employee ID is required.")

    if not password:
        raise ValueError("Password is required.")

    allowed_roles = {"Employee", "Support Staff", "Admin"}

    if role not in allowed_roles:
        raise ValueError("Invalid employee role.")

    password_hash = hash_password(password)

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO employees (
                    employee_id, password_hash, role
                )
                VALUES (?, ?, ?)
                """,
                (employee_id.strip(), password_hash, role)
            )

        return True

    except sqlite3.IntegrityError:
        raise ValueError("This employee ID is already registered.")


def authenticate_employee(employee_id, password):
    """Verify employee credentials and return account details."""
    if not employee_id or not password:
        return None

    with get_connection() as connection:
        employee = connection.execute(
            """
            SELECT employee_id, password_hash, role
            FROM employees
            WHERE employee_id = ?
            """,
            (employee_id.strip(),)
        ).fetchone()

    if employee is None:
        return None

    if not verify_password(password, employee["password_hash"]):
        return None

    return {
        "employee_id": employee["employee_id"],
        "role": employee["role"]
    }
