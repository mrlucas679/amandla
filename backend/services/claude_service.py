"""
Rights service for AMANDLA.
Generates SA disability rights complaint letters and incident analyses.

Uses local Ollama model as the primary AI engine.
Falls back to heuristic analysis and a template letter when Ollama is unavailable.
No cloud API keys needed — everything runs locally.
"""
import os
import re
import json
import logging
import functools
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _get_ollama_config() -> Tuple[str, str]:
    """Return (base_url, model_name) from environment variables.

    Result is cached after first call so os.getenv() is only called once.
    dotenv is loaded by backend.main at startup before this is ever called.

    Returns:
        Tuple of (base_url, model_name) — both are guaranteed non-empty strings.
    """
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model: str = os.getenv("OLLAMA_MODEL", "amandla")
    return base_url, model


# ── System prompt for SA disability rights analysis ────────
_RIGHTS_SYSTEM = """You are a South African disability rights legal assistant.
When a disabled person reports discrimination, you must:
1. Identify what happened and which rights were violated
2. Map the incident to specific South African laws
3. Use formal South African legal language

Key laws:
- Employment Equity Act No. 55 of 1998, s.6
- Promotion of Equality and Prevention of Unfair Discrimination Act No. 4 of 2000 (PEPUDA), s.7
- Constitution of the Republic of South Africa, s.9(3)
- Labour Relations Act No. 66 of 1995, s.191
- National Health Act No. 61 of 2003, s.6
- South African Schools Act No. 84 of 1996

Always cite exact section numbers."""


async def _call_ollama(
    prompt: str,
    max_tokens: int = 1500,
    system: Optional[str] = None,
) -> Optional[str]:
    """Send a prompt to the local Ollama model and return the response text.

    Args:
        prompt: The user prompt string to send.
        max_tokens: Maximum number of tokens in the response.
        system: Optional system prompt that overrides the Modelfile default.
            Pass _RIGHTS_SYSTEM here so the Modelfile's landmark-recognition
            system prompt does not interfere with rights analysis calls.

    Returns:
        The response text string, or None if Ollama is unreachable.
    """
    try:
        base_url, model_name = _get_ollama_config()
        # Build request body. Always include the rights system prompt so the
        # Modelfile's landmark-recognition default never leaks into rights calls.
        request_body: dict = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.2,
            "num_predict": max_tokens,
        }
        if system:
            request_body["system"] = system

        from backend.services.ollama_pool import get_client
        client = get_client()
        response = await client.post(
            f"{base_url}/api/generate",
            json=request_body,
            timeout=30.0,
        )
        if response.status_code != 200:
            logger.warning(f"[Rights] Ollama returned status {response.status_code}")
            return None
        text = response.json().get("response", "").strip()
        if text:
            return text
        return None
    except Exception as e:
        logger.warning(f"[Rights] Ollama request failed: {e}")
        return None


async def analyse_incident(description: str, incident_type: str = "workplace") -> dict:
    """
    Extracts key facts from an incident description.

    Fallback chain: Ollama (local AI) → heuristic (keyword-based).

    Args:
        description: What the user says happened to them.
        incident_type: Context like "workplace", "hospital", etc.

    Returns:
        Dict with what_happened, location, severity, laws_likely_violated.
    """
    # Try Ollama first
    prompt = f"""Analyse this South African disability discrimination incident and return ONLY a JSON object.

Incident type: {incident_type}
Description: {description}

Return this exact JSON structure (no markdown, no code fences, just the JSON):
{{"what_happened": "one clear sentence", "location": "setting or context", "severity": "minor OR moderate OR serious", "laws_likely_violated": ["specific law and section"]}}

Severity guide: serious = job loss / physical harm / denied emergency care; moderate = ongoing harassment / denied accommodation; minor = isolated rude incident.
Always include Constitution s.9(3)."""

    try:
        raw_response = await _call_ollama(prompt, max_tokens=500, system=_RIGHTS_SYSTEM)
        if raw_response:
            # Strip markdown code fences if Ollama wraps its output
            cleaned = re.sub(r"^```[a-z]*\n?", "", raw_response)
            cleaned = re.sub(r"\n?```$", "", cleaned).strip()
            result = json.loads(cleaned)
            logger.info(f"[Rights] Ollama analysis — severity: {result.get('severity')}")
            return result
    except (json.JSONDecodeError, KeyError) as parse_error:
        logger.warning(f"[Rights] Ollama response not valid JSON: {parse_error}")
    except Exception as e:
        logger.warning(f"[Rights] Ollama analyse_incident failed: {e}")

    # Fallback: keyword-based heuristic (always works offline)
    return _heuristic_analysis(description, incident_type)


async def generate_rights_letter(
    incident_description: str,
    user_name: str,
    employer_name: str,
    incident_date: str,
    analysis: Optional[dict] = None
) -> dict:
    """
    Generates a formal SA disability rights complaint letter.

    Fallback chain: Ollama (local AI) → template (always works offline).

    Args:
        incident_description: What happened.
        user_name: Name of the complainant.
        employer_name: Name of the respondent.
        incident_date: Date the incident occurred.
        analysis: Optional dict from analyse_incident().

    Returns:
        Dict with 'letter' (full text), 'laws_cited' (list), 'model' (string).
    """
    from datetime import date
    import random
    ref = f"AMANDLA-RIGHTS-{date.today().year}-{random.randint(100, 999)}"

    laws_context = ""
    if analysis and analysis.get("laws_likely_violated"):
        laws_context = f"\nLaws already identified: {', '.join(analysis['laws_likely_violated'])}"

    prompt = f"""Write a complete, formal South African disability rights complaint letter.

Complainant: {user_name}
Respondent: {employer_name}
Date of incident: {incident_date}
Reference number: {ref}{laws_context}

Incident: {incident_description}

Requirements:
- Today's date at the top
- Address blocks with placeholders like [YOUR ADDRESS]
- The reference number above
- Formal salutation
- Opening paragraph with purpose and legal basis
- Factual paragraph describing what happened
- Legal paragraph citing SPECIFIC SA laws and section numbers
- Demands: written apology within 7 days, corrective steps
- Consequences: CCMA referral, SAHRC complaint, Equality Court
- Professional closing and signature block

Write ONLY the letter — no commentary."""

    try:
        raw_letter = await _call_ollama(prompt, max_tokens=1500, system=_RIGHTS_SYSTEM)
        if raw_letter and len(raw_letter) > 100:
            # Extract which laws were cited in the letter
            laws_cited = _extract_laws_from_text(raw_letter)
            _, model_name = _get_ollama_config()
            logger.info(f"[Rights] Ollama letter generated. Laws cited: {laws_cited}")
            return {
                "letter": raw_letter,
                "laws_cited": laws_cited,
                "model": f"ollama/{model_name}",
            }
    except Exception as e:
        logger.warning(f"[Rights] Ollama generate_rights_letter failed: {e}")

    # Fallback: template letter (always works offline)
    letter = _template_letter(incident_description, user_name, employer_name, incident_date)
    return {"letter": letter, "laws_cited": _default_laws(), "model": "template"}


def _extract_laws_from_text(text: str) -> list:
    """Scan a letter for known SA law references and return a list.

    Args:
        text: The full letter text to scan.

    Returns:
        List of law citation strings found in the text.
    """
    laws_cited = []
    if "Employment Equity" in text:
        laws_cited.append("Employment Equity Act s.6")
    if "Promotion of Equality" in text or "PEPUDA" in text:
        laws_cited.append("Promotion of Equality Act s.7")
    if "Constitution" in text or "s.9(3)" in text:
        laws_cited.append("Constitution s.9(3)")
    if "Labour Relations" in text:
        laws_cited.append("Labour Relations Act s.191")
    if "National Health" in text:
        laws_cited.append("National Health Act s.6")
    return laws_cited


# ── OFFLINE FALLBACKS ──────────────────────────────────────

def _heuristic_analysis(description: str, incident_type: str) -> dict:
    """Simple keyword-based rights analysis when Ollama is unavailable."""
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