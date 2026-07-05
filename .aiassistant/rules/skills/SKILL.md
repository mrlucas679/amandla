---
name: superpowers
description: >
  A complete, structured software development workflow that enforces a disciplined
  brainstorm → plan → TDD → execute → review cycle. Activate this skill whenever
  the user is about to build a new feature, start implementing something, write code,
  debug a problem, or says anything like "let's build", "help me implement", "how
  should I approach", "start coding", "add a feature", "fix this bug", or "let's
  work on X". Also activate when writing new skills. This skill overrides the
  default impulse to jump straight into code — the agent MUST check this skill
  FIRST. Even a 1% chance it applies means you should invoke it.
---

# Superpowers — Structured Development Workflow

**Source:** Based on [obra/superpowers](https://github.com/obra/superpowers) — a battle-tested
agentic skills framework used by 149k+ developers.

**Core principle:** Never jump straight into code. Every session follows the full workflow.
Shortcuts are violations. The complexity lives in the system — not in your daily experience.

---

## The Mandatory Workflow

Follow these phases in order. Do not skip. Do not reorder.

### Phase 1 — BRAINSTORM (before any code or planning)

**Trigger:** Any new feature, task, fix, or vague idea.

1. **Do NOT write code or a plan yet.**
2. Ask the user targeted questions to fully understand the goal:
   - What problem does this solve?
   - What does success look like?
   - What constraints exist (performance, backwards compat, dependencies)?
   - What edge cases matter?
   - What should NOT be in this version?
3. Present your understanding back in short, digestible chunks (≤3 bullet points at a time).
4. Get explicit confirmation: *"Does this capture what you want?"*
5. Save the confirmed spec to `docs/specs/YYYY-MM-DD-<feature-name>.md`.

**Hard rule:** If the user hasn't confirmed a spec, you cannot move to Phase 2.

---

### Phase 2 — WRITE THE PLAN

**Trigger:** User has confirmed the brainstormed spec.

1. Create a git worktree for isolated development:
   ```bash
   git worktree add ../feature-<name> -b feature/<name>
   ```
2. Run setup and verify baseline (all existing tests must pass before you start).
3. Break work into **bite-sized tasks** (2–5 minutes each):
   - Each task has: exact file paths, complete code, verification steps
   - Tasks are small enough for a junior developer to execute without judgment
4. Save plan to `docs/plans/YYYY-MM-DD-<feature-name>.md` with checkboxes:
   ```markdown
   - [ ] Task 1: Create X in src/y.ts
   - [ ] Task 2: Add test for X
   ```
5. Show the full plan to the user and get sign-off before executing.

**Hard rule:** No execution without a signed-off plan.

---

### Phase 3 — TEST-DRIVEN DEVELOPMENT (during execution)

**This is non-negotiable.** Every task follows RED → GREEN → REFACTOR.

#### RED Phase
1. Write a failing test FIRST.
2. Run it. Watch it fail. Confirm it fails for the right reason.
3. **Do not write implementation code yet.**

```
Write test → Run test → See it FAIL → Proceed
```

#### GREEN Phase
4. Write the **minimum** code to make the test pass.
5. Run the test. Watch it pass.
6. Do not add anything extra. YAGNI.

#### REFACTOR Phase
7. Clean up code without breaking tests.
8. Run tests again. Still passing? Commit.

**Violations — delete and restart:**
- Wrote code before writing the test? **Delete the code. Start over.**
- Test was written after code? **Delete both. Start over.**
- Rationalizing "I'll write the test later"? **That's the violation.**

---

### Phase 4 — EXECUTE THE PLAN

1. Work through tasks one by one using TDD (Phase 3) for each.
2. After each task: run the full test suite. All tests must pass before the next task.
3. Commit after each passing task:
   ```bash
   git add -p && git commit -m "feat: [task description]"
   ```
4. Request code review between major milestones (see Phase 5).

**Subagent dispatch (when available):**
- Spawn a fresh subagent per task for isolated, clean context.
- Each subagent gets: the plan, the specific task, and the TDD requirement.
- Review subagent output before accepting: check spec compliance first, then code quality.

---

### Phase 5 — CODE REVIEW

Run before merging or after completing a milestone.

**Pre-review checklist:**
- [ ] All tests pass
- [ ] No TODO/FIXME left from this work
- [ ] No dead code added
- [ ] No unnecessary dependencies added
- [ ] Matches the approved spec (nothing extra, nothing missing)

**Review dimensions (in order of severity):**
1. **Critical** — spec violations, broken tests, security issues → BLOCK, do not merge
2. **Major** — missing error handling, poor naming, logic gaps → fix before merging
3. **Minor** — style, minor improvements → fix or note for follow-up

**Receiving review:** Never argue. Either fix it or explicitly acknowledge why you're not.

---

### Phase 6 — FINISH THE BRANCH

**Trigger:** All plan tasks complete and review passed.

1. Verify: all tests green, no regressions.
2. Present options:
   - Merge to main (squash recommended)
   - Open a PR for human review
   - Keep branch for further work
   - Discard the worktree
3. Clean up worktree after merge:
   ```bash
   git worktree remove ../feature-<name>
   ```

---

## Systematic Debugging (when something is broken)

Follow this 4-phase process. Do NOT guess and check.

**Phase 1 — Reproduce:** Confirm the bug is reproducible. Write a failing test that captures it.

**Phase 2 — Isolate:** Narrow down where it occurs. Add logging/assertions to trace the path.

**Phase 3 — Root cause:** Trace backward from the symptom to the original trigger. See `references/root-cause-tracing.md`.

**Phase 4 — Fix & verify:**
1. Write the fix.
2. Run the failing test — it must now PASS.
3. Run the full test suite — nothing new breaks.
4. Commit only after both checks pass.

**If 3 fixes have failed:** Stop. Question the architecture. Discuss with user before more attempts.

**Hard rule:** Never claim something is fixed without running the test that proves it.

---

## Verification Before Completion

Before declaring ANY task done:

```
[ ] The specific thing I was asked to do works
[ ] I ran the test/check that proves it works
[ ] I didn't break anything else (full test suite green)
[ ] The output matches what was in the spec
```

Saying "it should work" or "I think it's done" without evidence is a violation.

---

## Writing New Skills

When creating a skill:

1. **Define** what problem the skill solves and when it triggers.
2. **Write** the SKILL.md following the format above.
3. **Test** it: simulate the skill being invoked and verify the output is correct.
4. **If you didn't watch failure before writing, you don't know if the skill works.**

Keep SKILL.md under 500 lines. Move large reference material to `references/`.

---

## Anti-Patterns (Never Do These)

| Anti-pattern | Why it's bad |
|---|---|
| Jumping to code before brainstorming | Builds the wrong thing |
| Planning before spec is confirmed | Wasted planning effort |
| Writing code before tests | No safety net, can't verify |
| Claiming fixed without running test | Lies to the user |
| Adding code not required by spec | YAGNI violation |
| Skipping code review | Ships hidden problems |
| Arguing with review feedback | Breaks trust |

---

## Quick Reference

```
New work:     BRAINSTORM → PLAN → (TDD × tasks) → REVIEW → FINISH
Each task:    RED (write failing test) → GREEN (minimal code) → REFACTOR → COMMIT
Bug:          REPRODUCE → ISOLATE → ROOT CAUSE → FIX + VERIFY
Done check:   Test passes + suite green + matches spec
```
