# ADR: Frontend Modernization Target

Date: 2026-07-05
Status: proposed

## Context

The current frontend was built quickly for a hackathon. It uses separate HTML/CSS/JS files for hearing, deaf, and rights windows. The app now needs to become a long-term product with reliable state, accessibility, testing, and a modern interface.

The frontend has to support:

- Multiple Electron windows or role-specific views.
- A secure preload bridge with no renderer `require()`.
- Real-time WebSocket session state.
- Speech recording and transcription feedback.
- 3D avatar rendering and sign playback.
- Camera/MediaPipe sign input.
- Rights workflow and document export.
- Emergency overlays and high-pressure communication.
- Offline/missing-Ollama states.

## Decision

Use **React 19 + TypeScript + Vite inside Electron** for the renderer rebuild.

Use Electron as the desktop shell for now. Keep FastAPI as the backend. Migrate the renderer first while stabilizing protocol contracts.

Recommended stack:

| Layer | Choice |
|---|---|
| Desktop shell | Electron 43+ |
| Electron tooling | Electron Forge Vite template or equivalent Vite/Electron setup |
| Renderer | React 19 |
| Language | TypeScript strict mode |
| Build | Vite |
| 3D | Three.js package-managed; evaluate React Three Fiber for componentized avatar scene |
| State | Small explicit stores for session, connection, AI status, conversation, avatar queue |
| Tests | Vitest for units, Playwright for rendered flows, pytest for backend |
| Accessibility | WCAG checks, keyboard tests, reduced-motion visual checks |

## Why Not Keep Vanilla JS

Vanilla JS is acceptable for a small demo. AMANDLA is no longer that.

Current risks:

- Manual DOM updates spread across windows.
- Duplicated connection logic.
- Weak protocol typing.
- No component-level testing.
- Harder accessibility audits.
- Harder visual redesign.
- Easy to reintroduce direct backend calls.

## Why Not Next.js

Next.js adds routing and server rendering that do not match the desktop core problem. The app already has FastAPI as the server. Electron renderers should remain focused, local, and packageable.

## Why Not Tauri Now

Tauri is worth revisiting later, but Electron is the lower-risk path today because the app already depends on Chromium behavior, WebSocket, WebAudio, MediaPipe/camera permissions, canvas/WebGL, preload IPC, and packaged backend process management.

## Target Shape

```text
src/
  main/
    main.ts
    windows.ts
    backend-process.ts
    security.ts
  preload/
    index.ts
    bridge-types.ts
  renderer/
    main.tsx
    app/
      AmandlaApp.tsx
      routes.tsx
    roles/
      hearing/HearingView.tsx
      deaf/DeafView.tsx
      rights/RightsView.tsx
      interpreter/InterpreterView.tsx
    components/
      AvatarStage/
      Conversation/
      EmergencyOverlay/
      ConnectionStatus/
      SpeechControls/
      SignControls/
      RightsCase/
    protocol/
      messages.ts
      guards.ts
    state/
      sessionStore.ts
      websocketStore.ts
      conversationStore.ts
      avatarStore.ts
```

## Migration Strategy

1. Define typed WebSocket message contracts in TypeScript.
2. Keep current backend protocol stable while adding tests.
3. Create a React shell that can open as hearing/deaf/rights by role.
4. Port preload bridge to TypeScript and expose a narrower API.
5. Port connection/session/emergency/status first.
6. Port hearing input and conversation transcript.
7. Port deaf avatar stage and quick/assist controls.
8. Port rights workflow.
9. Replace old renderer files after parity tests pass.

## Non-Negotiables

- No direct renderer fetches to backend.
- No renderer `require()`.
- No `nodeIntegration: true`.
- No raw secrets in renderer logs.
- No untyped WebSocket payloads in new code.
- No CDN-critical assets unless explicitly justified.
- No UI rewrite marked done without screenshots or rendered tests.

## Open Questions

- Whether to keep two physical BrowserWindows or move to one multi-pane window with optional pop-out roles.
- Whether React Three Fiber improves avatar maintainability enough to justify migration.
- Whether interpreter view should become first-class in the clean branch after Claude's work is reconciled.
- Whether rights workflow belongs in the same app shell or a modal/case workspace.
- Which component library, if any, should be used. Default should be custom restrained components plus accessible primitives, not a heavy theme kit.

