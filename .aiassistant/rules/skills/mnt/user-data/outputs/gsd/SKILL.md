---
name: gsd
description: >
  Spec-driven development system that prevents context rot and quality degradation
  across long-running builds. Activate when the user wants to start a new project,
  add a significant feature, or says anything like "I want to build X", "let's start
  a new project", "help me plan this", "I have an idea", "let's work on a new
  feature", "/gsd", or "get shit done". Also activate when a project is growing
  complex and the agent is losing context clarity, or when the user wants structured
  phases with verification gates. GSD is your context engineering layer — use it
  proactively before quality degrades, not after.
---

# GSD — Get Shit Done

**Source:** Based on [gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done) —
a lightweight, spec-driven development system trusted by engineers at Amazon, Google, Shopify,
and Webflow.

**Core problem solved:** Context rot — the quality degradation that happens as an AI fills its
context window. GSD solves this by breaking work into fresh, isolated execution phases, each
with its own clean context.

**Philosophy:** No enterprise theater. No story points, sprint ceremonies, or Jira workflows.
Just a system that gives the AI everything it needs to do the work *and verify it*.

---

## The GSD Workflow

### Step 1 — MAP THE CODEBASE (existing projects only)

**Skip for brand-new projects.**

For existing codebases, run a parallel analysis before planning:

```
Spawn parallel agents to analyze:
- Stack and dependencies (STACK.md)
- Architecture and component relationships (ARCHITECTURE.md)
- File/folder conventions (STRUCTURE.md)
- Code patterns and style (CONVENTIONS.md)
- Test setup and coverage (TESTING.md)
- External integrations (INTEGRATIONS.md)
- Known concerns and tech debt (CONCERNS.md)
```

Save results to `.planning/codebase/`. Planning will automatically load these patterns so
questions focus on what you're *adding*, not re-explaining what's already there.

---

### Step 2 — NEW PROJECT INITIALIZATION

**Trigger:** User wants to build something new.

Run the questioning → research → requirements → roadmap flow:

#### 2a. QUESTIONING PHASE

Ask until you fully understand the idea. Don't proceed until every item below is answered:

```
□ Core goal — What is this, in one sentence?
□ Target user — Who uses it and how?
□ Must-have features (v1 scope)
□ Nice-to-have features (v2+)
□ Out of scope (explicitly excluded)
□ Tech preferences or constraints
□ Success criteria — how do we know it's done?
□ Known risks or hard problems
```

Ask 3–5 focused questions at a time. Pause for answers. Never assume.

#### 2b. RESEARCH PHASE (optional but recommended)

Spawn parallel research agents to investigate:
- Standard stacks and patterns for this domain
- Known pitfalls or gotchas
- Relevant libraries, APIs, or tools

Save research to `.planning/research/`.

#### 2c. REQUIREMENTS

From questioning + research, extract:

```markdown
## v1 Requirements (must ship)
- [concrete, testable requirement]
- ...

## v2 Requirements (future)
- ...

## Explicitly Out of Scope
- ...
```

Show requirements to user. Get explicit approval.

**Scope reduction detection:** If at any point the planner drops a v1 requirement without
user approval, flag it immediately. Requirements are locked once approved.

#### 2d. ROADMAP

Break v1 requirements into phases:

```markdown
## Phase 1: [Name]
Goal: [one sentence]
Requirements covered: [list from REQUIREMENTS.md]
Deliverable: [what the user will see/test]

## Phase 2: [Name]
...
```

Each phase should produce working, testable software on its own. Show roadmap to user.
Get explicit approval before any implementation begins.

**Saves:** `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`

---

### Step 3 — DISCUSS PHASE (before each phase)

**Never skip.** Skipping leads to more iterations later.

Before executing any phase:
1. Review the phase goal and requirements it covers.
2. Ask the user targeted clarifying questions:
   - Any preferences about how this should work?
   - Any constraints not already captured?
   - Any edge cases to handle?
3. Confirm understanding before proceeding.

Spend 5–10 minutes here. It saves hours of back-and-forth.

---

### Step 4 — PLAN PHASE (per phase)

Create a detailed execution plan for the current phase:

```markdown
# Phase X Plan: [Name]

## Files to create or modify
- src/foo.ts — [what it's responsible for]
- tests/foo.test.ts — [what it verifies]

## Tasks (in order)
- [ ] Task 1: [exact description, file path, what to implement]
  Verification: [how to confirm it's done]
- [ ] Task 2: ...
```

Rules:
- Each task has a clear verification step
- Tasks are small (2–5 min) and independent where possible
- File responsibilities are defined before writing code (prevents overlap)
- Show plan to user. Get sign-off.

---

### Step 5 — EXECUTE PHASE

**Context isolation is key.** Each phase runs in a fresh context:

```
Spawn execution agent with:
- PROJECT.md (vision and context)
- REQUIREMENTS.md (what must be true)
- Current phase plan
- Codebase analysis (from Step 1)
- Relevant project-specific skills
```

The main session stays lean (30–40% context). Heavy lifting happens in the isolated agent.

#### During execution:
1. Work through plan tasks in order.
2. After each task: run verification. If it fails, fix before moving to next task.
3. No task is "done" without its verification passing.

**Schema drift detection:** If ORM/database schema files change, flag it — migrations are
likely required. Don't silently proceed.

---

### Step 6 — VERIFY PHASE

After execution, before calling a phase complete:

```
□ All tasks in the plan are checked off
□ All verification steps passed
□ No requirements silently dropped
□ No regressions in existing functionality
□ User can see/test the deliverable
```

Write a phase summary:
```markdown
## Phase X Summary
Completed: [what was built]
Verified: [how it was tested]
Notes: [anything the user should know]
Next phase: [what's coming]
```

Update `STATE.md` with current phase, status, and what's next.

---

### Step 7 — REVIEW PHASE (quality gate)

Run a structured review before marking phase complete:

```
Security review:
□ No hardcoded credentials
□ No path traversal vulnerabilities
□ Input validation on user-supplied data
□ No sensitive data logged

Code quality review:
□ Functions have clear single responsibilities
□ Error paths are handled
□ No obvious performance issues
□ Code matches project conventions (from CONVENTIONS.md)
```

Peer review (when configured): spawn a reviewer agent with the diff and the plan.
Reviewer checks spec compliance first, then code quality.

---

## Context Management Rules

GSD solves context rot. Follow these rules:

1. **Fresh context per phase** — don't carry stale state from phase to phase.
2. **Load only what's needed** — inject PROJECT.md, requirements, and the current plan.
   Don't load the full codebase into every context.
3. **STATE.md is the source of truth** — always update it. Agents should read it at start.
4. **If context > 60%, stop** — summarize, update STATE.md, start fresh.

---

## Quick Commands Reference

| What you want | What to do |
|---|---|
| Start a brand new project | Step 2 (new project init) |
| Add a major feature to existing code | Step 1 (map codebase) → Step 2 |
| Work on the next phase | Step 3 (discuss) → Step 4 (plan) → Step 5 (execute) → Step 6 (verify) |
| Review quality before shipping | Step 7 (review) |
| Something small/quick | Skip GSD — just prompt directly |

**GSD is for non-trivial work.** For a color change or a typo fix, use GSD's overhead is
overkill — just fix it directly.

---

## State Files Reference

```
.planning/
├── PROJECT.md       — Vision, goals, tech choices, what we're building
├── REQUIREMENTS.md  — Versioned requirements (v1/v2/out-of-scope)
├── ROADMAP.md       — Phases mapped to requirements
├── STATE.md         — Current milestone, active phase, last completed task
├── research/        — Domain research from research agents
├── codebase/        — Codebase analysis (stack, architecture, conventions)
└── phases/
    └── XX-name/
        ├── XX-PLAN.md          — Detailed task plan
        ├── XX-SUMMARY.md       — What was built
        ├── XX-VERIFICATION.md  — How it was verified
        └── XX-CONTEXT.md       — Context injected into execution agent
```

---

## Anti-Patterns

| Anti-pattern | Consequence |
|---|---|
| Skipping discuss-phase | More rework, Claude makes wrong assumptions |
| Starting execution without an approved plan | Builds the wrong thing |
| Not updating STATE.md between phases | Context rot, agent loses orientation |
| Running GSD on a 2-line bug fix | Waste of overhead |
| Letting context exceed 60% without resetting | Quality degrades silently |
| Planner silently drops requirements | Scope creep goes undetected |

---

## When NOT to use GSD

- Tiny fixes (typos, color changes, one-liners)
- Quick questions or explorations
- Tasks where the answer is already obvious

For small tasks, just do them directly. GSD's power is in sustained, complex builds.
