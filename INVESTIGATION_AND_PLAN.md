# AMANDLA — Deep Investigation & Fix Plan
> Generated: March 30, 2026  
> Based on: full read of every source file in the codebase  
> Status: **PLAN ONLY — no code changed yet**

---

## How to Use This Document

Each issue has:
- **Severity** — CRITICAL / HIGH / MEDIUM / LOW
- **What is wrong** — exact description of the bug or gap
- **Where it is** — file(s) + line reference
- **Root cause** — why it is broken
- **Fix plan** — exactly what to change

Issues are ordered from most to least urgent.

---

## CRITICAL — App features are completely broken

---

### ISSUE 1 — CSP blocks MediaPipe WASM: camera sign recognition never works

**Severity:** CRITICAL  
**Feature broken:** deaf window camera mode, MediaPipe hand tracking  

**What is wrong:**  
The `connect-src` directive in the Content-Security-Policy (CSP) only allows `ws://localhost:8000` and `http://localhost:8000`. MediaPipe's `Hands` library loads its WASM binary and model `.bin` files by fetching them from `https://cdn.jsdelivr.net` at runtime (via its `locateFile` callback). These fetches are blocked by the CSP. MediaPipe silently fails to initialise — no error shown to the user, camera button does nothing useful.

**Where it is:**  
- `src/main.js` line 17 — the `CSP` constant, specifically the `connect-src` directive  
- `src/windows/deaf/index.html` lines ~738–750 — `locateFile` callback pointing to `cdn.jsdelivr.net`

**Root cause:**  
When the CSP was written, only the backend WebSocket and HTTP calls were considered. The MediaPipe CDN fetches were overlooked.

**Fix plan:**  
In `src/main.js`, add `https://cdn.jsdelivr.net` to `connect-src`:
```
connect-src 'self' ws://localhost:8000 http://localhost:8000 https://cdn.jsdelivr.net;
```

---

### ISSUE 2 — Ollama model role conflict: Modelfile system prompt fights every other caller

**Severity:** CRITICAL  
**Feature broken:** SASL translation, rights analysis, letter generation, signs-to-English reconstruction  

**What is wrong:**  
The `Modelfile` sets a built-in SYSTEM prompt that locks the `amandla` Ollama model into being a **landmark recognition engine**. Five different callers each expect the model to play a completely different role, but none of them override the system prompt in their API request:

| Caller | Role it needs | Sets `system` in request? |
|--------|--------------|--------------------------|
| `ollama_service.py` | Landmark → sign name | ✗ (relies on Modelfile) |
| `ollama_client.py` | English → sign names list | ✗ (embeds prompt inline) |
| `main.py` `_ollama_signs_to_english` | SASL → English sentence | ✗ (embeds prompt inline) |
| `claude_service.py` `_call_ollama` | SA rights legal analysis | ✗ (embeds prompt inline) |
| `transformer.py` `_translate_with_llm` | English → SASL gloss | ✗ (embeds in full_prompt) |

When Ollama's `/api/generate` is called with a `prompt` but no `system` key, the model uses its **built-in system prompt from the Modelfile**. This means rights analysis, letter generation, SASL transformation, and sign reconstruction are all answered by a model that believes it is a hand-landmark classifier. Results are unpredictable and often wrong.

**Where it is:**  
- `Modelfile` — the `SYSTEM` block  
- `backend/services/ollama_service.py` `recognize_sign()` — intentional (correct)  
- `backend/services/ollama_client.py` `_try_ollama()` — missing `"system"` key  
- `backend/main.py` `_ollama_signs_to_english()` — missing `"system"` key  
- `backend/services/claude_service.py` `_call_ollama()` — missing `"system"` key  
- `sasl_transformer/transformer.py` `_translate_with_llm()` — missing `"system"` key  

**Root cause:**  
The Modelfile was written for landmark recognition. The other callers were written to embed their system prompts inside the `prompt` string rather than passing them as a separate `"system"` key in the Ollama API body. Ollama honours the `"system"` request field and uses it instead of the Modelfile default — but only if you pass it.

**Fix plan:**  
For each caller that is NOT doing landmark recognition, add `"system": "..."` to the Ollama API request JSON body:

1. **`ollama_client.py`** — add `"system": "You are a SASL sign language converter. Return only a JSON array of SASL sign names."` to the `json={...}` body.  
2. **`main.py` `_ollama_signs_to_english()`** — add `"system": "You reverse SASL gloss notation to natural English. Return one sentence only."`.  
3. **`claude_service.py` `_call_ollama()`** — add `"system": _RIGHTS_SYSTEM` and remove the inline system block from `prompt`.  
4. **`transformer.py` `_translate_with_llm()`** — add `"system": SASL_SYSTEM_PROMPT` and build `prompt` with only the user message (no system block inline).  
5. **Leave `ollama_service.py` unchanged** — it uses the Modelfile system prompt correctly.

---

### ISSUE 3 — `sasl_text` backend handler splits multi-word signs on whitespace

**Severity:** CRITICAL  
**Feature broken:** deaf user typed SASL input, AssistMode phrases  

**What is wrong:**  
In `backend/main.py`, the `sasl_text` handler splits the deaf user's typed input with plain `.split()`:
```python
signs = [w.strip('.,!?;:\'"') for w in sasl_text.upper().split()
         if w.strip('.,!?;:\'"')]
```
This breaks every multi-word sign. Examples:
- User types `"THANK YOU"` → split to `["THANK", "YOU"]` (2 separate unknown words)
- User types `"HOW ARE YOU"` → split to `["HOW", "ARE", "YOU"]`
- User types `"I LOVE YOU"` → split to `["I", "LOVE", "YOU"]`

The `_signs_to_english` fallback lowercase-maps unknown words, so the output accidentally looks correct in many cases. But when Ollama is available, it receives individual words instead of meaningful sign units, degrading quality and causing inconsistent reconstruction.

**Where it is:**  
`backend/main.py` lines ~768–770 (inside the `sasl_text` handler)

**Root cause:**  
Simple `str.split()` doesn't know that "THANK YOU" is a single SASL sign. The sign names with spaces need to be matched against a known list before falling back to word-by-word splitting.

**Fix plan:**  
Add a `_split_sasl_gloss(text)` helper function that:
1. Builds an ordered list of known multi-word sign names (from `_SINGLE_SIGN_SENTENCES` keys + a static list).
2. Tries longest-match first: scans for multi-word signs in the text before splitting on spaces.
3. Falls back to single-word splitting for unrecognised tokens.

Known multi-word signs to handle: `"THANK YOU"`, `"HOW ARE YOU"`, `"I'M FINE"`, `"I LOVE YOU"`, `"CAN NOT"`, `"GOOD MORNING"`, `"GOOD NIGHT"`.

---

## HIGH — Features exist but produce wrong or degraded output

---

### ISSUE 4 — AssistMode phrases routed through wrong backend pipeline

**Severity:** HIGH  
**Feature broken:** deaf user's Assist Mode communication  

**What is wrong:**  
`mode_controller.js` dispatches selected phrases (e.g. `"I am feeling dizzy"`) as a `sasl_text` WebSocket message. In `backend/main.py`, the `sasl_text` handler treats the payload as a SASL gloss sequence (sign names in SASL order) and runs `_signs_to_english()` on it, which was designed to reverse engineer SASL → English.

`"I am feeling dizzy"` → split to `["I", "AM", "FEELING", "DIZZY"]` → these are treated as SASL sign names → Ollama is asked to reconstruct English from these "signs". The output may be correct by accident (since `_simple_signs_to_english` lowercases unknowns), but the intent is wrong. More importantly: the Ollama SASL-reversal prompt teaches it that inputs are SASL gloss where verbs come last and time words come first. An English phrase like `"I need to call my family"` might be mangled.

**Where it is:**  
- `src/windows/deaf/mode_controller.js` line ~208 — `window.dispatchEvent(new CustomEvent('amandla:assistPhrase', ...))`  
- `src/windows/deaf/index.html` lines ~768–773 — `amandla:assistPhrase` event listener → sends `sasl_text`  
- `backend/main.py` lines ~750–780 — `sasl_text` handler runs SASL reversal pipeline  

**Root cause:**  
AssistMode was wired to the existing `sasl_text` message type because it was the only deaf→hearing channel. The correct path for ready-made English phrases is a direct `deaf_speech` bypass that skips the reconstruction step entirely.

**Fix plan:**  
1. In `deaf/index.html`, change the `amandla:assistPhrase` listener to send a new message type: `'assist_phrase'` with `text: phrase`.  
2. In `backend/main.py`, add a handler for `'assist_phrase'` that sends the phrase **directly** to the hearing window as `deaf_speech` — no SASL reconstruction needed. The phrase is already natural English.  
3. Add `'assist_phrase'` to the valid message types list in `CLAUDE.md`.

---

### ISSUE 5 — Ollama landmark recognition sends raw coordinates with no feature extraction

**Severity:** HIGH  
**Feature broken:** MediaPipe camera sign recognition accuracy  

**What is wrong:**  
`ollama_service.py` forwards raw x,y,z coordinate lists to the Ollama LLM for sign identification. A 3B-parameter LLM cannot meaningfully classify signs from 63 floating-point numbers (21 points × x,y,z). Signs differ by finger angles, relative positions, and hand orientation — information that must be computed geometrically from the raw points. Without pre-processing, the model guesses randomly and almost always returns `UNKNOWN` or a low-confidence result.

**Where it is:**  
`backend/services/ollama_service.py` `recognize_sign()` function lines ~40–65

**Root cause:**  
Raw coordinates are an implementation shortcut. Real sign classifiers compute derived features: finger extension ratios, inter-finger angles, wrist orientation, palm normal vector, fingertip distances from wrist, etc. These human-readable features are what an LLM prompt can actually reason about.

**Fix plan:**  
Add a `_extract_features(landmarks)` helper to `ollama_service.py` that computes:
1. **Finger extension** — for each finger: is tip above MCP? (0/1 per finger = 5 values)
2. **Thumb position** — abducted or folded?
3. **Hand orientation** — palm facing camera, away, sideways?
4. **Fingertip spread** — are fingers spread apart or together?

Replace the raw JSON dump in the prompt with these computed features in plain English:  
```
"Index: extended. Middle: extended. Ring: curled. Pinky: curled. Thumb: abducted. Palm: facing camera."
```
This gives the LLM something it can actually classify against the 21 known signs in the Modelfile.

---

### ISSUE 6 — Deaf window emergency calls TTS `speakText()` — deaf users can't hear audio

**Severity:** HIGH  
**Feature broken:** deaf user's emergency experience  

**What is wrong:**  
In `src/windows/deaf/index.html`, `showEmergency()` calls:
```javascript
speakText('Emergency. Help has been alerted.')
```
The deaf window belongs to the **deaf user**. Calling TTS (Text-to-Speech) for a deaf person serves no purpose and wastes the Web Speech API call. The visual overlay already shows the emergency alert.

**Where it is:**  
`src/windows/deaf/index.html` `showEmergency()` function (~line 611)

**Root cause:**  
The `showEmergency()` function was copied from the hearing window and the TTS line was not removed.

**Fix plan:**  
Remove the `speakText(...)` call from the deaf window's `showEmergency()`. The visual overlay (`#emergency-overlay`) is already correct and sufficient.

---

## MEDIUM — Works but is wrong, inconsistent, or confusing

---

### ISSUE 7 — Rate limit cooldown (2s) is too short for rights operations

**Severity:** MEDIUM  
**Feature broken:** rights analysis and letter generation reliability  

**What is wrong:**  
`_HEAVY_CALL_INTERVAL_S = 2.0` is applied to `speech_upload`, `rights_analyze`, and `rights_letter` identically. Rights operations call Ollama which takes 10–30 seconds to respond. With a 2-second gate, a user can fire 15 rights requests before the first one completes. This floods the Ollama queue and causes all requests to queue or time out.

**Where it is:**  
`backend/main.py` line 82 — `_HEAVY_CALL_INTERVAL_S: float = 2.0`  

**Root cause:**  
A single constant was used for operations with very different latencies.

**Fix plan:**  
Replace the single constant with a per-type map:
```python
_HEAVY_CALL_INTERVALS: Dict[str, float] = {
    "speech_upload":  2.0,   # Whisper is fast after first load
    "rights_analyze": 30.0,  # Ollama takes 10–30s
    "rights_letter":  45.0,  # Letter generation is slower
}
```
Update `_check_rate_limit()` to look up the correct interval by `msg_type`.

---

### ISSUE 8 — Status dot ignores Whisper status; hearing user has no indicator for STT

**Severity:** MEDIUM  
**Feature broken:** hearing window status feedback  

**What is wrong:**  
Both `hearing/index.html` and `deaf/index.html` poll status and check only:
```javascript
statusDot.className = d.qwen === 'alive' ? '' : 'offline'
```
The `d.whisper` field is always ignored. If Whisper fails to load (missing model, wrong device, ffmpeg absent), the status dot stays green and the user gets no warning. They click the mic, wait 30 seconds, and see "Transcription failed — try typing instead" with no explanation.

**Where it is:**  
`src/windows/hearing/index.html` `pollStatus()` (~line 614)  
`src/windows/deaf/index.html` `pollStatus()` (~line 762)

**Fix plan:**  
Update the status dot logic to reflect both services:
```javascript
const ollama = d.qwen === 'alive'
const whisper = d.whisper === 'ready'
statusDot.className = (ollama && whisper) ? '' : 'offline'
statusDot.title = `AI: ${ollama ? 'online' : 'offline'} | Speech: ${whisper ? 'ready' : 'unavailable'}`
```
Also disable the mic button in `hearing/index.html` when `whisper !== 'ready'`.

---

### ISSUE 9 — Turn indicator resets after 4 seconds, but Whisper can take up to 45 seconds

**Severity:** MEDIUM  
**Feature broken:** turn indicator accuracy during speech input  

**What is wrong:**  
`setTurnIndicator()` in both windows resets itself to "Waiting…" after 4 seconds:
```javascript
window._turnTimer = setTimeout(function () {
    turnEl.textContent = 'Waiting…'
    turnEl.className = ''
}, 4000)
```
But Whisper transcription can take 15–45 seconds on first use. The deaf user sees "🎙 Hearing person is speaking" for 4 seconds, then "Waiting…", then the signs arrive 30 seconds later with no indicator — confusing.

**Where it is:**  
`src/windows/deaf/index.html` `setTurnIndicator()` (~line 510)  
`src/windows/hearing/index.html` `setTurnIndicator()` (~line 374)

**Fix plan:**  
- Increase the auto-reset timer to `12000` ms (12 seconds) — still auto-clears for quick typed messages.  
- When the `translating` message arrives at the deaf window, keep the indicator active until either `signs` or a timeout.  
- When the hearing window starts a recording (`isRecording = true`), hold the turn indicator active for the full recording duration + upload time.

---

### ISSUE 10 — `avatar_driver.js` loads 314 lines of dead code on every deaf window open

**Severity:** MEDIUM  
**Feature broken:** not broken — but wasteful and misleading  

**What is wrong:**  
`src/windows/deaf/index.html` loads `avatar_driver.js` before `avatar.js`. But `avatar.js` never calls a single function from `avatar_driver.js`. The driver was written to bridge a real GLB model to the avatar bone system, but the current avatar is a fully procedural Three.js skeleton built entirely inside `avatar.js`. `AvatarDriver`, `bindBonesFromGLTF`, `applyPoseToGLTF`, and all BONE_MAP constants are dead code that runs on every window open.

**Where it is:**  
`src/windows/deaf/index.html` — `<script src="avatar_driver.js"></script>`  
`src/windows/deaf/avatar_driver.js` — entire file  

**Root cause:**  
`avatar_driver.js` was written in anticipation of a GLB model upgrade that has not yet happened. It was left in the script loading order.

**Fix plan:**  
Two options — pick one before implementing:
- **Option A (quick):** Remove `<script src="avatar_driver.js"></script>` from `deaf/index.html`. Leave the file on disk for the future GLB upgrade.  
- **Option B (correct):** Implement the actual GLB model integration using `human_signing.fbx` converted to GLB (the conversion script already exists at `scripts/fbx_to_glb.py`).

---

### ISSUE 11 — `conn-banner` is inconsistent between hearing and deaf windows

**Severity:** MEDIUM  
**Feature broken:** connection error feedback in deaf window  

**What is wrong:**  
- **Hearing window:** banner uses `classList.toggle('visible', !connected)` and has a Dismiss button and CSS animation  
- **Deaf window:** banner uses `style.display = 'none'/'block'` with no Dismiss button and different styling  

The deaf window banner also lacks the `visible` CSS class that the hearing window uses (the hearing window's banner HTML starts hidden via CSS, not inline style).

**Where it is:**  
`src/windows/deaf/index.html` — `conn-banner` div and `onConnectionChange` handler  

**Fix plan:**  
Update the deaf window banner to match the hearing window:
1. Remove the inline `style="display:none"` from the deaf window's `conn-banner` div.  
2. Add the same `.visible` CSS class to `deaf/index.html`'s `<style>`.  
3. Update `onConnectionChange` to use `banner.classList.toggle('visible', !connected)`.  
4. Add a Dismiss button inside the banner.

---

### ISSUE 12 — `window.avatarPlaySigns` is documented as the public API but never called

**Severity:** MEDIUM  
**Feature broken:** API contract / documentation consistency  

**What is wrong:**  
`CLAUDE.md` documents the deaf window as: *"Deaf window calls `window.avatarPlaySigns(signs, text)` to animate"*. But in `deaf/index.html`, the actual message handler uses `window.AmandlaAvatar.queueSign(s)` in a forEach loop — never calling `window.avatarPlaySigns`. The global alias exists in `avatar.js` but is dead.

**Where it is:**  
`src/windows/deaf/index.html` — `signs` message handler (~line 453)  
`src/windows/deaf/avatar.js` — `window.avatarPlaySigns` (~line 470)

**Fix plan:**  
Two options:
- **Option A (simple):** Update `deaf/index.html` to call `window.avatarPlaySigns(msg.signs, msg.text)` instead of the forEach loop — this uses the documented API and handles the label update in one call.  
- **Option B:** Update `CLAUDE.md` to reflect that `window.AmandlaAvatar.queueSign()` is the actual API.  

Option A is cleaner since it also fixes the missing `updateLabel` call in the forEach path.

---

## LOW — Minor issues and edge cases

---

### ISSUE 13 — Emergency auto-dismiss (10 seconds) is too short for deaf users

**Severity:** LOW  
**Feature broken:** emergency alert readability  

**What is wrong:**  
Both windows auto-dismiss the emergency overlay after 10 seconds. A deaf user processes alerts visually and may need more time to read the overlay and understand the situation — especially if they are already stressed. 10 seconds is designed around hearing users who receive both visual and audio alerts simultaneously.

**Where it is:**  
`src/windows/hearing/index.html` `showEmergency()` — `remaining = 10`  
`src/windows/deaf/index.html` `showEmergency()` — `remaining = 10`

**Fix plan:**  
Increase auto-dismiss to `30` seconds on both windows. Retain the Dismiss button so users who are ready can clear it sooner.

---

### ISSUE 14 — Rights window `loading-msg` has two separate elements (`loading-msg` and `loading-msg-2`)

**Severity:** LOW  
**Feature broken:** code cleanliness  

**What is wrong:**  
`src/windows/rights/index.html` has two separate loading spinner elements — `loading-msg` (for step 2 analysis) and `loading-msg-2` (for step 3 letter). Both are shown/hidden with direct `style.display` manipulation duplicated across event handlers. The pattern is fragile.

**Fix plan:**  
Extract a reusable `showLoading(panelNum, show)` helper that handles both panels. Not critical but makes the code easier to maintain.

---

### ISSUE 15 — `quick-signs` categories hard-coded in `deaf/index.html` do not match the signs in `signs_library.js`

**Severity:** LOW  
**Feature broken:** quick sign buttons may silently do nothing if sign not found  

**What is wrong:**  
The CATEGORIES object in `deaf/index.html` includes signs like `'FREE'`, `'RIGHTS'`, `'LAW'`, `'EQUAL'` in the RIGHTS category. When the user taps one of these, `window.AmandlaAvatar.playSignNow(sign)` is called. If the sign name is not in `SIGN_LIBRARY`, `resolveSign()` returns `null`, the avatar does nothing, and no error is shown.

There is also a sign `'LOVE'` in EMOTIONS which may have an entry in `SIGN_LIBRARY` as `'LOVE'` (not `'I LOVE YOU'`). This needs verification.

**Fix plan:**  
Add a startup validation step in `deaf/index.html` that iterates all CATEGORIES entries and logs a warning for any sign name not found in `window.AMANDLA_SIGNS.SIGN_LIBRARY`. This prevents silent failures. No user-facing change needed.

---

## Implementation Order

Implement in this order to reduce risk and get the most value first:

| # | Issue | File(s) to change | Est. effort |
|---|-------|------------------|-------------|
| 1 | Fix CSP `connect-src` for MediaPipe | `src/main.js` | 5 min |
| 2 | Fix Ollama `system` prompt override in all callers | `ollama_client.py`, `main.py`, `claude_service.py`, `transformer.py` | 30 min |
| 3 | Fix `sasl_text` multi-word sign splitting | `backend/main.py` | 20 min |
| 4 | Remove `speakText` from deaf emergency | `src/windows/deaf/index.html` | 2 min |
| 5 | Add `assist_phrase` message type for AssistMode | `deaf/index.html`, `backend/main.py` | 20 min |
| 6 | Add landmark feature extraction | `backend/services/ollama_service.py` | 30 min |
| 7 | Fix rate limit intervals per operation type | `backend/main.py` | 10 min |
| 8 | Fix status dot to reflect Whisper + Ollama | `hearing/index.html`, `deaf/index.html` | 15 min |
| 9 | Fix turn indicator reset timer | `hearing/index.html`, `deaf/index.html` | 5 min |
| 10 | Remove dead `avatar_driver.js` load (Option A) | `deaf/index.html` | 2 min |
| 11 | Fix `conn-banner` consistency in deaf window | `deaf/index.html` | 10 min |
| 12 | Use `window.avatarPlaySigns` in signs handler | `deaf/index.html` | 5 min |
| 13 | Increase emergency auto-dismiss to 30s | `hearing/index.html`, `deaf/index.html` | 3 min |
| 14 | Add sign validation at startup (deaf window) | `deaf/index.html` | 10 min |

**Total estimated time:** ~2.5 hours for all 14 fixes.

---

## What Was NOT a Bug (Investigated and Confirmed Correct)

These were suspected during investigation but confirmed to be working correctly:

- **`translate_with_rules` is a public method** — it exists in `transformer.py` as a proper public wrapper around `_translate_with_rules`. The call in `main.py` is correct. ✓  
- **`sentenceToSigns` called with individual sign name strings** — works correctly because it checks `SIGN_LIBRARY[upper]` after the word map, so `sentenceToSigns("YESTERDAY")` → `SIGN_LIBRARY["YESTERDAY"]`. ✓  
- **Duplicate WebSocket connection guard** — the preload's `connect()` function has a session-key guard that silently ignores duplicate calls. The extra `getSessionId()` call in both renderers causes a no-op second connect. ✓  
- **Rights window CSP** — `_applyCSP(rightsWin)` IS called in `main.js`. ✓  
- **`sasl_ack` for text messages** — sent correctly after the hearing→deaf text path. Speech upload returns `sasl_gloss` in the request/response pair, which is handled in `uploadAudio()`. ✓  
- **ModeController init race** — `mode_controller.js` runs fully before the inline script, so `window.ModeController` is available when the toggle button listener is wired. ✓  
- **`_sign_buffers` race condition** — the cancel+recreate pattern in the sign debounce is correct; `asyncio.CancelledError` is raised at the `sleep` await, before the buffer is popped. ✓

