---
name: code-review
description: >
  Performs a thorough, structured code review following Clean Code, SOLID, DRY, KISS principles,
  and the Amandla project coding standards. Activate this skill whenever the user asks for a code review,
  asks "does this look good?", "can you check my code?", "review this function/file/PR", "is this clean code?",
  "refactor this", "is this production ready?", "check my implementation", or shows code and asks for feedback.
  Also activate when the user pastes code and seems uncertain about it — even without explicitly asking for a review.
---

# Code Review Skill

A great code review teaches, not just criticizes. Your goal is to help the developer grow, catch real problems,
and leave the code in a better state than you found it. Be specific, be constructive, explain the WHY.

---

## Review Philosophy

- Praise what is done well — good code deserves recognition
- Explain why something is a problem, not just that it is one
- Offer concrete fixes, not vague suggestions
- Prioritize: not everything needs to be fixed right now — distinguish must-fix from nice-to-have
- Remember: this developer is still learning. Language should be encouraging, not condescending

---

## Phase 1 — Understand Before Critiquing

Read the code completely before commenting. Ask yourself:
- What is this code supposed to do?
- Does it actually do that?
- Is it consistent with the rest of the codebase?

---

## Phase 2 — Functional Correctness

Check that the code actually works correctly:

- **Happy path**: does the code do what it's supposed to do in the normal case?
- **Edge cases**: what happens with empty input, null/undefined, zero, very large values?
- **Error cases**: what happens when things go wrong? Are errors handled?
- **Boundary conditions**: off-by-one errors, array bounds, loop conditions
- **Async/await**: are all Promises awaited? Are race conditions possible?
- **Type safety**: are types checked/validated before use?

---

## Phase 3 — Code Quality Checklist

### Naming
- [ ] Variable names describe what they hold (not `x`, `temp`, `data`, `val`, `flag`)
- [ ] Function names describe what they do (verb + noun: `calculateTotal`, `fetchUserData`)
- [ ] Boolean names read as questions (`isLoading`, `hasError`, `canSubmit`)
- [ ] No abbreviations unless universally understood (`url`, `id`, `db` are OK; `usr`, `msg`, `tmp` are not)

### Functions
- [ ] Each function does exactly ONE thing
- [ ] Functions are under 30 lines — if longer, they should be broken up
- [ ] Functions have a descriptive comment explaining purpose, parameters, and return value
- [ ] No side effects that aren't obvious from the function name
- [ ] Parameters are validated at the start of the function

### DRY (Don't Repeat Yourself)
- [ ] No duplicated code blocks — if the same logic appears twice, it should be a function
- [ ] No copy-pasted code with minor variations

### Magic Numbers and Constants
- [ ] No magic numbers (`if (status === 4)` → should be `if (status === STATUS.ACTIVE)`)
- [ ] Repeated string values are constants (`const MAX_AUDIO_SIZE = 10 * 1024 * 1024`)

### Comments
- [ ] Every function has a JSDoc or Python docstring comment
- [ ] Non-obvious logic has inline comments
- [ ] No commented-out dead code left in place (remove it — git history preserves it)
- [ ] No TODO comments without a ticket/issue reference

### Imports and Dependencies
- [ ] No unused imports
- [ ] No new third-party packages added without explaining why they're needed
- [ ] Imports are organized (standard library → third-party → local)

---

## Phase 4 — SOLID Principles Check

### S — Single Responsibility
Each class/module should have one reason to change.
> Red flag: a function called `processAndSaveAndNotify()` does three things.

### O — Open/Closed
Code should be open for extension, closed for modification.
> Red flag: adding a new message type requires editing a long if/else chain instead of adding a handler.

### L — Liskov Substitution
Subclasses should be usable wherever their parent is expected.
> Mostly relevant in Python service classes.

### I — Interface Segregation
Don't force callers to depend on methods they don't use.
> Red flag: a service class with 20 methods where callers only ever use 2 of them.

### D — Dependency Inversion
High-level modules should not depend on low-level modules — both depend on abstractions.
> Red flag: `hearing.js` directly calling `fetch('/api/...')` instead of going through `window.amandla.*`.

---

## Phase 5 — Security Quick Check

Even in a code review (not a full audit), flag obvious security issues:

- Hardcoded credentials or API keys → immediate flag
- `innerHTML = userInput` → XSS vulnerability
- User input concatenated into a command or query → injection vulnerability
- `eval()` or `exec()` on untrusted input → critical
- Missing input validation on a public-facing function → flag

For deep security review, recommend using the `security-audit` skill.

---

## Phase 6 — Error Handling

- [ ] All async functions have try/catch
- [ ] Catch blocks do something useful (log + rethrow, or handle gracefully)
- [ ] No empty catch blocks (`catch (e) {}` — this hides bugs)
- [ ] Error messages to users are friendly, not raw exceptions
- [ ] Network failures are handled (what happens if the WebSocket disconnects?)

---

## Phase 7 — Amandla-Specific Patterns

When reviewing Amandla code, also check:

### Frontend (Electron Renderers)
- No `require()` calls — all backend calls go through `window.amandla.*`
- No direct `fetch()` calls to the backend — use the preload bridge
- Event listeners are cleaned up when the page unmounts

### Backend (FastAPI)
- WebSocket message types are validated against known types before processing
- All responses include proper HTTP status codes
- `load_dotenv()` is NOT called in service files (only `backend/main.py`)

### Signs / Avatar
- `sign_maps.py` is the only place English→SASL mappings are defined
- `FINISH`/`WILL` aspect markers are preserved
- Modal verbs are not treated as filler words

---

## Review Output Format

```
## Code Review

### ✅ What's Good
[Be specific about what is well-written]

### 🔴 Must Fix (blocks merge/shipping)
**Issue**: [What the problem is]
**Why**: [Why this matters — teach the developer]
**Fix**:
```code
[Exact code to fix it]
```

### 🟡 Should Fix (important but not blocking)
[Same format as above]

### 🟢 Nice to Have (suggestions for improvement)
[Minor suggestions, style preferences, future improvements]

### Summary
[One paragraph: overall quality assessment, key takeaways for the developer]
```

---

## After the Review

1. Offer to implement any "Must Fix" items (present a plan first, wait for approval)
2. If major refactoring is needed, propose it as a separate task — don't try to do everything at once
3. Acknowledge what the developer did well — learning is hard and good work deserves recognition

---

## Environment Notes

**In Claude Code (terminal/JetBrains):**
```bash
# Check for common issues automatically
# Python: style and unused imports
flake8 backend/ --max-line-length=100
# JavaScript: linting
npx eslint src/ --ext .js
# Check for TODO comments without references
grep -rn "TODO\|FIXME\|HACK\|XXX" . --include="*.py" --include="*.js"
```

**In Claude.ai (browser):** Work from the code the user shares. Ask for context if needed:
"Which file is this from?" or "What should this function do in the edge case of X?"
