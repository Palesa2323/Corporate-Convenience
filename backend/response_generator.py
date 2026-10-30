

from backend.classifier import predict_department


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
    """Identify requests that need urgent attention."""
    text = message.lower()

    if any(phrase in text for phrase in URGENT_PHRASES):
        return "Urgent"

    return "Normal"


def detect_issue_type(message, department):
    """Identify the specific type of employee request."""
    text = message.lower()

    if department == "Finance":
        if any(word in text for word in [
            "salary", "payslip", "pay slip", "payroll",
            "wages", "overtime", "bonus", "salary payment"
        ]):
            return "Salary and Payroll"

        if any(word in text for word in [
            "invoice", "supplier", "vendor"
        ]):
            return "Supplier Payment"

        if any(word in text for word in [
            "expense", "reimbursement", "expense claim"
        ]):
            return "Expense Claim"

        if any(word in text for word in [
            "tax", "deduction"
        ]):
            return "Tax and Deductions"

    elif department == "HR":
        if any(word in text for word in [
            "annual leave", "sick leave", "maternity leave",
            "parental leave", "family responsibility leave"
        ]):
            return "Leave Request"

        if any(word in text for word in [
            "contract", "employment letter", "reference letter"
        ]):
            return "Employment Documents"

        if any(word in text for word in [
            "benefits", "wellness", "employee benefits"
        ]):
            return "Employee Benefits"

    elif department == "IT":
        if any(word in text for word in [
            "password", "login", "log in", "account locked"
        ]):
            return "Account Access"

        if any(word in text for word in [
            "email", "outlook"
        ]):
            return "Email Support"

        if any(word in text for word in [
            "wifi", "wi-fi", "internet", "network", "vpn"
        ]):
            return "Network Support"

        if any(word in text for word in [
            "laptop", "computer", "keyboard", "monitor", "printer"
        ]):
            return "Computer and Hardware"

    elif department == "Operations":
        if any(word in text for word in [
            "air conditioner", "air conditioning", "lights",
            "leak", "lift", "generator"
        ]):
            return "Office Maintenance"

        if any(word in text for word in [
            "stationery", "office supplies", "chairs",
            "utensils", "paper"
        ]):
            return "Office Supplies"

        if any(word in text for word in [
            "meeting room", "book a room", "workshop"
        ]):
            return "Meeting Room Support"

    return "General Request"


def generate_response(message, department, tone="Formal",
                      priority="Normal"):
    """Generate a department-specific draft response."""

    if priority == "Urgent":
        return (
            "Urgent IT Support Notice: Please follow the instruction "
            "not to use your laptop or computer. Do not attempt to "
            "troubleshoot or restart the device. Contact IT Support "
            "through an approved alternative channel. A human support "
            "agent must review this case. Please confirm whether IT "
            "Support gave you this instruction or whether you saw "
            "a security warning."
        )

    issue_type = detect_issue_type(message, department)

    responses = {
        "Finance": {
            "Salary and Payroll": (
                "Thank you for contacting the Finance Department. "
                "Your salary or payslip query has been received. "
                "The Finance team will need to review the payroll "
                "and payment records. Please provide the relevant "
                "pay period and any supporting information through "
                "the approved company channel."
            ),
            "Supplier Payment": (
                "Thank you for contacting Finance. Your supplier "
                "payment query has been received. The team will "
                "review the invoice and payment status. Please "
                "provide the supplier name and invoice reference."
            ),
            "Expense Claim": (
                "Thank you for contacting Finance. Your expense "
                "claim query has been received. Please provide "
                "the expense reference and supporting receipts "
                "so the team can review your submission."
            ),
            "Tax and Deductions": (
                "Thank you for contacting Finance. Your tax or "
                "deduction query has been received. The team will "
                "review the relevant financial records and provide "
                "feedback."
            ),
        },

        "HR": {
            "Leave Request": (
                "Thank you for contacting HR. Your leave-related "
                "query has been received. The HR team will review "
                "your leave request and the applicable company "
                "leave policy. Please provide your requested dates "
                "if you have not already done so."
            ),
            "Employment Documents": (
                "Thank you for contacting HR. Your employment "
                "document request has been received. The team will "
                "review your request and advise you on the required "
                "documentation."
            ),
            "Employee Benefits": (
                "Thank you for contacting HR. Your employee "
                "benefits query has been received. The HR team "
                "will review the relevant benefits information "
                "and provide guidance."
            ),
        },

        "IT": {
            "Account Access": (
                "Thank you for contacting IT Support. Your account "
                "access issue has been received. The technical "
                "team will review the problem. Please provide the "
                "system or application affected and any error "
                "message displayed. Do not share your password."
            ),
            "Email Support": (
                "Thank you for contacting IT Support. Your email "
                "issue has been received. Please provide the error "
                "message and indicate whether the problem affects "
                "sending, receiving or accessing emails."
            ),
            "Network Support": (
                "Thank you for contacting IT Support. Your network "
                "connection issue has been received. Please indicate "
                "whether the issue affects Wi-Fi, internet or VPN "
                "access and provide any error message."
            ),
            "Computer and Hardware": (
                "Thank you for contacting IT Support. Your computer "
                "or hardware issue has been received. Please provide "
                "the device type and explain when the problem started."
            ),
        },

        "Operations": {
            "Office Maintenance": (
                "Thank you for contacting Operations. Your office "
                "maintenance issue has been received. The team will "
                "review the problem and arrange the appropriate "
                "maintenance support. Please provide the office "
                "location."
            ),
            "Office Supplies": (
                "Thank you for contacting Operations. Your office "
                "supplies request has been received. The team will "
                "review the request and advise on availability "
                "and delivery arrangements."
            ),
            "Meeting Room Support": (
                "Thank you for contacting Operations. Your meeting "
                "room request has been received. Please provide "
                "the preferred date, time and number of attendees "
                "so the team can assist."
            ),
        },
    }

    reply = responses.get(department, {}).get(issue_type)

    if reply is None:
        general_responses = {
            "Finance": (
                "Thank you for contacting Finance. Your financial "
                "query has been received and will be reviewed."
            ),
            "HR": (
                "Thank you for contacting HR. Your employee-related "
                "query has been received and will be reviewed."
            ),
            "IT": (
                "Thank you for contacting IT Support. Your technical "
                "query has been received and will be reviewed."
            ),
            "Operations": (
                "Thank you for contacting Operations. Your workplace "
                "request has been received and will be reviewed."
            ),
        }

        reply = general_responses.get(
            department,
            "Thank you for contacting Corporate Convenience. "
            "Your request has been received for review."
        )

    if tone == "Friendly":
        reply = "Hi! " + reply

    elif tone == "Urgent":
        reply = "Priority support request: " + reply

    return reply


def analyse_message(message, tone="Formal"):
    """Classify an employee request and generate a draft response."""

    if not isinstance(message, str) or not message.strip():
        raise ValueError("Please enter an employee support message.")

    message = message.strip()

    department = predict_department(message)
    priority = detect_priority(message)

    if priority == "Urgent":
        department = "IT"

    issue_type = detect_issue_type(message, department)

    return {
        "employee_message": message,
        "predicted_department": department,
        "issue_type": issue_type,
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

    if not isinstance(new_message, str) or not new_message.strip():
        raise ValueError("Please enter a follow-up message.")

    if not isinstance(previous_message, str):
        raise ValueError("The original message is required.")

    follow_up = new_message.strip().lower()

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
            "Thank you for the update. Your original laptop or "
            "security issue remains flagged for urgent IT review. "
            "Please follow the safety instruction and wait for "
            "IT Support guidance."
        )

    return (
        f"Thank you for your follow-up regarding: "
        f"'{previous_message}'. Your additional message has been "
        f"noted for {department} support. A support agent can "
        f"assist with your additional details."
    )


if __name__ == "__main__":
    message = input("Enter an employee support message: ")
    result = analyse_message(message)

    for key, value in result.items():
        print(f"{key}: {value}")
