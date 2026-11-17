
"""
Rules and thresholds for detecting potentially
inconsistent AI-generated support responses.
"""

# Existing departments in Corporate Convenience
DEPARTMENTS = ("IT", "HR", "Finance", "Operations")

# Existing response tones
ALLOWED_TONES = ("Formal", "Friendly", "Urgent")

# Minimum similarity required before comparing two tickets.
SIMILARITY_THRESHOLD = 0.75

# Response quality checks
QUALITY_CHECKS = {
    "acknowledgement": (
        "thank you",
        "received",
        "understand",
        "sorry to hear",
    ),
    "next_step": (
        "please provide",
        "please contact",
        "will review",
        "will investigate",
        "contact the",
        "support team",
    ),
}

# Responses must never encourage employees to share credentials.
CREDENTIAL_RISK_PHRASES = (
    "share your password",
    "send your password",
    "provide your password",
    "share your login credentials",
    "send your authentication code",
)

# Flag unsupported claims that require human review.
UNSUPPORTED_CLAIM_PHRASES = (
    "your issue has been resolved",
    "your request has been approved",
    "your salary will be paid",
    "payment will be made on",
)

# Risk levels used by the detector
RISK_LEVELS = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
}

# Risk points assigned to detected issues
RISK_WEIGHTS = {
    "missing_acknowledgement": 1,
    "missing_next_step": 1,
    "response_quality_difference": 2,
    "tone_inconsistency": 2,
    "department_difference": 1,
    "credential_request": 3,
    "unsupported_claim": 3,
}
