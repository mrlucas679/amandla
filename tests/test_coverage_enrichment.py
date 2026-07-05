"""
Tests for sign-coverage enrichment in the SASL Transformer.

Run with: pytest tests/test_coverage_enrichment.py -v

Covers the coverage-retry support added alongside keyframe animation:
1. _enrich_with_library — uncertain tokens force fingerspelling
2. _enrich_with_library — sign_coverage / fingerspelled_words population
3. _compute_coverage — ratio math and empty-input behaviour

No Ollama or network access needed.
"""

import json
import os
import tempfile

from sasl_transformer.models import (
    GlossToken,
    SignType,
    TranslationResponse,
)
from sasl_transformer.transformer import SASLTransformer


def _token(gloss, position, uncertain=False):
    """Build a raw (pre-enrichment) token the way _translate_with_llm does."""
    return GlossToken(
        gloss=gloss,
        original_english=gloss.lower(),
        sign_type=SignType.SIGN,
        in_library=False,
        position=position,
        uncertain=uncertain,
    )


def _response(tokens):
    return TranslationResponse(
        original_english=" ".join(t.original_english for t in tokens),
        gloss_text=" ".join(t.gloss for t in tokens),
        tokens=tokens,
        non_manual_markers=[],
        unknown_words=[],
        translation_notes="",
    )


class TestCoverageEnrichment:
    """Tests for _enrich_with_library and _compute_coverage."""

    def setup_method(self):
        """Create a transformer backed by a small temp sign library."""
        self.test_data = {
            "signs": {
                "HELLO": {"animation_id": "sign_hello", "category": "greetings", "variants": []},
                "GO": {"animation_id": "sign_go", "category": "verbs", "variants": []},
                "HOME": {"animation_id": "sign_home", "category": "places", "variants": []},
            }
        }
        self.test_path = os.path.join(tempfile.gettempdir(), "test_coverage_library.json")
        with open(self.test_path, "w") as f:
            json.dump(self.test_data, f)
        self.transformer = SASLTransformer(sign_library_path=self.test_path)

    def teardown_method(self):
        if os.path.exists(self.test_path):
            os.remove(self.test_path)

    def test_known_sign_marked_in_library(self):
        response = self.transformer._enrich_with_library(_response([_token("HELLO", 0)]))
        assert response.tokens[0].in_library is True
        assert response.tokens[0].sign_type == SignType.SIGN
        assert response.fingerspelled_words == []
        assert response.sign_coverage == 1.0

    def test_uncertain_token_forces_fingerspell_even_if_in_library(self):
        """An uncertain token must fingerspell even when the gloss matches the library."""
        response = self.transformer._enrich_with_library(
            _response([_token("HELLO", 0, uncertain=True)])
        )
        tok = response.tokens[0]
        assert tok.sign_type == SignType.FINGERSPELL
        assert tok.in_library is False
        assert "HELLO" in response.fingerspelled_words
        assert "HELLO" in response.unknown_words
        assert response.sign_coverage == 0.0

    def test_unknown_gloss_fingerspelled(self):
        response = self.transformer._enrich_with_library(_response([_token("XYLOPHONE", 0)]))
        assert response.tokens[0].sign_type == SignType.FINGERSPELL
        assert response.fingerspelled_words == ["XYLOPHONE"]
        assert response.sign_coverage == 0.0

    def test_digit_counts_as_number_not_fingerspell(self):
        response = self.transformer._enrich_with_library(_response([_token("42", 0)]))
        assert response.tokens[0].sign_type == SignType.NUMBER
        assert response.fingerspelled_words == []
        # NUMBER counts toward coverage (it is signed, not spelled letter-by-letter)
        assert response.sign_coverage == 1.0

    def test_sign_coverage_ratio(self):
        """2 known + 1 number of 4 tokens → coverage 0.75."""
        response = self.transformer._enrich_with_library(
            _response([
                _token("HELLO", 0),
                _token("GO", 1),
                _token("7", 2),
                _token("XYLOPHONE", 3),
            ])
        )
        assert response.sign_coverage == 0.75
        assert response.fingerspelled_words == ["XYLOPHONE"]

    def test_compute_coverage_matches_enrichment(self):
        response = self.transformer._enrich_with_library(
            _response([_token("HELLO", 0), _token("XYLOPHONE", 1)])
        )
        assert self.transformer._compute_coverage(response) == 0.5

    def test_compute_coverage_empty_tokens_is_full(self):
        """Empty input should never trigger the low-coverage retry."""
        assert self.transformer._compute_coverage(_response([])) == 1.0
