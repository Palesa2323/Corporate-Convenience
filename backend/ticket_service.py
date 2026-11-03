from backend.response_generator import (
    analyse_message,
    generate_acknowledgement
)
from backend.database import save_employee_ticket


def submit_ticket(message, employee_id, tone="Formal"):
    """Analyse a complaint, save the ticket and prepare acknowledgement."""

    if not isinstance(message, str) or not message.strip():
        raise ValueError("Ticket message cannot be empty.")

    if not isinstance(employee_id, str) or not employee_id.strip():
        raise ValueError("Employee ID is required.")

    # Analyse the employee's complaint.
    analysis = analyse_message(message, tone=tone)

    # Save the ticket with its department and priority.
    ticket = save_employee_ticket(
        message=message.strip(),
        department=analysis["predicted_department"],
        employee_id=employee_id.strip(),
        priority=analysis["priority"]
    )

    # Get the ticket reference number.
    ticket_id = ticket.get("ticket_id")

    analysis["acknowledgement"] = generate_acknowledgement(
    analysis["predicted_department"],
    analysis["priority"]
)
    analysis["acknowledgement"] += (
    f"\n\nYour ticket reference number is {ticket_id}."
)

    return {
        "ticket": ticket,
        "analysis": analysis
    }

