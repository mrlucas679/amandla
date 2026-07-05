"""
Deterministic scorer for the golden translation fixtures (MASTER_PLAN Phase 1).

Scores a gloss-token sequence against a fixture case on five axes:

1. required-sign recall        — every expected sign present
2. forbidden signs             — banned glosses absent
3. marker preservation         — WILL/MUST/CAN/FINISH survive
4. word order                  — [before, after] pairs hold (the SASL axis a
                                 bag-of-signs metric cannot see)
5. avatar-library compliance   — unknown-sign count vs the signs the avatar
                                 can actually play (signs_library.js is ground
                                 truth, NOT the transformer's JSON library)

No network, no Ollama, no Node — the JS library is parsed with a regex.
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SIGNS_LIBRARY_JS = REPO_ROOT / "signs_library.js"
GOLDEN_DIR = Path(__file__).resolve().parent

# Matches library entries like  'HELLO': sign(  or  "I'M FINE": signWithFrames(
_SIGN_KEY_RE = re.compile(r"""^\s*(['"])([A-Z][A-Z0-9 '\-]*)\1\s*:\s*sign""", re.MULTILINE)


def load_known_signs(js_path=SIGNS_LIBRARY_JS):
    """Return the set of sign names the avatar can actually play."""
    text = Path(js_path).read_text(encoding="utf-8")
    return {m.group(2) for m in _SIGN_KEY_RE.finditer(text)}


def load_cases(filename):
    with open(GOLDEN_DIR / filename, encoding="utf-8") as fh:
        return json.load(fh)["cases"]


def _contains_sign(glosses, name):
    """True if `name` appears in the gloss sequence.

    Multi-word library signs (e.g. 'THANK YOU') match either as a single
    token or as a consecutive run of tokens.
    """
    if name in glosses:
        return True
    words = name.split(" ")
    if len(words) > 1:
        for i in range(len(glosses) - len(words) + 1):
            if glosses[i:i + len(words)] == words:
                return True
    return False


def _first_index(glosses, name):
    """Index of the first occurrence of `name` (multi-word aware); -1 if absent."""
    words = name.split(" ")
    if len(words) == 1:
        return glosses.index(name) if name in glosses else -1
    for i in range(len(glosses) - len(words) + 1):
        if glosses[i:i + len(words)] == words:
            return i
    return glosses.index(name) if name in glosses else -1


def score_case(case, glosses):
    """Score one fixture case against a produced gloss sequence.

    Returns a dict with per-axis results and an overall `passed` flag.
    A `critical` case passes only when every axis is clean.
    """
    required = case.get("expected_required_signs", [])
    forbidden = case.get("expected_forbidden_signs", [])
    markers = case.get("expected_markers", [])
    order_pairs = case.get("expected_order", [])
    max_unknown = case.get("max_unknown_signs", 0)
    allow_fs = case.get("allow_fingerspell", False)

    missing_required = [s for s in required if not _contains_sign(glosses, s)]
    forbidden_hits = [s for s in forbidden if _contains_sign(glosses, s)]
    missing_markers = [m for m in markers if not _contains_sign(glosses, m)]

    order_violations = []
    for before, after in order_pairs:
        i, j = _first_index(glosses, before), _first_index(glosses, after)
        if i >= 0 and j >= 0 and i >= j:
            order_violations.append([before, after])

    known = load_known_signs()
    covered = set()
    for name in known:
        idx = _first_index(glosses, name)
        if idx >= 0:
            covered.update(range(idx, idx + len(name.split(" "))))
    unknown_signs = [g for i, g in enumerate(glosses) if i not in covered]
    unknown_ok = len(unknown_signs) <= max_unknown if allow_fs else len(unknown_signs) <= max_unknown

    recall = 1.0 if not required else (len(required) - len(missing_required)) / len(required)

    passed = (
        not missing_required
        and not forbidden_hits
        and not missing_markers
        and not order_violations
        and unknown_ok
    )

    return {
        "id": case["id"],
        "priority": case.get("priority", "normal"),
        "passed": passed,
        "required_recall": round(recall, 3),
        "missing_required": missing_required,
        "forbidden_hits": forbidden_hits,
        "missing_markers": missing_markers,
        "order_violations": order_violations,
        "unknown_signs": unknown_signs,
        "glosses": glosses,
    }


def summarize(results):
    """Aggregate a result list into the baseline report shape."""
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    critical = [r for r in results if r["priority"] == "critical"]
    critical_passed = sum(1 for r in critical if r["passed"])
    mean_recall = round(sum(r["required_recall"] for r in results) / total, 3) if total else 1.0
    return {
        "cases_total": total,
        "cases_passed": passed,
        "critical_total": len(critical),
        "critical_passed": critical_passed,
        "mean_required_recall": mean_recall,
        "failures": [
            {k: r[k] for k in ("id", "missing_required", "forbidden_hits",
                               "missing_markers", "order_violations", "unknown_signs", "glosses")}
            for r in results if not r["passed"]
        ],
    }
