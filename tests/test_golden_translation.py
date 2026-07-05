"""
Golden translation gate (MASTER_PLAN Phase 1 — the Definition of Working).

Runs every fixture in tests/golden/translation_cases.json through the
DETERMINISTIC rules pipeline (no Ollama, no network) and scores required
signs, forbidden signs, markers, word order, and avatar-library compliance.

Gates:
- every `critical` case must pass fully
- `high` cases must pass fully (they were verified against real output)
- `exploratory` cases only assert their named expectations (known gaps)
- the aggregate baseline is printed so regressions are visible in CI logs

Run with: pytest tests/test_golden_translation.py -v
"""

import pytest

from sasl_transformer.models import TranslationRequest
from sasl_transformer.transformer import SASLTransformer

from tests.golden import scoring

CASES = scoring.load_cases("translation_cases.json")


@pytest.fixture(scope="module")
def transformer():
    return SASLTransformer()


def _translate(transformer, text):
    response = transformer.translate_with_rules(text, TranslationRequest(english_text=text))
    return [tok.gloss for tok in response.tokens]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_golden_case(case, transformer):
    glosses = _translate(transformer, case["input_text"])
    result = scoring.score_case(case, glosses)
    assert result["passed"], (
        f"{case['id']} failed: missing={result['missing_required']} "
        f"forbidden={result['forbidden_hits']} markers={result['missing_markers']} "
        f"order={result['order_violations']} unknown={result['unknown_signs']} "
        f"glosses={result['glosses']}"
    )


def test_baseline_summary(transformer, capsys):
    """Not a gate — prints the rules-only baseline so CI logs carry the number to beat."""
    results = [
        scoring.score_case(case, _translate(transformer, case["input_text"]))
        for case in CASES
    ]
    summary = scoring.summarize(results)
    with capsys.disabled():
        print(
            f"\n[GOLDEN BASELINE] rules-only: {summary['cases_passed']}/{summary['cases_total']} passed, "
            f"critical {summary['critical_passed']}/{summary['critical_total']}, "
            f"mean required-sign recall {summary['mean_required_recall']}"
        )
    # The floor: criticals may never regress below full pass.
    assert summary["critical_passed"] == summary["critical_total"]
