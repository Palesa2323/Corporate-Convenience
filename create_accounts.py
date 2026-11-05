"""
Create one TEST account of every type, all with the same password.

Run once from the project root:

    python create_test_accounts.py

Accounts that already exist are skipped, so it is safe to run again.
Change these passwords before real people use the system.
"""

from backend.database import _insert_employee

PASSWORD = "Test12345"

# (employee ID, role, department)
ACCOUNTS = [
    ("ADMIN001", "Admin",         None),
    ("IT001",    "Support Staff", "IT"),
    ("FIN001",   "Support Staff", "Finance"),
    ("HR001",    "Support Staff", "HR"),
    ("OPS001",   "Support Staff", "Operations"),
    ("EMP100",   "Employee",      None),
]

print(f"Creating test accounts (password: {PASSWORD})\n")

for employee_id, role, department in ACCOUNTS:
    label = department if role == "Support Staff" else role

    try:
        _insert_employee(employee_id, PASSWORD, role, department)
        print(f"  created   {employee_id:<9} {label}")
    except ValueError as error:
        print(f"  skipped   {employee_id:<9} {label}  ({error})")

print("\nDone. Sign in with any ID above and the password shown.")