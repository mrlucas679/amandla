---
name: skill-manager
description: >
  The meta-skill that manages, audits, and evolves the entire skill library. Activate this skill
  whenever the user asks "what skills do we have?", "do we need a new skill?", "can you check our skills?",
  "are our skills up to date?", "what skill covers X?", or when starting ANY new project or feature — to
  check if the current skill set is sufficient or if a gap needs filling. Also activate when a task
  feels unfamiliar, when a new technology is being introduced, or when the user mentions building something
  that doesn't clearly fit an existing skill. Think of this as the skill librarian — always consulted first.
---

# Skill Manager

You are the librarian of a living skill library. Your job is to:
1. Know what skills exist and what they cover
2. Match user tasks to the right skills
3. Spot gaps — when something valuable isn't covered by any skill
4. Recommend creating new skills when the gap is real and recurring
5. Keep skills from going stale as the project evolves

---

## The Current Skill Library

### Project Foundation Skills
| Skill | Triggers On | Covers |
|-------|-------------|--------|
| `amandla-code-standards` | Any Amandla code change | AI rules, architecture, planning-first, CLAUDE.md constraints |
| `project-bootstrap` | "start new project", "create project", "scaffold" | New project structure, CLAUDE.md, .gitignore, folder layout |
| `product-planning` | "new feature idea", "plan this", "PRD", "MVP" | PRDs, feature scoping, MVP definition, user stories |

### Code Quality Skills
| Skill | Triggers On | Covers |
|-------|-------------|--------|
| `code-review` | "review this", "check my code", "is this good?" | Clean Code, SOLID, DRY, naming, error handling |
| `security-audit` | "security check", "vulnerabilities", "OWASP" | OWASP Top 10, Electron/FastAPI security, secrets |
| `refactoring` | "clean this up", "refactor", "this is messy" | Safe incremental refactoring, patterns |
| `testing-strategy` | "write tests", "how to test", "TDD" | Unit/integration/E2E, pytest, test patterns |
| `debugging` | "it's broken", "error", "why isn't this working" | Systematic debugging, Python/JS/Electron |

### Platform Skills
| Skill | Triggers On | Covers |
|-------|-------------|--------|
| `python-fastapi` | Any FastAPI/Python backend work | FastAPI patterns, Pydantic, async/await, WebSocket |
| `electron-ipc` | Any Electron window/preload work | IPC, contextBridge, preload patterns, security |
| `api-design` | "design this API", "new endpoint", "WebSocket message" | REST/WebSocket design, versioning, contracts |

### Dev Workflow Skills
| Skill | Triggers On | Covers |
|-------|-------------|--------|
| `git-workflow` | Git/GitHub questions, before commit/push | Branching, Conventional Commits, PRs, GitHub Actions |
| `documentation` | "write docs", "README", "explain this code" | README structure, docstrings, API docs, CHANGELOG |
| `performance-optimization` | "it's slow", "optimize", "performance" | Profiling, bottlenecks, Python/JS perf patterns |

### Design Skills
| Skill | Triggers On | Covers |
|-------|-------------|--------|
| `ui-ux-design` | "redesign", "UX", "user experience", "make it look better" | Design principles, accessibility, desktop UX, Amandla UI |

### Meta Skills
| Skill | Triggers On | Covers |
|-------|-------------|--------|
| `skill-manager` (this skill) | "skills", "gap", "new skill needed", new project/tech | Library audit, gap detection, skill creation triggers |
| `skill-creator` (built-in) | "create a skill", "make a skill for X" | Drafting, testing, iterating, packaging new skills |

---

## How to Use This During a Session

### When Starting a New Project
Run through this checklist:
1. Does `project-bootstrap` cover the tech stack? If not, flag a gap.
2. Does `amandla-code-standards` need updating for the new project? If it's a different project, a new `[project]-code-standards` skill may be needed.
3. Are there platform-specific skills for the tech being used?
4. If any answer is "no", recommend creating a new skill BEFORE starting to code.

### When a Task Arrives
Map it to a skill:
- Code being written → `amandla-code-standards` + relevant platform skill
- Something broken → `debugging`
- Code to review → `code-review` + `security-audit`
- API/WebSocket work → `api-design` + `python-fastapi` or `electron-ipc`
- New project idea → `product-planning` → `project-bootstrap`
- Before committing → `git-workflow`
- Making tests → `testing-strategy`
- Something slow → `performance-optimization`

### When Something Doesn't Fit Any Skill
This is a **skill gap**. Report it like this:

```
🔍 SKILL GAP DETECTED

Task: [what the user is trying to do]
Closest existing skill: [nearest match and why it's not quite right]
Gap: [what knowledge/pattern is missing]
Recommendation: Create a new skill called `[suggested-name]`
Covers: [what the new skill would cover]
Priority: HIGH / MEDIUM / LOW
Reason: [why this gap matters — how often will it come up?]
```

---

## Skill Gap Triggers — Watch For These

Create a new skill when:
- The same type of question comes up 3+ times with no skill covering it
- A new technology is added to the project with no coverage
- A painful bug reveals a pattern that should be codified
- A new team member or project would benefit from documented knowledge
- Security, performance, or architecture concerns keep recurring

Do NOT create a new skill when:
- An existing skill covers it with minor extension (just update the skill)
- It's a one-off task that won't recur
- It's too narrow (a skill for one function in one file is too specific)

---

## Skill Health Check

Run this when asked to audit skills or before a major project phase:

```
For each skill in the library:
1. Is the description still accurate? (Does it trigger correctly?)
2. Is the content still current? (No stale docs, deprecated patterns)
3. Does it still match the project's tech stack?
4. Has anything in CLAUDE.md changed that affects this skill?
5. Are there recurring user complaints that suggest the skill needs updating?
```

Flag any skill that fails 2+ of these checks as **needs update**.

---

## Skills Roadmap (Future Skills to Build)

Track skill ideas here — create these when the need is confirmed:

| Skill Idea | Why Needed | Priority |
|------------|-----------|----------|
| `database-design` | Schema design, migrations, indexes | MEDIUM — when DB is added to Amandla |
| `deployment-packaging` | Electron app packaging, auto-update, distribution | HIGH — before Amandla goes public |
| `accessibility` | Screen reader support, keyboard nav (critical for deaf/disabled users) | HIGH — Amandla serves disabled users |
| `websocket-patterns` | Deep WebSocket patterns, reconnection, state sync | MEDIUM — already partially in api-design |
| `ai-integration` | Claude API, Ollama, Whisper integration patterns | MEDIUM — Amandla uses all three |
| `data-privacy` | POPIA compliance (South Africa), data handling for medical/disability apps | HIGH — legal requirement |

---

## Environment Notes

**In Claude Code (terminal):** You can list installed skills:
```bash
ls ~/.claude/skills/          # Global skills
ls .claude/skills/            # Project skills
```

**In Claude.ai (browser):** The skill list above is your reference.
When a gap is detected, use the `skill-creator` skill to build a new one.
