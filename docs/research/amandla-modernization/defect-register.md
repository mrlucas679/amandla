# AMANDLA Defect Register

Date: 2026-07-05
Status: initial evidence-backed register

This register starts from the clean `codex/modernization-research` branch. Claude's dirty checkout is treated as external evidence only.

## Severity

- **P0** - blocks running or proving the app locally.
- **P1** - likely runtime/security/protocol defect.
- **P2** - modernization blocker or cleanup risk.
- **P3** - polish, docs, or future hardening.

## Findings

| ID | Severity | Area | Evidence | Why It Matters | Proposed Direction |
|---|---:|---|---|---|---|
| DEF-001 | P0 | Local runtime | Current check finds Ollama `0.30.10` installed and serving, but `ollama list` is empty. Shell still only finds broken Windows Store Python aliases at `C:\Users\Admin\AppData\Local\Microsoft\WindowsApps\python.exe`; `py` is unavailable. | App cannot be started or tested as documented; AI services have no local model available. | Install real Python, then pull/evaluate Ollama models before any runtime claims. |
| DEF-002 | P1 | WebSocket runtime | `backend/ws/handler.py:136` calls `_handle_assist_phrase(session, session_id, msg)` but the endpoint variable is `sessionId`. | Assist mode can raise `NameError` and break a core deaf-to-hearing path. | Add regression test, rename to `sessionId`, or normalize endpoint variable naming. |
| DEF-003 | P1 | Protocol drift | `src/preload/preload.js:92` uses `new WebSocket(url, [\`amandla-${currentSecret || ''}\`])`; `docs/WEBSOCKET_PROTOCOL.md:13`, `tests/test_e2e_pipeline.py:122`, and scripts still use `?token=`. | Tests and docs do not prove the real protocol. | Make subprotocol auth the single source of truth or intentionally revert all clients to query-token auth. |
| DEF-004 | P1 | Connection lifecycle | `src/windows/hearing/hearing.js:71`, `src/windows/deaf/deaf.js:81`, and `src/windows/rights/rights.js:17` manually call `window.amandla.connect(id, role)` while preload auto-connects once secret/session/role are known. | Can create invalid empty-token connection attempts and reconnect noise. | Renderer should not call `connect`; preload should own connection lifecycle. |
| DEF-005 | P1 | Renderer/backend boundary | `signs_library.js:1544` and `1545` call backend `fetch()` directly. | Violates the preload-only bridge rule and weakens packaging/offline control. | Move sign-map/filler retrieval behind preload, bundle static generated data, or inject data from backend once at startup. |
| DEF-006 | P1 | HTTP error leakage | `sasl_transformer/routes.py:83` returns `HTTPException(..., detail=str(e))`. | Violates project rule against exposing raw internals to clients. | Log details server-side; return generic client error. |
| DEF-007 | P1 | Dependency security | `npm audit` reports 22 vulnerabilities total; direct fixes include Electron `43.0.0` and electron-builder `26.15.3`. Production-only audit still reports `js-yaml`. | Distribution on old Electron/build tooling is not defensible. | Upgrade platform dependencies in a controlled branch with smoke tests. |
| DEF-008 | P1 | AI recognition validity | `Modelfile` asks `qwen2.5:3b` to infer SASL signs from MediaPipe landmarks; current HARPS assets and ASL sensor dataset provenance are unclear. | Landmark-to-sign LLM guessing is not proven sign recognition. | Gate camera recognition behind evaluated model/DTW/reference clips or mark as experimental. |
| DEF-009 | P1 | UI testability | Current renderer is imperative HTML/CSS/JS with duplicated state, inline handlers, CDN scripts, and manual DOM updates. | Hard to redesign or test at product quality. | Migrate to React + TypeScript + Vite with typed protocol and component state. |
| DEF-010 | P2 | Documentation drift | `README.md` and `CLAUDE.md` say zero direct renderer fetches; current code has direct fetches. `CLAUDE.md` role list excludes newer interpreter work seen in dirty checkout. | Agents and developers can follow outdated instructions. | Create one current architecture doc after reconciling Claude WIP. |
| DEF-011 | P2 | Repo noise | `data/conversations.db*`, archived docs, duplicate transformer folder, and ASL dataset are present in the repo. | Makes it hard to know what matters and increases accidental coupling. | Use document inventory to propose explicit deletion/move PR. |
| DEF-012 | P2 | Packaging/runtime drift | Clean branch uses port `8000`; Claude dirty checkout appears to use `8002` and has vendored assets/fonts. | Two parallel realities make research conclusions fragile. | Reconcile branch state before implementation; do not overwrite Claude WIP. |
| DEF-013 | P2 | Accessibility | Current UI uses symbol-heavy buttons, color-heavy status, small topbar text, and emergency overlays with motion. | The target users need accessible, pressure-proof interactions. | Add WCAG keyboard/focus/contrast/reduced-motion gates before claiming UX quality. |
| DEF-014 | P2 | CSP/offline posture | Clean branch allows external Google Fonts, jsdelivr, and cdnjs; dirty checkout appears to vendor some assets. | App behavior changes when offline; CSP still includes `unsafe-inline`. | Prefer vendored/package-managed assets, remove inline handlers, tighten CSP over time. |

## First Tests To Add

1. WebSocket assist phrase regression test.
2. WebSocket auth test using subprotocol token, not query token.
3. Renderer connection lifecycle test or preload unit test proving no empty-token connection.
4. SASL transformer route error test proving generic client response.
5. Golden translation fixtures for common greetings, medical, rights, and SA English/slang.
6. Dependency/security gate in CI: `npm audit --omit=dev --audit-level=moderate` plus full audit as advisory.
