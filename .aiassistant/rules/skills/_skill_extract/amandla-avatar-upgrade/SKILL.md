---
name: amandla-avatar-upgrade
description: >
  Complete upgrade guide for replacing Amandla's geometry-based Three.js avatar with the TalkingHead
  library + Avaturn photorealistic human model. Covers installation, avatar loading, SASL sign library
  retargeting from the old keyframe format to TalkingHead gestureTemplates, emotion/mood mapping,
  idle animations, and integration with the existing WebSocket sign pipeline.
  Activate when the user says "upgrade the avatar", "replace the avatar", "TalkingHead", "Avaturn",
  "realistic avatar", "the avatar looks bad", "improve how the avatar looks", or when working on
  src/windows/deaf/avatar.js or src/windows/deaf/deaf.js. This is the single source of truth
  for the entire avatar modernisation effort.
---

# Amandla Avatar Upgrade: TalkingHead + Avaturn

## What This Upgrade Achieves

The current avatar is built from Three.js cylinder geometry with manually coded bone rotations.
After this upgrade, Amandla will have:
- A **photorealistic human avatar** (created from a selfie at avaturn.me)
- **Real facial expressions**: blinking, eyebrow raises, smiles, 52 ARKit blend shapes
- **Lip-sync** (for the hearing side or future TTS features)
- **Idle animations**: breathing, subtle head movement, eye contact
- **Moods**: happy, sad, neutral, angry — driven by message content
- All existing **100+ SASL signs** retargeted to the new rig automatically

**Everything stays inside the existing Electron + FastAPI stack. No framework migration.**

---

## Architecture After Upgrade

```
deaf/index.html
  └─ loads TalkingHead via CDN importmap (no npm install needed)
  └─ loads avatar.js (rewritten to use TalkingHead)

deaf.js (unchanged interface)
  └─ still calls window.avatarPlaySigns(signs, text)
  └─ internally converts signs → TalkingHead gestureTemplates

signs_library.js (unchanged)
  └─ still exports AMANDLA_SIGNS with existing keyframe format
  └─ avatar.js converts the format at runtime — no edits to signs_library.js
```

**The public API `window.avatarPlaySigns(signs, text)` stays exactly the same.**
`deaf.js` calls it exactly as before. Only `avatar.js` and `index.html` change.

---

## Phase 1 — Get the Avaturn GLB File

Before writing any code, get the avatar model. Do this ONCE manually:

1. Go to **https://avaturn.me** — click "Create Avatar"
2. Upload a selfie or use the manual sliders to create the desired look
3. When satisfied, click **"Export"** → select **GLB format**
4. Save the file as `src/windows/deaf/avatars/amandla-avatar.glb`
5. Create the directory if needed: `mkdir -p src/windows/deaf/avatars/`

**Requirements the GLB must meet for TalkingHead:**
- Mixamo-compatible bone rig (Avaturn T2 provides this automatically)
- ARKit blend shapes (52 shape keys — Avaturn T2 provides these)
- Oculus visemes (15 shape keys — Avaturn T2 provides these)

Avaturn T2 avatars satisfy all three requirements out of the box.

**File size note:** Avaturn GLBs are typically 5–15 MB. This is acceptable for a desktop Electron app.
Add `src/windows/deaf/avatars/*.glb` to `.gitignore` — don't commit binary model files.

```bash
# Add to .gitignore:
echo "src/windows/deaf/avatars/*.glb" >> .gitignore
```

---

## Phase 2 — Update deaf/index.html

Replace the current Three.js script tags with the TalkingHead importmap.
Read the full current `deaf/index.html` first, then make these changes:

### Remove (find and delete these existing script/module imports):
- Any `import * as THREE from 'three'` or CDN Three.js script tags
- Any existing `import { ... } from '...'` for Three.js addons
- The current `<script src="avatar.js">` tag (will be replaced)

### Add before `</head>`:
```html
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

### Add before `</body>`:
```html
<div id="avatar-container" style="width:100%;height:60vh;position:relative;"></div>
<script type="module" src="avatar.js"></script>
```

**Important:** The `type="module"` on the script tag is required — TalkingHead uses ES modules.
The CSP in `src/main.js` already allows `cdn.jsdelivr.net` style imports from self, but
if the avatar fails to load, check the Electron CSP configuration allows the CDN URLs.

---

## Phase 3 — Rewrite avatar.js

This is the main implementation. Write the complete new `src/windows/deaf/avatar.js`:

```javascript
/**
 * avatar.js — Amandla deaf window avatar engine v3.0
 *
 * Uses TalkingHead library (met4citizen/TalkingHead) for photorealistic
 * avatar rendering with ARKit facial expressions, lip-sync, and Mixamo
 * bone-based sign language gestures.
 *
 * Public API (unchanged from v2):
 *   window.avatarPlaySigns(signs, text) — plays an array of SASL sign names
 *
 * Dependencies:
 *   - TalkingHead@1.7 via importmap in index.html
 *   - avatars/amandla-avatar.glb (Avaturn T2 export)
 *   - ../../signs_library.js loaded as window.AMANDLA_SIGNS
 */

import { TalkingHead } from "talkinghead";

// ─── Constants ────────────────────────────────────────────────────────────────

/** Path to the Avaturn GLB model, relative to deaf/index.html */
const AVATAR_GLB_PATH = "./avatars/amandla-avatar.glb";

/** Milliseconds to hold a sign before moving to the next */
const SIGN_HOLD_MS = 800;

/** Milliseconds gap (neutral pose) between signs */
const SIGN_GAP_MS = 200;

/** Milliseconds for transition into and out of a gesture */
const GESTURE_TRANSITION_MS = 400;

// ─── Module State ─────────────────────────────────────────────────────────────

/** @type {TalkingHead|null} The TalkingHead instance */
let head = null;

/** @type {boolean} True after avatar has loaded successfully */
let avatarReady = false;

/** @type {boolean} True while a sign sequence is animating */
let isAnimating = false;

// ─── Initialisation ───────────────────────────────────────────────────────────

/**
 * Initialises the TalkingHead avatar and loads the Avaturn GLB model.
 * Called automatically when this module loads.
 * Sets window.avatarPlaySigns once ready.
 */
async function initAvatar() {
  const container = document.getElementById("avatar-container");
  if (!container) {
    console.error("[avatar] #avatar-container not found in DOM");
    return;
  }

  try {
    // Create TalkingHead instance — no TTS endpoint needed (we handle signs directly)
    head = new TalkingHead(container, {
      modelFPS: 30,
      cameraView: "full",           // Show full body for signing
      cameraDistance: 0.5,          // Slightly zoomed out from default
      avatarMood: "neutral",
      avatarIdleEyeContact: 0.3,    // Occasional eye contact while idle
      avatarSpeakingHeadMove: 0.3,  // Subtle head movement
      lightAmbientIntensity: 2,
      lightDirectIntensity: 30,
    });

    _setStatus("Loading avatar...");

    await head.showAvatar({
      url: AVATAR_GLB_PATH,
      body: "F",                    // Change to "M" for male avatar
      avatarMood: "neutral",
      lipsyncLang: "en",
      // Avaturn T2 bone adjustment — corrects slight neck forward tilt
      baseline: {
        headRotateX: -0.04,
      },
      // Retarget Avaturn skeleton to TalkingHead expected positions
      retarget: {
        Neck: { ry: 0 },
        LeftShoulder: { rz: 0.1 },
        RightShoulder: { rz: -0.1 },
      },
    });

    // Build gestureTemplates from the existing SASL signs library
    _registerSASLSigns();

    // Expose the public API
    window.avatarPlaySigns = playSignSequence;
    window.avatarSetMood = setMood;

    avatarReady = true;
    _setStatus("Ready");
    console.log("[avatar] TalkingHead avatar loaded successfully");

  } catch (error) {
    console.error("[avatar] Failed to load avatar:", error);
    _setStatus("Avatar unavailable — check avatars/amandla-avatar.glb");
  }
}

// ─── SASL Sign Registration ───────────────────────────────────────────────────

/**
 * Converts all signs in window.AMANDLA_SIGNS from the legacy keyframe format
 * into TalkingHead gestureTemplates.
 *
 * Legacy format (signs_library.js):
 *   animations.push(["mixamorigLeftForeArm", "rotation", "x", Math.PI/2, "+"]);
 *
 * TalkingHead gestureTemplate format:
 *   { 'LeftForeArm.rotation': { x: Math.PI/2, y: 0, z: 0 } }
 *
 * The "mixamorig" prefix is stripped — TalkingHead removes it automatically,
 * but we strip it here too for consistency with the gestureTemplate keys.
 */
function _registerSASLSigns() {
  const signs = window.AMANDLA_SIGNS;
  if (!signs) {
    console.warn("[avatar] window.AMANDLA_SIGNS not found — signs_library.js not loaded");
    return;
  }

  let registered = 0;
  for (const [signName, signDef] of Object.entries(signs)) {
    const gestureTemplate = _convertSignToGesture(signDef);
    if (gestureTemplate && Object.keys(gestureTemplate).length > 0) {
      head.gestureTemplates[signName] = gestureTemplate;
      registered++;
    }
  }

  console.log(`[avatar] Registered ${registered} SASL signs as gesture templates`);
}

/**
 * Converts a single SASL sign definition (array of keyframe phases) into
 * a TalkingHead gestureTemplate (flat bone rotation object).
 *
 * We use the FINAL phase of each sign as the held pose — this is the
 * position the hand rests in at the peak of the sign movement.
 *
 * @param {object} signDef - Sign definition from AMANDLA_SIGNS
 * @returns {object} TalkingHead gestureTemplate bone rotation object
 */
function _convertSignToGesture(signDef) {
  if (!signDef?.animations || !Array.isArray(signDef.animations)) {
    return {};
  }

  // Accumulate bone rotations across all animation phases
  // Each phase is an array of: ["boneName", "rotation", "axis", value, "±"]
  const boneRotations = {};

  for (const phase of signDef.animations) {
    if (!Array.isArray(phase)) continue;
    for (const keyframe of phase) {
      const [rawBoneName, property, axis, value] = keyframe;
      if (property !== "rotation") continue;

      // Strip the "mixamorig" prefix — TalkingHead doesn't use it
      const boneName = rawBoneName.replace(/^mixamorig/, "");
      const key = `${boneName}.rotation`;

      if (!boneRotations[key]) {
        boneRotations[key] = { x: 0, y: 0, z: 0 };
      }
      boneRotations[key][axis] = value;
    }
  }

  return boneRotations;
}

// ─── Sign Playback ────────────────────────────────────────────────────────────

/**
 * Plays a sequence of SASL sign names on the avatar.
 * This is the main public API, called by deaf.js.
 *
 * @param {string[]} signs - Array of SASL sign name strings from the backend
 * @param {string} originalText - Original English text (used for mood inference)
 * @returns {Promise<void>}
 */
async function playSignSequence(signs, originalText) {
  if (!avatarReady || !head) {
    console.warn("[avatar] Avatar not ready — cannot play signs");
    return;
  }

  if (!signs || signs.length === 0) return;

  // Prevent overlapping sign sequences
  if (isAnimating) {
    console.log("[avatar] Already animating — queuing not yet implemented");
    return;
  }

  isAnimating = true;
  _setMoodFromText(originalText);

  try {
    for (const signName of signs) {
      await _playSingleSign(signName);
      await _pause(SIGN_GAP_MS); // Brief neutral gap between signs
    }
  } finally {
    // Return to idle regardless of success or error
    head.stopGesture(GESTURE_TRANSITION_MS);
    isAnimating = false;
  }
}

/**
 * Plays a single named sign gesture.
 * Falls back to fingerspelling if the sign is not in the library.
 *
 * @param {string} signName - The SASL sign name (e.g., "HELLO", "WATER")
 * @returns {Promise<void>}
 */
async function _playSingleSign(signName) {
  const isKnown = signName in (head.gestureTemplates || {});

  if (isKnown) {
    // Play the registered gesture and wait for SIGN_HOLD_MS
    head.playGesture(signName, SIGN_HOLD_MS / 1000, false, GESTURE_TRANSITION_MS);
    await _pause(SIGN_HOLD_MS);
  } else {
    // Unknown sign — fingerspell it letter by letter
    console.log(`[avatar] Unknown sign "${signName}" — fingerspelling`);
    await _fingerspellWord(signName);
  }
}

/**
 * Fingerspells a word letter by letter using the handshape gestures.
 *
 * @param {string} word - The word to fingerspell
 * @returns {Promise<void>}
 */
async function _fingerspellWord(word) {
  for (const letter of word.toUpperCase()) {
    const letterGesture = `FS_${letter}`; // e.g., "FS_A", "FS_B"
    if (letterGesture in (head.gestureTemplates || {})) {
      head.playGesture(letterGesture, SIGN_HOLD_MS / 2 / 1000, false, 150);
      await _pause(SIGN_HOLD_MS / 2);
    }
  }
}

// ─── Mood and Emotion ─────────────────────────────────────────────────────────

/**
 * Sets the avatar's mood based on keywords in the translated text.
 * TalkingHead supports: "neutral", "happy", "angry", "sad", "fear",
 * "disgust", "love", "sleep"
 *
 * @param {string} text - The original English text being signed
 */
function _setMoodFromText(text) {
  if (!head || !text) return;

  const lower = text.toLowerCase();
  let mood = "neutral";

  if (/thank|please|help|great|good|love|happy/.test(lower)) mood = "happy";
  else if (/sorry|sad|pain|hurt|sick|difficult/.test(lower)) mood = "sad";
  else if (/emergency|urgent|danger|help me|call|now/.test(lower)) mood = "fear";
  else if (/no|stop|wrong|not|don't/.test(lower)) mood = "angry";

  head.setMood(mood);
}

/**
 * Directly sets the avatar's mood. Exposed as window.avatarSetMood.
 *
 * @param {string} mood - One of: neutral, happy, angry, sad, fear, disgust, love, sleep
 */
function setMood(mood) {
  if (!head) return;
  const validMoods = ["neutral", "happy", "angry", "sad", "fear", "disgust", "love", "sleep"];
  if (!validMoods.includes(mood)) {
    console.warn(`[avatar] Unknown mood: "${mood}". Valid moods: ${validMoods.join(", ")}`);
    return;
  }
  head.setMood(mood);
}

// ─── Utilities ────────────────────────────────────────────────────────────────

/**
 * Returns a Promise that resolves after the given number of milliseconds.
 *
 * @param {number} ms - Milliseconds to wait
 * @returns {Promise<void>}
 */
function _pause(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Updates the loading/status text shown below the avatar.
 * Looks for an element with id="avatar-status".
 *
 * @param {string} message - Status message to display
 */
function _setStatus(message) {
  const statusEl = document.getElementById("avatar-status");
  if (statusEl) statusEl.textContent = message;
}

// ─── Bootstrap ────────────────────────────────────────────────────────────────

// Start loading as soon as the module runs
initAvatar();
```

---

## Phase 4 — Register Fingerspelling Gestures

After `_registerSASLSigns()` runs, manually add the 26 fingerspelling handshapes
if they are not already in `signs_library.js`. Add this function call inside `initAvatar()`:

```javascript
// Inside initAvatar(), after _registerSASLSigns():
_registerFingerspellingAlphabet();
```

```javascript
/**
 * Registers the SASL fingerspelling alphabet as gesture templates.
 * These are used as fallback when a sign word is not in the library.
 * Bone values approximate SASL handshapes — refine per sign.
 */
function _registerFingerspellingAlphabet() {
  // Example — A handshape (closed fist with thumb out)
  head.gestureTemplates["FS_A"] = {
    "LeftHandThumb1.rotation": { x: 0.3, y: -0.1, z: 0.4 },
    "LeftHandIndex1.rotation": { x: 1.4, y: 0, z: 0 },
    "LeftHandMiddle1.rotation": { x: 1.4, y: 0, z: 0 },
    "LeftHandRing1.rotation": { x: 1.4, y: 0, z: 0 },
    "LeftHandPinky1.rotation": { x: 1.4, y: 0, z: 0 },
  };
  // Add B through Z following the same pattern...
  // Reference: https://en.wikipedia.org/wiki/SASL_manual_alphabet
}
```

The full 26-letter alphabet needs to be built out sign by sign.
This is a task for a separate session — the infrastructure is in place.

---

## Phase 5 — Update deaf.js (Minimal Changes)

`deaf.js` already calls `window.avatarPlaySigns(signs, text)`. That API is unchanged.
The only addition needed is a check for avatar readiness and optional mood calls:

```javascript
// In deaf.js — find the section that handles "signs" messages
// and optionally add mood setting for emergency signs:

window.amandla.onMessage((message) => {
  if (message.type === "signs") {
    // This call already exists and continues to work unchanged:
    window.avatarPlaySigns(message.signs, message.original_text);
  }
  if (message.type === "emergency") {
    // New: set urgency mood for emergency phrases
    if (window.avatarSetMood) window.avatarSetMood("fear");
    window.avatarPlaySigns(message.signs, message.original_text);
  }
});
```

---

## Phase 6 — Verification Checklist

Before calling this done, verify each item:

```
□ src/windows/deaf/avatars/amandla-avatar.glb exists (downloaded from Avaturn)
□ avatars/*.glb is in .gitignore  
□ index.html has the TalkingHead importmap in <head>
□ index.html has <div id="avatar-container"> in <body>
□ index.html script tag for avatar.js has type="module"
□ avatar.js loads without console errors
□ Avatar appears in the deaf window (not blank)
□ Avatar blinks and breathes in idle state
□ window.avatarPlaySigns exists after avatar loads
□ Sending a known sign (e.g., "HELLO") makes the avatar gesture
□ Sending an unknown word triggers fingerspelling
□ Mood changes visible when emergency message arrives
□ deaf.js still works without any other changes
□ Hearing window is unaffected
```

---

## Known Limitations and Future Work

| Limitation | Impact | Future Fix |
|-----------|--------|-----------|
| Fingerspelling alphabet incomplete (26 letters) | Unknown words fall through silently | Build out FS_A–FS_Z gesture templates |
| Sign transition is instant (no SLERP between keyframe phases) | Looks slightly mechanical on complex signs | Implement phase-by-phase animation using TalkingHead's `speakAudio` anim object |
| Avaturn GLB not in source control | Teammates must export their own | Store in project cloud storage (Google Drive, S3) and document download step |
| CSP may block CDN imports in some Electron configs | Avatar fails to load silently | Add CDN domains to Electron CSP allowlist in main.js |

---

## References

- TalkingHead GitHub: https://github.com/met4citizen/TalkingHead
- TalkingHead CDN: `https://cdn.jsdelivr.net/gh/met4citizen/TalkingHead@1.7/modules/talkinghead.mjs`
- Avaturn web creator: https://avaturn.me
- Avaturn Three.js integration docs: https://docs.avaturn.me/docs/integration/web/threejs/
- Detailed reference docs → see `references/bone-names.md` and `references/talkinghead-api.md`
