---
name: Electron launch requires unsetting ELECTRON_RUN_AS_NODE
description: Claude Code sets ELECTRON_RUN_AS_NODE=1 in its shell, breaking Electron API — must unset before launching
type: feedback
---

Always launch Electron with `env -u ELECTRON_RUN_AS_NODE npm run electron` from the worktree directory, not plain `npm run electron`.

**Why:** Claude Code's shell sets `ELECTRON_RUN_AS_NODE=1` in its environment. This env var makes Electron run as a plain Node.js process — all Electron APIs (`app`, `BrowserWindow`, `ipcMain`, etc.) become `undefined`. The app crashes immediately on line 6 of `src/main.js` when trying to call `app.commandLine.appendSwitch(...)`.

**How to apply:** Any time the user asks to run, launch, or start the AMANDLA Electron app, prepend `env -u ELECTRON_RUN_AS_NODE` to the npm/electron command.
