# AMANDLA React Migration Plan

Status: proposed, not implemented
Date: 2026-07-05
Branch: `codex/modernization-research`

## Decision

Move AMANDLA's renderer layer to React 19, TypeScript, and Vite while keeping Electron and FastAPI for the first rebuild phase.

This is a migration plan, not permission to start coding. The current app has protocol, runtime, security, testing, and model-readiness gaps that must be stabilized before a UI rewrite can be trusted.

## Why React

React is the strongest fit for this project because AMANDLA needs a stateful, accessibility-heavy desktop UI with several real-time surfaces:

- Hearing controls, transcript, speech state, and TTS state.
- Deaf avatar, sign queue, sign selection, assist mode, camera state, and recognition confidence.
- Rights workflow with multi-step request/response state.
- Shared connection, emergency, status, history, and error surfaces.

React gives component boundaries, typed props, testable state transitions, and a large accessibility/testing ecosystem without forcing a server-rendered web framework into an Electron desktop app.

## Current Evidence

Local repo:

- `package.json` uses Electron 35.7.5, electron-builder 25, `concurrently`, `wait-on`, and `electron-updater`.
- There is no React, Vite, TypeScript, Vitest, Playwright, or component-testing setup yet.
- Renderer code is direct DOM JavaScript under `src/windows/*`.
- `src/preload/preload.js` already centralizes most backend communication and should become the typed contract boundary.
- `signs_library.js` currently performs direct backend `fetch()` calls, which conflicts with the preload-only renderer rule.
- Current automated tests are mostly Python/backend oriented and cannot run yet because Python is unavailable in this environment.

Current package checks on 2026-07-05:

| Package | Latest checked version |
|---|---:|
| `react` | 19.2.7 |
| `vite` | 8.1.3 |
| `electron` | 43.0.0 |
| `@electron-forge/plugin-vite` | 7.11.2 |
| `@vitejs/plugin-react` | 6.0.3 |
| `vitest` | 4.1.9 |
| `@vitest/browser` | 4.1.9 |
| `@playwright/test` | 1.61.1 |
| `three` | 0.185.1 |
| `@react-three/fiber` | 9.6.1 |
| `@react-three/drei` | 10.7.7 |
| `zustand` | 5.0.14 |
| `zod` | 4.4.3 |
| `axe-core` | 4.12.1 |

## Recommended Stack

| Layer | Recommendation | Reason |
|---|---|---|
| Desktop shell | Keep Electron | The app already depends on multi-window desktop behavior, local backend startup, native dialogs, and packaged desktop delivery. |
| Main/preload build | Electron Forge with Vite plugin, or a minimal Vite setup if migration risk is lower | Official Forge Vite docs cover compiling main, preload, and renderer code. |
| Renderer | React 19 + TypeScript + Vite | Modern component model, fast dev loop, strong test ecosystem, and good fit for complex stateful UI. |
| Runtime state | Start with React context plus small stores; add Zustand only where cross-screen state becomes noisy | Keeps the first migration simple and avoids unnecessary state architecture. |
| Protocol validation | TypeScript types plus Zod client validators; mirror Pydantic models on backend later | Prevents drift between preload, renderer, tests, and WebSocket handlers. |
| 3D/avatar | Keep current Three.js engine first; wrap it behind a React component boundary | Replacing avatar logic and UI at the same time would hide animation regressions. |
| Future avatar option | Evaluate React Three Fiber after pose/animation tests exist | R3F can improve React integration, but only after current avatar behavior is measurable. |
| Tests | Vitest, Testing Library, Vitest Browser Mode, Playwright Electron, axe | Covers pure components, browser-rendered components, Electron flows, and accessibility. |
| Icons | `lucide-react` if/when UI implementation begins | Consistent with modern React interfaces and avoids handcrafted icon code. |

## Alternatives Rejected For Now

| Alternative | Decision | Why |
|---|---|---|
| Keep vanilla DOM JS | Reject for modernization | Current UI is hard to test, hard to share state across windows, and encourages ad hoc DOM mutation. |
| Next.js | Reject | Server/web framework assumptions do not help a local Electron desktop app and add unnecessary routing/build complexity. |
| Tauri | Defer | Smaller runtime is attractive, but rewriting the shell while Python/Ollama/protocol issues remain would widen scope. |
| Svelte/Solid/Vue | Defer | Technically viable, but React has the strongest fit for hiring, docs, testing, and 3D ecosystem support here. |
| Rewrite FastAPI in Node | Reject for now | The backend already contains Python ML, SASL, Whisper, and HARPS code. Rewriting it would delay proof of the product. |

## Migration Phases

### Phase R0 - Stabilize Before React

React work should not begin until Phase 1 rescue items are complete:

- Python is installed and backend tests can run.
- Ollama is reinstalled and model availability is explicit.
- WebSocket auth protocol is reconciled between code, docs, and tests.
- The assist-phrase `session_id` bug is fixed.
- Manual renderer `connect()` races are removed or made harmless.
- Direct renderer backend `fetch()` calls are removed or mediated through preload.
- Raw exception details are removed from HTTP/WebSocket user-facing responses.

Exit gate: the existing app launches far enough to run a smoke test, or each remaining launch failure is documented with a defect ID.

### Phase R1 - Add Parallel React Renderer

Do not delete old renderer files yet.

Proposed new structure:

```text
src/
  main/
    main.ts
  preload/
    preload.ts
    amandla-api.ts
  renderer/
    app/
      App.tsx
      role-router.tsx
    protocol/
      messages.ts
      validators.ts
    shared/
      components/
      hooks/
      stores/
      styles/
    windows/
      hearing/
      deaf/
      rights/
      interpreter/
```

Initial work:

- Create the build scaffold.
- Type `window.amandla` globally.
- Compile one inert React window without changing production behavior.
- Add tests that prove the preload API surface is present and renderer code has no direct Node access.

Exit gate: old app still launches, React shell builds, no production behavior has been replaced yet.

### Phase R2 - Define Protocol Contracts

Before migrating screens, lock down the message contract:

- Add TypeScript discriminated unions for WebSocket messages.
- Add Zod validators at the preload boundary.
- Mark request/response messages that require `request_id`.
- Mark broadcast messages that must not include `request_id`.
- Mirror the final contract in backend tests and `docs/WEBSOCKET_PROTOCOL.md`.

Exit gate: protocol tests catch missing `request_id`, unknown message types, auth mismatch, and bad roles.

### Phase R3 - Migrate Shared Shell

Build shared React surfaces:

- Connection state.
- Emergency overlay.
- Service status.
- Error toast/dialog system with generic user-facing messages.
- Transcript/history display.
- Request pending and timeout states.

Exit gate: shared shell works for hearing, deaf, and rights roles without duplicating WebSocket code.

### Phase R4 - Migrate Hearing Window

Migrate:

- Text input.
- Speech upload controls.
- Language selector.
- TTS output.
- History panel.
- Emergency action.

Exit gate: golden hearing-to-deaf text cases pass through the WebSocket mock and, later, the real backend smoke test.

### Phase R5 - Migrate Deaf Window

Migrate:

- Avatar mount and lifecycle.
- Sign queue display.
- Quick sign buttons.
- Assist mode.
- Camera/landmark state.
- Recognition confidence and fallback states.

Avatar rule: keep current Three.js animation code behind a React adapter first. Only evaluate React Three Fiber after pose tests exist.

Exit gate: avatar receives signs, handles unknown signs, does not blank the canvas, and maintains target frame rate on a test scene.

### Phase R6 - Migrate Rights Window

Migrate:

- Rights wizard.
- Analyze request.
- Letter generation request.
- Pending, timeout, error, and copied/export states.

Exit gate: rights requests are rate-limited, sanitized, and return generic errors on failures.

### Phase R7 - Package And Remove Legacy UI

Only after all role windows pass:

- Remove legacy HTML/CSS/JS renderer files with explicit user approval.
- Remove stale CDN dependencies where package-managed alternatives exist.
- Update packaging scripts.
- Run security, accessibility, and Electron E2E gates.

Exit gate: packaged app launches, backend starts, WebSocket connects, and no direct renderer backend calls remain.

## Design Brief Gate

Before any visual redesign or React implementation, confirm this brief:

AMANDLA should feel like a modern accessibility-grade communication workspace, not a hackathon demo. The user should immediately see two roles communicating in real time, with clear status, trustworthy errors, large readable controls, strong keyboard/focus behavior, and a serious but humane South African identity.

Visual target still needed:

- Existing app style to preserve, or
- New reference system to match, or
- Three visual concepts generated and selected before implementation.

## Source Notes

- React 19 official release and version docs support React 19 as the current major line.
- Electron Forge provides official Vite and Vite + TypeScript templates.
- Electron's security docs support preserving context isolation and a narrow preload API.
- Vitest Browser Mode and Playwright Electron docs support browser-rendered component tests and Electron E2E tests.
- WCAG 2.2 focus and contrast guidance should drive the UI rebuild gates.
