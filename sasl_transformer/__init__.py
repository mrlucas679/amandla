"""
SASL Transformer — English to South African Sign Language grammar converter.

This module converts English sentences (from Whisper STT) into SASL gloss notation,
which drives both the avatar animation queue and the on-screen SASL text display.

SASL Grammar Rules Applied:
    - Subject + Object + Verb (SOV) word order
    - Time/date markers moved to sentence start
    - Articles (a, an, the) dropped
    - Auxiliary verbs (is, am, are, was, were) dropped
    - All verbs converted to base form (no tenses)
    - Topic-Comment structure
    - Question words moved to end
    - Aspect markers (FINISH for past, WILL for future) at end
"""

from sasl_transformer.transformer import SASLTransformer
from sasl_transformer.models import (
    TranslationRequest,
    TranslationResponse,
    GlossToken,
)
from sasl_transformer.config import settings

__all__ = [
    "SASLTransformer",
    "TranslationRequest",
    "TranslationResponse",
    "GlossToken",
    "settings",
]
