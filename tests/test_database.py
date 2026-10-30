
from backend.database import save_ticket, get_ticket, get_all_tickets

# Test saving a ticket
ticket = save_ticket(
    "I cannot connect to Wi-Fi",
    "IT"
)

print("Saved ticket:")
print(ticket)

# Test retrieving that ticket
retrieved = get_ticket(ticket["ticket_id"])

print("\nRetrieved ticket:")
print(retrieved)

# Test retrieving all tickets
print("\nAll tickets:")
print(get_all_tickets())

# Basic checks
assert retrieved is not None
assert retrieved["message"] == "I cannot connect to Wi-Fi"
assert retrieved["department"] == "IT"
assert retrieved["status"] == "Open"

print("\nAll database tests passed!")
