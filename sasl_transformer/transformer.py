"""
SASL Transformer — the core translation engine.

Takes English text (from Whisper STT) and converts it to SASL gloss
notation using the local Ollama model. Falls back to rule-based conversion
if Ollama is unavailable.

Flow:
    1. Receive English sentence
    2. Send to Ollama with SASL grammar rules (system prompt)
    3. Parse the structured JSON response
    4. Check each token against the sign library
    5. Return TranslationResponse with tokens, gloss text, and metadata
"""

import json
import logging
import re
from collections import OrderedDict
from typing import Optional

from sasl_transformer.config import settings
from sasl_transformer.grammar_rules import (
    SASL_SYSTEM_PROMPT,
    ARTICLES_TO_DROP,
    AUXILIARY_VERBS_TO_DROP,
    PREPOSITIONS_TO_DROP,
    TIME_WORDS,
    QUESTION_WORDS,
    IRREGULAR_VERB_BASE_FORMS,
)
from sasl_transformer.models import (
    GlossToken,
    SignType,
    TranslationRequest,
    TranslationResponse,
)
from sasl_transformer.sign_library import SignLibrary

logger = logging.getLogger(__name__)


class SASLTransformer:
    """
    Converts English sentences to SASL gloss notation.

    Uses the local Ollama model as the primary translation engine, with a
    rule-based fallback for when Ollama is unavailable.

    Usage:
        transformer = SASLTransformer()
        response = await transformer.translate("I went to the store yesterday")
        print(response.gloss_text)  # "YESTERDAY STORE I GO FINISH"
        print(response.tokens)      # List of GlossTokens for the avatar
    """

    def __init__(
        self,
        sign_library_path: Optional[str] = None,
    ):
        """
        Initialise the SASL transformer.

        Args:
            sign_library_path: Path to the sign library JSON.
                Defaults to the path in settings.
        """
        # Load the sign library
        lib_path = sign_library_path or settings.sign_library_path
        self._sign_library = SignLibrary(lib_path)

        # Simple LRU cache for repeated translations
        self._cache: OrderedDict[str, TranslationResponse] = OrderedDict()
        self._cache_enabled = settings.sasl_cache_enabled
        self._cache_max_size = settings.sasl_cache_max_size

        logger.info(
            "SASL Transformer initialised — model: %s @ %s, library: %d signs, cache: %s",
            settings.ollama_model,
            settings.ollama_base_url,
            self._sign_library.total_signs,
            "enabled" if self._cache_enabled else "disabled",
        )

    @property
    def sign_library(self) -> SignLibrary:
        """Access the sign library directly (for adding signs, etc.)."""
        return self._sign_library

    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        """
        Translate an English sentence into SASL gloss notation.

        This is the main method your app calls. It:
        1. Checks the cache for repeated sentences
        2. Calls the Claude API for grammar transformation
        3. Falls back to rule-based conversion on API failure
        4. Checks each token against the sign library
        5. Returns the full TranslationResponse

        Args:
            request: TranslationRequest containing the English text.

        Returns:
            TranslationResponse with gloss text, tokens, and metadata.
        """
        english_text = request.english_text.strip()

        if not english_text:
            return self._empty_response(english_text)

        # Check cache first
        cache_key = f"{english_text}|{request.include_non_manual}"
        if self._cache_enabled and cache_key in self._cache:
            logger.debug("Cache hit for: %s", english_text[:50])
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]

        # Try LLM-based translation first
        try:
            response = await self._translate_with_llm(english_text, request)
            logger.info(
                "LLM translation: '%s' → '%s'",
                english_text[:50],
                response.gloss_text,
            )
        except Exception as e:
            logger.warning(
                "LLM translation failed, using fallback: %s", e,
            )
            response = self._translate_with_rules(english_text, request)
            logger.info(
                "Fallback translation: '%s' → '%s'",
                english_text[:50],
                response.gloss_text,
            )

        # Enrich tokens with sign library data
        response = self._enrich_with_library(response)

        # Cache the result
        if self._cache_enabled:
            self._cache[cache_key] = response
            # Evict oldest if cache is full
            while len(self._cache) > self._cache_max_size:
                self._cache.popitem(last=False)

        return response

    async def translate_text(self, english_text: str) -> TranslationResponse:
        """
        Convenience method — translate a plain string.

        Args:
            english_text: English sentence to translate.

        Returns:
            TranslationResponse with SASL gloss.
        """
        request = TranslationRequest(english_text=english_text)
        return await self.translate(request)

    async def _translate_with_llm(
        self,
        english_text: str,
        request: TranslationRequest,
    ) -> TranslationResponse:
        """
        Use the local Ollama model to translate English → SASL gloss.

        Sends the SASL grammar system prompt + user text to Ollama's
        /api/generate endpoint. This is the primary and most accurate
        translation method when Ollama is running.

        Args:
            english_text: The English sentence to translate.
            request: The full translation request with options.

        Returns:
            TranslationResponse with gloss text and tokens.

        Raises:
            RuntimeError: If Ollama is unreachable or returns an error.
        """
        import httpx
        import asyncio

        # Build the user message with optional context
        user_message = f"Convert this English sentence to SASL gloss:\n\n{english_text}"
        if request.context:
            user_message = (
                f"Previous context: {request.context}\n\n"
                f"Convert this English sentence to SASL gloss:\n\n{english_text}"
            )

        # Combine system prompt + user message into one prompt for Ollama
        full_prompt = f"{SASL_SYSTEM_PROMPT}\n\n{user_message}"

        # Call Ollama's local /api/generate endpoint
        ollama_url = f"{settings.ollama_base_url}/api/generate"
        request_body = {
            "model": settings.ollama_model,
            "prompt": full_prompt,
            "stream": False,
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as http_client:
                response = await http_client.post(ollama_url, json=request_body)

            if response.status_code != 200:
                raise RuntimeError(
                    f"Ollama returned status {response.status_code} — is 'ollama serve' running?"
                )

            # Extract text from Ollama's JSON response
            raw_response = response.json().get("response", "").strip()

            if not raw_response:
                raise RuntimeError("Ollama returned an empty response")

        except httpx.ConnectError:
            raise RuntimeError(
                "Cannot connect to Ollama — make sure 'ollama serve' is running on "
                f"{settings.ollama_base_url}"
            )
        except httpx.TimeoutException:
            raise RuntimeError("Ollama request timed out — the model may be loading")

        # Parse the JSON response from the LLM
        parsed = self._parse_llm_response(raw_response)

        # Build tokens list
        tokens = []
        for i, token_data in enumerate(parsed.get("tokens", [])):
            tokens.append(
                GlossToken(
                    gloss=token_data["gloss"].upper(),
                    original_english=token_data.get("original_english", ""),
                    sign_type=SignType.SIGN,  # Will be updated by _enrich_with_library
                    in_library=False,         # Will be updated by _enrich_with_library
                    position=i,
                    notes=token_data.get("notes", ""),
                )
            )

        # Build non-manual markers list
        non_manual = []
        if request.include_non_manual:
            non_manual = parsed.get("non_manual_markers", [])

        return TranslationResponse(
            original_english=english_text,
            gloss_text=parsed.get("gloss_text", ""),
            tokens=tokens,
            non_manual_markers=non_manual,
            unknown_words=[],  # Will be populated by _enrich_with_library
            translation_notes=parsed.get("translation_notes", ""),
        )

    def _parse_llm_response(self, raw: str) -> dict:
        """
        Parse the JSON response from the LLM (Ollama).

        Handles edge cases like markdown code fences around the JSON.
        """
        # Strip markdown code fences if present
        cleaned = raw.strip()
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse LLM JSON response: %s\nRaw response: %s",
                e,
                raw[:500],
            )
            raise ValueError(f"Invalid JSON from LLM: {e}") from e

    def _translate_with_rules(
        self,
        english_text: str,
        request: TranslationRequest,
    ) -> TranslationResponse:
        """
        Rule-based fallback translator.

        Less accurate than the LLM, but works offline. Applies basic
        SASL grammar rules: drop articles, reorder time words, convert
        verbs to base form, SOV ordering.
        """
        words = english_text.lower().split()

        # Phase 1: Separate time words, question words, and content words
        time_markers = []
        question_markers = []
        content_words = []
        has_past_tense = False

        for word in words:
            clean = word.strip(".,!?;:'\"")

            if not clean:
                continue

            # Drop articles
            if clean in ARTICLES_TO_DROP:
                continue

            # Drop auxiliary verbs but detect tense
            if clean in AUXILIARY_VERBS_TO_DROP:
                if clean in ("was", "were", "did", "had"):
                    has_past_tense = True
                continue

            # Drop most prepositions
            if clean in PREPOSITIONS_TO_DROP:
                continue

            # Collect time words
            if clean in TIME_WORDS:
                time_markers.append(clean.upper())
                if clean in ("yesterday", "ago", "last"):
                    has_past_tense = True
                continue

            # Collect question words
            if clean in QUESTION_WORDS:
                question_markers.append(clean.upper())
                continue

            # Convert verbs to base form
            base = self._to_base_form(clean)
            if base != clean:
                has_past_tense = True

            content_words.append(base.upper())

        # Phase 2: Reorder — Time + Content (SOV approximate) + Aspect + Question
        gloss_parts = []

        # Time markers go first
        gloss_parts.extend(time_markers)

        # Content words (basic SOV: try to move verbs to end)
        # This is a rough approximation — the LLM does this much better
        gloss_parts.extend(content_words)

        # Past tense marker
        if has_past_tense and "FINISH" not in gloss_parts:
            gloss_parts.append("FINISH")

        # Question words go last
        gloss_parts.extend(question_markers)

        # Build tokens
        tokens = []
        for i, gloss in enumerate(gloss_parts):
            tokens.append(
                GlossToken(
                    gloss=gloss,
                    original_english=gloss.lower(),
                    sign_type=SignType.SIGN,
                    in_library=False,
                    position=i,
                    notes="",
                )
            )

        # Non-manual markers for questions
        non_manual = []
        if request.include_non_manual and question_markers:
            if any(q in question_markers for q in ["WHO", "WHAT", "WHERE", "WHEN", "WHY", "HOW"]):
                non_manual = ["furrowed brows", "head tilt forward"]
            else:
                non_manual = ["raised eyebrows"]

        gloss_text = " ".join(gloss_parts)

        return TranslationResponse(
            original_english=english_text,
            gloss_text=gloss_text,
            tokens=tokens,
            non_manual_markers=non_manual,
            unknown_words=[],
            translation_notes="Fallback rule-based translation (LLM unavailable). Word order may be approximate.",
        )

    def _to_base_form(self, word: str) -> str:
        """
        Convert a word to its base/infinitive form.

        Handles irregular verbs via lookup table, and regular
        verbs via suffix stripping (-ed, -ing, -s).
        """
        clean = word.lower().strip(".,!?;:'\"")

        # Check irregular verbs first
        if clean in IRREGULAR_VERB_BASE_FORMS:
            return IRREGULAR_VERB_BASE_FORMS[clean]

        # Regular verb suffix stripping
        if clean.endswith("ing"):
            # running → run (double consonant)
            stem = clean[:-3]
            if len(stem) >= 2 and stem[-1] == stem[-2]:
                return stem[:-1]
            # driving → drive (silent e)
            if stem and stem[-1] not in "aeiou":
                return stem + "e"
            return stem if stem else clean

        if clean.endswith("ed"):
            stem = clean[:-2]
            if stem and stem[-1] == stem[-2]:
                return stem[:-1]
            if not stem:
                return clean
            return stem

        if clean.endswith("ies"):
            return clean[:-3] + "y"

        if clean.endswith("es") and len(clean) > 3:
            return clean[:-2]

        if clean.endswith("s") and not clean.endswith("ss") and len(clean) > 2:
            return clean[:-1]

        return clean

    def _enrich_with_library(self, response: TranslationResponse) -> TranslationResponse:
        """
        Check each token against the sign library and update sign_type
        and in_library fields. Builds the unknown_words list.
        """
        unknown_words = []
        enriched_tokens = []

        for token in response.tokens:
            # Check the sign library
            if self._sign_library.has_sign(token.gloss):
                enriched = token.model_copy(
                    update={
                        "in_library": True,
                        "sign_type": SignType.SIGN,
                    }
                )
            elif token.gloss.isdigit():
                enriched = token.model_copy(
                    update={
                        "in_library": False,
                        "sign_type": SignType.NUMBER,
                    }
                )
            else:
                enriched = token.model_copy(
                    update={
                        "in_library": False,
                        "sign_type": SignType.FINGERSPELL,
                    }
                )
                unknown_words.append(token.gloss)

            enriched_tokens.append(enriched)

        return response.model_copy(
            update={
                "tokens": enriched_tokens,
                "unknown_words": unknown_words,
            }
        )

    def _empty_response(self, original: str) -> TranslationResponse:
        """Return an empty response for empty input."""
        return TranslationResponse(
            original_english=original,
            gloss_text="",
            tokens=[],
            non_manual_markers=[],
            unknown_words=[],
            translation_notes="Empty input received.",
        )

    def clear_cache(self) -> int:
        """Clear the translation cache. Returns number of entries cleared."""
        count = len(self._cache)
        self._cache.clear()
        logger.info("Cleared %d cached translations", count)
        return count
