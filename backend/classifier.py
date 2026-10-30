

from functools import lru_cache
from pathlib import Path

import joblib

# Locate the trained model relative to this file.
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR.parent / "models" / "model.joblib"


# Clear department-specific phrases.
# These rules handle requests with an unambiguous business meaning.
DEPARTMENT_RULES = {
    "Finance": [
        "salary",
        "payslip",
        "pay slip",
        "payroll",
        "wages",
        "overtime payment",
        "salary deduction",
        "tax deduction",
        "bonus payment",
        "missing salary",
        "salary payment",
    ],
    "HR": [
        "annual leave",
        "sick leave",
        "maternity leave",
        "parental leave",
        "employment contract",
        "employee benefits",
        "probation period",
        "employee records",
        "workplace conduct",
        "employment reference",
        "staff wellness",
    ],
    "IT": [
        "computer password",
        "reset my password",
        "company email",
        "laptop",
        "wifi",
        "wi-fi",
        "vpn",
        "network error",
        "computer freezing",
        "software installation",
        "multi-factor authentication",
        "account locked",
    ],
    "Operations": [
        "air conditioner",
        "office lights",
        "office cleaning",
        "office supplies",
        "meeting room",
        "broken office door",
        "office furniture",
        "water dispenser",
        "office generator",
        "building maintenance",
    ],
}


@lru_cache(maxsize=1)
def load_model():
    """Load the trained classification model once."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found at: {MODEL_PATH}. "
            "Run train_model.py first."
        )

    return joblib.load(MODEL_PATH)


def rule_based_prediction(message: str):
    """Check for clear department-specific keywords."""
    text = message.lower()

    for department, phrases in DEPARTMENT_RULES.items():
        if any(phrase in text for phrase in phrases):
            return department

    return None


def predict_department(message: str) -> str:
    """
    Use clear business rules first.
    If no rule matches, use the trained ML model.
    """
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Please enter a workplace request.")

    message = message.strip()

    # Step 1: Check explicit department rules.
    rule_prediction = rule_based_prediction(message)

    if rule_prediction:
        return rule_prediction

    # Step 2: Use machine learning for other requests.
    model = load_model()
    prediction = model.predict([message])

    return str(prediction[0])
