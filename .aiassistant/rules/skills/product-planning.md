---
name: product-planning
description: >
  Structures new feature ideas, project planning, PRD creation, MVP definition, and user story writing
  into production-quality plans before any code is written. Activate when the user says "I have an idea",
  "let's build X", "new feature", "PRD", "product requirements", "what should we build next", "MVP",
  "user story", "plan this out", or presents a vague concept that needs to be shaped before coding starts.
  Also activate at the start of any new project sprint. Ideas that skip planning become bad code.
---

# Product Planning Skill

A feature without a plan becomes a bug. Time spent planning prevents 10x the time debugging.
The goal: turn a rough idea into a clear, actionable spec before a single line of code is written.

---

## Phase 1 — Idea to Problem Statement

Before thinking about the solution, deeply understand the PROBLEM.

Ask these questions (or infer from context):

1. **Who has this problem?** — Be specific. "Deaf users" is too vague. "A deaf user communicating in real-time with a hearing shopkeeper" is precise.

2. **What is the actual pain?** — What is the user currently unable to do, or struggling to do?

3. **Why does it matter?** — What happens if we don't solve it? Who is impacted?

4. **How do we know this is a real problem?** — Observation? User feedback? Personal experience?

Write this as a one-paragraph **Problem Statement**:
> "When [specific user] tries to [do specific thing], they [face this problem], which causes [this consequence]. This matters because [impact]."

**Example for Amandla:**
> "When a deaf Amandla user wants to communicate urgency or emergency to a hearing person, they currently have no fast-access button for common emergency phrases. They must wait for the full sign animation, which is too slow in a crisis. This matters because emergencies are exactly when Amandla must work fastest."

---

## Phase 2 — Define the Solution

Now describe the solution in plain language. No code. No wireframes yet.

Write a **Solution Statement**:
> "We will [build/add/change] X, which will allow [user] to [accomplish goal] by [mechanism]."

Then answer:
- What does the user see?
- What do they do?
- What happens as a result?
- What does success look like?

---

## Phase 3 — Scope (MVP vs Full Vision)

Every feature has a minimal version and an ideal version. Build the minimal version first.

### The MVP Test
For each proposed feature, ask: "Can users get the core value without this?"
- If YES → it's a "nice to have", not MVP
- If NO → it's MVP

**Example:**
| Feature | MVP? | Reason |
|---------|------|--------|
| Quick-access emergency phrases | ✅ YES | Without this, the pain point isn't solved |
| Customizable phrase categories | ❌ NO | Useful but the core value works without it |
| Phrase usage analytics | ❌ NO | Nice, but not needed for core function |
| Multi-language emergency phrases | ❌ NO | English first, expand later |

---

## Phase 4 — User Stories

Write user stories in this format:
> "As a [specific user type], I want to [do something], so that [I achieve this outcome]."

Each user story should be:
- **Independent**: can be built without depending on another story
- **Small**: completable in a few days
- **Testable**: you can verify it works

**Example User Stories for Emergency Phrases:**
1. As a deaf user, I want to tap a button labeled "EMERGENCY" to instantly send the phrase "I need help" to the hearing window, so that I can communicate urgency in under 2 seconds.
2. As a deaf user, I want to see 3-4 pre-configured emergency phrases on the deaf window, so that I can tap the right one without typing.
3. As a hearing user, I want to see the emergency phrase appear prominently in red on my window, so that I immediately notice the urgency.

---

## Phase 5 — Technical Considerations

Now (and only now) think about technical implications:

- What files will be created or changed?
- What new API endpoints or WebSocket message types are needed?
- Are there security implications?
- Are there performance implications?
- Does this conflict with any existing architecture decisions in CLAUDE.md?

Flag if the implementation would require changing any non-negotiable constraints.

---

## Phase 6 — Acceptance Criteria

Define exactly what "done" means. These become your test cases.

```
Feature: Emergency Phrases

GIVEN the Amandla app is running and connected
WHEN a deaf user taps the "EMERGENCY" button
THEN the hearing window receives a message type 'emergency'
AND the message appears highlighted in red within 500ms
AND the avatar signs the phrase simultaneously

GIVEN the backend is disconnected
WHEN a deaf user taps the "EMERGENCY" button
THEN the UI shows an error state (not a blank screen)
AND a reconnect option is presented
```

---

## Phase 7 — The PRD (Product Requirements Document)

For larger features, compile phases 1-6 into this template:

```markdown
# PRD: [Feature Name]

**Date**: [date]
**Status**: Draft / Under Review / Approved
**Author**: [name]

## Problem Statement
[One paragraph from Phase 1]

## Solution Overview
[Solution statement from Phase 2]

## Scope — MVP
[Table from Phase 3 — only MVP items]

## Out of Scope (Future)
[Non-MVP items to revisit later]

## User Stories
[List from Phase 4]

## Technical Notes
[Notes from Phase 5]

## Acceptance Criteria
[BDD scenarios from Phase 6]

## Open Questions
[Anything still unresolved that blocks implementation]
```

---

## Phase 8 — Before Handing Off to Development

Final checks:
- [ ] Problem is clearly defined (not just "users want X")
- [ ] MVP scope is agreed upon
- [ ] Acceptance criteria are specific enough to write tests from
- [ ] Technical constraints reviewed against CLAUDE.md
- [ ] No ambiguous requirements ("fast" → define in milliseconds, "prominent" → define in pixels)
- [ ] Open questions are resolved or explicitly tracked

---

## Environment Notes

**In Claude Code (terminal):** Create the PRD as a markdown file:
```bash
mkdir -p docs/planning
touch docs/planning/prd-emergency-phrases.md
```

**In Claude.ai (browser):** Walk through each phase conversationally.
I'll ask the questions and help structure the answers. Planning in conversation
before writing code is the right order — always.
