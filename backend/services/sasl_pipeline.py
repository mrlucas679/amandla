"""SASL pipeline: English text → SASL-ordered sign names + gloss text.

This is the HEARING → DEAF pipeline entry point.
The hearing person speaks/types plain English; this module converts
it to proper SASL grammar (SOV word order, no articles, FINISH/WILL
aspect markers, time-first, question-words last) before it reaches
the deaf user's screen.

Fallback chain:
  1. SASL transformer via Ollama LLM — most accurate, full grammar
  2. Rule-based SASL transformer — applies all 13 SASL grammar rules offline
  3. Raw sign word list — last resort, no grammar ordering

FEAT-5: Multilingual support — if the input language is not English,
the text is first translated to English via Ollama before entering
the SASL pipeline.  English input bypasses translation entirely.

All AI runs locally via Ollama — no cloud API keys needed.
"""

import logging
import os
import time as _time

logger = logging.getLogger(__name__)

# Module-level SASL transformer singleton (lazy init on first use)
_sasl_transformer = None

# Empty result constant — returned when input is blank or all tiers fail
_EMPTY_RESULT = {"signs": [], "text": "", "original_english": ""}

# ── FEAT-5: Multilingual constants ─────────────────────────────────────────

# Ollama base URL and model for translation (reuse shared env vars)
_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_TRANSLATION_MODEL = os.getenv("TRANSLATION_OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", "amandla"))

# Timeout for the Ollama translation call (seconds)
TRANSLATION_TIMEOUT_S = 10.0

# Temperature for translation — low value for deterministic output
TRANSLATION_TEMPERATURE = 0.1

# Language codes that are treated as English (no translation needed)
ENGLISH_LANG_CODES = {"en", "english"}

# System prompt instructing Ollama to act as a translator
TRANSLATION_SYSTEM_PROMPT = (
    "You are a professional translator. "
    "Translate the given text into clear, natural English. "
    "Return ONLY the English translation — no explanations, no notes, "
    "no quotation marks, no extra text. Just the translated sentence."
)

# Human-readable labels for South Africa's 11 official languages
# plus common Whisper language codes.  Keys are Whisper two-letter codes.
SA_LANGUAGE_LABELS = {
    "en": "English",
    "af": "Afrikaans",
    "zu": "isiZulu",
    "xh": "isiXhosa",
    "st": "Sesotho",
    "tn": "Setswana",
    "nso": "Sepedi",
    "ts": "Xitsonga",
    "ve": "Tshivenda",
    "nr": "isiNdebele",
    "ss": "siSwati",
}


def _language_label(code: str) -> str:
    """Return a human-readable label for a Whisper language code.

    Args:
        code: Two- or three-letter language code from Whisper (e.g. 'af').

    Returns:
        Human-readable label (e.g. 'Afrikaans'), or the raw code if unknown.
    """
    if not code:
        return "Unknown"
    return SA_LANGUAGE_LABELS.get(code.lower(), code)


async def _translate_to_english(text: str, language_code: str) -> str:
    """Translate non-English text to English via Ollama.

    Uses the shared connection pool from ollama_pool.  On any failure
    (timeout, bad status, empty response) the original text is returned
    unchanged so the SASL pipeline can still attempt best-effort processing.

    Args:
        text:          The non-English input text.
        language_code: Whisper language code (e.g. 'af' for Afrikaans).

    Returns:
        English translation string, or the original text on failure.
    """
    label = _language_label(language_code)
    prompt = f'Translate the following {label} text to English:\n\n{text}'

    try:
        from backend.services.ollama_pool import get_client
        client = get_client()
        response = await client.post(
            f"{_OLLAMA_BASE_URL}/api/generate",
            json={
                "model":       _TRANSLATION_MODEL,
                "prompt":      prompt,
                "system":      TRANSLATION_SYSTEM_PROMPT,
                "stream":      False,
                "temperature": TRANSLATION_TEMPERATURE,
            },
            timeout=TRANSLATION_TIMEOUT_S,
        )
        if response.status_code != 200:
            logger.warning("[SASL] Translation HTTP %d — using original text", response.status_code)
            return text

        translated = response.json().get("response", "").strip()
        if not translated:
            logger.warning("[SASL] Empty translation response — using original text")
            return text

        logger.info("[SASL] Translated %s → English: '%s' → '%s'", label, text[:50], translated[:50])
        return translated

    except Exception as exc:
        logger.warning("[SASL] Translation failed (%s) — using original text: %s", type(exc).__name__, exc)
        return text


async def text_to_sasl_signs(text: str, language: str | None = None) -> dict:
    """Convert text → SASL-ordered sign names + gloss text.

    If a non-English language code is provided, the text is first translated
    to English via Ollama before entering the SASL pipeline.  English input
    bypasses translation entirely (no double-translation).

    Args:
        text:     Input text (English or another language).
        language: Optional Whisper-detected language code (e.g. 'af', 'zu').
                  None or 'en' means English — no translation needed.

    Returns:
        {
            signs:            list of SASL sign name strings,
            text:             SASL gloss string,
            original_english: the English text that entered the SASL pipeline,
            source_language:  language code if translated (absent for English),
            original_input:   pre-translation text if translated (absent for English),
        }
    """
    global _sasl_transformer
    if not text:
        return {**_EMPTY_RESULT}

    # ── FEAT-5: Pre-translate non-English input ──────────────────────────
    source_language = None
    original_input = None
    if language and language.lower() not in ENGLISH_LANG_CODES:
        source_language = language
        original_input = text
        text = await _translate_to_english(text, language)

    pipeline_start = _time.monotonic()

    def _build_result(signs, gloss_text, english, **extras):
        """Build a standardised pipeline result dict.

        Includes source_language and original_input when a translation
        from a non-English language occurred (FEAT-5).

        Args:
            signs:      List of SASL sign name strings.
            gloss_text: SASL gloss string.
            english:    The English text that was fed to the pipeline.
            **extras:   Optional keys (e.g. non_manual_markers).

        Returns:
            dict with signs, text, original_english, and optional translation metadata.
        """
        result = {
            "signs": signs,
            "text": gloss_text,
            "original_english": english,
        }
        # FEAT-5: Attach translation metadata when input was non-English
        if source_language:
            result["source_language"] = source_language
        if original_input:
            result["original_input"] = original_input
        result.update(extras)
        return result

    # Ensure the transformer singleton is initialised once for all paths below
    if _sasl_transformer is None:
        from sasl_transformer.transformer import SASLTransformer
        _sasl_transformer = SASLTransformer()

    # Import once — used by both tier 1 and tier 2
    from sasl_transformer.models import TranslationRequest

    # 1. Try SASL transformer (proper grammar ordering via Ollama)
    try:
        tier_start = _time.monotonic()
        response = await _sasl_transformer.translate(TranslationRequest(english_text=text))
        sign_names = [tok.gloss for tok in response.tokens]
        elapsed_ms = (_time.monotonic() - tier_start) * 1000
        if sign_names:
            logger.info("[SASL] Tier 1 (LLM) %.0fms: '%s' → '%s'", elapsed_ms, text[:50], response.gloss_text)
            return _build_result(
                sign_names, response.gloss_text, text,
                non_manual_markers=response.non_manual_markers or [],
            )
    except Exception as exc:
        logger.warning("[SASL] Transformer failed, falling back: %s", exc)

    # 2. Grammar-aware rule-based fallback (no network needed — applies all 13 SASL rules)
    try:
        tier_start = _time.monotonic()
        rule_response = _sasl_transformer.translate_with_rules(
            text, TranslationRequest(english_text=text)
        )
        rule_signs = [tok.gloss for tok in rule_response.tokens]
        elapsed_ms = (_time.monotonic() - tier_start) * 1000
        if rule_signs:
            logger.info("[SASL] Tier 2 (rules) %.0fms: '%s' → '%s'", elapsed_ms, text[:50], rule_response.gloss_text)
            return _build_result(
                rule_signs, rule_response.gloss_text, text,
                non_manual_markers=rule_response.non_manual_markers or [],
            )
    except Exception as rule_err:
        logger.warning("[SASL] Rule-based fallback failed: %s", rule_err)

    # 3. Last resort: raw word list (no grammar, but better than nothing)
    try:
        tier_start = _time.monotonic()
        from backend.services.ollama_client import classify_text_to_signs
        sign_names = await classify_text_to_signs(text)
        elapsed_ms = (_time.monotonic() - tier_start) * 1000
        total_ms = (_time.monotonic() - pipeline_start) * 1000
        logger.info("[SASL] Tier 3 (raw) %.0fms (total %.0fms): '%s' → %s", elapsed_ms, total_ms, text[:50], sign_names)
        return _build_result(sign_names, " ".join(sign_names), text)
    except Exception as fallback_err:
        total_ms = (_time.monotonic() - pipeline_start) * 1000
        logger.error("[SASL] All 3 tiers failed (%.0fms): '%s' — %s", total_ms, text[:50], fallback_err)
        return _build_result([], "", text)

