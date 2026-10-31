
import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from backend.classifier import predict_department


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GEMINI_MODEL = "gemini-3.8-flash"

logger = logging.getLogger(__name__)

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


# --------------------------------------------------
# GEMINI CONNECTION
# --------------------------------------------------

def get_gemini_client():
    """Create a Gemini client using the stored API key."""

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("Gemini API key was not found.")

    return genai.Client(api_key=api_key)



def generate_with_gemini(prompt):
    """Generate a response using Google's Gemini Interactions API."""

    client = get_gemini_client()

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=prompt,
        store=False
    )

    if not interaction.output_text:
        raise RuntimeError("Gemini returned an empty response.")

    return interaction.output_text.strip()


# --------------------------------------------------
# PRIORITY DETECTION
# --------------------------------------------------

def detect_priority(message):
    """Identify requests that need urgent attention."""

    text = message.lower()

    if any(phrase in text for phrase in URGENT_PHRASES):
        return "Urgent"

    return "Normal"


# --------------------------------------------------
# ISSUE TYPE DETECTION
# --------------------------------------------------

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


# --------------------------------------------------
# GEMINI RESPONSE GENERATION
# --------------------------------------------------

def generate_ai_response(
    message,
    department,
    issue_type,
    tone="Formal",
    priority="Normal"
):
    """
    Generate a professional workplace response using Gemini.
    """

    tone_instructions = {
        "Formal": (
            "Use professional, respectful and clear business language."
        ),
        "Friendly": (
            "Use a warm, approachable and helpful tone while remaining "
            "professional."
        ),
        "Urgent": (
            "Use concise, direct language that communicates the need "
            "for prompt attention without creating unnecessary panic."
        )
    }

    tone_instruction = tone_instructions.get(
        tone,
        tone_instructions["Formal"]
    )

    if priority == "Urgent":
        safety_instruction = """
        IMPORTANT SAFETY REQUIREMENTS:

        This ticket has been flagged as urgent.

        If it concerns a possible cybersecurity incident:
        - Tell the employee not to continue using the potentially
          compromised device.
        - Tell them not to restart or troubleshoot that device.
        - Direct them to contact IT Support through an approved
          alternative device or communication channel.
        - Never ask the employee to share their password.
        - Do not claim that the security issue has been resolved.

        Make it clear that a human support agent must review the case.
        """
    else:
        safety_instruction = """
        No special urgent safety instruction has been triggered.
        """

    prompt = f"""
    You are the AI communication assistant for Corporate Convenience,
    an internal workplace ticket management system.

    Your responsibility is to draft a helpful response to an employee
    who has submitted a workplace support request.

    TICKET INFORMATION:

    Employee message:
    {message}

    Responsible department:
    {department}

    Issue type:
    {issue_type}

    Priority:
    {priority}

    Required response tone:
    {tone}

    TONE INSTRUCTIONS:
    {tone_instruction}

    RESPONSE REQUIREMENTS:

    1. Respond directly to the employee's actual concern.
    2. Acknowledge the issue and explain the appropriate next step.
    3. Ask for relevant missing information only when necessary.
    4. Keep the response clear, concise and professional.
    5. Make the response specific to the responsible department.
    6. Do not simply repeat the employee's message.
    7. Do not invent company policies, procedures, deadlines,
       payment dates or contact details.
    8. Do not claim that a ticket has been resolved or approved.
    9. Never request passwords, authentication codes or private
       login credentials.
    10. Do not provide unsupported legal, financial or HR advice.
    11. Return only the response intended for the employee.
    12. Do not include analysis, headings or explanations about AI.

    {safety_instruction}

    Generate the employee-facing response now.
    """

    return generate_with_gemini(prompt)


# --------------------------------------------------
# FALLBACK RESPONSE TEMPLATES
# --------------------------------------------------

def generate_response(message, department, tone="Formal",
                      priority="Normal"):
    """
    Generate a Gemini response, falling back to existing templates
    if the Gemini service is unavailable.
    """

    issue_type = detect_issue_type(message, department)

    # Try actual Generative AI first.
    try:
        return generate_ai_response(
            message=message,
            department=department,
            issue_type=issue_type,
            tone=tone,
            priority=priority
        )

    except Exception as error:
        logger.warning(
            "Gemini response generation failed. "
            "Using fallback templates. Error: %s",
            error
        )

    # Existing template-based fallback.
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


# --------------------------------------------------
# MAIN TICKET ANALYSIS
# --------------------------------------------------

def analyse_message(message, tone="Formal"):
    """Classify an employee request and generate a draft response."""

    if not isinstance(message, str) or not message.strip():
        raise ValueError("Please enter an employee support message.")

    allowed_tones = {"Formal", "Friendly", "Urgent"}

    if tone not in allowed_tones:
        raise ValueError(
            "Tone must be Formal, Friendly or Urgent."
        )

    message = message.strip()

    department = predict_department(message)
    priority = detect_priority(message)

    if priority == "Urgent":
        department = "IT"

    issue_type = detect_issue_type(message, department)

    draft_response = generate_response(
        message=message,
        department=department,
        tone=tone,
        priority=priority
    )

    return {
        "employee_message": message,
        "predicted_department": department,
        "issue_type": issue_type,
        "priority": priority,
        "tone": tone,
        "draft_response": draft_response,
        "requires_human_review": priority == "Urgent",
    }


# --------------------------------------------------
# FOLLOW-UP RESPONSE GENERATION
# --------------------------------------------------

def generate_follow_up(previous_message, new_message, department,
                       tone="Formal"):
    """Generate a context-aware Gemini follow-up response."""

    if not isinstance(new_message, str) or not new_message.strip():
        raise ValueError("Please enter a follow-up message.")

    if not isinstance(previous_message, str):
        raise ValueError("The original message is required.")

    if department not in {"HR", "IT", "Finance", "Operations"}:
        raise ValueError("Invalid support department.")

    if tone not in {"Formal", "Friendly", "Urgent"}:
        raise ValueError(
            "Tone must be Formal, Friendly or Urgent."
        )

    previous_message = previous_message.strip()
    new_message = new_message.strip()

    priority = detect_priority(previous_message)

    if department == "IT" and priority == "Urgent":
        safety_context = """
        This is an ongoing urgent IT security-related case.

        Maintain the original safety instruction.
        Do not advise the employee to restart or troubleshoot
        a potentially compromised device.
        Direct them to approved alternative IT communication channels.
        A human support agent must review the case.
        """
    else:
        safety_context = """
        Continue assisting with the original workplace support issue.
        Do not claim that the issue has been resolved.
        """

    prompt = f"""
    You are the AI communication assistant for Corporate Convenience.

    An employee has sent a follow-up to an existing support ticket.

    Original employee message:
    {previous_message}

    New follow-up message:
    {new_message}

    Responsible department:
    {department}

    Required tone:
    {tone}

    Respond to the employee's latest message while considering
    the original conversation.

    Requirements:
    - Acknowledge the new information.
    - Maintain context from the original request.
    - Provide a useful next step.
    - Do not invent company policies or procedures.
    - Do not claim that the ticket is resolved.
    - Never request passwords or authentication codes.
    - Keep the response concise and professional.
    - Return only the employee-facing response.

    {safety_context}
    """

    try:
        return generate_with_gemini(prompt)

    except Exception as error:
        logger.warning(
            "Gemini follow-up generation failed. "
            "Using fallback response. Error: %s",
            error
        )

    # Preserve the existing urgent IT fallback.
    if department == "IT" and priority == "Urgent":

        if any(word in new_message.lower() for word in [
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


# --------------------------------------------------
# LOCAL TESTING
# --------------------------------------------------

if __name__ == "__main__":

    message = input("Enter an employee support message: ")

    print("\nChoose response tone:")
    print("1. Formal")
    print("2. Friendly")
    print("3. Urgent")

    choice = input("Enter choice (1-3): ")

    tones = {
        "1": "Formal",
        "2": "Friendly",
        "3": "Urgent"
    }

    selected_tone = tones.get(choice, "Formal")

    try:
        result = analyse_message(message, selected_tone)

        print("\n--- TICKET ANALYSIS ---")

        for key, value in result.items():
            print(f"{key}: {value}")

    except Exception as error:
        print(f"\nError: {error}")
