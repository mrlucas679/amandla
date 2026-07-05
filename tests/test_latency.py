"""
Latency harness for the deterministic translation tiers (MASTER_PLAN Phase 1).

Measures the offline hot path — Tier 0 (phrase match) and Tier 1 (rules) —
over the golden fixture inputs and prints cold/warm-median/p95 so every CI
run carries the numbers.

The CI gates here are deliberately loose (an order of magnitude above the
observed baseline): they exist to catch pathological regressions — an
accidental network call, an O(n²) blowup, a model sneaking into the hot
path — not to benchmark runner hardware. The user-facing budgets in
MASTER_PLAN Section 4 (text→first-sign ≤ 1s end-to-end) are enforced at the
app level in Phase 2.

Run with: pytest tests/test_latency.py -v -s
"""

import asyncio
import statistics
import time

import pytest

from backend.services import sasl_pipeline

from tests.golden import scoring

# Loose CI gates — order-of-magnitude guards, not benchmarks.
PHRASE_TIER_P95_MS = 50.0
RULES_TIER_P95_MS = 250.0

_PHRASE_INPUTS = ["I need help", "This is an emergency", "I'm hungry", "Call the police"]
_RULES_INPUTS = [c["input_text"] for c in scoring.load_cases("translation_cases.json")]


def _measure(texts, repeats=5):
    """Return (cold_ms, warm_median_ms, warm_p95_ms) for the pipeline over texts."""

    async def run_all():
        timings = []
        for i in range(repeats):
            for text in texts:
                start = time.perf_counter()
                await sasl_pipeline.text_to_sasl_signs(text)
                timings.append((time.perf_counter() - start) * 1000)
        return timings

    timings = asyncio.run(run_all())
    cold = timings[0]
    warm = sorted(timings[len(texts):])  # drop the first (cold) pass
    median = statistics.median(warm)
    p95 = warm[max(0, int(len(warm) * 0.95) - 1)]
    return cold, median, p95


@pytest.fixture(scope="module", autouse=True)
def _warm_transformer():
    # Initialise the transformer singleton once so 'cold' measures the
    # pipeline, not one-time model/library loading.
    asyncio.run(sasl_pipeline.text_to_sasl_signs("hello"))


def test_phrase_tier_latency(capsys):
    cold, median, p95 = _measure(_PHRASE_INPUTS)
    with capsys.disabled():
        print(f"\n[LATENCY] Tier 0 (phrase): cold={cold:.1f}ms median={median:.1f}ms p95={p95:.1f}ms")
    assert p95 < PHRASE_TIER_P95_MS, (
        f"Phrase tier p95 {p95:.1f}ms exceeds {PHRASE_TIER_P95_MS}ms — "
        "something heavy has entered the exact-match hot path"
    )


def test_rules_tier_latency(capsys):
    cold, median, p95 = _measure(_RULES_INPUTS, repeats=3)
    with capsys.disabled():
        print(f"[LATENCY] Tier 1 (rules): cold={cold:.1f}ms median={median:.1f}ms p95={p95:.1f}ms")
    assert p95 < RULES_TIER_P95_MS, (
        f"Rules tier p95 {p95:.1f}ms exceeds {RULES_TIER_P95_MS}ms — "
        "check for accidental network/model calls in the deterministic path"
    )
