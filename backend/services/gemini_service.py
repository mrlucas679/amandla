"""
Google Gemini service for AMANDLA.

Uses the google-genai SDK (google.genai).

Provides three capabilities:
  1. analyse_incident(description, incident_type) → SA disability rights analysis
  2. generate_rights_letter(...)                  → formal complaint letter
  3. classify_text_to_signs(text)                 → SASL sign name list

Used as a fallback when:
  - ANTHROPIC_API_KEY is absent (rights module: Claude → Gemini → heuristic)
  - Ollama is unavailable (text-to-signs: Ollama → Gemini → rule-based)
"""
import os
import re
import json
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")

_RIGHTS_SYSTEM = """You are a South African disability rights legal assistant for the AMANDLA app.
AMANDLA is a real-time sign language communication bridge that helps deaf South Africans communicate.

When a disabled person reports an incident of discrimination, your job is to:
1. Identify exactly what happened and which rights were violated
2. Map the incident to the specific South African laws that apply
3. Draft a formal, professional complaint letter the person can send

Key South African disability rights laws:
- Employment Equity Act No. 55 of 1998, s.6 — prohibits unfair discrimination based on disability
- Promotion of Equality and Prevention of Unfair Discrimination Act No. 4 of 2000 (PEPUDA), s.7
- Constitution of the Republic of South Africa, s.9(3) — equality and non-discrimination
- Labour Relations Act No. 66 of 1995, s.191 — unfair dismissal / unfair labour practice
- National Health Act No. 61 of 2003, s.6 — equal access to health services
- South African Schools Act No. 84 of 1996 — equal access to education

Always be specific: cite exact section numbers, use formal South African legal language,
and write letters that could actually be submitted to the CCMA or an Equality Court."""


def _get_client():
    """Lazily import google.genai and return a configured Client. Returns None if unavailable."""
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except ImportError:
        logger.warning("[Gemini] google-genai not installed — run: pip install google-genai")
        return None
    except Exception as e:
        logger.warning(f"[Gemini] Could not initialise client: {e}")
        return None


def is_available() -> bool:
    """Return True if the Gemini service can be used."""
    return bool(GEMINI_API_KEY)


async def analyse_incident(description: str, incident_type: str = "workplace") -> dict:
    """
    Analyse a disability discrimination incident using Gemini.

    Returns:
        {
            "what_happened": "...",
            "location": "...",
            "severity": "minor|moderate|serious",
            "laws_likely_violated": ["Employment Equity Act s.6", ...]
        }
    Returns None on failure (caller falls back to heuristic).
    """
    client = _get_client()
    if client is None:
        return None

    prompt = f"""{_RIGHTS_SYSTEM}

Analyse this South African disability discrimination incident and return ONLY a JSON object.

Incident type: {incident_type}
Description: {description}

Return this exact JSON structure (no markdown, no code fences, just the JSON):
{{
  "what_happened": "one clear sentence summarising what the discriminatory act was",
  "location": "the setting or context (e.g. workplace, hospital, public transport)",
  "severity": "minor OR moderate OR serious",
  "laws_likely_violated": ["specific law and section", "another law and section"]
}}

Severity guide: serious = job loss / physical harm / denied emergency care; moderate = ongoing harassment / denied reasonable accommodation; minor = isolated rude incident.
Laws must include section numbers. Always include Constitution s.9(3)."""

    try:
        import asyncio
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        )
        text = response.text.strip()
        # Strip markdown code fences if present
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
        result = json.loads(text)
        logger.info(f"[Gemini] Incident analysed. Severity: {result.get('severity')}")
        return result
    except Exception as e:
        logger.warning(f"[Gemini] analyse_incident failed: {e}")
        return None


async def generate_rights_letter(
    incident_description: str,
    user_name: str,
    employer_name: str,
    incident_date: str,
    analysis: dict = None
) -> dict:
    """
    Generate a formal SA disability rights complaint letter using Gemini.

    Returns:
        {"letter": "full letter text", "laws_cited": [...], "model": "gemini-..."}
    Returns None on failure (caller falls back to template).
    """
    client = _get_client()
    if client is None:
        return None

    laws_context = ""
    if analysis and analysis.get("laws_likely_violated"):
        laws_context = f"\nLaws already identified: {', '.join(analysis['laws_likely_violated'])}"

    ref = f"AMANDLA-RIGHTS-2026-{abs(hash(employer_name)) % 900 + 100:03d}"

    prompt = f"""{_RIGHTS_SYSTEM}

Write a complete, formal South African disability rights complaint letter.

Complainant: {user_name}
Respondent (employer / institution): {employer_name}
Date of incident: {incident_date}
Reference number to use: {ref}{laws_context}

Incident description:
{incident_description}

Requirements for the letter:
- Today's date at the top
- Full address blocks (use placeholders like [YOUR ADDRESS])
- The reference number provided above
- Formal salutation ("Dear Sir/Madam" or "To Whom It May Concern")
- Opening paragraph stating the purpose and legal basis
- Factual paragraph describing exactly what happened
- Legal paragraph citing SPECIFIC South African laws and section numbers that apply
- Demands paragraph: written apology within 7 days, corrective steps, compliance confirmation
- Consequences paragraph: CCMA referral, SAHRC complaint, Equality Court action
- Professional closing and signature block

Write the complete letter now. Output only the letter — no commentary, no preamble."""

    try:
        import asyncio
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        )
        letter_text = response.text.strip()

        laws_cited = []
        if "Employment Equity" in letter_text:
            laws_cited.append("Employment Equity Act s.6")
        if "Promotion of Equality" in letter_text or "PEPUDA" in letter_text:
            laws_cited.append("Promotion of Equality Act s.7")
        if "Constitution" in letter_text or "s.9(3)" in letter_text:
            laws_cited.append("Constitution s.9(3)")
        if "Labour Relations" in letter_text:
            laws_cited.append("Labour Relations Act s.191")
        if "National Health" in letter_text:
            laws_cited.append("National Health Act s.6")

        logger.info(f"[Gemini] Rights letter generated. Laws cited: {laws_cited}")
        return {
            "letter": letter_text,
            "laws_cited": laws_cited,
            "model": GEMINI_MODEL
        }
    except Exception as e:
        logger.warning(f"[Gemini] generate_rights_letter failed: {e}")
        return None


async def signs_to_english(signs: list) -> str:
    """
    Convert a sequence of SASL sign names to a natural English sentence.

    Used for the deaf→hearing reconstruction path:
    e.g. ["WATER", "WANT", "I"] → "I need water"

    Returns None on failure (caller should use Ollama or simple fallback).
    """
    client = _get_client()
    if client is None or not signs:
        return None

    sign_str = " ".join(signs)

    prompt = f"""Convert these South African Sign Language (SASL) sign names to a single natural English sentence.

SASL signs: {sign_str}

Rules:
- SASL uses topic-comment and subject-object-verb order — restructure to natural English SVO
- Add pronouns, articles, and helper verbs as needed (e.g. "I", "a", "need", "am")
- Keep the sentence short, clear, and natural — as if a person actually said it
- Do NOT add explanation — output ONLY the English sentence
- Do NOT include the sign names in the output

Examples:
  WATER WANT → "I need some water"
  SICK DOCTOR → "I am sick and need a doctor"
  HELP PLEASE → "Please help me"
  PAIN HURT → "I am in pain"
  EMERGENCY AMBULANCE → "This is an emergency, call an ambulance"

SASL signs to convert: {sign_str}
Output:"""

    try:
        import asyncio
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        )
        text = response.text.strip().split('\n')[0].strip()
        # Sanity check — reject if it looks like it echoed sign names
        if text and len(text) < 250 and not any(s in text.upper().split() for s in signs[:1]):
            logger.debug(f"[Gemini] Signs→English: {signs} → {text!r}")
            return text
    except Exception as e:
        logger.debug(f"[Gemini] signs_to_english failed: {e}")

    return None


async def classify_text_to_signs(text: str) -> list:
    """
    Use Gemini to intelligently convert English text to SASL sign names.

    Returns an ordered list of uppercase sign name strings,
    or None on failure (caller should use rule-based fallback).
    """
    client = _get_client()
    if client is None or not text:
        return None

    prompt = f"""Convert this English sentence to South African Sign Language (SASL) sign names.

Sentence: "{text}"

Rules:
- Return ONLY a JSON array of uppercase sign name strings — nothing else
- Use the most natural SASL equivalent for each concept
- Drop filler words (the, a, is, are, of, etc.) — SASL omits them
- For common phrases, use the compound sign name (e.g. "THANK YOU" not "THANK" + "YOU")
- For unknown words, fingerspell letter by letter (e.g. "JOHN" → ["J","O","H","N"])

Valid sign names include: HELLO, GOODBYE, PLEASE, THANK YOU, SORRY, YES, NO, HELP,
WAIT, STOP, REPEAT, UNDERSTAND, WATER, PAIN, HURT, DOCTOR, NURSE, HOSPITAL, SICK,
MEDICINE, AMBULANCE, EMERGENCY, HAPPY, SAD, ANGRY, SCARED, LOVE, I LOVE YOU,
EXCITED, TIRED, HUNGRY, THIRSTY, WORRIED, CONFUSED, WHO, WHAT, WHERE, WHEN, WHY,
HOW, I, YOU, WE, THEY, COME, GO, LISTEN, LOOK, KNOW, WANT, GIVE, EAT, DRINK,
SLEEP, SIT, STAND, WALK, RUN, WORK, WASH, WRITE, READ, SIGN, TELL, LAUGH, CRY,
HUG, OPEN, CLOSE, GOOD, BAD, BIG, SMALL, HOT, COLD, QUIET, FAST, SLOW, HOME,
SCHOOL, FAMILY, MOM, DAD, BABY, FRIEND, CHILD, PERSON, MONEY, FREE, RIGHTS, LAW,
EQUAL, CAR, TAXI, BUS, TODAY, NOW, MORNING, NIGHT, HOW ARE YOU, I'M FINE.

Example: "Hello, how are you today?" → ["HELLO", "HOW ARE YOU"]

Output only the JSON array."""

    try:
        import asyncio
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        )
        raw = response.text.strip()
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start < 0 or end <= start:
            return None
        signs = json.loads(raw[start:end])
        if isinstance(signs, list) and all(isinstance(s, str) for s in signs):
            logger.debug(f"[Gemini] Text-to-signs: {text!r} → {signs}")
            return [s.upper() for s in signs]
    except Exception as e:
        logger.debug(f"[Gemini] classify_text_to_signs failed: {e}")

    return None