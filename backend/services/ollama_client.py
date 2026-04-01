"""Ollama client for AMANDLA text-to-signs mapping.

classify_text_to_signs(text) -> list[str]
  Tries the local 'amandla' Ollama model first, falls back to the
  rule-based word map in backend.services.sign_maps if Ollama is unavailable.

No cloud API keys needed — everything runs locally.
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

# ── Environment config (loaded once by backend.main at startup) ───────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "amandla")

# ── Import canonical rule-based converter from shared module ──────────────
from backend.services.sign_maps import sentence_to_sign_names as _rule_based_signs
from backend.services.sign_maps import WORD_MAP as _WORD_MAP

# ── Dynamic sign list for the Ollama prompt ───────────────────────────────
# Generated at import time from the single-source-of-truth WORD_MAP so the
# prompt always reflects the current sign inventory (no stale hardcoded list).
_ALL_SIGN_NAMES = sorted(set(_WORD_MAP.values()))
_SIGN_LIST_STR = ", ".join(_ALL_SIGN_NAMES)

# ── Translation cache (QUAL-1) ────────────────────────────────────────────
# Simple ordered dict cache: identical input → identical output, no re-call.
# Emergency phrases ("HELP", "STOP") hit this on every subsequent tap → <1ms.
from collections import OrderedDict as _OrderedDict
_classify_cache: _OrderedDict = _OrderedDict()
_CLASSIFY_CACHE_MAX: int = 500


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

    # Cache hit — return immediately, no Ollama or rule-based work needed
    if text in _classify_cache:
        _classify_cache.move_to_end(text)
        logger.debug("[OllamaClient] Cache hit: %s", text[:50])
        return list(_classify_cache[text])  # Return a copy so callers can mutate safely

    # 1. Try local Ollama model
    ollama_result = await _try_ollama(text)
    if ollama_result is not None:
        _cache_result(text, ollama_result)
        return ollama_result

    # 2. Rule-based fallback (no cloud AI — fully offline)
    logger.info("[OllamaClient] Ollama unavailable, using rule-based fallback")
    result = _rule_based_signs(text)
    _cache_result(text, result)
    return result


async def _try_ollama(text: str):
    """Call the local Ollama amandla model. Returns list or None on failure."""
    try:
        base = OLLAMA_BASE_URL
        model = OLLAMA_MODEL

        prompt = (
            f'Convert this English sentence to SASL sign names.\n'
            f'Sentence: "{text}"\n'
            f'Reply ONLY with a JSON array of uppercase sign name strings.\n'
            f'Valid signs: {_SIGN_LIST_STR}.\n'
            f'SASL grammar note: use FINISH for completed actions (past tense), '
            f'WILL for future, MUST/CAN for obligation/ability, NOT for negation.\n'
            f'Example: ["HELLO", "HOW ARE YOU"]'
        )

        from backend.services.ollama_pool import get_client
        client = get_client()
        r = await client.post(
            f"{base}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                # Override the Modelfile system prompt so this call is treated
                # as a sign-name converter, not a landmark classifier.
                "system": (
                    "You are a South African Sign Language (SASL) converter. "
                    "Given an English sentence, return ONLY a JSON array of "
                    "uppercase SASL sign name strings in SASL grammar order. "
                    "No explanation. No text outside the JSON array."
                ),
                "stream": False,
                "temperature": 0.1,
            },
            timeout=6.0,
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


def _cache_result(text: str, result: list) -> None:
    """Store a classification result in the LRU cache (evicts oldest if full)."""
    if len(_classify_cache) >= _CLASSIFY_CACHE_MAX:
        _classify_cache.popitem(last=False)  # Remove the oldest entry
    _classify_cache[text] = tuple(result)   # Store as tuple (immutable)