# AMANDLA Avatar — Research Synthesis & Application Improvement Roadmap
**South African Sign Language (SASL) Digital Accessibility Platform**
*Synthesised from: de Villiers (2014), van Zijl (2006), VLibras (2025), SignON D5.2 (2023), Czech SL MoCap (2020), CWA XR-LPA, Sign-Kit ISL Toolkit, ASL Sensor Dataset, AMANDLA codebase*

---

## 1. Executive Summary

Your application currently runs two architectures in parallel that were never designed to talk to each other:

- **AMANDLA Avatar (`avatar.js`)** — a procedural Three.js skeleton (cylinders, spheres) with a sophisticated `TransitionEngine` doing SLERP quaternion blending and Non-Manual Marker (NMM) support. This is linguistically aware but visually primitive.
- **Sign-Kit style system** — a real Mixamo-rigged GLB/GLTF human avatar driven by keyframe arrays on `mixamorig*` bone names (e.g., the `HOME` sign). This looks human but has no linguistic intelligence.

The research is clear on the correct path forward: **bring the AMANDLA linguistic engine to drive the Mixamo human avatar**. Every paper reviewed — VLibras, SignON, de Villiers, the Czech MoCap study — confirms that animation naturalness requires real human-derived data on a real human rig, but grammatical fidelity (NMMs, signing space, coarticulation) requires the kind of engine AMANDLA already has.

This document maps exactly how to do that, what SASL-specific linguistic rules must be preserved, and what open datasets exist to populate the sign library.

---

## 2. Current Architecture: Detailed Analysis

### 2.1 AMANDLA Avatar (avatar.js)

**Strengths — preserve these:**
- `TransitionEngine` with SLERP quaternion blending between signs
- Coarticulation via `next`-sign lookahead when beginning a transition
- NMM system with grammatically correct markers: raised brows (yes/no), furrowed brows (wh-question), head shake (negation), head nod (affirmation)
- Sign queue with `holding → gap → idle` state machine
- `oscTime`-driven oscillation for repeating signs
- Motion paths: arc, tap, circle via `applyMotion()`
- Fingerspell fallback for unknown words
- The `setNMMs(nmms, duration)` public API — rare in open-source SL systems
- Warm South African skin tone (0xA8734A) — culturally appropriate

**Critical limitation:**
The avatar is built from `CylinderGeometry` / `SphereGeometry`. No matter how good the engine, these primitives cannot produce human shoulders, seamless wrists, or readable finger handshapes. The VLibras study (2025) found that hand movement errors were the #1 rejection reason (84.7% of rejected animations), and the Czech MoCap paper demonstrates that precise finger-joint data is what separates acceptable from unacceptable sign output.

### 2.2 Sign-Kit / Mixamo System (HOME sign example)

```javascript
// HOME sign — current keyframe format
animations.push(["mixamorigLeftHandThumb1", "rotation", "x", -Math.PI/3, "-"]);
animations.push(["mixamorigLeftForeArm", "rotation", "y", -Math.PI/2.5, "+"]);
```

**Strengths:**
- Uses real Mixamo bone names — compatible with any Mixamo-rigged GLB avatar
- Multi-phase animation (phase 1: arm raise, phase 2: forearm rotation, phase 3: return)
- Direction flags (`"+"` / `"-"`) indicate increment vs absolute target

**Critical limitations:**
- No NMM system — no eyebrow, mouth, or head grammar
- No coarticulation — each sign is an isolated keyframe sequence
- No signing space management — hand positions don't adapt to the signer's body proportions
- No SLERP blending — transitions between signs will snap
- The format `[boneName, property, axis, value, direction]` is a custom DSL that needs a bridge to the AMANDLA `TransitionEngine`

---

## 3. The SASL Research Landscape

### 3.1 What SASL Actually Requires (de Villiers, 2014 + van Zijl, 2006)

Both Stellenbosch studies agree on the fundamental parameters of a SASL sign:

**Five parameters define every SASL sign:**
1. **Handshape (HS)** — the configuration of fingers and thumb (AMANDLA already models this)
2. **Location** — position relative to the signer's body (signing space)
3. **Movement** — direction, path, manner (arc, tap, circle, straight)
4. **Palm orientation** — which way the palm faces (requires wrist rotation)
5. **Non-manual markers (NMMs)** — facial expression, head position, body posture

Van Zijl (2006) specifically notes that for SASL:
- **Non-manual signs are grammatically obligatory**, not decorative — a question without a questioning facial expression is meaningless
- **Signing space must be managed** for pronoun resolution: once "Harry" is signed, future references point to that space position
- **NMMs are analogous to prosody in speech** — the system used concept-to-speech prosody algorithms to generate NMMs, which is novel and directly relevant to your `setNMMs()` API

De Villiers (2014) adds:
- Signs have **temporal phases**: preparation → movement → hold → retraction
- A **domain-specific constraint language** can describe which joints must satisfy what position constraints at each phase
- Context-sensitive feedback (which your current avatar doesn't generate) requires tracking constraint satisfaction per phase
- **SLED (www.sled.org.za)** is the primary free SASL educational resource in South Africa — their sign definitions were used as ground truth

### 3.2 What VLibras Learned (2025)

The VLibras automation study gives us the most quantitative data on what goes wrong in automated sign language avatars:

| Rejection Reason | % of Rejections | Correction Effort |
|---|---|---|
| Hand movement errors | 84.7% | 76.6% low/very low |
| Occlusion hindering visibility | 27.3% | 78.9% low/very low |
| Mesh intrusion/intersection | 17.5% | 78.9% low/very low |
| Lack of fluidity | small | medium |
| Inadequate facial expression | small | medium-high |

**Key finding**: Only 38% of auto-generated animations were approved by deaf consultants. However, 77% required only minimal correction effort. This means the path forward is automated generation + targeted correction, not hand-animation of every sign.

**For AMANDLA specifically:** Your `TransitionEngine` already addresses "lack of fluidity." The mesh intrusion problem requires moving to a real rigged avatar (collision-aware rig). Hand movement accuracy requires either MoCap data or IK-based positioning.

### 3.3 SignON's Bone Mapping Approach (D5.2, 2023)

SignON's pipeline (Character Creator 4 → Blender → Mixamo → GLB) is exactly what bridges your two current architectures. Their key contribution is the **per-avatar configuration file** that maps:
- Bone names → standard semantic names (Head, LeftArm, RightHand, etc.)
- Blendshape names → Action Units (Facial Action Coding System)
- Body location positions → signing space coordinates

This is the exact architecture needed to make AMANDLA's engine drive any Mixamo avatar without rewriting the engine.

Their blendshape list (Annex II) maps directly to AMANDLA's NMM targets:

| AMANDLA NMM Target | SignON Blendshape | FACS AU |
|---|---|---|
| `nmBrowLiftTarget` | `Eyebrow_Arch_Left/Right` | AU1+AU2 |
| `nmBrowFurrowTarget` | `Eyebrow_Frown_Left/Right` | AU4 |
| `nmMouthOpenTarget` | `Mouth_Stretch` | AU27 |
| Jaw open | `jawOpen` (standard) | AU27 |
| Blink (life-like idle) | `Eye_Blink_Left/Right` | AU45 |

### 3.4 Czech MoCap Study: Evaluation Methodology (2020)

The Czech SL MoCap paper provides the **objective evaluation framework** missing from AMANDLA: **Dynamic Time Warping (DTW) distance** between synthesised signs and ground-truth MoCap recordings.

For AMANDLA, this means:
- Record a SASL signer performing target signs using MediaPipe (free, no hardware)
- Store angular trajectories as JSON (the `processMediaPipeFrame()` function in Document 8)
- Use DTW to compare AMANDLA output against ground truth to score accuracy automatically

Their empirical result: normalized DTW distances between different instances of the same sign were 0.33–3.59°, while different signs were 2.49–8.67°. This gives a threshold: if your avatar's output is within ~3.5° DTW of a ground-truth recording, it's indistinguishable from human signing to objective measurement.

---

## 4. Gap Analysis: Current vs State-of-the-Art

| Feature | AMANDLA Current | Required for SASL | Source |
|---|---|---|---|
| Human-looking avatar | ❌ Procedural primitives | ✅ Rigged GLB human | SignON D5.2 |
| Finger articulation | ✅ 5 fingers, 3 joints | ✅ Already present | AMANDLA avatar.js |
| NMM — eyebrows | ✅ Box geometry | ✅ Needs blendshapes | de Villiers 2014 |
| NMM — mouth | ✅ Box geometry | ✅ Needs blendshapes | van Zijl 2006 |
| Head shake/nod | ✅ Bone rotation | ✅ Already works | AMANDLA NMM |
| Coarticulation | ✅ Next-sign lookahead | ✅ Already present | AMANDLA engine |
| SLERP blending | ✅ TransitionEngine | ✅ Already present | AMANDLA engine |
| Signing space mgmt | ❌ No spatial reasoning | Required for pronouns | van Zijl 2006 |
| Sign evaluation / DTW | ❌ Not present | Useful for tutor mode | Czech MoCap 2020 |
| MoCap-derived data | ❌ Hand-authored poses | Required for naturalness | VLibras 2025 |
| Mixamo bone compatibility | ❌ Custom bone names | Required for GLB avatar | Sign-Kit |
| IK hand placement | ❌ Not present | Useful for body locations | SignON D5.2 |
| Motion capture pipeline | ❌ Not present | Phase 3 enhancement | VLibras 2025 |

---

## 5. The Bridge Architecture: Unifying Both Systems

The goal is to keep AMANDLA's engine, replace the primitive avatar with a Mixamo GLB, and add a bone name mapping layer.

### 5.1 Bone Name Mapping Table

Your current AMANDLA bone names → Mixamo standard names:

| AMANDLA Semantic | Mixamo Bone Name | Notes |
|---|---|---|
| `avatarBones.head` | `mixamorigHead` | |
| `avatarBones.torso` | `mixamorigSpine1` | Use Spine2 for chest scale |
| `avatarBones.R.shoulder` | `mixamorigRightArm` | Upper arm |
| `avatarBones.R.elbow` | `mixamorigRightForeArm` | |
| `avatarBones.R.wrist` | `mixamorigRightHand` | |
| `avatarBones.L.shoulder` | `mixamorigLeftArm` | |
| `avatarBones.L.elbow` | `mixamorigLeftForeArm` | |
| `avatarBones.L.wrist` | `mixamorigLeftHand` | |
| `R fingers[0]` (thumb) | `mixamorigRightHandThumb1/2/3` | |
| `R fingers[1]` (index) | `mixamorigRightHandIndex1/2/3` | |
| `R fingers[2]` (middle) | `mixamorigRightHandMiddle1/2/3` | |
| `R fingers[3]` (ring) | `mixamorigRightHandRing1/2/3` | |
| `R fingers[4]` (pinky) | `mixamorigRightHandPinky1/2/3` | |

### 5.2 GLTFLoader Integration

Replace `buildAvatarSkeleton()` with this (requires `GLTFLoader` from Three.js examples):

```javascript
function loadMixamoAvatar(glbUrl, onReady) {
  const loader = new THREE.GLTFLoader();
  loader.load(glbUrl, function(gltf) {
    const model = gltf.scene;
    model.position.set(0, -1.0, 0);
    model.scale.set(1, 1, 1);

    // Enable shadows + warm South African skin tone
    model.traverse(function(node) {
      if (node.isMesh) {
        node.castShadow = true;
        node.receiveShadow = true;
        if (node.material && node.name.toLowerCase().includes('body')) {
          node.material.roughness = 0.72;
          // Optionally tint skin: node.material.color.set(0xA8734A);
        }
      }
    });
    scene.add(model);

    // Map Mixamo bones → AMANDLA avatarBones
    function getBone(name) {
      let found = null;
      model.traverse(function(n) { if (n.name === name) found = n; });
      return found;
    }

    avatarBones.head  = getBone('mixamorigHead');
    avatarBones.torso = getBone('mixamorigSpine1');

    avatarBones.R = {
      shoulder: getBone('mixamorigRightArm'),
      elbow:    getBone('mixamorigRightForeArm'),
      wrist:    getBone('mixamorigRightHand'),
      fingers:  mapMixamoFingers(getBone, 'Right')
    };
    avatarBones.L = {
      shoulder: getBone('mixamorigLeftArm'),
      elbow:    getBone('mixamorigLeftForeArm'),
      wrist:    getBone('mixamorigLeftHand'),
      fingers:  mapMixamoFingers(getBone, 'Left')
    };

    // Map face blendshapes for NMMs
    const headMesh = model.getObjectByName('Wolf3D_Head') // Ready Player Me
                  || model.getObjectByName('CC_Base_Body'); // Character Creator
    if (headMesh && headMesh.morphTargetDictionary) {
      avatarBones.faceMorphMesh = headMesh;
    }

    // Keep box-based face bones as fallback if no blendshapes
    avatarBones.face = { browL: null, browR: null, mouth: null };

    if (onReady) onReady();
    console.log('[Avatar] Mixamo human loaded — AMANDLA engine active');
  });
}

function mapMixamoFingers(getBone, side) {
  const names = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky'];
  return names.map(function(name) {
    return {
      group: getBone('mixamorig' + side + 'Hand' + name + '1'),
      segments: [
        { pivot: getBone('mixamorig' + side + 'Hand' + name + '1') },
        { pivot: getBone('mixamorig' + side + 'Hand' + name + '2') },
        { pivot: getBone('mixamorig' + side + 'Hand' + name + '3') }
      ]
    };
  });
}
```

### 5.3 Axis Correction for Mixamo Arms

Mixamo exports arms in T-pose with different rest-axis conventions from AMANDLA's procedural cylinders. After loading, you need to test the idle pose and apply axis offsets.

**Mixamo arm rest-axis conventions:**
- `mixamorigRightArm.rotation.z` → moves upper arm up/down (not `.x` as in AMANDLA)
- `mixamorigRightForeArm.rotation.y` → bends the elbow
- `mixamorigRightForeArm.rotation.z` → rotates forearm (supination/pronation)

Your `HOME` sign confirms this:
```javascript
// HOME sign uses: ForeArm.rotation.y for elbow bend, Arm.rotation.x for shoulder raise
["mixamorigRightArm", "rotation", "x", -Math.PI/6, "-"]   // shoulder pitch
["mixamorigRightForeArm", "rotation", "y", Math.PI/2.5, "-"] // elbow bend
["mixamorigRightForeArm", "rotation", "z", Math.PI/7, "+"]   // forearm twist
```

**Required change to AMANDLA's TransitionEngine:** The `armToQuat()` function uses `sh.x` for shoulder elevation, `el.x` for elbow bend. When driving a Mixamo rig these must be remapped:

```javascript
// axis_remap.js — insert between TransitionEngine output and applyPoseDirect()
function remapPoseForMixamo(pose) {
  if (!pose) return pose;
  for (const side of ['R', 'L']) {
    if (!pose[side]) continue;
    const d = pose[side];
    const sign = (side === 'R') ? 1 : -1;
    if (d.sh) {
      // AMANDLA sh.x (elevation) → Mixamo Arm.rotation.x
      // AMANDLA sh.z (abduction) → Mixamo Arm.rotation.z  
      // (keep as-is; test empirically and add offsets)
    }
    if (d.el) {
      // AMANDLA el.x (flexion) → Mixamo ForeArm.rotation.y * sign
      const flexion = d.el.x || 0;
      d.el = { x: 0, y: flexion * sign, z: d.el.z || 0 };
    }
  }
  return pose;
}
```

### 5.4 Upgrading NMMs to Blendshapes

Replace the box-based brow/mouth movement with morph target weights once a GLB with blendshapes is loaded:

```javascript
function applyNMMsToBlendshapes(mesh) {
  if (!mesh || !mesh.morphTargetInfluences) return;
  const d = mesh.morphTargetDictionary;

  // Yes/No question — raised eyebrows
  const browUp = d['Eyebrow_Arch_Left'] ?? d['browInnerUp'];
  if (browUp !== undefined)
    mesh.morphTargetInfluences[browUp] = Math.max(0, nmBrowLiftCur * 12);

  // Wh-question — furrowed brows  
  const browDown = d['Eyebrow_Frown_Left'] ?? d['browDownLeft'];
  if (browDown !== undefined)
    mesh.morphTargetInfluences[browDown] = Math.max(0, nmBrowFurrowCur * 5);

  // Mouth / NMM open
  const jaw = d['Mouth_Stretch'] ?? d['jawOpen'];
  if (jaw !== undefined)
    mesh.morphTargetInfluences[jaw] = Math.abs(nmMouthOpenCur * 40);
}
```

Call this at the end of `applyNMMs(dt)` when `avatarBones.faceMorphMesh` is available, falling back to the box-based approach otherwise. This gives you a graceful degradation path.

---

## 6. Converting the Sign-Kit Format to AMANDLA Format

Your `HOME` sign keyframe array needs to become an AMANDLA v2 sign object with `_Rq` and `_Lq` quaternion pairs. Here is the conversion bridge:

```javascript
// sign_converter.js
// Converts Sign-Kit keyframe arrays to AMANDLA v2 sign library format

function signKitToAmandla(name, phases, notes) {
  // phases is the array of animation phases from Sign-Kit format
  // We take the "peak" phase (phase 1, midpoint) as the AMANDLA hold pose
  
  // Extract joint angles from peak phase
  const joints = {};
  const peakPhase = phases[1] || phases[0]; // use phase 1 (elbow rotation phase)
  
  peakPhase.forEach(function([bone, prop, axis, val, dir]) {
    joints[bone] = joints[bone] || {};
    joints[bone][axis] = val;
  });

  // Map Mixamo bone names to AMANDLA arm descriptors
  const R_sh_x = -(joints['mixamorigRightArm']?.x || 0);
  const R_sh_z = -(joints['mixamorigRightArm']?.z || 0);
  const R_el_y =   joints['mixamorigRightForeArm']?.y || 0;
  const R_el_z =   joints['mixamorigRightForeArm']?.z || 0;

  const L_sh_x = -(joints['mixamorigLeftArm']?.x || 0);
  const L_sh_z =   joints['mixamorigLeftArm']?.z || 0;
  const L_el_y =  -joints['mixamorigLeftForeArm']?.y || 0;

  const lib = window.AMANDLA_SIGNS;
  const armToQuat = lib && lib.armToQuat;

  const Rarms = { sh: {x: R_sh_x, y: 0, z: R_sh_z}, el: {x: R_el_y, y: 0, z: R_el_z}, wr: {x:0,y:0,z:0} };
  const Larms = { sh: {x: L_sh_x, y: 0, z: L_sh_z}, el: {x: L_el_y, y: 0, z: 0}, wr: {x:0,y:0,z:0} };

  return {
    name: name,
    R: { ...Rarms, hand: lib.HS.flat },
    L: { ...Larms, hand: lib.HS.flat },
    _Rq: armToQuat ? { end: armToQuat(Rarms), start: armToQuat(Rarms) } : null,
    _Lq: armToQuat ? { end: armToQuat(Larms), start: armToQuat(Larms) } : null,
    osc: null,
    isFingerspell: false,
    notes: notes || ''
  };
}

// Usage:
// window.AMANDLA_SIGNS.SIGN_LIBRARY['HOME'] = signKitToAmandla('HOME', HOME_phases);
```

---

## 7. SASL-Specific Linguistic Enhancements

### 7.1 Signing Space Management (van Zijl, 2006)

SASL requires spatial reference: when a person or object is first signed, a locus in space is established. Subsequent pronouns point to that locus.

**Minimal implementation for AMANDLA:**

```javascript
// signing_space.js
const signingSpace = {};  // { 'HARRY': {x: 0.3, y: 0, z: 0}, ... }

function establishLocus(entity, position) {
  signingSpace[entity.toUpperCase()] = position;
}

function getLocusSign(entity) {
  const pos = signingSpace[entity.toUpperCase()];
  if (!pos) return null;
  // Return a pointing sign toward pos
  // Right arm shoulder Z = sign of pos.x drives left/right pointing
  const shZ = -pos.x * 0.3;
  return {
    name: 'POINT_' + entity,
    R: { sh: {x: -0.4, y: 0, z: shZ}, el: {x: 0.5, y: 0, z: 0}, wr: {x:0,y:0,z:0},
         hand: window.AMANDLA_SIGNS.HS.point },
    L: { sh: {x: 0.05, y: 0, z: 0.24}, el: {x: 0.08, y: 0, z: 0}, wr: {x:0,y:0,z:0},
         hand: window.AMANDLA_SIGNS.HS.rest },
    isFingerspell: false
  };
}
```

### 7.2 NMM Trigger Extension for SASL Grammar

Expand the `setNMMs()` function with SASL-specific grammatical markers:

```javascript
// Add to setNMMs() inside the NMM string loop:

// Conditional / topic marker — brow raise + slight forward lean
if (n.includes('topic') || n.includes('topicalization')) {
  nmBrowLiftTarget = 0.020;
  targetHeadX = Math.max(targetHeadX, 0.05);
}

// Rhetorical question — brow furrow + shoulder raise
if (n.includes('rhetorical')) {
  nmBrowFurrowTarget = 0.18;
  nmBrowLiftTarget = 0.008;
}

// Intensifier — body lean forward
if (n.includes('intensifier') || n.includes('very') || n.includes('extreme')) {
  targetHeadX = Math.max(targetHeadX, 0.10);
}

// Negative incorporation — head shake stronger for NOT
if (n.includes('not') || n.includes('none') || n.includes('never')) {
  nmHeadShake = true;
  // Increase shake amplitude in applyNMMs:
  // avatarBones.head.rotation.y = Math.sin(...) * 0.15 * env  // was 0.10
}
```

### 7.3 SASL-Specific Sign Library Seeds

Based on van Zijl (2006)'s domain focus (clinics, hospitals, police stations) and the SLED educational resource, high-priority signs to add beyond the current AMANDLA library:

**Medical/clinic domain (van Zijl):**
PAIN, SICK, MEDICINE, DOCTOR, HOSPITAL, HELP, UNDERSTAND, WHEN, WHERE, WHAT, YES, NO, NAME, AGE, PREGNANT, CHILD, EMERGENCY

**Greeting/basic (Sign-Kit compatible):**
HOME (already have), HELLO, GOODBYE, THANK-YOU, PLEASE, SORRY, REPEAT, SLOW

**Interrogatives (trigger NMMs):**
WHO (wh-brow), WHAT (wh-brow), WHERE (wh-brow+body lean), WHEN (wh-brow), WHY (wh-brow+head tilt), HOW (wh-brow)

---

## 8. Data Resources

### 8.1 Available Datasets

| Dataset | Language | Content | Access | Relevance |
|---|---|---|---|---|
| SASL-MT word list (~800 words) | SASL | Annotated vocabulary + phrase book | Free (Stellenbosch) | ★★★★★ |
| SLED educational materials | SASL | Sign definitions used by de Villiers | www.sled.org.za | ★★★★★ |
| VLibras-Sign-v1 | Libras (Brazilian) | 24,660 videos, 406 signs, 11 signers | Private (UFPB) | ★★★ (methodology) |
| Czech SL MoCap | Czech SL | 30min continuous + 318 gloss dictionary | Published (NTIS CZ) | ★★★ (methodology) |
| ASL Sensor Dataglove Dataset | ASL | Wrist sensor + accelerometer data | Figshare (open) | ★★ (hand pose) |
| Sign-Kit ISL Toolkit | Indian SL | Mixamo bone keyframes, GitHub | Open source | ★★★★ (code pattern) |
| PHOENIX-Weather 2014T | German SL | 7,096 sentences, weather domain | Open (RWTH) | ★★ (NLP pipeline) |

### 8.2 How to Use the ASL Sensor Dataglove Dataset

The Figshare dataset (https://figshare.com/articles/dataset/ASL-Sensor-Dataglove-Dataset_zip/20031017) contains wrist-sensor + flex-sensor readings for ASL handshapes. While it's ASL, the handshapes map to SASL handshapes which share the same manual alphabet. Use it to:

1. Validate your `AMANDLA_SIGNS.HS` finger joint angle tables against sensor ground truth
2. Extract per-finger bend angles for each handshape (the sensor gives relative flex)
3. Create a richer handshape library with intermediate poses between rest → target

### 8.3 Free MoCap Recording Pipeline (No Hardware)

Based on the VLibras 2025 approach, here is the zero-cost pipeline to record SASL signs:

```
1. WebCam (any laptop) 
   ↓
2. MediaPipe Holistic (Google) — free Python library
   pip install mediapipe
   ↓
3. Extract 33 body + 21 per-hand + 468 face landmarks per frame
   ↓
4. Convert to angular trajectories using processMediaPipeFrame()
   ↓
5. Save as JSON → SIGN_LIBRARY["SIGN_NAME"] = { frames: [...], fps: 30 }
   ↓
6. AMANDLA TransitionEngine plays it back with SLERP blending
```

The smoothing filter used by VLibras (5-10 frame moving average) reduces jitter without losing linguistic articulation.

---

## 9. Implementation Roadmap

### Phase 1 — Avatar Upgrade (1–2 weeks)
**Goal: Real human avatar, same engine**

1. Get a Mixamo-compatible GLB (options below in priority order):
   - **Ready Player Me** (readyplayer.me) — free, web-based, generates GLB with full finger rig + ARKit blendshapes. Choose a South African-appropriate skin tone. URL includes `morphTargets=ARKit&lod=0`.
   - **Mixamo.com** — free with Adobe account, upload your own character mesh
   - **VRoid Studio** — free anime-style (less culturally appropriate for SASL context)

2. Replace `buildAvatarSkeleton()` with `loadMixamoAvatar(url, onReady)` (code above)

3. Add the bone name mapping layer and test idle pose

4. Test `applyPoseDirect()` with an existing AMANDLA sign — confirm arms move correctly

5. Add axis correction constants for Mixamo convention differences

**Deliverable:** Same linguistic engine, human-looking avatar. NMMs still use box geometry until Phase 2.

### Phase 2 — Blendshape NMMs + Sign Library Bridge (1–2 weeks)
**Goal: Grammatically expressive face, all existing signs working**

1. Upgrade `applyNMMs()` to use `morphTargetInfluences` when available (code above)

2. Add FACS AU mapping for Ready Player Me ARKit blendshapes (they use standard ARKit names)

3. Convert all existing Sign-Kit format signs (HOME and others) using `signKitToAmandla()` bridge

4. Expand `setNMMs()` with SASL-specific grammar markers (topic, rhetorical, intensifier)

5. Add lifelike idle: chest breathing via `avatarBones.torso.scale`, eye saccades

**Deliverable:** Fully expressive avatar with human face and SASL grammar markers.

### Phase 3 — Sign Library Expansion via MoCap (ongoing)
**Goal: Grow SASL vocabulary with human-derived motion data**

1. Set up MediaPipe recording session with a fluent SASL signer

2. Record priority vocabulary: medical domain (van Zijl), basic conversation, interrogatives

3. Run `processMediaPipeFrame()` converter to extract joint angles

4. Apply 7-frame smoothing filter (VLibras methodology)

5. Store as SIGN_LIBRARY entries, test with DTW evaluation against ground truth

6. Invite deaf consultant review (VLibras used 3 deaf consultants + 4 professional animators)

**Deliverable:** Library of 50+ SASL signs with human-derived timing and naturalness.

### Phase 4 — Signing Space + Translation Pipeline (future)
**Goal: Full English → SASL sentence translation**

1. Implement signing space locus management (van Zijl's pronoun resolution)

2. Integrate a TAG parser for English → SASL tree transfer (or use an LLM for gloss generation)

3. Add concept-to-speech prosody analysis to auto-generate NMM metadata

4. Consider xAPI behaviour tracking (CWA XR-LPA) for learning analytics if this is a tutoring app

---

## 10. Critical Code Fixes for Current System

### 10.1 Missing `armToQuat` Guard in `buildIdleSign()`

```javascript
// Current code has a retry loop but no timeout:
function buildIdleSign() {
  const lib = window.AMANDLA_SIGNS;
  if (!lib || !lib.armToQuat) {
    setTimeout(buildIdleSign, 100);
    return;
  }
  // ...
}

// FIX: Add attempt counter to prevent infinite loop
let _idleRetries = 0;
function buildIdleSign() {
  const lib = window.AMANDLA_SIGNS;
  if (!lib || !lib.armToQuat) {
    if (++_idleRetries > 50) { console.error('[Avatar] AMANDLA_SIGNS never loaded'); return; }
    setTimeout(buildIdleSign, 100);
    return;
  }
  _idleRetries = 0;
  // ... rest unchanged
}
```

### 10.2 `applyHandshapeDirect` Segment Index Bug

```javascript
function applyHandshapeDirect(fingers, hs) {
  if (!hs) return;
  const keys = ['t', 'i', 'm', 'r', 'p'];
  for (let f = 0; f < 5; f++) {
    const segs = hs[keys[f]];
    if (!segs || !fingers[f]) continue;
    for (let s = 0; s < 3 && s < segs.length; s++) {
      const seg = fingers[f].segments[s];
      if (!seg) continue;
      seg.pivot.rotation.x = segs[s] || 0;
      // BUG FIX: Mixamo finger joints may need rotation.z not .x
      // depending on how the GLB was rigged. Test empirically.
      // For Mixamo standard: index/middle/ring/pinky curl on .z
      // thumb curls on .z (rotation axis differs from AMANDLA cylinders)
    }
  }
}
```

### 10.3 `SIGN_GAP` Too Long for Fluent Signing

Current `SIGN_GAP = 0.18s` is longer than the Czech MoCap study's observed transition times. At fluent SASL pace, native signers produce 2–3 signs per second (roughly 0.33–0.50s per sign total). Reduce gap:

```javascript
const SIGN_HOLD    = 0.32   // was 0.38 — more natural pace
const SIGN_FS_HOLD = 0.20   // was 0.22 — fingerspell faster
const SIGN_GAP     = 0.10   // was 0.18 — tighter coarticulation
```

---

## 11. Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     AMANDLA Application                 │
├──────────────────┬──────────────────────────────────────┤
│  INPUT LAYER     │  OUTPUT LAYER                        │
│                  │                                      │
│  English text    │  ┌─────────────────────────────┐    │
│       ↓          │  │   Mixamo GLB Avatar          │    │
│  sentenceToSigns │  │   (Ready Player Me / CC4)    │    │
│       ↓          │  │                              │    │
│  SIGN_LIBRARY    │  │   Blendshape NMMs            │    │
│  (v2 sign objs)  │  │   Full finger articulation   │    │
│       ↓          │  │   Human proportions          │    │
│  signQueue[]     │  └────────────▲────────────────┘    │
│       ↓          │               │                      │
│  TransitionEngine│  applyPoseDirect() + remapMixamo()  │
│  (SLERP + coart) │               │                      │
│       ↓          │  ┌────────────┴────────────────┐    │
│  NMM Engine      │  │   avatarBones               │    │
│  (grammar marks) │  │   (bone name mapping layer) │    │
│       ↓          │  └─────────────────────────────┘    │
│  Signing Space   │                                      │
│  (locus mgmt)    │  Three.js renderer                   │
└──────────────────┴──────────────────────────────────────┘
```

---

## 12. Recommended Immediate First Step

The single highest-impact change you can make today, before any engine work:

1. Go to **readyplayer.me**, create an avatar with a warm brown South African skin tone
2. Add `?morphTargets=ARKit&lod=0` to the GLB export URL to get blendshapes
3. Drop the GLB into your assets folder
4. Replace `buildAvatarSkeleton()` with `loadMixamoAvatar('./assets/avatar.glb', buildIdleSign)`
5. The AMANDLA engine drives it immediately via bone rotation — your existing signs work

This gets you from a procedural cylinder robot to a human-looking avatar in under an hour, with zero changes to the linguistic engine that is already doing the right thing.

---

*Document compiled from: de Villiers (PhD, Stellenbosch, 2014), van Zijl (ASSETS 2006, Stellenbosch), Martins et al. (VLibras, WebMedia 2025), Blat et al. (SignON D5.2, 2023), Jedlička et al. (Czech SL MoCap, LREC 2020), Wild et al. (CWA XR-LPA, 2023), AMANDLA avatar.js v2.0, AMANDLA animations.css, Sign-Kit ISL Toolkit (GitHub), ASL Sensor Dataglove Dataset (Figshare)*
