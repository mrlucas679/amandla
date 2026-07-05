# AMANDLA Modernization Verification Matrix

Status: proposed gates, not yet passing
Date: 2026-07-05
Branch: `codex/modernization-research`

## Purpose

This matrix turns the modernization research into proof. AMANDLA should not be called working, modern, secure, or accessible until each claim has a repeatable check.

Current state: most gates are not yet runnable because Python is unavailable, Ollama has no pulled models, and no React migration has been implemented.

## Project-Level Gates

| ID | Requirement | Proof Source | Automated Gate | Manual Proof | Status |
|---|---|---|---|---|---|
| REQ-001 | Work stays isolated from Claude | Git branch/worktree status | `git -C C:\Users\Admin\amandla-desktop-codex-research status` and `git -C C:\Users\Admin\amandla-desktop status` | Confirm docs exist only in Codex worktree | Passing so far |
| REQ-002 | No production code changes before approval | Git diff | `git diff --name-only` contains only `docs/research/...` | Review file list before handoff | Passing so far |
| REQ-003 | No destructive cleanup without approval | Git diff and filesystem | No deleted files in `git status` | Cleanup proposal names deletions without executing them | Passing so far |
| REQ-004 | Current app treated as unproven | Research docs | Defect register remains open until tests pass | Final summary avoids claiming runtime success | Passing so far |
| REQ-005 | Design brief confirmed before UI build | Product design brief | No React UI files added before confirmation | User confirms visual direction or selects visual option | Pending |

## Defect Gates

| Defect | Risk | Required Proof | Proposed Automated Gate | Current Status |
|---|---|---|---|---|
| DEF-001 | Python/model unavailable | Backend and Ollama can start locally | `python --version`, `ollama --version`, `ollama list`, `curl http://localhost:8000/health` | Failing: Python shim is broken; Ollama `0.30.10` runs but has no models |
| DEF-002 | Assist phrase WebSocket crash | `assist_phrase` routes without `NameError` | WebSocket integration test sends `assist_phrase` and expects `deaf_speech` | Not fixed |
| DEF-003 | WebSocket auth protocol drift | Code, docs, and tests use one auth method | Test valid token accepted and invalid token rejected using documented method | Not fixed |
| DEF-004 | Renderer manual connect race | Renderer does not open unauthenticated demo sockets | Playwright/Electron test checks one connection per role with token | Not fixed |
| DEF-005 | Direct renderer backend fetch | Renderers only use preload API | Static check fails on `fetch('http://localhost` in renderer-loaded code | Not fixed |
| DEF-006 | Raw exception exposure | Client gets generic errors only | HTTP tests force failures and assert no raw exception text | Not fixed |
| DEF-007 | Dependency vulnerabilities | Moderate+ production vulnerabilities addressed or accepted | `npm audit --omit=dev --audit-level=moderate` | Not fixed: production `js-yaml` vulnerability observed |
| DEF-008 | AI recognition validity | HARPS/Ollama outputs measured on known cases | Golden landmark/sign cases with confidence thresholds | No evaluator yet |
| DEF-009 | UI testability | UI state can be unit and E2E tested | Vitest component tests and Playwright Electron smoke tests | No React/test harness yet |
| DEF-010 | Documentation drift | Current docs match code and stale docs quarantined | Doc inventory checklist plus protocol doc tests | Partial research only |
| DEF-011 | Repo noise | Generated/duplicate artifacts removed or quarantined after approval | Git status excludes generated DB WAL/SHM and duplicate docs | Pending approval |
| DEF-012 | Dirty branch drift | Claude WIP is treated as non-authoritative evidence only | No file copied from dirty checkout without review | Passing so far |
| DEF-013 | Accessibility gaps | Keyboard, focus, contrast, reduced motion verified | axe, Playwright keyboard paths, WCAG checklist | No UI implementation yet |
| DEF-014 | CSP/offline posture | Required external domains are deliberate and minimized | Static CSP check plus offline launch test | Not fixed |

## Stack Decision Gates

| Claim | Required Proof | Gate |
|---|---|---|
| React is appropriate | Migration plan explains state, testing, accessibility, and alternatives | `react-migration-plan.md` accepted |
| Vite/Electron Forge is appropriate | Main, preload, and renderer can build separately | Prototype branch build, later |
| Keep FastAPI initially | Backend smoke and tests can be restored faster than a rewrite | Phase 1 rescue gates pass |
| Keep Three.js initially | Current avatar can be wrapped and measured before replacement | Canvas smoke, pose validator, frame-rate check |
| Do not move to Tauri now | Shell rewrite risk exceeds immediate benefit | Architecture decision record accepted |

## Runtime Gates

| Area | Gate | Target |
|---|---|---|
| Startup | App launches backend and Electron without crash | Backend health available before windows connect |
| Connection | Hearing/deaf/rights windows authenticate | Valid token accepted, bad token rejected |
| Hearing to deaf | Text becomes SASL signs and avatar receives them | Known golden prompts produce expected sign sets |
| Deaf to hearing | Sign queue reconstructs English | Known sign sequences produce readable English |
| Speech upload | Audio under 10 MB handled, oversized rejected | Generic errors and rate limits enforced |
| Rights workflow | Analyze and letter requests use WebSocket requests | `request_id` resolves once and errors are generic |
| History | Messages persist without breaking main flow | History fetch returns current session only unless `list_sessions` |
| Emergency | Shortcut/event reaches both role windows | Overlay visible and dismiss behavior tested |

## Accessibility Gates

| Requirement | Gate | Notes |
|---|---|---|
| Keyboard operation | Playwright tab/enter/escape paths for each core workflow | Must cover hearing send, deaf quick signs, rights wizard, emergency |
| Focus visibility | CSS review plus screenshot checks | Follow WCAG 2.2 focus-visible and focus-appearance guidance |
| Contrast | axe plus manual contrast checks | Especially status colors and disabled states |
| Reduced motion | `prefers-reduced-motion` behavior | Avatar can keep functional sign playback but UI effects reduce |
| Error comprehension | User-facing messages are plain, local, and non-technical | No Python stack details or raw provider errors |
| Screen reader names | Accessible names for icon buttons and status regions | Required if icon-only controls are used |

## Completion Definition

The modernization research phase is complete only when:

- The user approves or amends the deletion/quarantine proposal.
- The user confirms the design brief or selects a visual direction.
- Phase 1 rescue work has an approved implementation plan.
- The evaluation harness plan is converted into runnable tests.
- Runtime claims are backed by test output, not assumption.
