"""Sign reconstruction: SASL sign sequences → natural English.

Handles the DEAF → HEARING pipeline:
- Debounce buffer for quick-sign / MediaPipe signs
- Rule-based sign→English reconstruction
- Ollama-powered AI reconstruction (local, no cloud)
- Multi-word sign detection and SASL gloss splitting

All lookup tables are defined at module level so they are created once
at import time instead of on every function call.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional

from backend.shared import sign_buffers, sign_tasks

logger = logging.getLogger(__name__)

# ── Single-sign → complete natural English sentence ──────────────────────────
SINGLE_SIGN_SENTENCES: Dict[str, str] = {
    "HELP":       "I need help.",
    "WATER":      "I need water.",
    "DOCTOR":     "I need a doctor.",
    "NURSE":      "I need a nurse.",
    "HOSPITAL":   "I need to go to the hospital.",
    "SICK":       "I am not feeling well.",
    "PAIN":       "I am in pain.",
    "HURT":       "I am hurt.",
    "MEDICINE":   "I need medicine.",
    "AMBULANCE":  "Please call an ambulance.",
    "EMERGENCY":  "This is an emergency.",
    "HAPPY":      "I am happy.",
    "SAD":        "I am sad.",
    "ANGRY":      "I am angry.",
    "SCARED":     "I am scared.",
    "TIRED":      "I am tired.",
    "HUNGRY":     "I am hungry.",
    "THIRSTY":    "I am thirsty.",
    "WORRIED":    "I am worried.",
    "CONFUSED":   "I am confused.",
    "STOP":       "Please stop.",
    "WAIT":       "Please wait.",
    "REPEAT":     "Please repeat that.",
    "UNDERSTAND": "I understand.",
    "YES":        "Yes.",
    "NO":         "No.",
    "PLEASE":     "Please.",
    "THANK YOU":  "Thank you.",
    "SORRY":      "I am sorry.",
    "HELLO":      "Hello.",
    "GOODBYE":    "Goodbye.",
    "HOME":       "I want to go home.",
    "GO":         "I need to go.",
    "COME":       "Please come here.",
    "RIGHTS":     "I know my rights.",
    "LAW":        "This is against the law.",
    "EQUAL":      "I deserve equal treatment.",
    "GOOD":       "I am doing well.",
    "BAD":        "Things are not good.",
}

# ── Sign name → natural English word (for multi-sign reconstruction) ─────────
# Hand-curated overrides — these take priority over auto-generated mappings
# because they produce more natural English than the raw word form.
_SIGN_WORD_OVERRIDES: Dict[str, str] = {
    "I": "I", "YOU": "you", "WE": "we", "THEY": "they",
    "WANT": "need", "HELP": "help", "WATER": "water",
    "DOCTOR": "a doctor", "NURSE": "a nurse", "HOSPITAL": "the hospital",
    "SICK": "sick", "PAIN": "in pain", "HURT": "hurt",
    "MEDICINE": "medicine", "AMBULANCE": "an ambulance",
    "EMERGENCY": "an emergency", "HAPPY": "happy", "SAD": "sad",
    "ANGRY": "angry", "SCARED": "scared", "TIRED": "tired",
    "HUNGRY": "hungry", "THIRSTY": "thirsty", "WORRIED": "worried",
    "CONFUSED": "confused", "GOOD": "good", "BAD": "bad",
    "YES": "yes", "NO": "no", "PLEASE": "please",
    "THANK YOU": "thank you", "SORRY": "sorry",
    "STOP": "stop", "WAIT": "wait", "COME": "come", "GO": "go",
    "HOME": "home", "SCHOOL": "school", "WORK": "work",
}

# Auto-generate reverse mappings from the canonical sign_maps.WORD_MAP.
# For each (english_word → SIGN_NAME) pair, pick the shortest English word
# as the most natural reverse mapping. Hand-curated overrides take priority.
from backend.services.sign_maps import WORD_MAP as _WORD_MAP

# Invert WORD_MAP: collect all English words per sign name, pick shortest
_auto_reverse: Dict[str, str] = {}
for _word, _sign in _WORD_MAP.items():
    _sign_upper = _sign.upper()
    # Skip if already have a shorter word for this sign
    if _sign_upper in _auto_reverse and len(_auto_reverse[_sign_upper]) <= len(_word):
        continue
    _auto_reverse[_sign_upper] = _word

# Merge: auto-generated first, then overrides on top (overrides win)
SIGN_WORD_MAP: Dict[str, str] = {**_auto_reverse, **_SIGN_WORD_OVERRIDES}

# ── Multi-word sign detection (BUG-1 fix) ────────────────────────────────────
# Collect every multi-word sign name from the lookup tables so the SASL-text
# splitter can match them as single tokens instead of breaking on spaces.
# Sorted longest-first so that "HOW ARE YOU" matches before "HOW ARE".
MULTI_WORD_SIGNS: List[str] = sorted(
    {
        key for key in list(SINGLE_SIGN_SENTENCES.keys()) + list(SIGN_WORD_MAP.keys())
        if " " in key
    },
    key=len,
    reverse=True,
)


def split_sasl_gloss(text: str) -> List[str]:
    """Split a SASL gloss string into sign tokens, preserving multi-word signs.

    Uses longest-match first: scans through the uppercased text and greedily
    matches the longest known multi-word sign at each position before falling
    back to whitespace splitting for the remainder.

    Args:
        text: Raw SASL gloss string (e.g. "THANK YOU WATER HELP").

    Returns:
        List of sign name strings (e.g. ["THANK YOU", "WATER", "HELP"]).
        Each token has surrounding punctuation stripped.
    """
    if not text or not text.strip():
        return []

    upper = text.upper().strip()
    result: List[str] = []
    position = 0

    while position < len(upper):
        # Skip whitespace between tokens
        if upper[position] == " ":
            position += 1
            continue

        # Try each multi-word sign (longest-first) at the current position
        matched = False
        for multi_sign in MULTI_WORD_SIGNS:
            end = position + len(multi_sign)
            # Must match exactly and be followed by whitespace, punctuation, or end-of-string
            if upper[position:end] == multi_sign and (
                end >= len(upper) or not upper[end].isalpha()
            ):
                result.append(multi_sign)
                position = end
                matched = True
                break

        if not matched:
            # Fall back to grabbing the next whitespace-delimited token
            token_end = upper.find(" ", position)
            if token_end == -1:
                token_end = len(upper)
            token = upper[position:token_end].strip(".,!?;:'\"")
            if token:
                result.append(token)
            position = token_end

    return result


def simple_signs_to_english(signs: list) -> str:
    """Rule-based SASL sign sequence → natural English sentence (no network).

    For single known signs, returns a complete proper sentence.
    For sequences, builds the best English it can from a word map.

    Args:
        signs: List of SASL sign name strings (e.g. ["WATER", "WANT", "I"]).

    Returns:
        Natural English sentence string. Never returns None.
    """
    if not signs:
        return ""

    # Single sign — direct lookup
    if len(signs) == 1:
        key = signs[0].upper()
        if key in SINGLE_SIGN_SENTENCES:
            return SINGLE_SIGN_SENTENCES[key]

    # Multi-sign — word-level map + basic reconstruction
    words: List[str] = [str(SIGN_WORD_MAP.get(str(s).upper(), str(s).lower())) for s in signs]
    sentence: str = " ".join(words)
    if not sentence:
        return ""
    # Capitalise the first letter and ensure the sentence ends with a full stop
    capitalised = sentence[0].upper() + sentence[1:]
    return capitalised if capitalised.endswith(".") else capitalised + "."


async def ollama_signs_to_english(signs: list) -> Optional[str]:
    """Use local Ollama to reconstruct a SASL sign sequence into natural English.

    The prompt teaches the model SASL grammar so it knows what it's reversing:
    - SASL is verb-final (SOV order), unlike English SVO
    - No articles (a/an/the) — must be re-added in English
    - FINISH = completed past action marker
    - WILL = future marker
    - Time words (YESTERDAY, TOMORROW, etc.) appear at the start
    - Question words (WHO, WHAT, WHERE) appear at the END

    Args:
        signs: List of SASL sign name strings.

    Returns:
        Natural English sentence string, or None if Ollama is unavailable.
    """
    try:
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "amandla")
        sign_str = " ".join(signs)
        prompt = (
            "You are reversing South African Sign Language (SASL) gloss notation back into natural English.\n"
            "SASL grammar rules you must reverse:\n"
            "  1. SASL uses SOV order (Subject-Object-Verb) — verb is at the END. Reorder to English SVO.\n"
            "  2. SASL has no articles — add 'a', 'an', 'the' where natural in English.\n"
            "  3. FINISH at the end means the action is PAST tense (e.g. EAT FINISH → 'I have eaten').\n"
            "  4. WILL at the end means FUTURE tense (e.g. GO WILL → 'I will go').\n"
            "  5. Time words like YESTERDAY/TOMORROW appear first in SASL — move them naturally in English.\n"
            "  6. Question words like WHO/WHAT/WHERE appear at the END in SASL — move to the start in English.\n"
            "  7. NOT after a concept means negation (e.g. UNDERSTAND NOT → 'I do not understand').\n"
            "  8. Add pronouns (I, you, she, he, they) where they are missing but implied by context.\n\n"
            f"SASL signs to convert: {sign_str}\n\n"
            "Reply with ONLY the natural English sentence — no explanations, no quotes.\n"
            "Example: YESTERDAY STORE I GO FINISH → 'I went to the store yesterday.'\n"
            "Example: SICK DOCTOR → 'I am sick and need a doctor.'"
        )
        from backend.services.ollama_pool import get_client
        client = get_client()
        resp = await client.post(
            f"{base}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "system": (
                    "You convert South African Sign Language (SASL) gloss notation "
                    "back to natural English. Given a list of SASL sign names, "
                    "return ONE natural English sentence only. "
                    "No explanations. No extra text."
                ),
                "stream": False,
                "temperature": 0.2,
            },
            timeout=8.0,
        )
        if resp.status_code == 200:
            text = resp.json().get("response", "").strip().split("\n")[0].strip()
            max_response_length = 250
            if text and len(text) < max_response_length:
                return text
    except Exception as exc:
        logger.debug("[Signs2English] Ollama failed: %s", exc)
    return None


async def signs_to_english(signs: list) -> str:
    """Reconstruct SASL sign sequence to natural English.

    Fallback chain: Ollama (local AI) → rule-based.
    No cloud API needed — everything runs locally.

    Args:
        signs: List of SASL sign name strings.

    Returns:
        Natural English sentence string.
    """
    if not signs:
        return ""

    # 1. Ollama — local AI reconstruction
    try:
        ollama_result = await ollama_signs_to_english(signs)
        if ollama_result:
            logger.info("[Signs2English] Ollama: %s → %r", signs, ollama_result)
            return str(ollama_result)
    except Exception as exc:
        logger.debug("[Signs2English] Ollama unavailable: %s", exc)

    # 2. Rule-based fallback (always works offline)
    result = simple_signs_to_english(signs)
    logger.info("[Signs2English] Rule-based: %s → %r", signs, result)
    return result


async def debounce_and_flush(session_id: str, session: dict) -> None:
    """Wait 1.5s after last sign, then reconstruct and send to hearing.

    Called as an asyncio.Task per session. Cancelled and restarted each
    time a new sign arrives (debounce pattern).

    Args:
        session_id: The WebSocket session identifier.
        session:    The session dict containing connected users.
    """
    debounce_delay_s = 1.5
    await asyncio.sleep(debounce_delay_s)
    signs = sign_buffers.pop(session_id, [])
    sign_tasks.pop(session_id, None)
    if not signs:
        return
    english = await signs_to_english(signs)
    if not english:
        return
    hearing_ws = session["users"].get("hearing")
    if hearing_ws:
        from backend.ws.helpers import send_safe
        await send_safe(hearing_ws, {
            "type":  "deaf_speech",
            "text":  english,
            "signs": signs,
        })
        logger.info("[Signs2English] Sent to hearing: %r", english)

        # Log to conversation history (must never break the main flow)
        try:
            from backend.services.history_db import log_message
            await log_message(
                session_id=session_id,
                direction="deaf_to_hearing",
                original_text=" ".join(signs),
                sasl_gloss=" ".join(signs),
                translated_text=english,
                source="sign_button",
            )
        except Exception:
            pass

