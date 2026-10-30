
from backend.response_generator import analyse_message
from backend.database import save_employee_ticket


def submit_ticket(message, employee_id, tone="Formal"):
    """Analyse a workplace request and save it as an employee ticket."""

    if not message or not message.strip():
        raise ValueError("Ticket message cannot be empty.")

    if not employee_id or not employee_id.strip():
        raise ValueError("Employee ID is required.")

    # Analyse the employee's message using the AI modules.
    analysis = analyse_message(message, tone=tone)

    # Save the classified ticket under the employee's account.
    ticket = save_employee_ticket(
        message=message,
        department=analysis["predicted_department"],
        employee_id=employee_id
    )

    return {
        "ticket": ticket,
        "analysis": analysis
    }
