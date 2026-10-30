
from authy import register_employee, authenticate_employee

# Create a test employee
try:
    register_employee(
        employee_id="TEST001",
        password="TestPassword123!",
        role="Employee"
    )
    print("Employee registered successfully.")

except ValueError as error:
    print(error)

# Test correct login
employee = authenticate_employee(
    "TEST001",
    "TestPassword123!"
)

print("\nCorrect password:", employee)

# Test incorrect login
wrong_login = authenticate_employee(
    "TEST001",
    "WrongPassword"
)

print("\nIncorrect password:", wrong_login)

assert employee is not None
assert employee["role"] == "Employee"
assert wrong_login is None

print("\nAll authentication tests passed!")
