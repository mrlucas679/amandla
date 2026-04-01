---
name: amandla-code-standards
description: >
  Enforces the Amandla project's coding standards, architecture rules, and AI development principles on every code suggestion.
  Use this skill whenever writing, reviewing, or planning ANY code for the Amandla project — Electron frontend, FastAPI backend,
  WebSocket logic, SASL transformer, or signs library. Also triggers when the user asks to add a feature, fix a bug, refactor,
  or plan anything in the Amandla codebase. If the user mentions Amandla, avatar, signs, WebSocket, hearing window, deaf window,
  rights, FastAPI, Electron, or any file from the project, activate this skill immediately.
---

# Amandla Code Standards

You are working on **Amandla** — a hybrid Electron + FastAPI desktop application that is a real-time sign language
communication bridge for disabled South Africans. This is a production-quality project, not a hackathon prototype.
Every code change must meet the standards below without exception.

---

## 1. The Non-Negotiable Rules (read these before writing a single line)

### Planning First — Always
Before writing ANY code:
1. Present a plan: list which files will be created/changed, what functions will be written, and the approach
2. Wait for the user's approval
3. Only then write the code

This is the most important rule. Never skip it.

### Security (Highest Priority)
- NEVER hardcode secrets, API keys, passwords, or tokens — always use `.env` files
- Validate and sanitize ALL user inputs before processing
- Use parameterized queries for ALL database operations (prevents SQL injection)
- Never store sensitive data in plain text — hash passwords with bcrypt
- Error messages shown to users must NEVER expose internal system details
- CORS on FastAPI must stay `allow_origins=["*"]` — Electron is not a browser origin, changing this breaks the app
- Electron: always `contextIsolation: true`, `nodeIntegration: false`
- Never use `require()` in renderer code — use the preload bridge (`window.amandla.*`) only

### Code Quality
- Clean Code: readable, no magic numbers, no vague names (no `x`, `temp`, `data`, `val`)
- DRY: never duplicate code
- SOLID: each function/class does ONE thing only
- KISS: never over-engineer
- Maximum function length: 20–30 lines — break longer functions into smaller ones
- No unused variables or imports

### Commenting
- Every function needs a comment: what it does, what parameters it takes, what it returns
- Inline comments for any non-obvious logic
- Write comments as if explaining to a beginner

### Error Handling
- Every async call needs try/catch — no exceptions
- User-facing errors must be friendly messages, not raw exception dumps
- Never swallow errors silently (empty catch blocks are forbidden)
- Log errors for debugging

### Database / Data
- Never hardcode data arrays as replacements for database calls
- Always paginate large result sets
- Never raw concatenated SQL strings — always use parameterized queries

---

## 2. Amandla Architecture Rules

### File Ownership (Do Not Violate)
```
Electron Main      → src/main.js
Preload Bridge     → src/preload/preload.js  (ONLY way renderers talk to backend)
Hearing Window     → src/windows/hearing/
Deaf Window        → src/windows/deaf/
Rights Window      → src/windows/rights/
Backend            → backend/main.py + backend/services/
Signs Library      → signs_library.js (root)
Sign Mappings      → backend/services/sign_maps.py  ← SINGLE SOURCE OF TRUTH
SASL Transformer   → sasl_transformer/transformer.py
```

### DELETED FILES — Never Recreate These
- `src/windows/hearing/signs_library.js` — dead code, signs only load in deaf window
- `src/windows/hearing/avatar.js` — dead code, avatar only lives in deaf window

### WebSocket Message Types (Exact Strings — Lowercase)
`text`, `speech_upload`, `signs`, `sign`, `translating`, `deaf_speech`, `sasl_text`,
`assist_phrase`, `landmarks`, `emergency`, `status_request`, `rights_analyze`,
`rights_letter`, `history_request`, `history_response`, `sasl_ack`, `turn`

All request/response pairs include `request_id`. Broadcast messages (`signs`, `deaf_speech`, `turn`) do NOT.

### Backend Rules
- `.env` is loaded ONCE in `backend/main.py` — never call `load_dotenv()` again in services
- Session state is in-memory (`sessions` dict) — restart clears it, this is intentional
- Maximum audio upload: 10 MB
- Maximum text message: 5000 chars
- Session roles: exactly `"hearing"`, `"deaf"`, `"rights"`

### SASL / Signs Rules
- `sign_maps.py` is the SINGLE SOURCE OF TRUTH for English → SASL word mappings
- Modal verbs (`will`, `must`, `can`, etc.) map to SASL signs — they are NOT filler words
- `FINISH`/`WILL` aspect markers are critical SASL grammar — never remove them
- Non-English input is pre-translated to English via Ollama BEFORE the SASL pipeline

---

## 3. Checklist — Run This Before Delivering Any Code

Before presenting code to the user, mentally check:

- [ ] Did I present a plan first and wait for approval?
- [ ] Are all secrets in environment variables?
- [ ] Is every input validated/sanitized?
- [ ] Does every function have a comment?
- [ ] Are all errors handled with try/catch?
- [ ] Is every function under 30 lines?
- [ ] Are there any magic numbers? (replace with named constants)
- [ ] Are there any unused variables or imports?
- [ ] Does the code respect the file ownership boundaries above?
- [ ] Have I avoided recreating the deleted files?
- [ ] Does every async operation have proper error handling?

---

## 4. After Finishing Any Task

Always give the user:
1. Plain English summary of what was built
2. List of files created or changed
3. Follow-up tasks they should do (tests, .env updates, etc.)
4. Any areas that could be improved in a future iteration

---

## 5. When the User Makes a Mistake or There's a Bug

1. Explain what went wrong in plain simple language
2. Show 2–3 options to fix it with pros and cons of each
3. Wait for them to choose before making changes

---

## 6. Git Reminders (Mention When Relevant)

- Always suggest clear, descriptive commit messages
- Never commit `.env` files or secrets
- Always work on feature branches, not directly on `main`
- Commit messages format: `type(scope): description`
  - Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
  - Example: `feat(websocket): add request_id to broadcast messages`

---

## Environment Notes

**In Claude Code (terminal/JetBrains):** You have access to bash. Run linting, tests, and file operations directly.
```bash
# Check for hardcoded secrets
grep -rn "api_key\s*=" backend/ --include="*.py" | grep -v ".env"
# Run backend tests
python scripts/ws_test.py
curl http://localhost:8000/health
```

**In Claude.ai (browser):** Present code changes as diffs or complete files. Always tell the user exactly which file to update and where.
