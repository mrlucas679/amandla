# AMANDLA Modernization Roadmap

Date: 2026-07-05
Status: research draft on isolated branch

## Position

AMANDLA should be treated as a failed experiment that may contain valuable parts, not as a working product that needs cosmetic polish.

The target is a modern accessibility-grade desktop application: calm, reliable, offline-capable where possible, auditable, and designed around real communication pressure. The rebuild should feel closer to a serious Apple/Google/OpenAI-class tool than a hackathon demo.

## What Is Already Proven By Inspection

The clean branch is not stable enough to build on blindly.

| Area | Evidence | Risk |
|---|---|---|
| WebSocket handler | `backend/ws/handler.py` calls `_handle_assist_phrase(session, session_id, msg)` but the endpoint variable is `sessionId`. | Assist mode can crash on use. |
| Protocol docs/tests | `docs/WEBSOCKET_PROTOCOL.md`, `tests/test_e2e_pipeline.py`, and scripts still document/use `?token=...`; current preload/backend use WebSocket subprotocol `amandla-<token>`. | Tests and docs do not prove the real app path. |
| Renderer/backend boundary | `signs_library.js` directly fetches `http://localhost:8000/api/sasl/word-map` and `/filler-words`. | Violates the preload-only architecture rule and complicates packaging/offline behavior. |
| Connection race | Hearing, deaf, and rights renderers call `window.amandla.connect(id, role)` manually while preload also auto-connects after receiving secret. | Can create bad-token attempts, reconnect noise, and unclear ownership of connection state. |
| HTTP error hygiene | `sasl_transformer/routes.py` exposes `detail=str(e)`. | Violates the no-raw-exception rule. |
| UI architecture | HTML/CSS/JS are per-window imperative files with duplicated patterns and inline handlers. | Hard to test, redesign, and reason about state. |
| Security/dependencies | `npm audit` reports 22 vulnerabilities in the installed tree, including Electron/build-chain issues. Production-only audit still reports `js-yaml`. | Must upgrade before packaging or distribution. |
| Runtime prerequisites | Shell only finds Windows Store Python aliases, not a real Python executable. Ollama `0.30.10` is installed and serving, but no models are pulled. | Current start/test instructions are not executable on this machine. |
| AI/model proof | `Modelfile` is based on `qwen2.5:3b` and asks an LLM to infer signs from MediaPipe landmarks. | This is not proven recognition; needs evaluation or replacement. |

## Frontend Decision

Recommendation: rebuild the renderer as **React 19 + TypeScript + Vite inside Electron**, preferably using Electron Forge's Vite/TypeScript template or an equivalent `electron-vite` setup.

Why:

- The app has multiple complex states: hearing turn, deaf turn, connection, AI health, recording, translation progress, avatar playback, rights wizard, history, emergency overlay.
- TypeScript can make WebSocket messages explicit instead of relying on stringly typed payloads.
- React component boundaries let the UI become a real product surface instead of three rushed pages.
- Vite gives fast dev/build ergonomics, and Electron Forge has an official Vite template.
- The app already depends on Electron-specific capabilities: multiple windows, preload bridge, packaged backend process, global shortcut, camera/microphone permissions.

Alternatives:

| Option | Decision | Reason |
|---|---|---|
| Keep vanilla JS | Reject for rebuild, keep only for emergency patches. | Too much duplicated imperative state and weak testability. |
| Next.js | Reject for desktop core. | Server-components/routing benefits are not worth the extra desktop packaging complexity. |
| Svelte/Solid/Vue | Plausible, but not first choice. | Good frameworks, but React has stronger desktop/Three/testing ecosystem fit for this project. |
| Tauri | Defer. | Smaller binaries are attractive, but Electron gives predictable Chromium behavior for MediaPipe, WebAudio, canvas, WebSocket, and existing backend packaging. |
| Web-only app | Reject for current mission. | Local accessibility tool needs desktop permissions, local AI, packaged backend, and offline-friendly behavior. |

Suggested frontend shape:

```text
src/
  main/                    Electron main process
  preload/                 typed, narrow bridge only
  renderer/
    app/                   React app shell
    roles/
      hearing/
      deaf/
      rights/
      interpreter/
    components/
      connection/
      emergency/
      conversation/
      avatar/
      controls/
    state/
      websocket-store.ts
      ai-status-store.ts
      session-store.ts
    protocol/
      messages.ts
```

## UX Direction

The current UI is functional but looks like an internal prototype. The modern direction should be:

- One clear session surface with role-specific panes, not disconnected screens.
- A calm clinical/government-accessibility feel, not a marketing landing page.
- Obvious connection and AI-state indicators.
- Big, reliable controls for urgent communication.
- Transcript and SASL gloss visible without competing with the avatar.
- Deaf user reply flow optimized for speed: quick phrases, typed SASL, camera mode, and assist mode as peer options.
- Rights flow moved into a structured case workspace with draft, evidence, export, and local privacy indicators.
- Every loading/error/offline state designed, not improvised.

Design requirements:

- WCAG 2.2 contrast and keyboard navigation.
- No hidden essential state behind color alone.
- Reduced-motion support.
- Text must not overlap controls at small window widths.
- Emergency controls must be unmistakable and testable.

## Backend Decision

Keep FastAPI for now. Do not rewrite the backend while the product problem is still being clarified.

Modernize it by:

- Adding Pydantic message schemas for every WebSocket request and broadcast.
- Generating or maintaining a single protocol source of truth.
- Fixing request/response `request_id` contracts.
- Keeping rule-first SASL translation, with Ollama only as an assistive fallback.
- Replacing landmark-to-sign LLM guessing with evaluated recognition: MediaPipe landmarks plus a real temporal model, DTW against verified reference clips, or explicit "not ready" status.
- Keeping history, rate limiting, and session cleanup, but proving them with tests.

## Ollama Recovery And Model Plan

Earlier research assumed Ollama might be absent. Current check shows Ollama `0.30.10` is installed and serving, but `ollama list` is empty. Do not assume the `amandla` model exists.

Official Windows path:

1. Verify CLI availability: `ollama --version`.
2. Verify API availability: `http://localhost:11434/api/tags`.
3. Pull a base model candidate.
4. Create the AMANDLA model only after task-specific evaluation: `ollama create amandla -f Modelfile`.
5. Verify: `ollama list`, then `ollama run amandla`.
6. If Ollama is missing on another machine, install from https://docs.ollama.com/windows.

Model candidates to evaluate, not blindly accept:

| Candidate | Why consider | Risk |
|---|---|---|
| `qwen3.5:4b` | Newer 4B-class local candidate with multilingual and multimodal claims. | Needs JSON reliability and latency tests. |
| `qwen3:4b` | Smaller conservative fallback baseline. | Older than Qwen3.5; should not win by default. |
| `qwen3.5:2b` | Lightweight fallback for weak hardware. | May underperform on translation/reasoning. |
| `qwen3:8b` | Better likely quality if hardware allows. | More memory/latency. |
| Gemma E2B/E4B-class local model | Device-friendly comparison if local runtime support exists. | Verify actual runtime tag/support and test JSON compliance. |
| `gpt-oss:20b` | Strong open-weight reasoning candidate if the machine has enough memory. | Measure memory and latency before using it in any live path. |
| Current `qwen2.5:3b` | Existing Modelfile baseline. | Older and unproven; should not be the default without evaluation. |

Acceptance gate for a model:

- Produces valid JSON for its specific task role.
- Does not hallucinate signs outside the known sign library.
- Meets local latency budget.
- Improves over deterministic fallback on golden scenarios.
- Fails closed with `UNKNOWN` when confidence is low.
- Does not claim production camera sign recognition from generic landmark prompts.

## Evaluation Before Rebuild Completion

The rebuild is not real until these gates exist:

| Gate | What It Proves |
|---|---|
| WebSocket contract tests | Client and backend agree on auth, roles, request IDs, broadcasts, and errors. |
| Golden translation suite | English/SA English -> SASL output is stable, explainable, and not LLM-hallucinated. |
| SASL reconstruction suite | Deaf signs/SASL gloss -> English is predictable and safe. |
| Avatar validation harness | Each priority sign can be reviewed against reference material and scored. |
| Latency benchmark | Text-to-first-sign, speech-to-first-sign, and avatar FPS are measured. |
| Accessibility audit | Keyboard, contrast, focus, reduced motion, screen reader labels. |
| Security audit | Electron settings, CSP, preload boundary, raw error leakage, dependency scan. |
| Packaged build test | Windows app runs without global Python surprises and handles missing Ollama gracefully. |

## Research From The Old AI Dossier Adapted To AMANDLA

The AMD ACT II AI research dossier is not about this product, but it transfers several useful principles:

- Evidence contracts matter more than bigger prompts.
- Model outputs need validation, retry, fallback, and logging.
- Human review is a product feature, especially for accessibility and rights workflows.
- Public benchmarks are weak signals; product-specific golden scenarios are the real gate.
- Synthetic data is useful for tests and demos only when labeled and separated from real user data.
- Observability must log model name, provider, latency, fallback reason, and prompt/config version.

What should not transfer:

- Retail operations concepts.
- Multi-agent cascade complexity.
- AMD MI300X/vLLM narrative unless this project actually runs there.
- GraphRAG/vector DB as a first move before deterministic translation tests exist.

## Initial Rebuild Phases

### Phase 0 - Evidence And Cleanup

- Finish document inventory.
- Mark deletion candidates.
- Build defect register.
- Reconcile clean branch with Claude's dirty work without overwriting it.
- Restore local prerequisites: real Python, Ollama, model.

### Phase 1 - Stabilize Current Baseline

- Fix obvious backend/runtime blockers.
- Reconcile WebSocket auth docs/tests with actual subprotocol auth.
- Remove renderer direct backend fetches or move them into preload/API bridge.
- Add typed protocol definitions even before React migration.
- Add tests for the broken assist-phrase path.

### Phase 2 - Frontend Rebuild Shell

- Scaffold React + TypeScript + Vite/Electron.
- Port session, connection, emergency, and role routing first.
- Build hearing/deaf/rights screens as real components.
- Keep backend API shape stable during the UI migration.

### Phase 3 - Avatar And Sign Quality

- Keep current Three.js work only if it passes validation.
- Add sign validator tool.
- Prioritize the quick-sign set and medical/rights vocabulary.
- Add NMM and signing-space support as data, not hardcoded animation tricks.

### Phase 4 - AI And Evaluation

- Evaluate Ollama model candidates.
- Rule-first translation, model-as-fallback.
- Split AI evaluation by role: speech, English-to-SASL, SASL-to-English, rights analysis, rights letters, and experimental sign recognition.
- Add golden scenarios and latency logs.
- Only add translation memory/vector retrieval after deterministic tests prove the basics.

### Phase 5 - Packaging And Product Readiness

- Upgrade Electron/build chain.
- Package backend reliably.
- Verify missing Ollama and missing model flows.
- Run accessibility/security/performance gates.

## Immediate Next Actions

1. Build a defect register from the current code.
2. Create a deletion proposal from the document inventory.
3. Create the frontend migration ADR.
4. Add an Ollama restore guide and model evaluation matrix.
5. After approval, start Phase 1 fixes on this branch or a new implementation branch.
