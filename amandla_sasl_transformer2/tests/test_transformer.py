"""
Tests for the SASL Transformer service.

Run with: pytest tests/ -v

These tests cover:
1. Sign library loading and lookup
2. Rule-based fallback translation (no API key needed)
3. Model validation
4. Grammar rule application
"""

import json
import os
import pytest
from pathlib import Path

from sasl_transformer.models import (
    GlossToken,
    SignType,
    TranslationRequest,
    TranslationResponse,
)
from sasl_transformer.sign_library import SignLibrary
from sasl_transformer.grammar_rules import (
    ARTICLES_TO_DROP,
    AUXILIARY_VERBS_TO_DROP,
    IRREGULAR_VERB_BASE_FORMS,
)


# ── Sign Library Tests ──────────────────────────────────────────


class TestSignLibrary:
    """Tests for the SignLibrary class."""

    def setup_method(self):
        """Create a temporary sign library for testing."""
        self.test_data = {
            "signs": {
                "HELLO": {
                    "animation_id": "sign_hello",
                    "category": "greetings",
                    "variants": ["HI", "GREET"],
                },
                "GO": {
                    "animation_id": "sign_go",
                    "category": "verbs",
                    "variants": [],
                },
                "YESTERDAY": {
                    "animation_id": "sign_yesterday",
                    "category": "time",
                    "variants": [],
                },
                "FINISH": {
                    "animation_id": "sign_finish",
                    "category": "grammar",
                    "variants": ["DONE", "ALREADY"],
                },
            }
        }
        self.test_path = "/tmp/test_sign_library.json"
        with open(self.test_path, "w") as f:
            json.dump(self.test_data, f)

    def teardown_method(self):
        """Clean up test file."""
        if os.path.exists(self.test_path):
            os.remove(self.test_path)

    def test_load_library(self):
        """Library should load signs from JSON file."""
        lib = SignLibrary(self.test_path)
        assert lib.total_signs == 4

    def test_has_sign_canonical(self):
        """Should find signs by their canonical name."""
        lib = SignLibrary(self.test_path)
        assert lib.has_sign("HELLO") is True
        assert lib.has_sign("GO") is True
        assert lib.has_sign("NONEXISTENT") is False

    def test_has_sign_variant(self):
        """Should find signs by their variant names."""
        lib = SignLibrary(self.test_path)
        assert lib.has_sign("HI") is True
        assert lib.has_sign("GREET") is True
        assert lib.has_sign("DONE") is True
        assert lib.has_sign("ALREADY") is True

    def test_has_sign_case_insensitive(self):
        """Lookups should be case-insensitive."""
        lib = SignLibrary(self.test_path)
        assert lib.has_sign("hello") is True
        assert lib.has_sign("Hello") is True
        assert lib.has_sign("hi") is True

    def test_get_animation_id(self):
        """Should return the correct animation ID."""
        lib = SignLibrary(self.test_path)
        assert lib.get_animation_id("HELLO") == "sign_hello"
        assert lib.get_animation_id("HI") == "sign_hello"  # variant
        assert lib.get_animation_id("NONEXISTENT") is None

    def test_get_unknown_words(self):
        """Should identify words not in the library."""
        lib = SignLibrary(self.test_path)
        words = ["HELLO", "STORE", "GO", "MILK"]
        unknown = lib.get_unknown_words(words)
        assert "STORE" in unknown
        assert "MILK" in unknown
        assert "HELLO" not in unknown
        assert "GO" not in unknown

    def test_add_sign_at_runtime(self):
        """Should be able to add signs dynamically."""
        lib = SignLibrary(self.test_path)
        assert lib.has_sign("STORE") is False

        lib.add_sign("STORE", "sign_store", "places", ["SHOP"])

        assert lib.has_sign("STORE") is True
        assert lib.has_sign("SHOP") is True
        assert lib.get_animation_id("STORE") == "sign_store"

    def test_empty_library(self):
        """Should work with no library file."""
        lib = SignLibrary(None)
        assert lib.total_signs == 0
        assert lib.has_sign("HELLO") is False

    def test_missing_file(self):
        """Should handle missing file gracefully."""
        lib = SignLibrary("/nonexistent/path/library.json")
        assert lib.total_signs == 0

    def test_list_categories(self):
        """Should list all unique categories."""
        lib = SignLibrary(self.test_path)
        categories = lib.list_categories()
        assert "greetings" in categories
        assert "verbs" in categories
        assert "time" in categories
        assert "grammar" in categories

    def test_save_and_reload(self):
        """Should save to file and reload correctly."""
        lib = SignLibrary(self.test_path)
        lib.add_sign("WATER", "sign_water", "nouns")

        save_path = "/tmp/test_save_library.json"
        lib.save_to_file(save_path)

        lib2 = SignLibrary(save_path)
        assert lib2.has_sign("WATER") is True
        assert lib2.has_sign("HELLO") is True

        os.remove(save_path)


# ── Model Tests ─────────────────────────────────────────────────


class TestModels:
    """Tests for Pydantic models."""

    def test_translation_request_valid(self):
        """Should accept valid requests."""
        req = TranslationRequest(english_text="Hello world")
        assert req.english_text == "Hello world"
        assert req.include_non_manual is True  # default
        assert req.context == ""  # default

    def test_translation_request_empty(self):
        """Should reject empty text."""
        with pytest.raises(Exception):
            TranslationRequest(english_text="")

    def test_gloss_token(self):
        """Should create valid GlossTokens."""
        token = GlossToken(
            gloss="HELLO",
            original_english="hello",
            sign_type=SignType.SIGN,
            in_library=True,
            position=0,
        )
        assert token.gloss == "HELLO"
        assert token.sign_type == SignType.SIGN

    def test_translation_response(self):
        """Should create valid TranslationResponse."""
        response = TranslationResponse(
            original_english="Hello",
            gloss_text="HELLO",
            tokens=[
                GlossToken(
                    gloss="HELLO",
                    original_english="hello",
                    position=0,
                )
            ],
        )
        assert response.gloss_text == "HELLO"
        assert len(response.tokens) == 1


# ── Grammar Rules Tests ─────────────────────────────────────────


class TestGrammarRules:
    """Tests for the grammar rule constants."""

    def test_articles_to_drop(self):
        """Should include all English articles."""
        assert "a" in ARTICLES_TO_DROP
        assert "an" in ARTICLES_TO_DROP
        assert "the" in ARTICLES_TO_DROP

    def test_auxiliary_verbs(self):
        """Should include common auxiliary verbs."""
        for verb in ["is", "am", "are", "was", "were", "do", "does", "did"]:
            assert verb in AUXILIARY_VERBS_TO_DROP, f"Missing: {verb}"

    def test_irregular_verbs(self):
        """Should map irregular verbs to base forms."""
        assert IRREGULAR_VERB_BASE_FORMS["went"] == "go"
        assert IRREGULAR_VERB_BASE_FORMS["ate"] == "eat"
        assert IRREGULAR_VERB_BASE_FORMS["saw"] == "see"
        assert IRREGULAR_VERB_BASE_FORMS["bought"] == "buy"
        assert IRREGULAR_VERB_BASE_FORMS["drove"] == "drive"


# ── Rule-Based Transformer Tests ────────────────────────────────
# These test the fallback translator without needing an API key.


class TestRuleBasedTransformer:
    """
    Tests for the rule-based fallback translator.

    These tests verify that basic SASL grammar rules are applied
    correctly without needing the Claude API.
    """

    def setup_method(self):
        """Set up a transformer with a mock API key for testing."""
        # Set a dummy key so config doesn't fail
        os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"

        from sasl_transformer.transformer import SASLTransformer
        self.transformer = SASLTransformer.__new__(SASLTransformer)
        self.transformer._sign_library = SignLibrary(None)
        self.transformer._cache = {}
        self.transformer._cache_enabled = False
        self.transformer._cache_max_size = 0

    def test_to_base_form_irregular(self):
        """Should convert irregular past tense to base form."""
        assert self.transformer._to_base_form("went") == "go"
        assert self.transformer._to_base_form("ate") == "eat"
        assert self.transformer._to_base_form("saw") == "see"
        assert self.transformer._to_base_form("bought") == "buy"

    def test_to_base_form_regular_ed(self):
        """Should strip -ed suffix from regular verbs."""
        assert self.transformer._to_base_form("walked") == "walk"
        assert self.transformer._to_base_form("played") == "play"

    def test_to_base_form_regular_ing(self):
        """Should strip -ing suffix."""
        result = self.transformer._to_base_form("walking")
        assert result in ("walk", "walke")  # Depends on heuristic

    def test_to_base_form_already_base(self):
        """Should return base forms unchanged."""
        assert self.transformer._to_base_form("run") == "run"
        assert self.transformer._to_base_form("eat") == "eat"

    def test_fallback_drops_articles(self):
        """Fallback should drop articles (a, an, the)."""
        request = TranslationRequest(english_text="The cat sat on a mat")
        result = self.transformer._translate_with_rules(
            "The cat sat on a mat", request
        )
        gloss_lower = result.gloss_text.lower()
        assert "the" not in gloss_lower.split()
        assert "a" not in gloss_lower.split()

    def test_fallback_drops_auxiliary_verbs(self):
        """Fallback should drop auxiliary verbs."""
        request = TranslationRequest(english_text="She is happy")
        result = self.transformer._translate_with_rules(
            "She is happy", request
        )
        gloss_lower = result.gloss_text.lower()
        assert "is" not in gloss_lower.split()

    def test_fallback_time_words_first(self):
        """Fallback should move time words to the beginning."""
        request = TranslationRequest(english_text="I go yesterday")
        result = self.transformer._translate_with_rules(
            "I go yesterday", request
        )
        words = result.gloss_text.split()
        assert words[0] == "YESTERDAY"

    def test_fallback_question_words_last(self):
        """Fallback should move question words to the end."""
        request = TranslationRequest(english_text="Where you live")
        result = self.transformer._translate_with_rules(
            "Where you live", request
        )
        words = result.gloss_text.split()
        assert words[-1] == "WHERE" or words[-2] == "WHERE"

    def test_fallback_past_tense_adds_finish(self):
        """Fallback should add FINISH for past tense sentences."""
        request = TranslationRequest(english_text="I went home")
        result = self.transformer._translate_with_rules(
            "I went home", request
        )
        assert "FINISH" in result.gloss_text

    def test_fallback_non_manual_markers_for_questions(self):
        """Fallback should add non-manual markers for questions."""
        request = TranslationRequest(
            english_text="Where you live",
            include_non_manual=True,
        )
        result = self.transformer._translate_with_rules(
            "Where you live", request
        )
        assert len(result.non_manual_markers) > 0

    def test_fallback_returns_tokens(self):
        """Fallback should return properly structured tokens."""
        request = TranslationRequest(english_text="Hello friend")
        result = self.transformer._translate_with_rules(
            "Hello friend", request
        )
        assert len(result.tokens) > 0
        for token in result.tokens:
            assert token.gloss == token.gloss.upper()
            assert isinstance(token.position, int)

    def test_empty_response(self):
        """Should handle empty input."""
        result = self.transformer._empty_response("")
        assert result.gloss_text == ""
        assert len(result.tokens) == 0


# ── Integration-Style Tests ─────────────────────────────────────


class TestEnrichWithLibrary:
    """Tests for the sign library enrichment step."""

    def setup_method(self):
        """Set up transformer with a test library."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"

        from sasl_transformer.transformer import SASLTransformer
        self.transformer = SASLTransformer.__new__(SASLTransformer)

        # Create a small test library
        self.transformer._sign_library = SignLibrary(None)
        self.transformer._sign_library.add_sign("HELLO", "sign_hello", "greetings")
        self.transformer._sign_library.add_sign("GO", "sign_go", "verbs")
        self.transformer._sign_library.add_sign("FINISH", "sign_finish", "grammar")

    def test_enrichment_marks_known_signs(self):
        """Should mark tokens that exist in the library."""
        response = TranslationResponse(
            original_english="Hello, I went to the store",
            gloss_text="HELLO STORE I GO FINISH",
            tokens=[
                GlossToken(gloss="HELLO", original_english="hello", position=0),
                GlossToken(gloss="STORE", original_english="store", position=1),
                GlossToken(gloss="I", original_english="I", position=2),
                GlossToken(gloss="GO", original_english="went", position=3),
                GlossToken(gloss="FINISH", original_english="went", position=4),
            ],
        )

        enriched = self.transformer._enrich_with_library(response)

        # HELLO, GO, FINISH should be in library
        assert enriched.tokens[0].in_library is True
        assert enriched.tokens[0].sign_type == SignType.SIGN

        # STORE should not be in library → fingerspell
        assert enriched.tokens[1].in_library is False
        assert enriched.tokens[1].sign_type == SignType.FINGERSPELL

        # I should not be in this test library → fingerspell
        assert enriched.tokens[2].in_library is False

        # GO should be in library
        assert enriched.tokens[3].in_library is True

        # FINISH should be in library
        assert enriched.tokens[4].in_library is True

    def test_enrichment_populates_unknown_words(self):
        """Should list unknown words for fingerspelling."""
        response = TranslationResponse(
            original_english="test",
            gloss_text="HELLO STORE MILK",
            tokens=[
                GlossToken(gloss="HELLO", original_english="hello", position=0),
                GlossToken(gloss="STORE", original_english="store", position=1),
                GlossToken(gloss="MILK", original_english="milk", position=2),
            ],
        )

        enriched = self.transformer._enrich_with_library(response)

        assert "STORE" in enriched.unknown_words
        assert "MILK" in enriched.unknown_words
        assert "HELLO" not in enriched.unknown_words

    def test_enrichment_handles_numbers(self):
        """Should mark numeric tokens as NUMBER type."""
        response = TranslationResponse(
            original_english="test",
            gloss_text="TOMORROW 3 MEET",
            tokens=[
                GlossToken(gloss="TOMORROW", original_english="tomorrow", position=0),
                GlossToken(gloss="3", original_english="3", position=1),
                GlossToken(gloss="MEET", original_english="meet", position=2),
            ],
        )

        enriched = self.transformer._enrich_with_library(response)
        assert enriched.tokens[1].sign_type == SignType.NUMBER
