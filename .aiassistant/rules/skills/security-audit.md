---
name: security-audit
description: >
  Performs a thorough security audit of code against OWASP Top 10 (2025), with special checks for
  Electron apps, FastAPI backends, WebSocket communications, and Python/JavaScript codebases.
  Activate this skill whenever the user asks to: review code for security issues, check for vulnerabilities,
  audit an endpoint, review authentication or authorization logic, check if inputs are validated, review
  error handling, check environment variable usage, review WebSocket security, audit Electron security config,
  or prepare code for production. Also triggers on phrases like "is this secure?", "security check",
  "before I deploy", "production ready", or "check for vulnerabilities".
---

# Security Audit Skill

You are performing a security audit. Security is not optional — vulnerabilities in production can harm real users.
Amandla serves disabled South Africans who depend on this app. Every vulnerability matters.

---

## Phase 1 — Understand the Code First

Before flagging anything, understand what the code is supposed to do. Read:
- The function/endpoint's purpose
- What data flows in and out
- Who calls this code and with what trust level

Never flag false positives. A finding must be a real risk, not a theoretical one.

---

## Phase 2 — OWASP Top 10 Checklist (2025)

Work through each category systematically:

### A01 — Broken Access Control
- Does every endpoint verify the user has permission to access the requested resource?
- Can a user access another user's data by changing an ID in the URL?
- Are WebSocket sessions properly isolated? (In Amandla: session roles `hearing`/`deaf`/`rights` must only receive their messages)
- Does the `broadcast()` function leak messages to the wrong session/role?

### A02 — Cryptographic Failures
- Is any sensitive data stored or transmitted in plain text?
- Are passwords hashed with bcrypt (not MD5/SHA1)?
- Is HTTPS/WSS enforced in production? (Amandla uses HTTP locally — flag this for production deployment)
- Are API keys and secrets in environment variables, never in source code?

### A03 — Injection
- Are ALL database queries parameterized? (Never raw string concatenation in SQL)
- Is user text sanitized before being passed to Ollama/Whisper/Claude?
- Is there any shell injection risk? (File paths from user input passed to subprocess?)
- In the frontend: is any user text inserted into HTML without escaping? (XSS risk)

### A04 — Insecure Design
- Does the app validate message types over WebSocket before processing?
- Is there a maximum payload size enforced? (Amandla: 10 MB audio, 5000 chars text)
- Can a malicious client send unexpected message types to crash the backend?
- Does the app handle missing/null fields gracefully without crashing?

### A05 — Security Misconfiguration
- Is `DEBUG=True` or any debug mode accidentally left on?
- Is CORS set correctly? (Amandla must use `["*"]` for Electron — but flag if deployed as web app)
- Are error messages exposing stack traces to users?
- Is `nodeIntegration: false` and `contextIsolation: true` in all BrowserWindow configs?
- Is CSP properly configured in Electron main.js?

### A06 — Vulnerable and Outdated Components
- Are there any known-vulnerable npm or pip packages?

**In Claude Code (terminal):**
```bash
npm audit
pip-audit  # install with: pip install pip-audit --break-system-packages
```
**In Claude.ai (browser):** Ask the user to run these commands and share the output.

### A07 — Identification and Authentication Failures
- Is session management secure? (Amandla uses in-memory sessions — fine for desktop, flag for multi-user deployment)
- Are session IDs sufficiently random? (Amandla format: `'amandla-' + Date.now() + '-' + randomHex`)
- Is there any authentication on the WebSocket endpoint that should exist?

### A08 — Software and Data Integrity Failures
- Is the app validating data received over WebSocket before processing?
- Are there any `eval()` or `exec()` calls on untrusted input?
- Is the Electron app using Content Security Policy to prevent script injection?

### A09 — Security Logging and Monitoring Failures
- Are security-relevant events logged? (Failed connections, unexpected message types, oversized payloads)
- Are error logs written without exposing user data?
- Is there any personally identifiable information (PII) being logged?

### A10 — Server-Side Request Forgery (SSRF)
- Does any endpoint accept a URL from user input and fetch it?
- Could the Ollama integration be pointed at a malicious server?

---

## Phase 3 — Amandla-Specific Security Checks

These are specific to the Amandla tech stack:

### Electron Security
```
✓ contextIsolation: true in all BrowserWindow configs
✓ nodeIntegration: false in all BrowserWindow configs
✓ No require() calls in renderer code (hearing.js, deaf.js, rights.js)
✓ All backend calls go through window.amandla.* preload bridge
✓ CSP allows only googleapis.com and gstatic.com for fonts, nothing else external
✓ webviewTag: false (should not be using webviews)
```

### FastAPI/WebSocket Security
```
✓ Session ID is validated on connection (not empty, correct format)
✓ Role is validated against allowed values: ["hearing", "deaf", "rights"]
✓ Message size limits enforced BEFORE processing content
✓ Unknown message types are logged and ignored, not crashed on
✓ Rate limiting middleware is active (backend/middleware.py)
✓ No raw exception details in HTTP error responses
✓ load_dotenv() called ONCE only (in backend/main.py)
```

### Environment Variable Security
```
✓ ANTHROPIC_API_KEY not hardcoded anywhere
✓ OPENAI_API_KEY not hardcoded anywhere
✓ NVIDIA_API_KEY not hardcoded anywhere
✓ No API keys in any git-tracked file
✓ .env is in .gitignore
```

**Quick scan in Claude Code:**
```bash
# Check for hardcoded API keys
grep -rn "sk-\|api_key\s*=\s*['\"]" . --include="*.py" --include="*.js" | grep -v ".env" | grep -v "os.environ"
# Check .gitignore has .env
cat .gitignore | grep ".env"
```

---

## Phase 4 — Reporting Format

Structure your findings like this:

```
## Security Audit Report

### 🔴 Critical (Fix Before Any Deployment)
[List critical findings — direct exploitability, data exposure]

### 🟡 High (Fix Soon)
[List high-severity findings — could be exploited under certain conditions]

### 🟠 Medium (Plan to Fix)
[List medium findings — security improvements worth making]

### 🟢 Low / Informational
[Best practice improvements, minor hardening]

### ✅ Passed Checks
[List what passed so the user knows what's good]
```

For each finding, include:
- **What**: what is the vulnerability
- **Where**: exact file and line number if possible
- **Why**: why this is a risk in plain language
- **Fix**: exactly what code change fixes it

---

## Phase 5 — After the Audit

1. Summarize total findings by severity
2. Give the user a prioritized fix list (most critical first)
3. For each fix, offer to implement it (but wait for approval per the planning rule)
4. If no critical issues found, say so clearly — good news is also important

---

## Environment Notes

**In Claude Code (terminal/JetBrains):**
```bash
# Run full security checks
npm audit --audit-level=moderate
pip-audit
grep -rn "eval\|exec\|__import__" backend/ --include="*.py"
grep -rn "innerHTML\|dangerouslySetInnerHTML" src/ --include="*.js" --include="*.html"
```

**In Claude.ai (browser):** Walk through the checklist manually against shared code.
Ask the user to run `npm audit` and `pip-audit` from their terminal and share results.
