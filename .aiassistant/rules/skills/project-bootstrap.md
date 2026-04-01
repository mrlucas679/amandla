---
name: project-bootstrap
description: >
  Sets up a brand-new project with the correct structure, CLAUDE.md, .gitignore, folder layout,
  environment files, and README from day one. Activate this skill whenever the user says "start a new project",
  "create a new app", "scaffold a project", "I want to build X from scratch", "help me set up a new repo",
  or when a project is clearly at the beginning with no existing structure. Also activate when the user
  wants to reorganize an existing project to match best practices. Never let a project start without this.
---

# Project Bootstrap Skill

Starting a project correctly saves weeks of pain later. The goal: from zero to a clean, secure,
well-organized foundation in one session — before any feature code is written.

---

## Phase 1 — Understand What We're Building

Before touching the filesystem, ask (or infer from context):

1. **What is this?** — Desktop app? Web app? API? CLI tool? Library?
2. **Tech stack?** — Python/FastAPI? React? Electron? Node.js? Full-stack?
3. **Who uses it?** — Internal tool? Public product? Specific users with specific needs?
4. **What problem does it solve?** — One sentence.
5. **Does it handle sensitive data?** — If yes, extra security steps apply.

---

## Phase 2 — Project Structure

### For Electron + Python Backend (Amandla-style)
```
project-name/
├── src/
│   ├── main.js                 ← Electron main process
│   ├── preload/
│   │   └── preload.js          ← Secure IPC bridge
│   └── windows/
│       ├── main/               ← Each window gets its own folder
│       │   ├── index.html
│       │   ├── main.css
│       │   └── main.js
├── backend/
│   ├── main.py                 ← FastAPI app entry point
│   ├── middleware.py
│   └── services/               ← One file per service
├── scripts/                    ← Dev/test utilities
├── .env.example                ← Template (never .env itself)
├── .gitignore
├── CLAUDE.md                   ← AI context file
├── README.md
├── package.json
└── requirements.txt
```

### For Web App (React + Node/Python API)
```
project-name/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── utils/
│   │   └── App.jsx
│   └── public/
├── backend/
│   ├── routes/
│   ├── services/
│   ├── middleware/
│   └── main.py (or index.js)
├── .env.example
├── .gitignore
├── CLAUDE.md
└── README.md
```

### For Python CLI / Library
```
project-name/
├── src/project_name/
│   ├── __init__.py
│   ├── cli.py
│   └── core/
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
├── .env.example
├── .gitignore
├── CLAUDE.md
├── README.md
├── pyproject.toml
└── requirements-dev.txt
```

---

## Phase 3 — The CLAUDE.md Template

Every project must have a `CLAUDE.md`. This is the AI's source of truth.
Populate it with this template — filled in for the specific project:

```markdown
# CLAUDE.md — [PROJECT NAME]
> Last updated: [DATE]
> Single source of truth for AI coding agents on this project.

## 1. What This Is
[One paragraph: what the app does, who uses it, why it matters]

## 2. How to Start the App
```bash
# Prerequisites:
[list anything that must be running first]

# Start:
[exact command]
```

## 3. Architecture
[Folder structure with one-line explanations of what each folder does]

## 4. Key Constraints (Non-Negotiable)
[Security rules, CORS settings, what must never change, what must never be deleted]

## 5. Environment Variables
[List every env var, what it does, example value — never real values]

## 6. File Map
[Table: file → purpose → how often it changes]

## 7. Do NOT Recreate
[List any deliberately deleted files and why]

## 8. Testing
[How to run tests]
```

---

## Phase 4 — The .gitignore

Always create a thorough `.gitignore` before the first commit:

```gitignore
# Secrets — NEVER commit these
.env
.env.*
*.pem
*.key
secrets/

# Dependencies — can be reinstalled
node_modules/
__pycache__/
*.pyc
.venv/
venv/
env/
*.egg-info/
dist/
build/

# OS files
.DS_Store
Thumbs.db
desktop.ini

# IDE files
.vscode/
.idea/
*.swp
*.swo
.cursor/

# Logs
*.log
logs/
npm-debug.log*

# Test outputs
.coverage
htmlcov/
.pytest_cache/

# Electron
out/
```

---

## Phase 5 — The .env.example

Create `.env.example` with every variable the app needs — no real values, just documentation:

```env
# === AI Services ===
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here

# === Database ===
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# === Server ===
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
DEBUG=false

# === Feature Flags ===
FEATURE_X_ENABLED=false
```

Then tell the developer: **Copy `.env.example` to `.env` and fill in real values. Never commit `.env`.**

---

## Phase 6 — Initial README

```markdown
# [Project Name]

[One-sentence description of what this does]

## What It Does
[2-3 paragraphs about the problem it solves and how]

## Tech Stack
- [Frontend framework]
- [Backend framework]
- [Key libraries]

## Prerequisites
- [Runtime requirements]
- [Services that must be running]

## Setup
```bash
# Clone
git clone [url]
cd [project]

# Install dependencies
npm install
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your values

# Start
[start command]
```

## Project Structure
[Folder map from Phase 2]

## Contributing
[branch strategy, commit message format, PR process]
```

---

## Phase 7 — First Git Commit

```bash
git init
git add .
git commit -m "chore: initial project scaffold

- Add project structure
- Add CLAUDE.md with architecture documentation
- Add .gitignore
- Add .env.example
- Add README.md"

# Create remote repo and push
gh repo create [project-name] --public --source=. --remote=origin --push
```

---

## Phase 8 — Verify Before Starting Features

Checklist before writing any feature code:
- [ ] `.env` exists locally (not committed)
- [ ] `.env.example` is committed and complete
- [ ] `CLAUDE.md` is filled in
- [ ] `.gitignore` is working (`git status` shouldn't show `.env`)
- [ ] README makes sense to a stranger
- [ ] At least one branch protection rule set on GitHub
- [ ] `main` branch has the clean scaffold committed

---

## Environment Notes

**In Claude Code (terminal):** Can run all commands directly. Use `gh` CLI for GitHub setup.
```bash
gh repo create project-name --public --source=. --remote=origin --push
gh api repos/{owner}/{repo}/branches/main/protection --method PUT \
  --field required_pull_request_reviews[required_approving_review_count]=1
```

**In Claude.ai (browser):** Create all files and show the user what to copy into their terminal.
Provide the full git commands as a code block they can run step by step.
