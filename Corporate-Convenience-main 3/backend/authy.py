
import sqlite3

from werkzeug.security import generate_password_hash, check_password_hash

from backend.database import get_connection


DEPARTMENTS = {"HR", "IT", "Finance", "Operations"}
ALLOWED_ROLES = {"Employee", "Support Staff", "Admin"}


def hash_password(password):
    """Hash a password securely."""

    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    return generate_password_hash(password)


def verify_password(password, stored_hash):
    """Verify a password against its stored hash."""

    try:
        return check_password_hash(stored_hash, password)
    except (ValueError, TypeError):
        return False


def register_employee(employee_id, password, role="Employee", department=None):
    """Register an ordinary employee account."""

    if not employee_id or not employee_id.strip():
        raise ValueError("Employee ID is required.")

    if role != "Employee":
        raise ValueError("Employees cannot assign themselves privileged roles.")

    if department not in DEPARTMENTS and department is not None:
        raise ValueError("Invalid department.")

    password_hash = hash_password(password)

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO employees (
                    employee_id, password_hash, role, department
                )
                VALUES (?, ?, ?, ?)
                """,
                (employee_id.strip(), password_hash, "Employee", department)
            )

        return True

    except sqlite3.IntegrityError:
        raise ValueError("This employee ID is already registered.")


def provision_employee_account(
    admin_id,
    employee_id,
    password,
    role,
    department=None
):
    """Allow an existing Admin to create privileged accounts."""

    if not admin_id or not admin_id.strip():
        raise ValueError("Admin ID is required.")

    if not employee_id or not employee_id.strip():
        raise ValueError("Employee ID is required.")

    if role not in ALLOWED_ROLES:
        raise ValueError("Invalid employee role.")

    if role == "Support Staff" and department not in DEPARTMENTS:
        raise ValueError("Support Staff must have a valid department.")

    if role != "Support Staff":
        department = None

    with get_connection() as connection:
        admin = connection.execute(
            """
            SELECT role, is_active
            FROM employees
            WHERE employee_id = ?
            """,
            (admin_id.strip(),)
        ).fetchone()

    if not admin or admin["role"] != "Admin" or not admin["is_active"]:
        raise PermissionError("Only an active Admin can create accounts.")

    password_hash = hash_password(password)

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO employees (
                    employee_id, password_hash, role, department
                )
                VALUES (?, ?, ?, ?)
                """,
                (employee_id.strip(), password_hash, role, department)
            )

        return True

    except sqlite3.IntegrityError:
        raise ValueError("This employee ID is already registered.")


def authenticate_employee(employee_id, password):
    """Verify credentials and return account details."""

    if not employee_id or not password:
        return None

    with get_connection() as connection:
        employee = connection.execute(
            """
            SELECT employee_id, password_hash, role,
                   department, email, is_active
            FROM employees
            WHERE employee_id = ?
            """,
            (employee_id.strip(),)
        ).fetchone()

    if employee is None or not employee["is_active"]:
        return None

    if not verify_password(password, employee["password_hash"]):
        return None

    return {
        "employee_id": employee["employee_id"],
        "role": employee["role"],
        "department": employee["department"],
        "email": employee["email"]
    }
