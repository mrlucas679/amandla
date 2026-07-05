"""
Tests proving the D4 pipeline order from MASTER_PLAN.md:
deterministic rules run FIRST; the LLM is an optional assist consulted only
when rule coverage is low, and used only when it beats the rules' coverage.

Run with: pytest tests/test_pipeline_order.py -v
No Ollama or network access needed — the transformer singleton is faked.
"""

import asyncio

import pytest

from backend.services import sasl_pipeline
from sasl_transformer.models import GlossToken, SignType, TranslationResponse


def _response(glosses, coverage):
    tokens = [
        GlossToken(
            gloss=g,
            original_english=g.lower(),
            sign_type=SignType.SIGN,
            in_library=True,
            position=i,
        )
        for i, g in enumerate(glosses)
    ]
    return TranslationResponse(
        original_english=" ".join(g.lower() for g in glosses),
        gloss_text=" ".join(glosses),
        tokens=tokens,
        non_manual_markers=[],
        unknown_words=[],
        translation_notes="",
        sign_coverage=coverage,
    )


class FakeTransformer:
    """Records call order; returns pre-configured rule/LLM responses."""

    def __init__(self, rule_response, llm_response=None, llm_error=None):
        self.calls = []
        self._rule_response = rule_response
        self._llm_response = llm_response
        self._llm_error = llm_error

    def translate_with_rules(self, text, request):
        self.calls.append("rules")
        if isinstance(self._rule_response, Exception):
            raise self._rule_response
        return self._rule_response

    async def translate(self, request):
        self.calls.append("llm")
        if self._llm_error is not None:
            raise self._llm_error
        return self._llm_response


@pytest.fixture(autouse=True)
def _restore_singleton():
    original = sasl_pipeline._sasl_transformer
    yield
    sasl_pipeline._sasl_transformer = original


def _run(fake, text="hello you"):
    sasl_pipeline._sasl_transformer = fake
    return asyncio.run(sasl_pipeline.text_to_sasl_signs(text))


def test_rules_run_first_and_llm_skipped_on_good_coverage():
    """High rule coverage → the LLM must never be consulted."""
    fake = FakeTransformer(rule_response=_response(["HELLO", "YOU"], coverage=1.0))
    result = _run(fake)
    assert fake.calls == ["rules"], "LLM was consulted despite full rule coverage"
    assert result["signs"] == ["HELLO", "YOU"]
    assert result["sign_coverage"] == 1.0


def test_llm_consulted_when_rule_coverage_low():
    """Low rule coverage → LLM assist runs, and wins only by beating coverage."""
    fake = FakeTransformer(
        rule_response=_response(["HELLO", "XYLOPHONE"], coverage=0.5),
        llm_response=_response(["HELLO", "MUSIC"], coverage=1.0),
    )
    result = _run(fake)
    assert fake.calls == ["rules", "llm"], "rules must still run before the LLM"
    assert result["signs"] == ["HELLO", "MUSIC"]


def test_llm_result_rejected_when_it_does_not_beat_rules():
    """An LLM answer with equal-or-worse coverage is discarded — rules win."""
    fake = FakeTransformer(
        rule_response=_response(["HELLO", "XYLOPHONE"], coverage=0.5),
        llm_response=_response(["HELLO", "GUESS"], coverage=0.5),
    )
    result = _run(fake)
    assert fake.calls == ["rules", "llm"]
    assert result["signs"] == ["HELLO", "XYLOPHONE"], "rules output must be kept"


def test_rules_survive_llm_failure():
    """Ollama down → the rules result is returned untouched."""
    fake = FakeTransformer(
        rule_response=_response(["HELP", "ME"], coverage=0.5),
        llm_error=RuntimeError("ollama unreachable"),
    )
    result = _run(fake)
    assert fake.calls == ["rules", "llm"]
    assert result["signs"] == ["HELP", "ME"]


def test_threshold_constant_matches_plan():
    assert sasl_pipeline.LLM_ASSIST_COVERAGE_THRESHOLD == 0.70
