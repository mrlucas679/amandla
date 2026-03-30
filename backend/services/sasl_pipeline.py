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

All AI runs locally via Ollama — no cloud API keys needed.
"""

import logging

logger = logging.getLogger(__name__)

# Module-level SASL transformer singleton (lazy init on first use)
_sasl_transformer = None


async def text_to_sasl_signs(text: str) -> dict:
    """Convert English text → SASL-ordered sign names + gloss text.

    Args:
        text: English sentence from hearing user (e.g. "I went to the store yesterday").

    Returns:
        {
            signs:            list of SASL sign name strings,
            text:             SASL gloss string,
            original_english: the original English input
        }
    """
    global _sasl_transformer
    if not text:
        return {"signs": [], "text": "", "original_english": ""}

    # Ensure the transformer singleton is initialised once for all paths below
    if _sasl_transformer is None:
        from sasl_transformer.transformer import SASLTransformer
        _sasl_transformer = SASLTransformer()

    # 1. Try SASL transformer (proper grammar ordering via Ollama)
    try:
        from sasl_transformer.models import TranslationRequest
        response = await _sasl_transformer.translate(TranslationRequest(english_text=text))
        sign_names = [tok.gloss for tok in response.tokens]
        if sign_names:
            logger.info("[SASL] '%s' → '%s'", text[:50], response.gloss_text)
            return {
                "signs": sign_names,
                "text": response.gloss_text,
                "original_english": text,
            }
    except Exception as exc:
        logger.warning("[SASL] Transformer failed, falling back: %s", exc)

    # 2. Grammar-aware rule-based fallback (no network needed — applies all 13 SASL rules)
    try:
        from sasl_transformer.models import TranslationRequest
        rule_response = _sasl_transformer.translate_with_rules(
            text, TranslationRequest(english_text=text)
        )
        rule_signs = [tok.gloss for tok in rule_response.tokens]
        if rule_signs:
            logger.info("[SASL] Rule-based fallback: '%s' → '%s'", text[:50], rule_response.gloss_text)
            return {
                "signs": rule_signs,
                "text": rule_response.gloss_text,
                "original_english": text,
            }
    except Exception as rule_err:
        logger.warning("[SASL] Rule-based fallback failed: %s", rule_err)

    # 3. Last resort: raw word list (no grammar, but better than nothing)
    from backend.services.ollama_client import classify_text_to_signs
    sign_names = await classify_text_to_signs(text)
    return {
        "signs": sign_names,
        "text": " ".join(sign_names),
        "original_english": text,
    }

