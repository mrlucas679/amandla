# AMANDLA First Model Benchmark Runbook

Status: proposed, not implemented
Date: 2026-07-05
Branch: `codex/modernization-research`

## Purpose

This runbook describes the first safe benchmark sequence after the user approves implementation/testing work. It is written so AMANDLA can measure local models without changing production behavior or sending private data to cloud providers.

Current blocker: Python is not available in the shell, and Ollama is installed but has no pulled models.

Strategic update: after the dataset-first pivot, this runbook is optional local fallback research. AMANDLA should not be built around a small local LLM. The primary model strategy is cloud-assisted development/research plus an AMANDLA-owned specialized SASL model trained on consented data.

## Guardrails

- Run in the isolated research worktree first.
- Do not modify Claude's checkout at `C:\Users\Admin\amandla-desktop`.
- Do not send real user conversations, audio, legal stories, or private information to a cloud provider.
- Do not enable cloud providers in renderers. Provider calls belong behind the backend.
- Do not pull large models until small-model harness results show the benchmark is useful.
- Do not claim camera sign recognition is production-ready from generic or synthetic labels.

## Phase 0 - Confirm Environment

Commands to run after approval:

```powershell
git status --short --branch
Get-Command python, python3, py, ollama -ErrorAction SilentlyContinue
ollama --version
Invoke-RestMethod http://localhost:11434/api/tags
ollama list
```

Expected current state:

- Branch is `codex/modernization-research`.
- Ollama is available.
- Ollama model list is empty until a model is pulled.
- Python must be repaired before pytest or backend checks can run.

Abort if:

- The command is running inside Claude's original checkout by mistake.
- The branch is `main`, `master`, or Claude's active branch.
- Real user data is needed to continue.

## Phase 1 - Restore Python

Install a real Python runtime before any backend or model tests. The Windows Store shim is not enough.

Recommended checks:

```powershell
python --version
python -m pip --version
python -m venv .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip --version
```

Do not treat dependency installation as a model-quality result. First prove the runtime exists, then install only the dependencies needed for the test layer being run.

## Phase 2 - Restore Minimal Ollama Model Coverage

First pull:

```powershell
ollama pull qwen3.5:4b
ollama list
```

Why `qwen3.5:4b` first:

- It is small enough to be practical on this machine's RAM.
- It is newer than the earlier `qwen3:4b` recommendation and still in the 4B-class local range.
- It has better multilingual potential than the older `qwen2.5:3b` baseline.
- It is big enough to test structured helper behavior before trying heavier models.

Optional second pull if `qwen3.5:4b` is unstable or the project needs a conservative baseline:

```powershell
ollama pull qwen3:4b
```

Optional second pull if `qwen3.5:4b` is too slow:

```powershell
ollama pull qwen3.5:2b
```

Optional second pull if 4B-class models are fast but weak:

```powershell
ollama pull qwen3:8b
```

Do not pull `gpt-oss:20b` in the first run. It is a stretch experiment for later, after the fixture runner can measure latency and correctness.

## Phase 3 - Run Static Safety Checks First

Before asking any model for output, run forbidden-pattern checks. These checks protect the app from known recurring regressions.

Patterns to check:

```text
load_dotenv(
allow_origins=["http://localhost:8000"]
detail=str(e)
"error": str(e)
require(
fetch("http://localhost
src/windows/hearing/signs_library.js
src/windows/hearing/avatar.js
```

Expected result:

- No forbidden patterns in production code.
- If a pattern appears in docs or research files, it must be clearly marked as a warning example, not implementation guidance.

## Phase 4 - Run Rules Baseline

The first benchmark provider should be the deterministic pipeline, not the model.

Planned order:

1. Validate every fixture JSON file.
2. Load known signs from `signs_library.js` and mapping data from `backend/services/sign_maps.py`.
3. Run `translation_cases.json` through deterministic SASL mapping.
4. Run `sign_reconstruction_cases.json` through rule fallback reconstruction.
5. Record missing signs, dropped modal markers, and unknown words.

Decision rule:

- If rules already pass a case, a model should not replace them unless it improves a measured weakness.
- If rules fail a case, decide whether the correct fix is a map/rule update or model assistance.

## Phase 5 - Run `qwen3.5:4b` As A Constrained Helper

The local model should receive narrow tasks and return strict JSON.

Expected text-to-SASL helper output:

```json
{
  "signs": ["TOMORROW", "I", "WILL", "GO", "CLINIC"],
  "unknown_words": [],
  "confidence": 0.82,
  "needs_human_review": false
}
```

Expected signs-to-English helper output:

```json
{
  "text": "I need help.",
  "intent_tags": ["help_request"],
  "confidence": 0.84,
  "needs_human_review": false
}
```

Hard failures:

- Non-JSON output when JSON is required.
- Chain-of-thought or reasoning prose in user-facing fields.
- Invented sign names not present in the known sign list.
- Dropped critical terms such as `HELP`, `HURT`, `MUST`, `WILL`, or `FINISH`.
- Provider exception shown directly to the user.

## Phase 6 - Record Latency

Measure at least:

| Measurement | Why |
|---|---|
| Cold first token / first response | Shows startup pain after app launch. |
| Warm median latency | Shows normal use. |
| Warm p95 latency | Shows worst common delay. |
| Timeout rate | Shows reliability. |
| CPU and memory observation | Shows whether live desktop use is realistic. |

Initial live-communication target should be discovered from local measurements. Do not invent a latency target before seeing the laptop's CPU performance.

## Phase 7 - Optional Cloud Comparison

Cloud comparison is useful only after local fixtures work.

Allowed first cloud text baseline:

- OpenAI `gpt-5.5` with Structured Outputs through a backend provider abstraction.

Allowed first cloud speech comparisons:

- OpenAI speech models.
- Google Chirp 3.
- Azure Speech or MAI Transcribe where available.

Rules:

- Use synthetic or consented fixtures only.
- Keep API keys in environment variables, never in code or renderer state.
- Record provider, region, model, date, and privacy mode.
- Do not make cloud the default live path without product consent and a clear privacy mode.

## Phase 8 - First Decision After Benchmark

The first run should produce one of these decisions:

| Decision | Meaning |
|---|---|
| Keep rules-only for live SASL | Model adds no reliable value yet. |
| Use `qwen3.5:4b` as helper only | Model helps edge cases but deterministic validation remains in control. |
| Try `qwen3:8b` | 4B is too weak but fast enough to justify a larger local test. |
| Try `qwen3.5:2b` | 4B is too slow and a smaller fallback may be useful. |
| Research `gpt-oss:20b` later | Harness is ready and local quality needs a stronger model. |
| Use cloud only for quality mode | Local cannot meet a non-core task such as rights letters, but cloud must remain opt-in. |

## Output Artifacts

Each benchmark run should write:

```text
reports/
  eval/
    latest.json
    latest.md
    raw/
      ignored-provider-outputs/
```

The markdown report should include:

- Runtime versions.
- Pulled Ollama models.
- Fixture counts.
- Pass/fail counts.
- Critical failures.
- Latency summary.
- Privacy mode.
- Recommendation for the next model or rule change.

## Stop Conditions

Stop the benchmark and report blockers when:

- Python cannot be repaired.
- Ollama cannot serve a pulled model.
- Fixtures cannot be validated.
- A model leaks reasoning/prose into strict JSON fields repeatedly.
- A model drops critical safety/legal/medical information.
- A provider requires real user data before synthetic fixtures pass.
