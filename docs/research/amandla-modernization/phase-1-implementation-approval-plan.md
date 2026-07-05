# AMANDLA Phase 1 Implementation Approval Plan

Status: approval-ready plan; no production code changes yet
Date: 2026-07-05
Branch: `codex/modernization-research`

## Purpose

This is the exact next coding plan to request approval for. It turns the research package into the first measurable implementation step without starting the React rebuild and without disturbing Claude's checkout.

Phase 1 should prove three things:

1. The app can run in a known local environment.
2. The current protocol/security bugs are fixed and tested.
3. AMANDLA can evaluate deterministic rules and prepare the dataset/evaluation path before trusting any learned model output.

## Approval Boundary

If approved, I would change code and test files in this isolated research worktree only:

`C:\Users\Admin\amandla-desktop-codex-research`

I would not touch:

- `C:\Users\Admin\amandla-desktop`
- Claude's uncommitted work
- `.env`
- archived files
- generated databases
- `src/windows/hearing/signs_library.js`
- `src/windows/hearing/avatar.js`

## Work Package A - Runtime And Local Model Baseline

### Files Changed

No app source files initially.

### Commands

```powershell
python --version
py --version
ollama --version
Invoke-RestMethod http://localhost:11434/api/tags
ollama list
```

### Action

- Ask the user to install or approve installing Python 3.11/3.12 if still missing.
- Do not install packages until Python is real.
- Do not pull small local models as a default product strategy.

### Acceptance

- Python executable is real, not the Windows Store shim.
- Ollama is reachable.
- Ollama remains optional for fallback benchmarks; cloud-assisted research and dataset work are the strategic path.

## Work Package B - Static Safety Gate

### Files To Create

- `tools/eval/check_forbidden_patterns.ps1`
- `reports/eval/` output directory, ignored if raw output is later added

### What The Script Checks

Forbidden production patterns:

```text
load_dotenv(
allow_origins=["http://localhost:8000"]
detail=str(e)
"error": str(e)
fetch("http://localhost
src/windows/hearing/signs_library.js
src/windows/hearing/avatar.js
```

Renderer `require(` should be checked only in renderer folders, not Node/Electron main or test tooling.

### Acceptance

- Script exits non-zero on forbidden production patterns.
- Script ignores research docs where patterns are explicitly warning examples.
- Report names file and line number.

## Work Package C - Golden Fixture Skeleton

### Files To Create

- `tests/golden/translation_cases.json`
- `tests/golden/sign_reconstruction_cases.json`
- `tests/golden/speech_language_cases.json`
- `tests/golden/rights_cases.json`
- `tests/golden/provider_comparison_cases.json`
- `tests/golden/sign_recognition_dataset_card.json`

### Files To Create After Python Works

- `tools/eval/validate_golden_fixtures.py`
- `tools/eval/run_static_eval.py`

### Functions To Write

- `load_json_file(path)`
- `validate_common_fixture_fields(case)`
- `validate_translation_case(case)`
- `validate_sign_reconstruction_case(case)`
- `validate_rights_case(case)`
- `validate_provider_case(case)`
- `summarize_validation_results(results)`

### Acceptance

- Fixtures parse as JSON.
- Every case has `id`, `group`, `priority`, `privacy_mode`, `source`, `review_status`, and `notes`.
- The runner can validate fixtures without importing FastAPI or starting Electron.
- No real user audio or private incident data is committed.

## Work Package D - WebSocket Assist Phrase Crash Fix

### Files To Change

- `backend/ws/handler.py`
- `tests/test_ws_assist_phrase.py` or `tests/test_ws_message_contract.py`

### Current Evidence

`backend/ws/handler.py` calls:

```python
await _handle_assist_phrase(session, session_id, msg)
```

inside `websocket_endpoint(...)`, where the path parameter is named `sessionId`.

### Functions To Change

- `websocket_endpoint(...)`

### Planned Code Direction

- Normalize the path parameter once:

```python
session_id = sessionId
```

- Use `session_id` consistently inside the function.
- Keep the URL path parameter unchanged unless a wider FastAPI route rename is approved.

### Test

- Connect hearing and deaf roles.
- Send `{ "type": "assist_phrase", "text": "I need help" }` from deaf.
- Assert hearing receives `deaf_speech` or the expected assist forward message.

### Acceptance

- No `NameError`.
- Assist phrase reaches hearing role.
- Broadcast messages still omit `request_id`.

## Work Package E - WebSocket Auth Contract Reconciliation

### Files To Change

- `docs/WEBSOCKET_PROTOCOL.md`
- `tests/test_e2e_pipeline.py`
- `scripts/ws_test.py`
- `scripts/test_all_ws_handlers.py`
- possibly `backend/ws/handler.py` comments only

### Decision

Keep subprotocol auth as the implementation source of truth:

```javascript
new WebSocket(url, [`amandla-${secret}`])
```

Do not return to `?token=...` because query tokens leak more easily into logs.

### Test Cases

- Valid token subprotocol accepted.
- Missing token rejected.
- Bad token rejected.
- Query-token-only connection rejected, unless the user decides to support backwards compatibility.

### Acceptance

- Docs and tests match the real implementation.
- No docs tell developers to use `?token=` for current WebSockets.

## Work Package F - Preload Connection Guard

### Files To Change

- `src/preload/preload.js`
- `src/windows/hearing/hearing.js`
- `src/windows/deaf/deaf.js`
- `src/windows/rights/rights.js`

### Functions To Change

- `connect(sessionId, role, secret)` in `src/preload/preload.js`
- renderer startup code that manually calls `window.amandla.connect(...)`

### Planned Code Direction

- In preload, do not open a socket until `sessionId`, `role`, and `currentSecret` are all present.
- Remove renderer manual `connect()` calls if preload auto-connect is already handling session ID, secret, and role.
- Keep the public `window.amandla.connect()` method for controlled tests and future manual reconnect.

### Acceptance

- No connection attempt uses `amandla-` with an empty token.
- Renderers no longer race the preload bridge.
- No renderer uses `require()`.

## Work Package G - Renderer Backend Boundary

### Files To Change

- `signs_library.js`
- `src/preload/preload.js`
- possibly backend route wrapper or static generated map file later

### Current Evidence

`signs_library.js` directly fetches backend data.

### Recommended Phase 1 Direction

Use a preload bridge method as a temporary step:

- `window.amandla.getSignMaps()`

Then React migration can replace this with generated typed static assets if better.

### Acceptance

- `signs_library.js` no longer calls backend `fetch()` directly.
- No renderer calls `http://localhost:8000`.
- Deaf window still loads signs.

## Work Package H - Generic HTTP Errors

### Files To Change

- `sasl_transformer/routes.py`

### Function To Change

- `translate_to_sasl(...)`

### Planned Code Direction

- Log internal exception details server-side.
- Return a generic user-facing message for unexpected errors.
- For `ValueError`, return a safe validation message that does not include raw internals.

### Acceptance

- No `detail=str(e)` in production route responses.
- No `"error": str(e)` user-facing response.

## Work Package I - Dataset And Model Evaluation Runner

### Files To Create

- `tools/eval/run_model_eval.py`
- `tools/eval/validate_dataset_manifest.py`
- `tools/eval/prompts/english_to_sasl_helper.md`
- `tools/eval/prompts/signs_to_english_helper.md`
- `tools/eval/prompts/rights_analysis_helper.md`
- `reports/eval/latest.json`
- `reports/eval/latest.md`

### Functions To Write

- `load_known_signs(signs_library_path)`
- `load_translation_cases(path)`
- `score_required_signs(expected, actual)`
- `score_forbidden_signs(expected, actual)`
- `score_unknown_signs(known_signs, actual)`
- `call_ollama(model, prompt, payload)`
- `validate_model_json(response)`
- `write_eval_report(results)`
- `validate_consent_metadata(sample)`
- `validate_split_integrity(samples)`
- `validate_review_status(sample)`

### First Model Policy

Do not make `qwen3.5:4b` or any small local model the product center. Local model pulls are optional fallback benchmarks after deterministic fixtures and dataset schemas exist.

### Acceptance

- Deterministic rules are scored before model output.
- Any local model is scored only as a constrained helper.
- Invalid JSON is a failure.
- Unknown sign hallucination is a failure.
- Critical omissions are failures.
- Cloud providers are used only in explicit research/eval mode with synthetic or consented data.

## Work Package J - Cloud-Assisted Research Provider Plan

### Files To Create Later

- `backend/services/model_router.py`
- `backend/services/providers/openai_provider.py`
- `backend/services/providers/ollama_provider.py`
- `backend/services/providers/dataset_annotation_provider.py`

### Not In First Code Pass

Do not wire cloud into live user communication yet. Use cloud foundation models first for research, annotation assistance, engineering, and evaluator development.

### Acceptance For Later

- Cloud mode must be explicit.
- API keys stay in environment variables.
- Provider calls happen in backend only.
- Synthetic or consented fixtures only.
- Model-assisted labels must be human reviewed before becoming dataset truth.

## First Pull Request Shape

Recommended PR scope:

1. Static gate.
2. Golden fixture skeleton.
3. Assist phrase fix and test.
4. WebSocket auth docs/tests reconciliation.
5. Generic error fix.

Keep preload/sign-library refactor and model runner in a second PR if the first PR grows too large.

## Approval Request

Before writing code, the user should approve one of these scopes:

| Scope | What Happens |
|---|---|
| Minimal | Fix assist crash, auth docs/tests, generic error responses. |
| Evaluation-first | Add static gate, fixture skeleton, and deterministic evaluator before app fixes. |
| Full Phase 1 | Do all work packages A-I in the research worktree, excluding live cloud production routing. |

## Stop Conditions

Stop and report instead of forcing through if:

- Python cannot be repaired.
- Claude's checkout has already solved the same item differently and needs reconciliation.
- Fixing direct renderer fetch requires larger architecture changes than expected.
- Required cloud/data provider credentials or consent policy are unavailable for dataset work.
- Tests reveal a protocol difference not captured in this plan.
