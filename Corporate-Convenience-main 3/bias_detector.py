
"""
Bias and response consistency detection for Corporate Convenience.
"""

from difflib import SequenceMatcher

from backend.bias_rules import (
    SIMILARITY_THRESHOLD,
    QUALITY_CHECKS,
    CREDENTIAL_RISK_PHRASES,
    UNSUPPORTED_CLAIM_PHRASES,
    RISK_WEIGHTS,
)


def calculate_similarity(text_a, text_b):
    """Calculate similarity between two ticket messages."""

    return SequenceMatcher(
        None,
        text_a.lower().strip(),
        text_b.lower().strip()
    ).ratio()


def assess_response_quality(response):
    """Check basic response quality indicators."""

    text = response.lower()

    acknowledgement = any(
        phrase in text
        for phrase in QUALITY_CHECKS["acknowledgement"]
    )

    next_step = any(
        phrase in text
        for phrase in QUALITY_CHECKS["next_step"]
    )

    return {
        "acknowledgement": acknowledgement,
        "next_step": next_step,
        "quality_score": int(acknowledgement) + int(next_step)
    }


def detect_response_risks(response):
    """Identify potentially unsafe or unsupported content."""

    text = response.lower()
    findings = []

    if any(phrase in text for phrase in CREDENTIAL_RISK_PHRASES):
        findings.append({
            "type": "credential_request",
            "risk_level": "HIGH",
            "message": "Response may request sensitive login credentials."
        })

    if any(phrase in text for phrase in UNSUPPORTED_CLAIM_PHRASES):
        findings.append({
            "type": "unsupported_claim",
            "risk_level": "HIGH",
            "message": "Response may make an unsupported promise or claim."
        })

    return findings


def compare_responses(ticket_a, ticket_b):
    """
    Compare responses to two similar tickets.

    Expected fields:
    employee_message, department, tone, draft_response
    """

    message_a = ticket_a.get("employee_message", "")
    message_b = ticket_b.get("employee_message", "")

    response_a = ticket_a.get("draft_response", "")
    response_b = ticket_b.get("draft_response", "")

    required_values = [
        message_a, message_b, response_a, response_b
    ]

    if not all(
        isinstance(value, str) and value.strip()
        for value in required_values
    ):
        raise ValueError(
            "Both tickets must contain messages and draft responses."
        )

    similarity = calculate_similarity(message_a, message_b)

    findings = []

    # Only compare responses when tickets are sufficiently similar.
    if similarity < SIMILARITY_THRESHOLD:
        return {
            "comparison_performed": False,
            "similarity": round(similarity, 2),
            "risk_count": 0,
            "risk_score": 0,
            "findings": [],
            "requires_human_review": False,
            "message": "Tickets are not similar enough to compare."
        }

    quality_a = assess_response_quality(response_a)
    quality_b = assess_response_quality(response_b)

    # Compare response quality.
    if quality_a["quality_score"] != quality_b["quality_score"]:
        findings.append({
            "type": "response_quality_difference",
            "risk_level": "MEDIUM",
            "message": (
                "Similar tickets received responses with "
                "different quality indicators."
            ),
            "ticket_a_score": quality_a["quality_score"],
            "ticket_b_score": quality_b["quality_score"]
        })

    # Flag similar tickets associated with different departments.
    if ticket_a.get("department") != ticket_b.get("department"):
        findings.append({
            "type": "department_difference",
            "risk_level": "MEDIUM",
            "message": (
                "Similar tickets are associated with different "
                "departments. Review whether the routing was appropriate."
            )
        })

    # Compare requested response tones.
    if ticket_a.get("tone") != ticket_b.get("tone"):
        findings.append({
            "type": "tone_inconsistency",
            "risk_level": "MEDIUM",
            "message": (
                "The tickets were assigned different response tones. "
                "Review whether this difference was intentional."
            )
        })

    # Check both responses for safety risks.
    for label, response in [
        ("ticket_a", response_a),
        ("ticket_b", response_b)
    ]:
        for risk in detect_response_risks(response):
            findings.append({
                **risk,
                "ticket": label
            })

    # Calculate an overall risk score.
    risk_score = sum(
        RISK_WEIGHTS.get(finding["type"], 0)
        for finding in findings
    )

    return {
        "comparison_performed": True,
        "similarity": round(similarity, 2),
        "department_a": ticket_a.get("department"),
        "department_b": ticket_b.get("department"),
        "quality_a": quality_a,
        "quality_b": quality_b,
        "risk_count": len(findings),
        "risk_score": risk_score,
        "findings": findings,
        "requires_human_review": bool(findings)
    }


# Test the bias detection module independently.
