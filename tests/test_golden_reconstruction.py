"""
Golden sign-reconstruction gate (MASTER_PLAN Phase 1).

Runs deaf→hearing fixtures through the deterministic fallback
(simple_signs_to_english) and asserts INTENT preservation: expected concepts
present, forbidden inversions absent. Fluency is not scored — meaning is.

Run with: pytest tests/test_golden_reconstruction.py -v
"""

import pytest

from backend.services.sign_reconstruction import simple_signs_to_english

from tests.golden import scoring

CASES = scoring.load_cases("sign_reconstruction_cases.json")


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_reconstruction_case(case):
    text = simple_signs_to_english(case["input_signs"]).lower()

    assert text.strip(), f"{case['id']}: empty output for valid sign input"

    missing = [w for w in case["expected_text_contains"] if w.lower() not in text]
    assert not missing, f"{case['id']}: intent words {missing} missing from {text!r}"

    inversions = [w for w in case["forbidden_text_contains"] if w.lower() in text]
    assert not inversions, f"{case['id']}: forbidden phrase {inversions} present in {text!r}"
