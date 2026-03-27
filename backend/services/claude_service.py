"""
Rights service for AMANDLA.
Generates SA disability rights complaint letters and incident analyses.

Uses Gemini as the primary AI engine.
Falls back to heuristic analysis and a template letter when Gemini is unavailable.
"""
import logging

logger = logging.getLogger(__name__)


async def analyse_incident(description: str, incident_type: str = "workplace") -> dict:
    """
    Extracts key facts from an incident description.
    Returns dict with what_happened, location, severity, laws_likely_violated.
    Fallback chain: Gemini → heuristic.
    """
    try:
        from backend.services.gemini_service import analyse_incident as gemini_analyse
        result = await gemini_analyse(description, incident_type)
        if result is not None:
            return result
    except Exception as e:
        logger.warning(f"[Gemini] analyse_incident failed: {e}")

    return _heuristic_analysis(description, incident_type)


async def generate_rights_letter(
    incident_description: str,
    user_name: str,
    employer_name: str,
    incident_date: str,
    analysis: dict = None
) -> dict:
    """
    Generates a formal SA disability rights complaint letter.
    Falls back to a template if Gemini is unavailable.
    """
    try:
        from backend.services.gemini_service import generate_rights_letter as gemini_letter
        result = await gemini_letter(
            incident_description=incident_description,
            user_name=user_name,
            employer_name=employer_name,
            incident_date=incident_date,
            analysis=analysis,
        )
        if result is not None:
            return result
    except Exception as e:
        logger.warning(f"[Gemini] generate_rights_letter failed: {e}")

    # Final fallback: template
    letter = _template_letter(incident_description, user_name, employer_name, incident_date)
    return {"letter": letter, "laws_cited": _default_laws(), "model": "template"}


# ── OFFLINE FALLBACKS ──────────────────────────────────────

def _heuristic_analysis(description: str, incident_type: str) -> dict:
    """Simple keyword-based rights analysis when Gemini is unavailable."""
    desc_lower = description.lower()
    laws = []

    if any(w in desc_lower for w in ['work', 'job', 'employ', 'fired', 'dismiss', 'boss', 'manager', 'colleague']):
        laws += ["Employment Equity Act s.6", "Labour Relations Act s.191"]
    if any(w in desc_lower for w in ['shop', 'store', 'restaurant', 'public', 'service', 'access', 'ramp', 'lift', 'elevator']):
        laws += ["Promotion of Equality Act s.7"]
    if any(w in desc_lower for w in ['school', 'university', 'college', 'education', 'class']):
        laws += ["Promotion of Equality Act s.7", "South African Schools Act"]
    if any(w in desc_lower for w in ['hospital', 'clinic', 'doctor', 'nurse', 'health', 'medical']):
        laws += ["National Health Act s.6", "Promotion of Equality Act s.7"]

    if not laws:
        laws = _default_laws()

    if "Constitution s.9(3)" not in laws:
        laws.append("Constitution s.9(3)")

    severity = "serious"
    if any(w in desc_lower for w in ['fired', 'dismissed', 'assault', 'attack', 'emergency', 'denied access']):
        severity = "serious"
    elif any(w in desc_lower for w in ['rude', 'ignored', 'minor', 'small']):
        severity = "moderate"

    summary = description[:150] + ("…" if len(description) > 150 else "")

    return {
        "what_happened": summary,
        "location": incident_type,
        "severity": severity,
        "laws_likely_violated": list(dict.fromkeys(laws))
    }


def _default_laws() -> list:
    return ["Employment Equity Act s.6", "Constitution s.9(3)"]


def _template_letter(description: str, user_name: str, employer_name: str, incident_date: str) -> str:
    """Generates a template letter without AI when no API key is available."""
    from datetime import date
    import random
    today = date.today().isoformat()
    ref = f"AMANDLA-RIGHTS-{date.today().year}-{random.randint(100, 999)}"

    return f"""{today}

[YOUR ADDRESS]
[CITY, PROVINCE, POSTAL CODE]
[EMAIL ADDRESS]

{employer_name}
[ORGANISATION ADDRESS]
[CITY, PROVINCE, POSTAL CODE]

Reference: {ref}

Dear Sir/Madam,

RE: FORMAL COMPLAINT OF UNFAIR DISCRIMINATION AGAINST A PERSON WITH A DISABILITY

I, {user_name}, hereby lodge a formal complaint of unfair discrimination in terms of the following legislation:

1. The Employment Equity Act, No. 55 of 1998, Section 6, which prohibits unfair discrimination on the basis of disability.
2. The Promotion of Equality and Prevention of Unfair Discrimination Act, No. 4 of 2000 (PEPUDA), Section 7.
3. The Constitution of the Republic of South Africa, Section 9(3), which guarantees the right to equality and prohibits discrimination on the grounds of disability.

On or about {incident_date}, the following incident occurred:

{description}

This conduct constitutes unfair discrimination in terms of the above-mentioned legislation. As a person with a disability, I have a constitutional and statutory right to be treated with dignity and to have equal access to facilities and services.

DEMANDS:
1. A written apology acknowledging the discriminatory conduct within 7 (seven) days.
2. Confirmation in writing of the corrective steps taken to prevent recurrence.
3. Full compliance with all applicable disability rights legislation.

I request your written response within 14 (fourteen) days of receipt of this letter. Should I not receive a satisfactory response within this period, I reserve the right to refer the matter to:
- The Commission for Conciliation, Mediation and Arbitration (CCMA)
- The South African Human Rights Commission (SAHRC)
- The Equality Court in terms of PEPUDA

Yours faithfully,

{user_name}
[SIGNATURE]
{today}

---
Generated by AMANDLA — South African Sign Language Communication Bridge
Reference: {ref}"""