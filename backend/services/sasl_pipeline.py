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

import json
import logging
import os
import time as _time
from pathlib import Path


logger = logging.getLogger(__name__)

# ── FEAT-2: Offline phrase library ────────────────────────────────────────────
# Pre-mapped medical/emergency phrases that work with zero LLM involvement.
# Loaded once at import time from backend/data/offline_phrases.json.
_OFFLINE_PHRASES_PATH = Path(__file__).resolve().parent.parent.parent / "backend" / "data" / "offline_phrases.json"
_OFFLINE_PHRASES: dict[str, list[str]] = {}

def _load_offline_phrases() -> None:
    global _OFFLINE_PHRASES
    try:
        with open(_OFFLINE_PHRASES_PATH, encoding="utf-8") as f:
            _OFFLINE_PHRASES = json.load(f)
        logger.info("[SASL] Loaded %d offline phrases", len(_OFFLINE_PHRASES))
    except Exception as exc:
        logger.warning("[SASL] Could not load offline phrases: %s", exc)

_load_offline_phrases()

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


# ── Contraction / SA slang normalisation map ─────────────────────────────────
_CONTRACTIONS: dict[str, str] = {
    "i'm": "i am", "i'll": "i will", "i've": "i have", "i'd": "i would",
    "you're": "you are", "you'll": "you will", "you've": "you have",
    "he's": "he is", "she's": "she is", "it's": "it is",
    "we're": "we are", "we'll": "we will", "we've": "we have",
    "they're": "they are", "they'll": "they will", "they've": "they have",
    "don't": "do not", "doesn't": "does not", "didn't": "did not",
    "won't": "will not", "wouldn't": "would not", "couldn't": "could not",
    "shouldn't": "should not", "can't": "cannot", "isn't": "is not",
    "aren't": "are not", "wasn't": "was not", "weren't": "were not",
    "haven't": "have not", "hasn't": "has not", "hadn't": "had not",
    "gonna": "going to", "wanna": "want to", "gotta": "got to",
    # SA informal words not already in WORD_MAP
    "howzit": "hello how are you",
    "eish": "", "yoh": "",
    "lekker": "good", "sharp": "okay",
    "ja": "yes", "nee": "no",
}


def _normalize_informal(text: str) -> str:
    """Expand contractions and normalise SA informal words before the SASL pipeline.

    Handles both single-word tokens (e.g. "howzit" → "hello how are you") and
    multi-word phrases (e.g. "just now" → "later") by doing a substring pass
    for multi-word keys before splitting into tokens.  Empty expansions (e.g.
    "eish" → "") are dropped.
    """
    text_lower = text.lower()

    # First pass: replace multi-word keys as substrings (longest first)
    for phrase, expansion in sorted(_CONTRACTIONS.items(), key=lambda x: len(x[0]), reverse=True):
        if " " in phrase and phrase in text_lower:
            text_lower = text_lower.replace(phrase, expansion if expansion else "", 1)

    # Second pass: handle single-word tokens
    words = text_lower.split()
    result = []
    for w in words:
        expanded = _CONTRACTIONS.get(w)
        if expanded is None:
            result.append(w)
        elif expanded:               # non-empty expansion
            result.extend(expanded.split())
        # empty expansion → drop the word entirely
    return " ".join(result)


def _extract_phrases(text: str) -> tuple[list[str], str]:
    """Extract known PHRASE_MAP entries from text before any LLM is involved.

    Matches greedily (longest phrase first) so "how are you doing" is not
    accidentally consumed by the shorter "how are you".

    Returns:
        (phrase_signs, remaining_text) where phrase_signs is the ordered list
        of SASL sign names extracted and remaining_text is what's left over.
    """
    from backend.services.sign_maps import PHRASE_MAP
    text_lower = text.lower().strip()
    signs: list[str] = []
    remaining = text_lower

    for phrase in sorted(PHRASE_MAP.keys(), key=len, reverse=True):
        if phrase in remaining:
            signs.extend(PHRASE_MAP[phrase])
            remaining = remaining.replace(phrase, " ", 1)

    return signs, remaining.strip()


def _merge_ordered(
    phrase_signs: list[str],
    word_signs: list[str],
) -> list[str]:
    """Combine phrase-level signs and word-level signs in display order.

    Phrase signs were extracted left-to-right, so they naturally precede
    whatever words remain.  Simple concatenation preserves the correct order
    for the vast majority of sentences.
    """
    return phrase_signs + word_signs


async def text_to_sasl_signs(text: str, language: str | None = None) -> dict:
    """Convert text → SASL-ordered sign names + gloss text.

    Pipeline order (fixes the hallucination problem from LLM-first ordering):
      0. Pre-translate non-English → English  (FEAT-5)
      1. Normalise contractions + SA slang
      2. Extract known PHRASE_MAP entries  (deterministic, no LLM)
      3. Rule-based SASL transform for remaining words
      4. LLM (Ollama) only when rule-based fails or remaining text is complex
      5. Raw word-map fallback as last resort

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

    # ── Step 0: Pre-translate non-English input (FEAT-5) ────────────────
    source_language = None
    original_input = None
    if language and language.lower() not in ENGLISH_LANG_CODES:
        source_language = language
        original_input = text
        text = await _translate_to_english(text, language)

    pipeline_start = _time.monotonic()

    def _build_result(signs, gloss_text, english, **extras):
        result = {
            "signs": signs,
            "text": gloss_text,
            "original_english": english,
        }
        if source_language:
            result["source_language"] = source_language
        if original_input:
            result["original_input"] = original_input
        result.update(extras)
        return result

    # ── Step 1: Normalise contractions and SA slang ──────────────────────
    text = _normalize_informal(text)

    # ── Step 1.5: Offline phrase library (FEAT-2) ───────────────────────
    # Checked AFTER normalisation so contractions expand first:
    # "i'm in pain" → "i am in pain" → matches the offline entry.
    _text_lower = text.lower().strip()
    if _text_lower in _OFFLINE_PHRASES:
        _signs = _OFFLINE_PHRASES[_text_lower]
        _gloss = " ".join(_signs)
        logger.info("[SASL] Offline phrase match: '%s' → '%s'", _text_lower, _gloss)
        return _build_result(_signs, _gloss, text)

    # ── Step 2: Phrase extraction — deterministic, zero LLM involvement ──
    phrase_signs, remaining_text = _extract_phrases(text)

    if not remaining_text:
        # Entire input resolved to known phrases — return immediately
        gloss = " ".join(phrase_signs)
        logger.info("[SASL] Phrases only: '%s' → '%s'", text[:50], gloss)
        return _build_result(phrase_signs, gloss, text)

    # ── Steps 3–5 operate on remaining_text (phrases already extracted) ──

    # Ensure the transformer singleton is initialised
    if _sasl_transformer is None:
        from sasl_transformer.transformer import SASLTransformer
        _sasl_transformer = SASLTransformer()

    from sasl_transformer.models import TranslationRequest

    # ── Step 3: Rule-based SASL transform (offline, no network needed) ───
    try:
        tier_start = _time.monotonic()
        rule_response = _sasl_transformer.translate_with_rules(
            remaining_text, TranslationRequest(english_text=remaining_text)
        )
        rule_signs = [tok.gloss for tok in rule_response.tokens]
        elapsed_ms = (_time.monotonic() - tier_start) * 1000
        # Only return early if rule-based actually produced signs for the remaining
        # text.  If rule_signs is empty (all remaining words unknown), fall through
        # to LLM even when phrase_signs is non-empty — we don't want to silently
        # drop the untranslated remainder.
        if rule_signs:
            all_signs = _merge_ordered(phrase_signs, rule_signs)
            gloss = " ".join(all_signs)
            logger.info("[SASL] Phrase+Rules %.0fms: '%s' → '%s'", elapsed_ms, text[:50], gloss)
            return _build_result(
                all_signs, gloss, text,
                non_manual_markers=rule_response.non_manual_markers or [],
            )
        logger.debug("[SASL] Rules produced no signs for remaining text — trying LLM")
    except Exception as rule_err:
        logger.warning("[SASL] Rule-based failed: %s", rule_err)

    # ── Step 4: LLM (Ollama) — only for complex/ambiguous remaining text ─
    try:
        tier_start = _time.monotonic()
        response = await _sasl_transformer.translate(
            TranslationRequest(english_text=remaining_text)
        )
        llm_signs = [tok.gloss for tok in response.tokens]
        elapsed_ms = (_time.monotonic() - tier_start) * 1000
        # Same logic: only return early if LLM produced signs for remaining text.
        if llm_signs:
            all_signs = _merge_ordered(phrase_signs, llm_signs)
            gloss = " ".join(all_signs)
            logger.info("[SASL] Phrase+LLM %.0fms: '%s' → '%s'", elapsed_ms, text[:50], gloss)
            return _build_result(
                all_signs, gloss, text,
                non_manual_markers=response.non_manual_markers or [],
            )
    except Exception as exc:
        logger.warning("[SASL] LLM failed: %s", exc)

    # ── Step 5: Raw word-map — last resort ────────────────────────────────
    try:
        tier_start = _time.monotonic()
        from backend.services.ollama_client import classify_text_to_signs
        word_signs = await classify_text_to_signs(remaining_text)
        all_signs = _merge_ordered(phrase_signs, word_signs)
        elapsed_ms = (_time.monotonic() - tier_start) * 1000
        total_ms = (_time.monotonic() - pipeline_start) * 1000
        logger.info(
            "[SASL] Phrase+Raw %.0fms (total %.0fms): '%s' → %s",
            elapsed_ms, total_ms, text[:50], all_signs,
        )
        return _build_result(all_signs, " ".join(all_signs), text)
    except Exception as fallback_err:
        total_ms = (_time.monotonic() - pipeline_start) * 1000
        logger.error(
            "[SASL] All tiers failed (%.0fms): '%s' — %s",
            total_ms, text[:50], fallback_err,
        )
        # Return whatever phrases we did extract rather than empty
        return _build_result(phrase_signs, " ".join(phrase_signs), text)

