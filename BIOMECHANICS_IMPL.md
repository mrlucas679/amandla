# 




AMANDLA — Biomechanics Implementation Tracker

> Source: "Sign Language Animation — Full Biomechanics Research" (HTML reference doc)
> Priority order per research Section 13: forearm pronation → wrist orientation →
> handshape accuracy → head NMMs → eyebrow NMMs → coarticulation →
> scapulohumeral rhythm → facial morphemes → idle motion → body shifting.

---

## STATUS KEY

- [X]  Done
- [ ]  Not yet implemented

- [~] Partial / approximated

---

## 1. Handshapes (Section 02 — The Hand, 21 DOF)

### New HS presets added (Section 02 Table)

- [X]  `bhand` — B: all fingers flat/straight, thumb folded across palm
- [X]  `dhand` — D: index extended, others curve to touch thumb tip
- [X]  `ehand` — E: all fingers tightly bent, thumb tucked under
- [X]  `ihand` — I: only pinky extended, others in fist
- [X]  `mhand` — middle-finger shape: middle extended, others curled (SICK, MEDICINE)
- [X]  `nhand` — N: index+middle curled over thumb (NURSE variant)
- [X]  `ohand` — O: all fingers curved to meet thumb, full cup

### MCP spread (abduction/adduction)

- [X]  `spread` property added to all HS presets
- [X]  `open5` fan-spread: [0.22, 0.08, -0.08, -0.22]
- [X]  `vhand` V-spread: [0.20, -0.20, 0, 0]
- [X]  `flat` natural spread: [0.10, 0.03, -0.03, -0.10]
- [X]  `lhand` L-spread (index+thumb): [0.30, 0, 0, 0]
- [X]  `uhand` U-spread: [0.12, -0.12, 0, 0]
- [X]  `claw` claw spread: [0.15, 0.05, -0.05, -0.15]

### DIP–PIP tendon coupling (Section 02 — "DIP ≈ 0.67 × PIP")

- [X]  Enforced in `lerpFingerCurl` — DIP is clamped to max 0.67 × PIP after SLERP

### Sign handshape corrections (Section 11 — SASL Medical Table)

- [X]  SICK: `fhand` → `mhand` (research: "Middle finger extended, forehead/stomach")
- [X]  MEDICINE: `whand` → `mhand` (research: "Middle finger, circle in palm of weak hand")
- [X]  DOCTOR description updated (research: D or H shape on inside wrist)

---

## 2. Animation Mathematics (Section 07)

### Easing — Minimum Jerk Trajectory (Section 07.6)

- [X]  `Easing.minimumJerk` added: `10t³ − 15t⁴ + 6t⁵` (quintic smoothstep)
- [X]  TransitionEngine now uses `minimumJerk` as default (was `easeInOutCubic`)
- [X]  Fingerspelling still uses `easeOutQuad` (snappy)
- [X]  Per-sign easing override — `nmm.ease` field on each sign; TransitionEngine.begin() uses it when set

### Quaternion SLERP (Section 07.2)

- [X]  Already implemented in v2 — SLERP, eulerToQuat, quatToEuler, normaliseQuat
- [X]  Shortest-arc quaternion negation already handled

### Joint constraints (Section 07.5, Section 12)

- [X]  JOINT_LIMITS table already covers shoulder, elbow, forearm, wrist, finger joints

- [~] Swing-twist decomposition not implemented (uses simpler clamp approach)

### Forward Kinematics (Section 07.3)

- [X]  TalkingHead library handles FK internally through bone hierarchy

### Inverse Kinematics (Section 07.4)

- [~] IK for contact signs (touch-cheek, touch-wrist) not yet implemented

- [X]  Two-joint IK (law-of-cosines) — `twoJointIK(upperLen, lowerLen, targetDist)` added to signs_library.js and exported

---

## 3. Non-Manual Markers — NMMs (Section 06)

### NMM metadata per sign (Section 06 — Eyebrow Grammar, Head Motion)

- [X]  `nmm` field added to `sign()` function (15th parameter, optional)
- [X]  NMM added to: YES, NO, NOT, CAN NOT, HOW ARE YOU, I'M FINE, HELLO, GOODBYE,
  THANK YOU, SORRY, HELP, WHO, WHAT, WHERE, WHEN, WHY, HOW, WHICH,
  PAIN, HURT, SICK, EMERGENCY, HAPPY, SAD, ANGRY, SCARED, UNDERSTAND,
  WAIT, STOP, and all new signs
- [X]  NMM added to remaining signs: 26 key non-neutral signs updated (LOVE, NOT, WORRIED, CONFUSED, GOOD, BAD, etc.); all others default to neutral via sign() fallback

# 

## 

Avatar NMM grammar layer (Section 06 — Section 05)

- [X]  `_applyNMMFromSign()` function added to avatar.js
- [X]  `_applyNMMForSequence()` scans full sequence for grammar patterns
- [X]  Head nod → NMM_NOD gesture template registered (Neck bone)
- [X]  Head shake → NMM_SHAKE gesture template registered
- [X]  Head tilt → NMM_TILT gesture template registered
- [X]  Brow raised → mood 'happy' (closest TalkingHead approximation)
- [X]  Brow furrowed → mood 'sad' (closest TalkingHead approximation)
- [X]  True FACS AU control (AU1+2 raise, AU4 furrow) — `_initFaceMesh` discovers face mesh via traverse; `_setAU` tweens ARKit blendshapes (browInnerUp, browOuterUp*, browDown*)
- [X]  Mouth morphemes (mm, th, cs, oo, pah) — `_setAU` maps nmm.mouth values to mouthClose / mouthFunnel / mouthOpen / mouthStretch; called from `_applyNMMFromSign`

### Eyebrow grammar by clause type (Section 06 Table)

- [X]  WH-questions (WHO/WHAT/WHERE/WHEN/WHY/HOW/WHICH) → furrowed brows + tilt
- [X]  Y/N questions detected via HOW ARE YOU, HELP sequence → raised brows + tilt
- [X]  Negation (NOT, CAN NOT, NO in sequence) → head shake
- [X]  Affirmation (YES) → head nod
- [X]  Conditional ("if" clauses) → forward head lean — `_NMM_LEAN` template + text detection in `_applyNMMForSequence`

---

## 4. MCP Spread Applied in avatar.js (Section 02)

- [X]  `_handshapeToRotations()` applies `hand.spread[i]` to MCP bone z-rotation
- [X]  Spread index map: i=0, m=1, r=2, p=3

---

## 5. Movement Paths / Oscillations (Section 08)

- [X]  `osc` field per sign drives oscillation layer in animation loop
- [X]  Path types: linear (travel signs), arc (COME/GIVE), oscillating (YES/NO)
- [X]  Arc trajectory for travel signs — `phases.arc:true` on sign triggers 3-point arc (START→ARC_MID→END); ARC_MID computed from lerp+elbow lift; COME and GIVE enabled
- [X]  Circular path for WORLD/YEAR signs — `_runCircularOscillation` drives sin/cos quadrature on two bone axes; WORLD (`circ:{j:'R_sh',ax1:'x',ax2:'z',amp:0.25,freq:1.5}`) and YEAR (`circ:{j:'R_el',ax1:'x',ax2:'y',amp:0.28,freq:1.2}`) added to signs_library.js; word mappings added to WORD_MAP and sign_maps.py

---

## 6. Sign Phonology — Four Parameters (Section 09)

### Coarticulation (Section 09)

- [X]  Already implemented via `blendStart` and TRANSITION_HINTS in v2
- [X]  Default 30% overlap (blendStart=0.70)

### Sign Phases (Section 09)

- [X]  Preparation + nucleus + retraction approximated via transition timing
- [X]  Explicit three-phase model — `_playSingleSign` restructured as named Preparation/Nucleus/Retraction phases; per-sign timing via `nmm.phases.{ prep, nucleus, retract }`; YES/NO/AMBULANCE/EMERGENCY tuned

---

## 7. New Signs Added

### Disability / Communication

- [X]  `DEAF` — index from ear to chin
- [X]  `HEARING` — index taps near ear
- [X]  `BLIND` — V-hand at eyes then drops
- [X]  `DISABILITY` — D-hand sweeps forward from shoulder

---

## 8. Database (Section — Record-Keeping)

- [X]  `sign_count INTEGER DEFAULT 0` column added to conversations table
- [X]  `animation_version TEXT DEFAULT 'v2'` column added
- [X]  Auto-migration on startup (ALTER TABLE IF NOT EXISTS equivalent)
- [X]  `sign_count` auto-computed from sasl_gloss word count in `_sync_log_message`
- [X]  New columns returned in `get_session_history` responses

---

## 9. sign_maps.py — Vocabulary Expansion

### Medical vocabulary (Section 11)

- [X]  stethoscope → DOCTOR
- [X]  injection / shot / jab / needle → MEDICINE
- [X]  fever / temperature → SICK
- [X]  cough / coughing → SICK
- [X]  headache → PAIN
- [X]  stomachache / stomach ache → PAIN
- [X]  allergy / allergic → SICK
- [X]  wheelchair → DISABILITY (new)
- [X]  disabled / disability → DISABILITY (new)
- [X]  deaf / deafness → DEAF (new)
- [X]  blind / blindness → BLIND (new)
- [X]  hearing (person) → HEARING (new)

### Body parts

- [X]  head, arm, leg, back, stomach, chest, eye/eyes, ear/ears, tooth/teeth, hand, finger

### Signs / Communication

- [X]  sign language → SIGN
- [X]  interpreter → SIGN (closest available)

---

## 10. Scapulohumeral Rhythm (Section 03)

- [X]  2:1 GH/ST ratio applied — `_registerSASLSigns` post-processes all gesture templates; for each arm elevation >0.20 rad adds `RightShoulder/LeftShoulder.rotation` at 35% of arm elevation; runs before `_remapGestureTemplates` so bone name prefixing carries it through automatically

---

## 11. Idle Motion Layer (Section 10)

- [~] TalkingHead handles breathing, blink, eye contact via `avatarIdleEyeContact`

- [X]  Custom smooth-noise micro-tremor on wrist bones — `_startIdleTremor()` in avatar.js; 12 mrad amp, paused during signing
- [X]  Body micro-sway — sinusoidal Hips/Spine sway (0.4 Hz lateral, 0.25 Hz breathing); runs in same idle RAF loop as tremor

---

## 12. Animation Speed Reference Applied (Section 12)

- [X]  Fingerspelling: 180ms hold, 120ms transition (within research range 150–200ms)
- [X]  Sign nucleus: 600ms hold (within 200–600ms range)
- [X]  Sign gap: 120ms (within research preparation phase 100–200ms)
- [X]  Gesture transition: 200ms (within research 100–200ms range)
- [X]  Coarticulation overlap: 30% (blendStart=0.70)
