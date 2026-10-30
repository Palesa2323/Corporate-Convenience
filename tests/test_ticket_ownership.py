
from backend.database import save_employee_ticket, get_employee_tickets

# Create a test ticket for TEST001.
ticket = save_employee_ticket(
    message="I cannot access my company email.",
    department="IT",
    employee_id="TEST001"
)

print("Created ticket:")
print(ticket)

# Retrieve tickets belonging to TEST001.
employee_tickets = get_employee_tickets("TEST001")

print("\nTEST001 tickets:")
for item in employee_tickets:
    print(item)

# Confirm ownership.
assert ticket["employee_id"] == "TEST001"
assert any(
    item["ticket_id"] == ticket["ticket_id"]
    for item in employee_tickets
)

print("\nAll ticket ownership tests passed!")
