---
name: documentation
description: >
  Writes and improves documentation: README files, docstrings, API docs, changelogs, architecture
  decision records (ADRs), and code comments. Activate when the user asks to "write docs", "document this",
  "update the README", "add comments", "explain this code", "write a docstring", "update CHANGELOG",
  "explain the architecture", or when code exists without documentation. Also activate proactively
  after completing a major feature — documentation should be written while the code is fresh.
---

# Documentation Skill

Good documentation is the difference between a project others (and future-you) can understand,
and a project that only makes sense to present-you for the next two weeks.

For Amandla: this is a real product serving disabled users. Clear documentation enables
contributors, users, and even accessibility evaluators to understand what you built.

---

## The Documentation Hierarchy

```
1. Code comments     → explain WHY (not what — the code shows what)
2. Docstrings        → explain what functions/classes do, their inputs/outputs
3. README            → explain how to set up and use the project
4. CLAUDE.md         → explain architecture for AI assistants
5. API docs          → explain endpoints and message formats
6. CHANGELOG         → track what changed between versions
7. ADRs              → explain WHY key architecture decisions were made
```

---

## Part 1 — Code Comments

### What to Comment

```python
# ✅ Comment explains WHY — the code itself shows WHAT
# CORS must stay ["*"] because Electron renderers don't have a browser origin.
# Restricting origins would break all window communication.
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# ✅ Comment explains non-obvious business logic
# Modal verbs (will, must, can) map to SASL signs, NOT filler words.
# Treating them as filler would break grammatically critical ASL syntax.
MODAL_VERBS = {"will", "must", "can", "should", "would", "could"}

# ❌ Comment states the obvious — adds no value
# Set x to 5
x = 5

# ❌ Commented-out dead code — delete it, git history preserves it
# result = old_function(text)
result = new_function(text)
```

---

## Part 2 — Docstrings

### Python Docstring Pattern
```python
def translate_to_sasl(text: str, language: str | None = None) -> list[str]:
    """
    Translates English (or other language) text to SASL sign names.

    If language is not English, the text is first translated to English
    via Ollama before the SASL transformation pipeline runs.
    Empty input returns an empty list without error.

    Args:
        text: Input text to translate. Max 5000 characters.
        language: BCP-47 language code (e.g., 'af' for Afrikaans).
                  None or 'en' means English — skips translation step.

    Returns:
        List of SASL sign name strings in SASL word order (SOV).
        Unknown words are replaced with fingerspelled letter sequences.

    Raises:
        TranslationServiceError: If Ollama is unavailable for non-English input.

    Example:
        >>> translate_to_sasl("I want water")
        ["WATER", "WANT", "I"]

        >>> translate_to_sasl("Ek wil water hê", language="af")
        ["WATER", "WANT", "I"]
    """
```

### JavaScript JSDoc Pattern
```javascript
/**
 * Plays a sequence of SASL signs on the 3D avatar.
 * Signs animate in order with proper timing gaps between them.
 * If a sign is unknown, the avatar fingerspells the word letter by letter.
 *
 * @param {string[]} signs - Array of SASL sign name strings (e.g., ["HELLO", "WORLD"])
 * @param {string} originalText - Original English text (used for subtitle display)
 * @returns {Promise<void>} Resolves when all signs have finished animating
 *
 * @example
 * await window.avatarPlaySigns(["HELLO", "WORLD"], "Hello world");
 */
async function avatarPlaySigns(signs, originalText) { ... }
```

---

## Part 3 — README Template

```markdown
# Project Name

> One sentence that tells someone what this is in 5 seconds.

## What It Does
[2-3 paragraphs: the problem it solves, who uses it, why it matters]

## Demo
[Screenshot or GIF if possible — worth 1000 words]

## Tech Stack
- **Frontend**: [Electron / React / Vue]
- **Backend**: [FastAPI / Express / Django]
- **AI**: [Whisper, Ollama, Claude API]
- **Key Libraries**: [Three.js for avatar, etc.]

## Prerequisites
Before you start, make sure you have:
- [ ] Node.js 20+ installed
- [ ] Python 3.11+ installed
- [ ] [Any service that must be running first]

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/username/project.git
cd project

# 2. Install dependencies
npm install
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Open .env and fill in your values

# 4. Start the app
npm start
```

## Project Structure
```
src/                  ← Electron frontend
backend/              ← FastAPI backend
signs_library.js      ← SASL sign definitions
CLAUDE.md             ← Architecture for AI assistants
```

## Contributing
1. Branch from `main`: `git checkout -b feature/your-feature`
2. Make changes following the coding standards in CLAUDE.md
3. Open a Pull Request against `main`

## License
[License type]
```

---

## Part 4 — CHANGELOG Format

```markdown
# Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [1.2.0] - 2026-04-01

### Added
- Emergency phrase quick-access buttons on deaf window
- Support for Afrikaans input translation via Ollama
- Avatar idle breathing animation

### Changed
- WebSocket session timeout increased from 20 to 30 minutes
- SASL transformer now preserves FINISH marker in all past-tense inputs

### Fixed
- Avatar not resetting to idle after sign sequence completes
- WebSocket reconnection failing after backend restart

### Security
- Removed API key from debug log output in ollama_service.py

## [1.1.0] - 2026-03-28
...
```

---

## Part 5 — Architecture Decision Records (ADRs)

For important decisions, write a short ADR so future developers understand WHY.

```markdown
# ADR-001: Use In-Memory Sessions (Not Database)

## Date
2026-03-15

## Status
Accepted

## Context
Amandla sessions are real-time communication events that last minutes, not days.
We need to track which windows are connected to which session.

## Decision
Store session state in an in-memory Python dict in the FastAPI process.

## Consequences
**Positive:**
- No database dependency for an MVP desktop app
- Zero latency for session lookups
- Simple to understand and debug

**Negative:**
- Sessions are lost on backend restart
- Cannot scale to multiple backend instances (acceptable for desktop app)

## When to Revisit
If Amandla ever becomes a networked multi-user product.
```

---

## Environment Notes

**In Claude Code (terminal):**
```bash
# Check for missing docstrings in Python
grep -rn "^def \|^async def \|^class " backend/ --include="*.py" | \
  grep -v "test_"  # shows all functions — check if they have docstrings

# Generate API docs from FastAPI
# Just open: http://localhost:8000/docs
```

**In Claude.ai (browser):** When writing documentation, ask:
"If a new developer joined tomorrow, what would confuse them most?"
That's what the documentation needs to address first.
