# Product Design Brief

Date: 2026-07-05
Status: proposed brief - not yet confirmed for UI implementation

## Brief Playback

AMANDLA should become a modern desktop communication workspace for deaf and hearing South Africans. It should feel trustworthy, calm, fast, and serious: closer to a polished accessibility tool from Apple/Google/OpenAI than a hackathon demo.

The product must let a hearing person speak/type, let a deaf person read SASL gloss and avatar signing, let the deaf person reply quickly, and preserve rights/history workflows without making the screen feel like a pile of controls.

## Product Problem

When a deaf South African and a hearing person need to communicate in real time, the current app gives them a basic avatar and message controls but does not yet prove reliability, clarity, speed, or accessibility. This creates risk in the exact moments where the app matters: medical visits, workplace rights issues, public services, school, transport, or emergencies.

## Product Promise

AMANDLA helps two people hold a real conversation across hearing and deaf communication modes, with visible translation state, fallback paths, and a record of what happened.

## Primary Users

| User | Need |
|---|---|
| Deaf user | Understand incoming spoken/typed language through SASL gloss/avatar; reply quickly through signs, typed SASL, assist phrases, or camera when proven. |
| Hearing user | Speak/type naturally; see what was translated; hear/read deaf user's reply. |
| Support worker/interpreter | Monitor session context without disrupting the conversation. |
| Rights user | Document discrimination, generate a complaint letter, export record. |
| Developer/researcher | Run repeatable tests and prove model/UI behavior before shipping. |

## Visual Direction

No concrete visual source has been selected yet. The current design direction should be:

- Modern accessibility command center.
- Calm dark or neutral interface, not decorative sci-fi.
- Strong information hierarchy.
- Large reliable controls.
- Professional typography.
- Subtle status indicators.
- Human-centered avatar stage.
- Transcript and gloss treated as first-class content.
- Minimal ornament, no decorative clutter.

Inspirational quality bar:

- Apple-level restraint.
- Google-level clarity.
- ChatGPT-level conversational polish.
- Claude/Codex-level developer-grade state visibility.

This is not permission to copy those products. It is a quality target.

## Interaction Level

Target: full interactivity.

All controls should eventually work:

- Session connection.
- Send typed message.
- Record speech.
- Show translation progress.
- Play/replay signs.
- Adjust avatar speed.
- Send deaf reply.
- Use assist phrases.
- Trigger emergency.
- Open rights workflow.
- Export conversation.
- Handle offline/missing model states.

## Proposed App Model

Two viable layouts must be explored visually before implementation:

| Option | Description | When It Wins |
|---|---|---|
| Split Workspace | One Electron window with hearing pane, deaf/avatar pane, shared session rail, and optional pop-out windows. | Best for modern app cohesion and easier React state management. |
| Role Windows | Keep separate hearing/deaf/rights/interpreter windows, but rebuild each as a consistent React role surface. | Best if the physical split-screen interaction is essential. |

Research recommendation:

- Explore both visually.
- Do not commit to one until the user reviews mock directions.

## Core Screens To Redesign

1. Session lobby / readiness state.
2. Hearing conversation panel.
3. Deaf avatar and reply panel.
4. Assist phrase mode.
5. Camera recognition mode with "experimental" honesty.
6. Emergency state.
7. Rights case workspace.
8. Conversation history/export.
9. Settings: model, language, avatar speed, accessibility.
10. Developer/research diagnostics: model, latency, protocol, fallback reason.

## UX Requirements

- Every action gets feedback.
- Every AI call has loading, success, failure, and fallback states.
- Missing Ollama is a first-class state, not a terminal surprise.
- Missing model is distinct from Ollama not running.
- No feature claims accuracy unless evaluation exists.
- Color never carries meaning alone.
- Keyboard navigation works.
- Focus is visible and not obscured.
- Reduced-motion mode works.
- Emergency is reachable without precise pointer movement.
- Text and controls must not overlap at narrow window sizes.

## Content Requirements

Use plain, respectful wording.

Avoid:

- "AI magic"
- "perfect translation"
- "recognizes SASL" unless measured
- confusing technical errors
- long instructional text inside the main workflow

Prefer:

- "Translation service offline"
- "Using rule-based fallback"
- "Camera recognition is experimental"
- "Replay signs"
- "Save conversation record"

## Design Gates Before Build

Before implementing the React UI:

1. Confirm this brief.
2. Choose whether to explore split workspace, role windows, or both.
3. Generate or sketch exactly three visual directions.
4. Select one visual direction.
5. Build the React shell from that selected direction.
6. Verify with screenshots and accessibility checks.

## Open Questions

1. Should AMANDLA remain physically split across two windows, or become one unified workspace with pop-outs?
2. Should the rights workflow be part of the main conversation session or a separate case workspace?
3. Should camera recognition be hidden until evaluated, or shown as clearly experimental?
4. Should the avatar be the visual center, or should transcript/gloss dominate with avatar as support?
5. What languages should be visible in the first rebuild: English only until pipeline proven, or all South African languages with honest fallback labels?

