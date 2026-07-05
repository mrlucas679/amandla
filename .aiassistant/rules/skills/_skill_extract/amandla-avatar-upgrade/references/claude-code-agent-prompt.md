# Claude Code Agent Prompt: Amandla Avatar Upgrade

Copy and paste this entire prompt into Claude Code (JetBrains terminal or CLI)
to execute the avatar upgrade. Run from your Amandla project root.

---

```
You are a senior JavaScript/Electron developer performing a specific, scoped upgrade
to the Amandla deaf window avatar system. Follow these instructions exactly.

## Your Mission

Replace the current Three.js cylinder-based avatar in `src/windows/deaf/avatar.js`
with TalkingHead (https://github.com/met4citizen/TalkingHead) + an Avaturn GLB model.

## Step 1: Read Before Touching Anything

Read these files completely before writing a single line of code:
1. src/windows/deaf/avatar.js     — current avatar implementation
2. src/windows/deaf/deaf.js       — how avatar.js is called (find avatarPlaySigns)
3. src/windows/deaf/index.html    — current HTML, scripts, importmaps
4. signs_library.js               — the sign library format you must retarget
5. src/main.js                    — check CSP configuration
6. CLAUDE.md                      — architecture constraints

## Step 2: Verify the GLB Exists

Check whether the file `src/windows/deaf/avatars/amandla-avatar.glb` exists:
  - If YES: proceed to Step 3
  - If NO: stop and tell the user they must download it from https://avaturn.me
    first and save it to src/windows/deaf/avatars/amandla-avatar.glb.
    Do NOT proceed without the GLB — the code won't work without it.

## Step 3: Plan — Present Before Coding

List every file you will create or modify, what change you will make to each,
and what you will NOT touch. Wait for user confirmation before proceeding.

MUST NOT change:
- deaf.js (except the minimal addition in Phase 5 of the skill)
- hearing.js, hearing.css, hearing/index.html
- backend/ (anything in Python)
- signs_library.js
- preload.js
- src/main.js CSP (unless broken — see Step 4)

## Step 4: Check CSP for CDN Access

In src/main.js, find the Content-Security-Policy. Check if it allows:
- script-src: cdn.jsdelivr.net
- connect-src: cdn.jsdelivr.net

If these are blocked, add them. TalkingHead loads from jsdelivr.net CDN.
The importmap and the ES module both need this allowed.

Exact strings to look for and potentially add:
  script-src: add "https://cdn.jsdelivr.net"
  connect-src: add "https://cdn.jsdelivr.net"

## Step 5: Update index.html

In src/windows/deaf/index.html:

REMOVE any existing Three.js CDN imports or importmaps for three.js.

ADD this importmap in <head> (before any <script type="module"> tags):
```
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js/+esm",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/",
    "talkinghead": "https://cdn.jsdelivr.net/gh/met4citizen/TalkingHead@1.7/modules/talkinghead.mjs"
  }
}
</script>
```

ADD this to <body> where the avatar should appear:
```
<div id="avatar-container" style="width:100%;height:60vh;position:relative;background:#0a0a0a;"></div>
<div id="avatar-status" style="text-align:center;color:#666;font-size:14px;padding:8px;">Loading...</div>
```

CHANGE the avatar.js script tag to:
```
<script type="module" src="avatar.js"></script>
```

## Step 6: Write the New avatar.js

Write the complete new avatar.js exactly as specified in the
amandla-avatar-upgrade SKILL.md (the full Phase 3 implementation).

Critical requirements:
- window.avatarPlaySigns(signs, text) must exist after avatar loads
- The function signature must be IDENTICAL to the current one
- _convertSignToGesture() must handle the existing signs_library.js format
- All functions must have JSDoc comments
- All async calls must have try/catch
- No magic numbers — use named constants

## Step 7: Test the Integration

After writing code, verify:
1. Open deaf window — does the avatar appear? (not blank)
2. Open DevTools console — any errors?
3. Send a test message from hearing window
4. Does the avatar gesture for a known sign like "HELLO"?
5. Does fingerspelling trigger for an unknown word?

If any test fails, debug and fix before finishing.

## Step 8: Update .gitignore

Add this line to .gitignore:
  src/windows/deaf/avatars/*.glb

## Step 9: Final Summary

Tell me:
1. Every file that was changed and exactly what changed
2. Every file that was intentionally left unchanged
3. How to test that it's working
4. Any known limitations or things still needing work
5. Whether any CLAUDE.md constraints were approached or violated

IMPORTANT CONSTRAINTS FROM CLAUDE.md:
- Never recreate src/windows/hearing/signs_library.js or src/windows/hearing/avatar.js
- CORS must stay allow_origins=["*"] in backend
- contextIsolation:true, nodeIntegration:false in all BrowserWindows
- No require() in renderer files — this new avatar.js is a module, which is correct
```
