# MASTER IMPLEMENTATION PROMPT
## AMANDLA SASL Avatar — Complete Realistic Human Upgrade
### Copy everything below this line and paste it to Claude

---

You are a senior Three.js / GLTF / WebGL engineer specialising in sign language avatar systems and South African accessibility technology. Your task is to take the existing AMANDLA avatar code and produce a **complete, fully working replacement file** that upgrades the procedural cylinder-skeleton avatar to a realistic, linguistically correct South African Sign Language (SASL) avatar.

**This is a submission-deadline task. You must produce complete, runnable code with zero placeholders. Every function must be fully implemented.**

---

## PART 1 — EXISTING CODE TO IMPROVE

Here is the existing `avatar.js` you must improve. Read every line carefully before writing a single character of output code. Every feature in this existing code must be preserved and upgraded — nothing removed:

```javascript
[PASTE YOUR FULL avatar.js CODE HERE — the entire IIFE from (function() { to })(); ]
```

Here is the existing Sign-Kit style HOME sign you also need to integrate and convert to AMANDLA format:

```javascript
export const HOME = (ref) => {
    let animations = []
    animations.push(["mixamorigLeftHandThumb1", "rotation", "x", -Math.PI/3, "-"]);
    animations.push(["mixamorigLeftForeArm", "rotation", "x", Math.PI/70, "+"]);
    animations.push(["mixamorigLeftForeArm", "rotation", "z", -Math.PI/7, "-"]);
    animations.push(["mixamorigLeftArm", "rotation", "x", -Math.PI/6, "-"]);
    animations.push(["mixamorigRightHandThumb1", "rotation", "x", -Math.PI/3, "-"]);
    animations.push(["mixamorigRightForeArm", "rotation", "x", Math.PI/70, "+"]);
    animations.push(["mixamorigRightForeArm", "rotation", "z", Math.PI/7, "+"]);
    animations.push(["mixamorigRightArm", "rotation", "x", -Math.PI/6, "-"]);
    ref.animations.push(animations);
    animations = []
    animations.push(["mixamorigLeftForeArm", "rotation", "y", -Math.PI/2.5, "+"]);
    animations.push(["mixamorigRightForeArm", "rotation", "y", Math.PI/2.5, "-"]);
    ref.animations.push(animations);
    animations = []
    animations.push(["mixamorigLeftHandThumb1", "rotation", "x", 0, "+"]);
    animations.push(["mixamorigLeftForeArm", "rotation", "x", 0, "-"]);
    animations.push(["mixamorigLeftForeArm", "rotation", "z", 0, "+"]);
    animations.push(["mixamorigLeftArm", "rotation", "x", 0, "+"]);
    animations.push(["mixamorigRightHandThumb1", "rotation", "x", 0, "+"]);
    animations.push(["mixamorigRightForeArm", "rotation", "x", 0, "-"]);
    animations.push(["mixamorigRightForeArm", "rotation", "z", 0, "-"]);
    animations.push(["mixamorigRightArm", "rotation", "x", 0, "+"]);
    animations.push(["mixamorigLeftForeArm", "rotation", "y", -Math.PI/1.5, "-"]);
    animations.push(["mixamorigRightForeArm", "rotation", "y", Math.PI/1.5, "+"]);
    ref.animations.push(animations);
    if(ref.pending === false){ ref.pending = true; ref.animate(); }
}
```

---

## PART 2 — WHAT MUST CHANGE AND WHY (RESEARCH-BASED REQUIREMENTS)

The following requirements come directly from five peer-reviewed research sources on SASL and sign language avatars. You must implement all of them.

### REQUIREMENT 1 — Replace the procedural skeleton with a GLTF human avatar

**Source: SignON D5.2 (UPF, 2023); VLibras WebMedia 2025; Document 1 (GLTFLoader upgrade guide)**

The existing `buildAvatarSkeleton()` function creates `CylinderGeometry`, `SphereGeometry`, and `BoxGeometry` primitives. Research across three independent studies confirms this is the primary cause of sign rejection by Deaf users. The VLibras study found hand movement errors (caused partly by imprecise cylinder-based finger geometry) were the #1 rejection reason at 84.7%.

**What you must implement:**

Replace `buildAvatarSkeleton()` entirely with a `loadHumanAvatar()` function that uses `THREE.GLTFLoader` to load a `.glb` file. The function must:

1. Show a CSS skeleton loading state on the `#avatar-canvas` element while loading (`container.classList.add('skeleton')`)
2. Load the avatar from `'assets/models/avatar.glb'` (configurable via `window.AMANDLA_CONFIG.avatarUrl` if defined)
3. After loading, traverse the model with `model.traverse()` and for every `isMesh` node:
   - Set `castShadow = true` and `receiveShadow = true`
   - For any mesh whose `material.name` contains `"Skin"` or `"Body"` or `"skin"`: set `roughness = 0.72`, `metalness = 0.0`, and `color = new THREE.Color(0xA8734A)` (warm South African medium-brown skin tone — preserve the cultural specificity of the original)
4. Map all Mixamo-standard bone names to `avatarBones` using `model.getObjectByName()`:

```
avatarBones.head  → 'mixamorigHead'
avatarBones.torso → 'mixamorigSpine1'
avatarBones.R.shoulder → 'mixamorigRightArm'
avatarBones.R.elbow    → 'mixamorigRightForeArm'  
avatarBones.R.wrist    → 'mixamorigRightHand'
avatarBones.L.shoulder → 'mixamorigLeftArm'
avatarBones.L.elbow    → 'mixamorigLeftForeArm'
avatarBones.L.wrist    → 'mixamorigLeftHand'
```

5. Map fingers for both hands using a helper `mapMixamoFingers(model, side)` where side is `'Right'` or `'Left'`. Each finger must have a `segments` array of 3 objects each with a `pivot` property pointing to the corresponding bone:
```
fingers[0] = Thumb:  mixamorig{side}HandThumb1/2/3
fingers[1] = Index:  mixamorig{side}HandIndex1/2/3
fingers[2] = Middle: mixamorig{side}HandMiddle1/2/3
fingers[3] = Ring:   mixamorig{side}HandRing1/2/3
fingers[4] = Pinky:  mixamorig{side}HandPinky1/2/3
```

6. Find the face mesh that has `morphTargetDictionary` (try names `'Wolf3D_Head'`, `'CC_Base_Body'`, `'Head'`, `'head'` in order) and store it as `avatarBones.faceMorphMesh`. Also populate `avatarBones.face` with `{ browL: null, browR: null, mouth: null }` as fallback keys.

7. Add the model to the scene, remove the skeleton loading state, call `buildIdleSign()`, then `animate()`.

8. On error, log `'[Avatar] Failed to load GLB model. Falling back to procedural skeleton.'` and call the original `buildAvatarSkeleton()`.

**The original `buildAvatarSkeleton()` must be kept in the file as the fallback** — do not delete it.

---

### REQUIREMENT 2 — Mixamo axis correction layer

**Source: Sign-Kit ISL Toolkit (HOME sign analysis); SignON D5.2 Annex I (rest pose conventions)**

Mixamo avatars use different rotation axis conventions from the AMANDLA procedural rig. Mixamo's `mixamorigRightArm` rotates on `.z` for adduction and on `.x` for forward elevation. The AMANDLA engine outputs shoulder rotation as `sh.x` (elevation) and `sh.z` (adduction). These need remapping.

**What you must implement:**

Add a function `remapPoseForMixamo(pose)` that is called inside `applyPoseDirect(pose)` when a real GLB is loaded (guarded by a boolean `usingGLTFAvatar`). This function must:

1. For the RIGHT arm: map `data.el.x` (AMANDLA elbow flexion) → apply as `arm.elbow.rotation.y` (Mixamo forearm Y is elbow bend). Map `data.sh.x` → `arm.shoulder.rotation.x`, `data.sh.z` → `arm.shoulder.rotation.z` (same axes, no change needed for shoulder).
2. For the LEFT arm: same mapping but `el.y` gets negative sign because left forearm rotation is mirrored: `arm.elbow.rotation.y = -data.el.x`.
3. For wrists: `data.wr.x` → `arm.wrist.rotation.x`, `data.wr.z` → `arm.wrist.rotation.z`.
4. **Crucially**: For Mixamo finger joints, the curl axis is `.z` not `.x`. Modify `applyHandshapeDirect()` to check `usingGLTFAvatar` and when true, apply finger segment rotations to `seg.pivot.rotation.z` instead of `.rotation.x`.

---

### REQUIREMENT 3 — Blendshape-based Non-Manual Markers

**Source: SignON D5.2 Section 4.1.2 + Annex II (blendshape list + FACS AU mapping); de Villiers PhD Stellenbosch 2014 Chapter 11 (SASL features); van Zijl ASSETS 2006 (NMMs are grammatically obligatory)**

The existing `applyNMMs()` function moves `BoxGeometry` brows and mouth by changing `.position.y` and `.rotation.z`. This is acceptable as a fallback but must be replaced with morph target (blendshape) control when the GLB avatar has them.

The de Villiers dissertation (Stellenbosch 2014) and van Zijl (ASSETS 2006) both state: **Non-manual markers in SASL are grammatically obligatory, not decorative.** A question without a questioning facial expression is linguistically meaningless. The SignON project's Annex II defines the exact FACS Action Units:

| AMANDLA State | ARKit Name | CC4/RPM Name | FACS AU |
|---|---|---|---|
| `nmBrowLiftCur` | `browInnerUp` | `Eyebrow_Arch_Left` + `_Right` | AU1+AU2 |
| `nmBrowFurrowCur` | `browDownLeft` + `browDownRight` | `Eyebrow_Frown_Left` + `_Right` | AU4 |
| `nmMouthOpenCur` | `jawOpen` | `Mouth_Stretch` | AU27 |
| eye blink idle | `eyeBlinkLeft` + `eyeBlinkRight` | `Eye_Blink_Left` + `_Right` | AU45 |

**What you must implement:**

Modify `applyNMMs(dt)` to add a blendshape block after the existing box-geometry block. When `avatarBones.faceMorphMesh` exists and has `morphTargetInfluences`:

```javascript
const mesh = avatarBones.faceMorphMesh;
const d = mesh.morphTargetDictionary;

// Try ARKit names first (Ready Player Me), then CC4/SignON names
function setMorph(names, value) {
  for (const n of names) {
    if (d[n] !== undefined) {
      mesh.morphTargetInfluences[d[n]] = Math.max(0, Math.min(1, value));
      return;
    }
  }
}

setMorph(['browInnerUp', 'Eyebrow_Arch_Left'],   nmBrowLiftCur * 12);
setMorph(['browOuterUpLeft', 'Eyebrow_Arch_Right'], nmBrowLiftCur * 12);
setMorph(['browDownLeft', 'Eyebrow_Frown_Left'],  nmBrowFurrowCur * 5);
setMorph(['browDownRight','Eyebrow_Frown_Right'], nmBrowFurrowCur * 5);
setMorph(['jawOpen', 'Mouth_Stretch'],            Math.abs(nmMouthOpenCur * 40));
```

Also add automatic **eye blinking** as a lifelike idle behaviour. Track `eyeBlinkTimer` and `eyeBlinkDuration`. Every 3–7 seconds (randomised), trigger a 120ms blink (morphTarget `eyeBlinkLeft`/`eyeBlinkRight` or `Eye_Blink_Left`/`Eye_Blink_Right` from 0 → 1 → 0).

---

### REQUIREMENT 4 — Upgrade the setNMMs() function with full SASL grammar markers

**Source: van Zijl ASSETS 2006 (SASL non-manual signs as prosody analogues); de Villiers Chapter 10 Section 10.1 (SASL grammatical markers); VLibras 2025 (inadequate facial expression = rejection)**

Expand the existing `setNMMs()` NMM string detection to cover the complete set of SASL grammatical NMMs. The current code handles: raised eyebrows, furrowed/wh-question, head shake, head nod, mouth open. **Add the following missing markers:**

```javascript
// SASL: Topicalization — topic or subject marker at sentence start
// Linguistic requirement: raised brows + slight head tilt forward
if (n.includes('topic') || n.includes('topicalization') || n.includes('about')) {
  nmBrowLiftTarget = Math.max(nmBrowLiftTarget, 0.018);
  targetHeadX = Math.max(targetHeadX, 0.05);
}

// SASL: Rhetorical question — looks like wh-question but without open mouth
if (n.includes('rhetorical')) {
  nmBrowFurrowTarget = 0.16;
}

// SASL: Intensifier / emphasis — body lean forward, bigger brow
if (n.includes('intensifier') || n.includes('very') || n.includes('extreme') || n.includes('strong')) {
  targetHeadX = Math.max(targetHeadX, 0.09);
  nmBrowLiftTarget = Math.max(nmBrowLiftTarget, 0.015);
}

// SASL: Conditional / if — raised brows held at start of conditional clause  
if (n.includes('conditional') || n.includes('if-clause')) {
  nmBrowLiftTarget = Math.max(nmBrowLiftTarget, 0.022);
}

// SASL: Negative incorporation — stronger head shake + brow furrow
// Required with signs NOT, NONE, NEVER, REFUSE (van Zijl 2006)
if (n.includes('not') || n.includes('none') || n.includes('never') || n.includes('refuse')) {
  nmHeadShake = true;
  nmBrowFurrowTarget = Math.max(nmBrowFurrowTarget, 0.12);
}

// SASL: Surprise / exclamation — raised brows + mouth open
if (n.includes('surprise') || n.includes('exclamation') || n.includes('wow')) {
  nmBrowLiftTarget = Math.max(nmBrowLiftTarget, 0.030);
  nmMouthOpenTarget = Math.min(nmMouthOpenTarget, -0.014);
}
```

---

### REQUIREMENT 5 — Signing Space Management

**Source: van Zijl ASSETS 2006 Section 3 (signing space, pronoun resolution, locus placement)**

Van Zijl's SASL-MT system specifically identifies signing space management as essential for SASL grammar. When a person or object is first signed, a spatial position (locus) is established. Future pronoun references must point to that position.

**What you must implement:**

Add a `SigningSpace` module inside the IIFE:

```javascript
const SigningSpace = (function() {
  const loci = {};  // entity → {x, y, z} in signing space

  function establish(entity, xPos) {
    // xPos: -0.4 (far left) to +0.4 (far right), 0 = centre
    loci[entity.toUpperCase()] = { x: xPos, y: 0, z: 0 };
  }

  function getPointingSign(entity) {
    const loc = loci[entity.toUpperCase()];
    if (!loc) return null;
    const lib = window.AMANDLA_SIGNS;
    const shZ = -(loc.x * 0.5); // pointing right = shoulder abducts right
    const Rarms = { sh: {x: -0.35, y: 0, z: shZ}, el: {x: 0.6, y: 0, z: 0}, wr: {x:0,y:0,z:0} };
    const Larms = { sh: {x: 0.05, y: 0, z: 0.24}, el: {x: 0.08, y: 0, z: 0}, wr: {x:0,y:0,z:0} };
    return {
      name: 'POINT-' + entity,
      R: { ...Rarms, hand: lib && lib.HS ? lib.HS.point : null },
      L: { ...Larms, hand: lib && lib.HS ? lib.HS.rest : null },
      _Rq: lib && lib.armToQuat ? { end: lib.armToQuat(Rarms), start: lib.armToQuat(Rarms) } : null,
      _Lq: lib && lib.armToQuat ? { end: lib.armToQuat(Larms), start: lib.armToQuat(Larms) } : null,
      isFingerspell: false,
      osc: null
    };
  }

  function clear() { Object.keys(loci).forEach(k => delete loci[k]); }

  return { establish, getPointingSign, clear };
})();
```

Expose this on the public API: `window.AmandlaAvatar.signingSpace = SigningSpace`.

---

### REQUIREMENT 6 — Sign-Kit to AMANDLA format converter

**Source: Sign-Kit ISL Toolkit (GitHub); SignON D5.2 Section 3.2 (supporting different avatar configurations)**

The HOME sign and any other Sign-Kit format signs must be converted to AMANDLA v2 sign objects so the TransitionEngine can SLERP between them. Without this, sign transitions will snap.

**What you must implement:**

Add a `convertSignKitSign(name, phases, handshapeR, handshapeL)` function that:

1. Takes the Sign-Kit `phases` array (array of animation arrays)
2. Extracts the peak pose from `phases[1]` (or `phases[0]` if only one phase)
3. Builds AMANDLA-format `R` and `L` arm descriptor objects
4. Maps Mixamo bone names to AMANDLA arm properties using this table:
   - `mixamorigRightArm.x` → `R.sh.x` (negated, AMANDLA uses opposite convention)
   - `mixamorigRightArm.z` → `R.sh.z` (negated)
   - `mixamorigRightForeArm.y` → `R.el.x` (Mixamo Y elbow = AMANDLA X elbow)
   - `mixamorigRightForeArm.z` → `R.el.z`
   - `mixamorigLeftArm.x` → `L.sh.x` (negated)
   - `mixamorigLeftForeArm.y` → `L.el.x` (negated + sign flip)
5. Calls `lib.armToQuat()` if available to populate `_Rq` and `_Lq`
6. Returns a complete v2 sign object with `name`, `R`, `L`, `_Rq`, `_Lq`, `osc: null`, `isFingerspell: false`

Add the HOME sign converted at the bottom of the file so it auto-registers:

```javascript
// Register HOME sign when AMANDLA_SIGNS is ready
function registerConvertedSigns() {
  const lib = window.AMANDLA_SIGNS;
  if (!lib || !lib.armToQuat) { setTimeout(registerConvertedSigns, 150); return; }
  if (lib.SIGN_LIBRARY) {
    // HOME sign peak pose extracted from Sign-Kit phases
    lib.SIGN_LIBRARY['HOME'] = convertSignKitSign('HOME', [
      // Phase 1 peak: both arms raised, forearms rotated inward
      [
        ["mixamorigRightArm", "rotation", "x", -Math.PI/6],
        ["mixamorigRightForeArm", "rotation", "y", Math.PI/2.5],
        ["mixamorigRightForeArm", "rotation", "z", Math.PI/7],
        ["mixamorigLeftArm", "rotation", "x", -Math.PI/6],
        ["mixamorigLeftForeArm", "rotation", "y", -Math.PI/2.5],
        ["mixamorigLeftForeArm", "rotation", "z", -Math.PI/7],
      ]
    ], lib.HS.flat, lib.HS.flat);
  }
}
registerConvertedSigns();
```

---

### REQUIREMENT 7 — Lifelike Idle Animations

**Source: Document 8 (AAA upgrade guide — applyLifelikeIdle); SignON D5.2 Section 4.1 (avatar quality); VLibras 2025 (realism improvements)**

The current idle uses shoulder sway. Replace with physiologically correct breathing.

**What you must implement:**

Replace the idle block in `animate()` with `applyLifelikeIdle(dt, oscTime)`:

```javascript
// Lifelike idle state variables (declare at top of IIFE)
let eyeGazeTimer = 0;
let eyeGazeTargetX = 0, eyeGazeTargetY = 0;
let eyeBlinkTimer = 3.5;
let eyeBlinkPhase = 0; // 0=open, 1=closing, 2=opening

function applyLifelikeIdle(dt, oscTime) {
  // 1. Chest breathing (torso scale, not shoulder shrug)
  // Based on physiological observation: ribcage expands on inhale
  if (avatarBones.torso) {
    const breathIn = Math.sin(oscTime * 0.25 * Math.PI * 2);
    avatarBones.torso.scale.set(
      1.0 + breathIn * 0.015,  // ribs expand sideways
      1.0 + breathIn * 0.005,  // chest lifts slightly
      1.0 + breathIn * 0.020   // chest pushes forward
    );
  }

  // 2. Subtle arm breathing (much smaller than original — not a shrug)
  if (avatarBones.R && avatarBones.L && animState === 'idle') {
    const sway = Math.sin(oscTime * 0.40) * 0.008; // halved from original
    avatarBones.R.shoulder.rotation.z = lerpVal(avatarBones.R.shoulder.rotation.z, -0.24 + sway, 0.05);
    avatarBones.L.shoulder.rotation.z = lerpVal(avatarBones.L.shoulder.rotation.z,  0.24 - sway, 0.05);
  }

  // 3. Eye saccades — humans never stare perfectly still
  // (Document 8: micro eye movements every 1-3 seconds)
  eyeGazeTimer -= dt;
  if (eyeGazeTimer <= 0) {
    eyeGazeTargetX = (Math.random() - 0.5) * 0.04;
    eyeGazeTargetY = (Math.random() - 0.5) * 0.015;
    eyeGazeTimer = 1.5 + Math.random() * 2.5;
  }
  const leftEye = avatarBones.faceMorphMesh
    ? avatarBones.faceMorphMesh.parent && avatarBones.faceMorphMesh.parent.getObjectByName
      ? avatarBones.faceMorphMesh.parent.getObjectByName('mixamorigLeftEye')
      : null
    : null;
  if (leftEye) {
    leftEye.rotation.y += (eyeGazeTargetX - leftEye.rotation.y) * 0.08;
    leftEye.rotation.x += (eyeGazeTargetY - leftEye.rotation.x) * 0.08;
    const rightEye = leftEye.parent.getObjectByName('mixamorigRightEye');
    if (rightEye) {
      rightEye.rotation.y = leftEye.rotation.y;
      rightEye.rotation.x = leftEye.rotation.x;
    }
  }

  // 4. Automatic eye blinks (idle only)
  eyeBlinkTimer -= dt;
  if (eyeBlinkTimer <= 0 && eyeBlinkPhase === 0) {
    eyeBlinkPhase = 1;
    eyeBlinkTimer = 0.06; // 60ms close
  }
  if (eyeBlinkPhase > 0 && avatarBones.faceMorphMesh && avatarBones.faceMorphMesh.morphTargetDictionary) {
    const d = avatarBones.faceMorphMesh.morphTargetDictionary;
    const names = ['eyeBlinkLeft','eyeBlinkRight','Eye_Blink_Left','Eye_Blink_Right'];
    const blinkValue = eyeBlinkPhase === 1 ? (1.0 - eyeBlinkTimer / 0.06) : (eyeBlinkTimer / 0.06);
    names.forEach(n => {
      if (d[n] !== undefined)
        avatarBones.faceMorphMesh.morphTargetInfluences[d[n]] = Math.min(1, Math.max(0, blinkValue));
    });
    eyeBlinkTimer -= dt; // already decremented above for close phase
    if (eyeBlinkTimer <= 0) {
      if (eyeBlinkPhase === 1) { eyeBlinkPhase = 2; eyeBlinkTimer = 0.08; } // 80ms open
      else { eyeBlinkPhase = 0; eyeBlinkTimer = 3.0 + Math.random() * 4.0; }
    }
  }
}
```

Replace the existing idle block in `animate()` with:
```javascript
} else { // idle
  applyLifelikeIdle(dt, oscTime);
  if (signQueue.length > 0 && idleSign && TE) {
    startNextTransition(idleSign);
  }
}
```

---

### REQUIREMENT 8 — Forearm Twist Bone (Candy-Wrapper Fix)

**Source: Document 8 (AAA upgrade guide — updateTwistBones); SignON D5.2 Section 3.2 (mesh intrusion/intersection); VLibras 2025 (mesh intrusion = 17.5% of rejections)**

When the wrist rotates (palm up vs palm down), the forearm skin must also rotate partway — otherwise it pinches at the wrist like a candy wrapper. Mixamo rigs include `mixamorigRightForeArmTwist` and `mixamorigLeftForeArmTwist` bones for exactly this.

**What you must implement:**

Add `updateTwistBones()` and call it every frame in `animate()`:

```javascript
function updateTwistBones() {
  if (!usingGLTFAvatar || !avatarBones.R || !avatarBones.L) return;

  function applyTwist(side) {
    const arm = avatarBones[side];
    if (!arm || !arm.wrist) return;
    const twistBoneName = 'mixamorig' + (side === 'R' ? 'Right' : 'Left') + 'ForeArmTwist';
    if (!arm._twistBone) {
      // Cache the twist bone reference on first call
      if (scene) scene.traverse(n => { if (n.name === twistBoneName) arm._twistBone = n; });
    }
    if (arm._twistBone) {
      // Apply 50% of wrist roll to twist bone (prevents full candy-wrapper)
      arm._twistBone.rotation.y = arm.wrist.rotation.y * 0.5;
    }
  }

  applyTwist('R');
  applyTwist('L');
}
```

---

### REQUIREMENT 9 — Infinite retry guard on buildIdleSign

**Source: Code review of existing avatar.js**

The current `buildIdleSign()` will retry forever if `window.AMANDLA_SIGNS` never loads. Add a counter:

```javascript
let _idleRetries = 0;
function buildIdleSign() {
  const lib = window.AMANDLA_SIGNS;
  if (!lib || !lib.armToQuat) {
    if (++_idleRetries > 80) {
      console.error('[Avatar] AMANDLA_SIGNS library never loaded after 8s. Check script order.');
      return;
    }
    setTimeout(buildIdleSign, 100);
    return;
  }
  _idleRetries = 0;
  // ... rest of existing function unchanged
}
```

---

### REQUIREMENT 10 — Timing calibration for fluent SASL pace

**Source: Czech SL MoCap (LREC 2020) — average sign duration 0.38s continuous signing; VLibras 2025 — lack of fluidity as rejection reason**

The Czech MoCap study recorded average sign duration of 0.81s in dictionary mode and 0.38s in continuous signing. AMANDLA's current constants are tuned for dictionary mode. For fluent conversational signing, reduce:

```javascript
const SIGN_HOLD    = 0.32   // was 0.38 — matches continuous signing pace
const SIGN_FS_HOLD = 0.19   // was 0.22 — fingerspell at ~5 chars/sec
const SIGN_GAP     = 0.10   // was 0.18 — tighter coarticulation gap
```

---

### REQUIREMENT 11 — Mobile optimisation (avatar load)

**Source: SignON D5.2 Section 4.2 (mobile adaptation); VLibras 2025 Section 3.4 (VRM model specifications)**

SignON reduced avatar file size from 91.7MB to 17MB without visual quality loss on mobile by: halving texture resolution, removing invisible meshes, and 40% vertex decimation. Your loading function must support a mobile hint:

```javascript
// Add to loadHumanAvatar()
const isMobile = /iPhone|iPad|Android|Mobile/i.test(navigator.userAgent);
const avatarUrl = isMobile
  ? (window.AMANDLA_CONFIG && window.AMANDLA_CONFIG.avatarUrlMobile) || 'assets/models/avatar_mobile.glb'
  : (window.AMANDLA_CONFIG && window.AMANDLA_CONFIG.avatarUrl) || 'assets/models/avatar.glb';
```

---

### REQUIREMENT 12 — Enhanced public API

**Source: SignON D5.2 (configuration file per avatar); de Villiers 2014 (extensibility requirement); van Zijl 2006 (signing space)**

Extend `window.AmandlaAvatar` with:

```javascript
window.AmandlaAvatar = {
  // existing:
  initAvatar, queueSign, queueSentence, playSignNow, setNMMs, destroyAvatar,
  // NEW:
  signingSpace: SigningSpace,          // locus management for pronouns
  setAvatarUrl: function(url, mobileUrl) {
    window.AMANDLA_CONFIG = window.AMANDLA_CONFIG || {};
    window.AMANDLA_CONFIG.avatarUrl = url;
    if (mobileUrl) window.AMANDLA_CONFIG.avatarUrlMobile = mobileUrl;
  },
  reloadAvatar: function() {
    // Destroys current avatar bones and reloads the GLB
    avatarBones = {};
    usingGLTFAvatar = false;
    loadHumanAvatar();
  },
  isGLTFAvatar: function() { return usingGLTFAvatar; },
  registerSign: function(name, signObj) {
    const lib = window.AMANDLA_SIGNS;
    if (lib && lib.SIGN_LIBRARY) lib.SIGN_LIBRARY[name] = signObj;
  },
  registerSignKitSign: function(name, phases, handshapeR, handshapeL) {
    const converted = convertSignKitSign(name, phases, handshapeR, handshapeL);
    if (converted) window.AmandlaAvatar.registerSign(name, converted);
    return converted;
  }
}
```

---

## PART 3 — COMPLETE OUTPUT SPECIFICATION

Produce a **single complete JavaScript file** that contains everything listed above. The file must:

1. Begin with a clear comment block: version number, date, list of all changes made
2. Be wrapped in `(function() { 'use strict'; ... })();` exactly as the original
3. Keep every constant, state variable, function, and public API from the original — nothing removed
4. Add all new state variables at the top alongside existing ones, clearly grouped
5. Have `loadHumanAvatar()` and `buildAvatarSkeleton()` both present — `loadHumanAvatar()` is called first, falls back to `buildAvatarSkeleton()` on error
6. Have `usingGLTFAvatar = false` as a state variable, set to `true` after GLB loads successfully
7. Guard all GLB-specific logic with `if (usingGLTFAvatar)` checks
8. Call `updateTwistBones()` in `animate()` after `applyPoseDirect()`
9. Call `applyLifelikeIdle(dt, oscTime)` in the idle branch of the state machine
10. Call `applyNMMsToBlendshapes()` inside `applyNMMs()` as the last operation
11. Have `SigningSpace` module fully implemented
12. Have `convertSignKitSign()` fully implemented
13. Have `registerConvertedSigns()` called at the bottom of the IIFE
14. Export `window.AmandlaAvatar` with the full enhanced public API
15. Have zero `// TODO` comments, zero placeholder functions, zero stub implementations

**Do not output any explanation, commentary, or markdown fencing — output only the complete JavaScript file, starting with the comment block.**

---

## PART 4 — ADDITIONAL CONTEXT FOR AVATAR SOURCING

When the output code is running, the developer will need to provide the `.glb` file. Include a comment block at the top of `loadHumanAvatar()` that says exactly:

```
/*
 * GLB SOURCING GUIDE — SASL AVATAR
 * ─────────────────────────────────
 * Option 1 (RECOMMENDED — Free, 5 minutes):
 *   1. Go to https://readyplayer.me
 *   2. Create avatar, choose warm brown skin tone for SASL cultural accuracy
 *   3. Export URL: https://models.readyplayer.me/[ID].glb?morphTargets=ARKit&lod=0
 *   4. This gives you: full finger rig + 52 ARKit blendshapes for NMMs
 *   5. Bone names: mixamorigHead, mixamorigRightArm, etc. (Mixamo standard)
 *
 * Option 2 (Mixamo.com — Free with Adobe account):
 *   1. Upload any character mesh
 *   2. Auto-rig → download FBX → convert to GLB via Blender
 *   3. Bone names are mixamorig standard — fully compatible
 *
 * Option 3 (Character Creator 4 → Blender → Mixamo pipeline):
 *   Per SignON D5.2 Annex I: CC4 → export FBX → Blender (apply transforms,
 *   fix rest pose) → Mixamo (auto-rig) → Blender (second pass + script) → GLB
 *   This gives highest quality but takes ~15 minutes per avatar.
 *
 * MOBILE: Create a second GLB with:
 *   - Textures halved (1024px max, was 2048) — saves ~55% file size
 *   - Invisible meshes removed (legs/torso under clothing) — saves ~10%
 *   - 40% vertex decimation on far-camera meshes — saves ~5%
 *   Per SignON D5.2 Section 4.2: 91.7MB → 17MB with no perceptible mobile quality loss
 */
```

---

## PART 5 — VALIDATION CHECKLIST

After generating the code, verify internally (do not output this verification, just use it to self-check):

- [ ] `buildAvatarSkeleton()` still exists as fallback
- [ ] `loadHumanAvatar()` exists and uses `THREE.GLTFLoader`
- [ ] `usingGLTFAvatar` boolean declared and toggled
- [ ] `remapPoseForMixamo()` implemented and called in `applyPoseDirect()`
- [ ] Finger curl axis switches to `.z` when `usingGLTFAvatar`
- [ ] `applyNMMs()` uses blendshape `setMorph()` helper when `faceMorphMesh` available
- [ ] Eye blink state machine implemented (3 phases: open/closing/opening)
- [ ] All new SASL NMM markers added to `setNMMs()`
- [ ] `SigningSpace` module fully implemented with `establish()`, `getPointingSign()`, `clear()`
- [ ] `convertSignKitSign()` fully implemented
- [ ] HOME sign registered via `registerConvertedSigns()`
- [ ] `applyLifelikeIdle()` implemented with chest breathing + eye saccades
- [ ] `updateTwistBones()` implemented and called in `animate()`
- [ ] Infinite retry guard on `buildIdleSign()` with 80-attempt max
- [ ] SIGN_HOLD = 0.32, SIGN_FS_HOLD = 0.19, SIGN_GAP = 0.10
- [ ] Mobile URL detection in `loadHumanAvatar()`
- [ ] `window.AmandlaAvatar` has all new API methods
- [ ] GLB sourcing comment block inside `loadHumanAvatar()`
- [ ] Zero TODO comments, zero stubs, every function complete

---

*This prompt is based on: de Villiers, H.A.C. (2014) A Vision-based South African Sign Language Tutor, PhD, Stellenbosch University; van Zijl, L. (2006) South African Sign Language Machine Translation Project, ASSETS 2006; Martins et al. (2025) Automatic 3D Animation Generation for Sign Language, WebMedia 2025; Blat et al. (2023) SignON D5.2 A Virtual Character; Jedlička et al. (2020) Sign Language Motion Capture Dataset for Data-driven Synthesis, LREC 2020; Sign-Kit ISL Toolkit (GitHub); AMANDLA avatar.js v2.0*
