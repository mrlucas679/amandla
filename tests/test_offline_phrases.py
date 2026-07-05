"""
Tests for the offline phrase library tier (mined from rescue/dev-2026-07).

Proves:
- exact phrase match bypasses all other tiers (Tier 0)
- contraction/SA-slang normalisation feeds the phrase match
- punctuation does not break matching
- no copula glosses (AM/IS/ARE) remain in the phrase data
- non-phrase input still flows to the rules tier

Run with: pytest tests/test_offline_phrases.py -v
No Ollama needed — phrase and rules tiers are fully offline.
"""

import asyncio

from backend.services import sasl_pipeline


def _run(text):
    return asyncio.run(sasl_pipeline.text_to_sasl_signs(text))


def test_phrases_loaded():
    assert len(sasl_pipeline._OFFLINE_PHRASES) >= 50


def test_exact_phrase_match():
    result = _run("I need help")
    assert result["signs"] == ["HELP", "NEED", "I"]


def test_punctuation_does_not_break_match():
    result = _run("I need help!")
    assert result["signs"] == ["HELP", "NEED", "I"]


def test_contraction_normalisation_feeds_phrase_match():
    """'I'm hungry' must expand to 'i am hungry' and hit the phrase entry."""
    result = _run("I'm hungry")
    assert result["signs"] == ["HUNGRY", "I"]


def test_sa_slang_normalisation():
    """'Howzit' expands to the greeting phrase before translation."""
    result = _run("Howzit")
    assert "HELLO" in result["signs"]


def test_no_copula_glosses_in_phrase_data():
    """English copulas are not SASL signs and must never be glossed."""
    for phrase, signs in sasl_pipeline._OFFLINE_PHRASES.items():
        assert "AM" not in signs, f"{phrase!r} glosses the copula AM"
        assert "IS" not in signs, f"{phrase!r} glosses the copula IS"
        assert "ARE" not in signs, f"{phrase!r} glosses the copula ARE"


def test_non_phrase_falls_through_to_rules():
    result = _run("Tomorrow I will go to the doctor")
    assert result["signs"][0] == "TOMORROW", "rules tier should still apply time-first order"
    assert "WILL" in result["signs"]


def test_emergency_phrase():
    result = _run("This is an emergency")
    assert result["signs"] == ["EMERGENCY"]
