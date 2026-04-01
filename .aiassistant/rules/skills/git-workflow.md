---
name: git-workflow
description: >
  Guides Git and GitHub best practices: branching strategy, commit messages, pull requests, code reviews,
  GitHub Actions CI/CD, and protecting the main branch. Activate this skill whenever the user asks about
  git commits, branching, merging, pull requests, GitHub Actions, CI/CD pipelines, how to push code,
  how to collaborate on GitHub, what commit message to write, how to set up automated testing, how to
  protect main branch, how to handle merge conflicts, or anything involving "git", "GitHub", "branch",
  "PR", "merge", "push", "commit", or "deploy". Also activate when the user is about to commit or push.
---

# Git & GitHub Workflow Skill

Good Git hygiene protects your work, enables collaboration, and makes debugging easier.
For Amandla: you are working toward a real product that will serve disabled users — the codebase deserves proper version control.

---

## Core Principle: Main Branch is Sacred

**Never push directly to `main`.** Main always contains working, tested, reviewed code.
All work happens on feature branches, then merges into main through a pull request.

---

## Part 1 — Branching Strategy

### Branch Naming Convention
```
feature/short-description     → new features
fix/short-description          → bug fixes
refactor/short-description     → code cleanup, no behavior change
docs/short-description         → documentation only
chore/short-description        → dependencies, config, tooling
```

**Examples for Amandla:**
```bash
git checkout -b feature/avatar-talkinghead-upgrade
git checkout -b fix/websocket-session-cleanup
git checkout -b refactor/sasl-transformer-dry
git checkout -b docs/claude-md-update
```

### Branch Lifecycle
```bash
# 1. Always branch from up-to-date main
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# 2. Work, commit often (at least once per logical unit of change)
git add .
git commit -m "feat(avatar): load GLB model from Avaturn"

# 3. Keep your branch up to date with main (avoid big merge conflicts)
git fetch origin
git rebase origin/main   # preferred over merge for cleaner history

# 4. When ready: push and open a PR
git push origin feature/your-feature-name
gh pr create --title "feat: upgrade avatar to TalkingHead + Avaturn" --body "..."
```

---

## Part 2 — Commit Message Standards

Use the **Conventional Commits** format. This makes the history readable and enables automated changelogs.

### Format
```
type(scope): short description (max 72 chars)

[optional body: explain WHY, not what — the diff shows what]

[optional footer: BREAKING CHANGE: ..., Closes #123]
```

### Types
| Type | When to use |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code change that doesn't add features or fix bugs |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `chore` | Dependencies, build config, tooling |
| `security` | Security fixes (treat as high priority) |
| `perf` | Performance improvement |

### Scopes for Amandla
`avatar`, `websocket`, `backend`, `hearing`, `deaf`, `rights`, `sasl`, `signs`, `auth`, `config`, `electron`

### Good vs Bad Examples
```bash
# ❌ Bad commits (vague, no context)
git commit -m "fix"
git commit -m "update code"
git commit -m "changes"
git commit -m "WIP"

# ✅ Good commits (specific, conventional)
git commit -m "feat(avatar): integrate TalkingHead class for lip-sync and blendshapes"
git commit -m "fix(websocket): clean up sign_buffers and tasks in finally block"
git commit -m "security(backend): move API keys to environment variables"
git commit -m "refactor(sasl): extract aspect marker logic into separate function"
git commit -m "docs(claude-md): update architecture diagram after rights window refactor"
```

---

## Part 3 — Pull Requests

### Before Opening a PR
- [ ] Branch is up to date with main (`git rebase origin/main`)
- [ ] All tests pass locally
- [ ] No `.env` files, `node_modules`, or build artifacts committed
- [ ] No debug/console.log statements left in production code
- [ ] PR contains ONE logical change — not five unrelated fixes bundled together

### PR Description Template
```markdown
## What this PR does
[1-2 sentences explaining the change]

## Why
[Why this change is needed]

## How to test
[Steps to manually verify it works]

## Screenshots (if UI change)
[Before/after screenshots]

## Checklist
- [ ] I tested the happy path
- [ ] I tested error cases
- [ ] I added/updated comments
- [ ] No hardcoded secrets
- [ ] No console.log debug statements
```

**In Claude Code:**
```bash
# Create PR with gh CLI
gh pr create \
  --title "feat(avatar): integrate TalkingHead for realistic sign language avatar" \
  --body "$(cat .github/pr_template.md)" \
  --base main \
  --head feature/avatar-talkinghead-upgrade
```

---

## Part 4 — GitHub Actions (CI/CD)

Setting up automated checks protects `main` from bad code.

### Recommended Workflow for Amandla
Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Check for hardcoded secrets
        run: |
          # Fail if any API key patterns found in source
          ! grep -rn "sk-\|ANTHROPIC_API_KEY\s*=\s*['\"]" backend/ --include="*.py"

      - name: Lint Python code
        run: |
          pip install flake8
          flake8 backend/ --max-line-length=100 --exclude=__pycache__

      - name: Security audit (Python)
        run: |
          pip install pip-audit
          pip-audit

  frontend-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm ci

      - name: Security audit (npm)
        run: npm audit --audit-level=high

      - name: Check for hardcoded secrets
        run: |
          ! grep -rn "api_key\s*=\s*['\"]" src/ --include="*.js"

  security-review:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    permissions:
      pull-requests: write
      contents: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2
      - uses: anthropics/claude-code-security-review@main
        with:
          comment-pr: true
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
```

### Protect the Main Branch
Go to GitHub → Repository Settings → Branches → Add rule for `main`:
- ✅ Require a pull request before merging
- ✅ Require at least 1 approval (even if it's just you reviewing your own PR after a day)
- ✅ Require status checks to pass (select your CI jobs)
- ✅ Require branches to be up to date before merging
- ✅ Do not allow bypassing the above settings

---

## Part 5 — What Should Never Be in Git

These must always be in `.gitignore`:
```gitignore
# Secrets
.env
.env.*
*.pem
*.key

# Dependencies (can be reinstalled)
node_modules/
__pycache__/
*.pyc
.venv/
venv/

# Build outputs
dist/
build/
*.egg-info/

# OS files
.DS_Store
Thumbs.db

# IDE files
.vscode/
.idea/
*.swp

# Logs
*.log
logs/
```

**Check your .gitignore is working:**
```bash
git status  # .env should NOT appear here
git ls-files --others --ignored --exclude-standard  # shows what's being ignored
```

---

## Part 6 — Useful Git Commands for Amandla Dev

```bash
# See what changed since last commit
git diff

# See what's staged for commit
git diff --staged

# See the log with a nice graph
git log --oneline --graph --all

# Undo last commit (keep changes)
git reset HEAD~1

# Stash work in progress before switching branches
git stash
git stash pop  # restore it

# See all branches (including remote)
git branch -a

# Delete a branch after merging
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name

# Find which commit introduced a bug
git bisect start
git bisect bad           # current version is bad
git bisect good v1.0     # v1.0 was good
# git will checkout commits for you to test — mark each good or bad
```

---

## Environment Notes

**In Claude Code (terminal/JetBrains):** All git and `gh` commands work directly.
Install `gh` CLI if not present: `winget install GitHub.cli` (Windows) or `brew install gh` (Mac).

**In Claude.ai (browser):** Share command outputs and I'll help interpret them.
Show me `git log --oneline -10` or `git status` output to get specific help.
