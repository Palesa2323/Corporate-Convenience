
from classifier import predict_department


URGENT_PHRASES = [
    "do not use your laptop",
    "don't use your laptop",
    "do not use your computer",
    "stop using your laptop",
    "security warning",
    "suspicious activity",
    "account compromised",
    "possible virus",
    "hacked",
]


def detect_priority(message):
    text = message.lower()
    return (
        "Urgent"
        if any(phrase in text for phrase in URGENT_PHRASES)
        else "Normal"
    )


def generate_response(message, department, tone="Formal",
                      priority="Normal"):
    if priority == "Urgent":
        return (
            "Urgent IT Support Notice: Please follow the instruction "
            "not to use your laptop. Do not attempt to troubleshoot "
            "or restart it. Contact IT Support through an approved "
            "alternative channel. A human support agent should review "
            "this case. Did IT Support give you this instruction, "
            "or did you see a warning message?"
        )

    replies = {
        "IT": "Thank you for contacting IT Support. Please describe the technical issue.",
        "HR": "Thank you for contacting HR. Please explain your employee-related query.",
        "Finance": "Thank you for contacting Finance. Please describe your payment or expense query.",
        "Operations": "Thank you for contacting Operations. Please describe the workplace issue.",
    }

    reply = replies.get(
        department,
        "Thank you for contacting Corporate Convenience. Your request needs review."
    )

    if tone == "Friendly":
        reply = "Hi! " + reply
    elif tone == "Urgent":
        reply = "Priority support request: " + reply

    return reply


def analyse_message(message, tone="Formal"):
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Please enter an employee support message.")

    message = message.strip()
    department = predict_department(message)
    priority = detect_priority(message)

    # Route the known laptop/security phrases to IT for review.
    if priority == "Urgent":
        department = "IT"

    return {
        "employee_message": message,
        "predicted_department": department,
        "priority": priority,
        "tone": tone,
        "draft_response": generate_response(
            message, department, tone, priority
        ),
        "requires_human_review": priority == "Urgent",
    }

def generate_follow_up(previous_message, new_message, department,
                       tone="Formal"):
    """Generate a template-based reply using conversation context."""

    if not new_message or not new_message.strip():
        raise ValueError("Please enter a follow-up message.")

    follow_up = new_message.strip().lower()

    # Keep the original issue in context for laptop/security cases.
    if department == "IT" and any(
        phrase in previous_message.lower()
        for phrase in URGENT_PHRASES
    ):
        if any(word in follow_up for word in [
            "who", "contact", "call", "help", "where"
        ]):
            return (
                "Please contact your organisation's IT Support team "
                "through an approved alternative device or channel. "
                "Continue following the original safety instruction "
                "and wait for IT guidance."
            )

        return (
            "Thank you for the update. Your original laptop/security "
            "issue remains flagged for urgent IT review. Please follow "
            "the safety instruction and wait for IT Support guidance."
        )

    return (
        f"Thank you for your follow-up regarding: "
        f"'{previous_message}'. Your message has been noted for "
        f"{department} support. A support agent can assist with "
        f"your additional details."
    )


if __name__ == "__main__":
    message = input("Enter an employee support message: ")
    result = analyse_message(message)

    for key, value in result.items():
        print(f"{key}: {value}")
