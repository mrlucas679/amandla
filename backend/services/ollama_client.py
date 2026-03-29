"""Ollama client for AMANDLA text-to-signs mapping.

classify_text_to_signs(text) -> list[str]
  Tries the local 'amandla' Ollama model first, falls back to the
  rule-based word map in backend.services.sign_maps if Ollama is unavailable.

No cloud API keys needed — everything runs locally.
"""
import os
import json
import logging
import httpx

logger = logging.getLogger(__name__)

# ── Environment config (loaded once by backend.main at startup) ───────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "amandla")

# ── Import canonical rule-based converter from shared module ──────────────
from backend.services.sign_maps import sentence_to_sign_names as _rule_based_signs


async def classify_text_to_signs(text: str) -> list:
    """Convert English text to an ordered list of SASL sign name strings.

    Fallback chain: Ollama (local AI) → rule-based word map.

    Args:
        text: Transcribed English sentence from hearing user.

    Returns:
        Ordered list of SASL sign name strings (e.g. ["HELLO", "HOW ARE YOU"]).
    """
    if not text:
        return []

    # 1. Try local Ollama model
    ollama_result = await _try_ollama(text)
    if ollama_result is not None:
        return ollama_result

    # 2. Rule-based fallback (no cloud AI — fully offline)
    logger.info("[OllamaClient] Ollama unavailable, using rule-based fallback")
    return _rule_based_signs(text)


async def _try_ollama(text: str):
    """Call the local Ollama amandla model. Returns list or None on failure."""
    try:
        base = OLLAMA_BASE_URL
        model = OLLAMA_MODEL

        prompt = (
            f'Convert this English sentence to SASL sign names.\n'
            f'Sentence: "{text}"\n'
            f'Reply ONLY with a JSON array of uppercase sign name strings.\n'
            f'Valid signs: HELLO, GOODBYE, PLEASE, THANK YOU, SORRY, YES, NO, HELP, '
            f'WAIT, STOP, REPEAT, UNDERSTAND, WATER, PAIN, HURT, DOCTOR, NURSE, '
            f'HOSPITAL, SICK, MEDICINE, AMBULANCE, EMERGENCY, HAPPY, SAD, ANGRY, '
            f'SCARED, LOVE, I LOVE YOU, TIRED, HUNGRY, THIRSTY, WORRIED, CONFUSED, '
            f'WHO, WHAT, WHERE, WHEN, WHY, HOW, I, YOU, WE, THEY, COME, GO, LISTEN, '
            f'LOOK, KNOW, WANT, GIVE, EAT, DRINK, SLEEP, SIT, STAND, WALK, RUN, WORK, '
            f'WASH, WRITE, READ, SIGN, TELL, LAUGH, CRY, HUG, OPEN, CLOSE, GOOD, BAD, '
            f'BIG, SMALL, HOT, COLD, QUIET, FAST, SLOW, HOME, SCHOOL, FAMILY, MOM, '
            f'DAD, BABY, FRIEND, CHILD, MONEY, FREE, RIGHTS, LAW, EQUAL, CAR, TAXI, '
            f'BUS, TODAY, NOW, MORNING, NIGHT.\n'
            f'Example: ["HELLO", "HOW ARE YOU"]'
        )

        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.post(
                f"{base}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False, "temperature": 0.1}
            )
            if r.status_code != 200:
                return None

            raw = r.json().get("response", "").strip()

            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start < 0 or end <= start:
                return None

            signs = json.loads(raw[start:end])
            if isinstance(signs, list) and all(isinstance(s, str) for s in signs):
                return [s.upper() for s in signs]

    except Exception as e:
        logger.debug(f"[OllamaClient] Ollama text-to-signs unavailable: {e}")

    return None