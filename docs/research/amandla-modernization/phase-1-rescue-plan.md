# Phase 1 Rescue Plan

Date: 2026-07-05
Status: proposed implementation plan - no code changes yet

Phase 1 is not the React rebuild. Phase 1 makes the current codebase testable and honest enough that a React rebuild has a stable backend/protocol to stand on.

## Objective

Get AMANDLA to a measurable baseline:

- Local prerequisites restored.
- WebSocket protocol consistent.
- Critical backend bugs fixed.
- Renderer/backend boundary enforced.
- Security footguns removed.
- Tests updated to the real protocol.
- The app clearly handles missing Ollama/model states.

## Non-Goals

- Do not redesign the full UI in Phase 1.
- Do not replace FastAPI.
- Do not delete large datasets/models until approved.
- Do not claim camera sign recognition is production-ready.
- Do not migrate all renderer code to React yet.

## Work Order

### 1. Restore Runtime Prerequisites

Evidence:

- Current verification shows Ollama `0.30.10` is installed and serving, but no models are pulled.
- Shell only finds Windows Store Python aliases.

Actions:

- Install real Python 3.11 or 3.12.
- Install Ollama for Windows from official docs only if it is missing on a target machine.
- Run `ollama serve` if the service is not already available.
- Pull/evaluate at least one candidate model.
- Recreate `amandla` model only after choosing base model.

Acceptance:

```powershell
python --version
pip --version
ollama --version
ollama list
curl http://localhost:11434/api/tags
```

### 2. Fix WebSocket Assist-Mode Crash

Files:

- `backend/ws/handler.py`
- `tests/` or `scripts/` WebSocket smoke tests

Problem:

- Assist dispatch uses undefined `session_id`.

Plan:

- Normalize endpoint variable to `session_id` once at function entry, or change the call to `sessionId`.
- Add a regression test that sends `assist_phrase` from deaf role and expects `deaf_speech` on hearing role.

Acceptance:

- Assist phrase does not crash.
- Hearing client receives phrase with `source: "assist"`.

### 3. Reconcile WebSocket Authentication

Files:

- `src/preload/preload.js`
- `backend/ws/handler.py`
- `docs/WEBSOCKET_PROTOCOL.md`
- `tests/test_e2e_pipeline.py`
- `scripts/ws_test.py`
- `scripts/test_all_ws_handlers.py`

Problem:

- Current client/backend use WebSocket subprotocol.
- Docs/tests use `?token=`.

Plan:

- Keep subprotocol auth because it avoids putting the token in URLs/logs.
- Update docs/tests/scripts to use `websockets.connect(..., subprotocols=[f"amandla-{token}"])`.
- Update stale comments in `src/main.js` and `backend/shared.py`.

Acceptance:

- Bad token rejected.
- Missing token rejected.
- Valid subprotocol token accepted.
- Docs match implementation.

### 4. Remove Renderer Manual Connect Race

Files:

- `src/windows/hearing/hearing.js`
- `src/windows/deaf/deaf.js`
- `src/windows/rights/rights.js`
- `src/preload/preload.js`

Problem:

- Renderers manually call `connect(sessionId, role)` without a secret.
- Preload already auto-connects after `session-id`, `session-secret`, and `role`.

Plan:

- Remove manual renderer `connect()` calls.
- Keep `window.amandla.connect()` only for controlled tests or future explicit reconnect.
- Add a preload guard: do not open a socket until secret is non-empty.

Acceptance:

- No WebSocket attempt is made with `amandla-` empty token.
- All windows connect after IPC values arrive.

### 5. Enforce Preload-Only Backend Access

Files:

- `signs_library.js`
- `src/preload/preload.js`
- `sasl_transformer/routes.py` or backend route wrappers

Problem:

- `signs_library.js` directly fetches backend data.

Plan options:

| Option | Direction |
|---|---|
| A | Bundle generated word/filler maps at build time. Best for offline and packaged app. |
| B | Add preload methods for sign map/filler retrieval. Better short-term compatibility. |
| C | Remove dynamic fetch and treat backend `sign_maps.py` as backend-only. Simplest if frontend does not need it. |

Recommended Phase 1:

- Use option B as a bridge.
- Decide in React migration whether to move to generated typed assets.

Acceptance:

- `rg "fetch\\(" src signs_library.js` finds no renderer backend fetch.
- No renderer directly calls `http://localhost:8000`.

### 6. Remove Raw Error Exposure

Files:

- `sasl_transformer/routes.py`
- `sasl_transformer/websocket_handler.py` if active

Problem:

- `detail=str(e)` exposes internals.

Plan:

- Log exception with server logger.
- Return generic `Translation failed. Please try again.` or validation-specific safe errors.

Acceptance:

- Search finds no `detail=str(e)` or user-facing `"error": str(e)`.

### 7. Add Baseline Tests

Tests:

- `tests/test_ws_auth.py`
- `tests/test_ws_assist_phrase.py`
- `tests/test_sasl_route_errors.py`
- Update `tests/test_e2e_pipeline.py`.

Acceptance:

- Tests cover the exact bugs fixed above.
- Backend can run in a test mode without requiring full Ollama for deterministic paths.

### 8. Dependency Security Upgrade Plan

Files:

- `package.json`
- `package-lock.json`

Plan:

- Upgrade `electron` to current major after smoke testing.
- Upgrade `electron-builder` or consider Electron Forge migration during React rebuild.
- Upgrade `electron-updater`.
- Keep full `npm audit` as advisory, but require `npm audit --omit=dev --audit-level=moderate` to pass before packaging.

Acceptance:

- Production audit clean or documented exception.
- App opens windows after Electron upgrade.
- CSP/security settings unchanged or stricter.

## Phase 1 Exit Criteria

AMANDLA is ready for the React rebuild only when:

- Python is installed, Ollama is verified, and at least one evaluated local model is available.
- Backend starts.
- Health endpoint works.
- WebSocket auth tests pass.
- Assist phrase regression test passes.
- Renderer no longer makes direct backend fetches.
- No raw exception details reach HTTP clients.
- Missing Ollama/model state is visible and non-crashing.
- The cleanup proposal has been approved or explicitly deferred.

## Risks

- Claude's dirty work may already fix some items differently. Reconcile before implementing.
- Electron major upgrade can break packaged builds.
- Model evaluation may show local model quality is insufficient; fallback UX must be honest.
- Removing direct fetches may expose hidden coupling in `signs_library.js`.
