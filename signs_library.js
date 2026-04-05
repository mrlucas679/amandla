/**
 * AMANDLA — SASL Sign Language Library  v2.0
 * ============================================
 * Source: Einstein Hands SASL Dictionary (336 pages)
 *         YOLO-v11 ASL research paper (2025)
 *
 * WHAT'S NEW IN v2.0 — THE TRANSITION ENGINE
 * -------------------------------------------
 * The original library stored one static pose per sign. The avatar
 * had no idea how to travel between poses, causing four problems:
 *   1. Hands snapped/jumped between signs (no blending)
 *   2. Paths looked unnatural (linear Euler interpolation)
 *   3. Timing was robotic (constant speed, no ease-in/out)
 *   4. Fingers clipped through each other (no joint limits)
 *
 * v2.0 fixes all four with a layered transition engine:
 *
 *   LAYER 1 — SLERP on quaternions
 *     Joint rotations are stored as {x,y,z,w} quaternions and
 *     blended with spherical linear interpolation. This takes the
 *     shortest arc through rotation space — exactly how a real
 *     wrist moves — and eliminates gimbal lock.
 *
 *   LAYER 2 — Cubic ease-in/out timing
 *     All transitions use a cubic easeInOut curve so the hand
 *     accelerates out of the starting pose and decelerates into
 *     the target, matching how human muscles actually move.
 *
 *   LAYER 3 — Coarticulation overlap
 *     Real signers begin moving toward the next sign before
 *     finishing the current one. The engine starts blending
 *     toward the next pose at 70% through the current sign.
 *     This can be tuned per sign-pair via TRANSITION_HINTS.
 *
 *   LAYER 4 — Anatomical joint limits
 *     After SLERP, every joint is clamped to its physical range
 *     of motion (JOINT_LIMITS table). This prevents fingers from
 *     hyperextending or passing through each other mid-transition.
 *
 * HOW THE ANIMATION LOOP USES THIS FILE
 * --------------------------------------
 * 1. Call sentenceToSigns(text) → array of sign objects
 * 2. Feed each sign to your avatar one by one
 * 3. For each sign, call TransitionEngine.begin(fromSign, toSign)
 * 4. Each frame, call TransitionEngine.tick(deltaTime) → pose
 * 5. Apply pose to your Three.js skeleton bones
 * 6. Oscillation (osc) is applied on top by your animation loop
 *
 * HOW TO ADD A NEW SIGN
 * ---------------------
 * 1. Find the word in the Einstein Hands dictionary
 * 2. Copy the closest existing sign as a template
 * 3. Set startPose = where the hand is at sign onset
 * 4. Set endPose   = where the hand is at sign completion
 *    (for simple signs with no travel, startPose ≈ endPose)
 * 5. Add TRANSITION_HINTS if this sign has unusual coarticulation
 *
 * ROTATION VALUES (radians — same as v1):
 * ----------------------------------------
 * sh.x negative = arm raises forward/up
 * sh.z negative = right arm abducts outward (away from body)
 * sh.z positive = left arm abducts outward
 * el.x negative = elbow bends (forearm comes up)
 * wr.x = wrist flex/extend
 * wr.y = wrist rotate (pronation/supination)
 */

'use strict';

// ═══════════════════════════════════════════════════════════════════
// SECTION 1 — HANDSHAPE PRESETS
// Each = { i, m, r, p, t } finger curl values
// [mcp, pip, dip] — 0 = straight, ~1.5 = fully curled
// ═══════════════════════════════════════════════════════════════════
const HS = {
  open5:  { i:[0.08,0.05,0.03], m:[0.08,0.05,0.03], r:[0.08,0.05,0.03], p:[0.08,0.05,0.03], t:[0.05,0.05] },
  flat:   { i:[0.10,0.06,0.04], m:[0.10,0.06,0.04], r:[0.10,0.06,0.04], p:[0.10,0.06,0.04], t:[0.28,0.40] },
  fist_A: { i:[1.15,1.55,1.05], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[-0.15,0.10] },
  fist_S: { i:[1.15,1.55,1.05], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.45,0.55] },
  point1: { i:[0.15,0.08,0.05], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.45,0.25] },
  vhand:  { i:[0.15,0.08,0.05], m:[0.15,0.08,0.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.50,0.35] },
  whand:  { i:[0.08,0.05,0.03], m:[0.08,0.05,0.03], r:[0.08,0.05,0.03], p:[1.15,1.55,1.05], t:[0.50,0.75] },
  yhand:  { i:[1.15,1.55,1.05], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[0.08,0.05,0.03], t:[-0.10,0.05] },
  lhand:  { i:[0.15,0.08,0.05], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[-0.20,0.05] },
  chand:  { i:[0.70,0.90,0.60], m:[0.70,0.90,0.60], r:[0.70,0.90,0.60], p:[0.70,0.90,0.60], t:[0.15,0.20] },
  xhand:  { i:[0.55,1.55,1.05], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.45,0.25] },
  claw:   { i:[0.70,0.90,0.60], m:[0.70,0.90,0.60], r:[0.70,0.90,0.60], p:[0.70,0.90,0.60], t:[0.30,0.30] },
  thand:  { i:[0.55,0.90,0.60], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.55,0.55] },
  fhand:  { i:[0.55,0.90,0.60], m:[0.08,0.05,0.03], r:[0.08,0.05,0.03], p:[0.08,0.05,0.03], t:[0.55,0.55] },
  ghand:  { i:[0.15,0.08,0.05], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[-0.10,0.10] },
  uhand:  { i:[0.15,0.08,0.05], m:[0.15,0.08,0.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.50,0.55] },
  rest:   { i:[0.20,0.15,0.10], m:[0.20,0.15,0.10], r:[0.20,0.15,0.10], p:[0.20,0.15,0.10], t:[0.20,0.12] },

  // ── Distinct fingerspelling handshapes ──────────────────────────────────
  // These fix alphabet collisions where multiple letters shared the same shape.
  // I  — pinky only extended (not index)
  i_hs:  { i:[1.15,1.55,1.05], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[0.08,0.05,0.03], t:[0.45,0.25] },
  // D  — index up, thumb forward touching middle base
  d_hs:  { i:[0.15,0.08,0.05], m:[0.90,1.10,0.60], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.10,0.45] },
  // K  — index and middle up, thumb between them (forward, low curl)
  k_hs:  { i:[0.15,0.08,0.05], m:[0.15,0.08,0.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.10,0.15] },
  // N  — two fingers bent at angle over thumb
  n_hs:  { i:[0.70,0.50,0.30], m:[0.70,0.50,0.30], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.55,0.35] },
  // P  — like K but middle slightly more flexed (P points down in real signing)
  p_hs:  { i:[0.15,0.08,0.05], m:[0.28,0.14,0.06], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.10,0.20] },
  // R  — index and middle together, middle more bent to approximate cross
  r_hs:  { i:[0.15,0.08,0.05], m:[0.38,0.18,0.08], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.45,0.35] },
};

// ═══════════════════════════════════════════════════════════════════
// SECTION 2 — ARM POSITION PRESETS (unchanged from v1)
// ═══════════════════════════════════════════════════════════════════
const ARM = {
  idle_R:      { sh:{x:0.05,y:0,z:-0.22}, el:{x:0.08,y:0,z:0}, wr:{x:0,y:0,z:0} },
  idle_L:      { sh:{x:0.05,y:0,z: 0.22}, el:{x:0.08,y:0,z:0}, wr:{x:0,y:0,z:0} },
  chin_R:      { sh:{x:-1.30,y:0,z:-0.10}, el:{x:-0.20,y:0,z:0}, wr:{x:0,y:0,z:0} },
  chest_R:     { sh:{x:-0.30,y:0,z:-0.55}, el:{x:-0.20,y:0,z:0}, wr:{x:0.15,y:0,z:0} },
  chest_L:     { sh:{x:-0.30,y:0,z: 0.55}, el:{x:-0.20,y:0,z:0}, wr:{x:0.15,y:0,z:0} },
  forehead_R:  { sh:{x:-1.48,y:0,z:-0.06}, el:{x:-0.18,y:0,z:0}, wr:{x:0,y:0,z:0} },
  forward_R:   { sh:{x:-0.50,y:0,z:-0.14}, el:{x:-0.88,y:0,z:0}, wr:{x:0,y:0,z:0} },
  forward_L:   { sh:{x:-0.50,y:0,z: 0.14}, el:{x:-0.88,y:0,z:0}, wr:{x:0,y:0,z:0} },
  raised_R:    { sh:{x:-1.25,y:0,z:-0.28}, el:{x:-0.50,y:0,z:0}, wr:{x:0.12,y:0,z:0} },
  raised_L:    { sh:{x:-1.25,y:0,z: 0.28}, el:{x:-0.50,y:0,z:0}, wr:{x:0.12,y:0,z:0} },
  tummy_R:     { sh:{x:-0.20,y:0,z:-0.40}, el:{x:-0.30,y:0,z:0}, wr:{x:0,y:0,z:0} },
  flat_palm_L: { sh:{x:-1.18,y:0,z:0.28},  el:{x:-0.25,y:0,z:0}, wr:{x:-0.65,y:0.3,z:0} },
};

const IL = ARM.idle_L, IR = ARM.idle_R;
const NR = HS.rest,    NL = HS.rest;

// ═══════════════════════════════════════════════════════════════════
// SECTION 3 — ANATOMICAL JOINT LIMITS
// Applied after SLERP to prevent physically impossible poses.
// Values are in radians. Tune these to match your rig's skeleton.
//
// Convention: { minX, maxX, minY, maxY, minZ, maxZ }
//   positive x = forward flex, negative x = extension/raising
//   positive z = left abduction, negative z = right abduction
// ═══════════════════════════════════════════════════════════════════
const JOINT_LIMITS = {
  // Shoulder — wide range but can't fully rotate behind body
  R_sh: { minX:-1.60, maxX: 0.30, minY:-0.50, maxY: 0.50, minZ:-0.90, maxZ: 0.10 },
  L_sh: { minX:-1.60, maxX: 0.30, minY:-0.50, maxY: 0.50, minZ:-0.10, maxZ: 0.90 },

  // Elbow — hinge joint, only flexes in one direction
  R_el: { minX:-2.40, maxX: 0.05, minY:-0.10, maxY: 0.10, minZ:-0.05, maxZ: 0.05 },
  L_el: { minX:-2.40, maxX: 0.05, minY:-0.10, maxY: 0.10, minZ:-0.05, maxZ: 0.05 },

  // Wrist — flex/extend and rotate, limited radial/ulnar deviation
  R_wr: { minX:-0.80, maxX: 0.80, minY:-1.40, maxY: 1.40, minZ:-0.40, maxZ: 0.40 },
  L_wr: { minX:-0.80, maxX: 0.80, minY:-1.40, maxY: 1.40, minZ:-0.40, maxZ: 0.40 },

  // Finger MCP (knuckle) — flex/extend and slight side spread
  finger_MCP: { minX:-0.10, maxX: 1.20, minY:-0.25, maxY: 0.25, minZ:-0.10, maxZ: 0.10 },

  // Finger PIP (middle joint) — flex only, no hyperextension
  finger_PIP: { minX: 0.00, maxX: 1.80, minY: 0.00, maxY: 0.00, minZ: 0.00, maxZ: 0.00 },

  // Finger DIP (tip joint) — flex only, limited range
  finger_DIP: { minX: 0.00, maxX: 1.10, minY: 0.00, maxY: 0.00, minZ: 0.00, maxZ: 0.00 },

  // Thumb — saddle joint, complex but simplified here
  thumb_CMC: { minX:-0.20, maxX: 0.60, minY:-0.10, maxY: 0.80, minZ: 0.00, maxZ: 0.00 },
  thumb_MCP: { minX:-0.10, maxX: 0.60, minY: 0.00, maxY: 0.00, minZ: 0.00, maxZ: 0.00 },
};

// ═══════════════════════════════════════════════════════════════════
// SECTION 4 — QUATERNION UTILITIES
// Used internally by the TransitionEngine.
// These replace raw Euler interpolation with SLERP — the key fix
// for unnatural paths and gimbal lock.
// ═══════════════════════════════════════════════════════════════════

/**
 * Convert Euler angles {x, y, z} (radians, XYZ order) to a quaternion {x,y,z,w}.
 * This is how we convert the existing pose data into the format needed for SLERP.
 */
function eulerToQuat(e) {
  const cx = Math.cos(e.x / 2), sx = Math.sin(e.x / 2);
  const cy = Math.cos(e.y / 2), sy = Math.sin(e.y / 2);
  const cz = Math.cos(e.z / 2), sz = Math.sin(e.z / 2);
  return {
    x: sx * cy * cz + cx * sy * sz,
    y: cx * sy * cz - sx * cy * sz,
    z: cx * cy * sz + sx * sy * cz,
    w: cx * cy * cz - sx * sy * sz,
  };
}

/**
 * Convert quaternion {x,y,z,w} back to Euler angles {x, y, z} (radians, XYZ order).
 * Used to apply the interpolated rotation back to your Three.js bones.
 */
function quatToEuler(q) {
  // Normalise first to avoid numerical drift
  const len = Math.sqrt(q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w);
  const qn = { x:q.x/len, y:q.y/len, z:q.z/len, w:q.w/len };

  const sinr = 2 * (qn.w * qn.x + qn.y * qn.z);
  const cosr = 1 - 2 * (qn.x * qn.x + qn.y * qn.y);
  const rx = Math.atan2(sinr, cosr);

  const sinp = 2 * (qn.w * qn.y - qn.z * qn.x);
  const ry = Math.abs(sinp) >= 1 ? Math.sign(sinp) * Math.PI / 2 : Math.asin(sinp);

  const siny = 2 * (qn.w * qn.z + qn.x * qn.y);
  const cosy = 1 - 2 * (qn.y * qn.y + qn.z * qn.z);
  const rz = Math.atan2(siny, cosy);

  return { x: rx, y: ry, z: rz };
}

/**
 * Spherical Linear Interpolation between two quaternions.
 * t = 0 → returns qa, t = 1 → returns qb.
 * Takes the shortest arc through rotation space — no gimbal lock,
 * no weird paths, exactly like a real joint moving.
 */
function slerp(qa, qb, t) {
  let dot = qa.x*qb.x + qa.y*qb.y + qa.z*qb.z + qa.w*qb.w;

  // If dot is negative, negate qb to take the shorter arc
  let bx = qb.x, by = qb.y, bz = qb.z, bw = qb.w;
  if (dot < 0) { bx=-bx; by=-by; bz=-bz; bw=-bw; dot=-dot; }

  // If very close, fall back to linear interpolation to avoid division by zero
  if (dot > 0.9995) {
    return normaliseQuat({
      x: qa.x + t*(bx - qa.x),
      y: qa.y + t*(by - qa.y),
      z: qa.z + t*(bz - qa.z),
      w: qa.w + t*(bw - qa.w),
    });
  }

  const theta0 = Math.acos(dot);
  const theta  = theta0 * t;
  const sinT0  = Math.sin(theta0);
  const s0 = Math.cos(theta) - dot * Math.sin(theta) / sinT0;
  const s1 = Math.sin(theta) / sinT0;

  return {
    x: s0 * qa.x + s1 * bx,
    y: s0 * qa.y + s1 * by,
    z: s0 * qa.z + s1 * bz,
    w: s0 * qa.w + s1 * bw,
  };
}

function normaliseQuat(q) {
  const len = Math.sqrt(q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w);
  return { x:q.x/len, y:q.y/len, z:q.z/len, w:q.w/len };
}

/**
 * Clamp a value to [min, max]
 */
function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }

/**
 * Apply joint limits to an Euler angle object.
 * limits = { minX, maxX, minY, maxY, minZ, maxZ }
 */
function applyJointLimits(euler, limits) {
  return {
    x: clamp(euler.x, limits.minX, limits.maxX),
    y: clamp(euler.y, limits.minY, limits.maxY),
    z: clamp(euler.z, limits.minZ, limits.maxZ),
  };
}

// ═══════════════════════════════════════════════════════════════════
// SECTION 5 — EASING FUNCTIONS
// Controls the speed profile of transitions.
// easeInOutCubic: accelerates out, decelerates in — matches muscle.
// easeOutQuad: fast start, gentle landing — good for snappy signs.
// linear: constant speed — only for oscillations, never transitions.
// ═══════════════════════════════════════════════════════════════════
const Easing = {
  easeInOutCubic: t => t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2, 3)/2,
  easeOutQuad:    t => 1 - (1-t)*(1-t),
  easeInQuad:     t => t * t,
  linear:         t => t,
};

// ═══════════════════════════════════════════════════════════════════
// SECTION 6 — TRANSITION HINTS
// Per sign-pair overrides for coarticulation and duration.
// If a pair is not listed, defaults are used.
//
// blendStart: 0.0–1.0 — when to begin crossfading to the next sign
//   0.5 = start blending at 50% through current sign (earlier overlap)
//   0.7 = start blending at 70% (default — works for most signs)
//   0.9 = start blending at 90% (almost fully complete before blending)
//
// duration: seconds — how long the transition between signs takes
//   Fingerspelling: 0.10–0.18s (fast)
//   Short signs (YES, NO, I): 0.25–0.35s
//   Medium signs: 0.35–0.45s (default)
//   Large/sweeping signs (AMBULANCE, FIRE): 0.50–0.65s
// ═══════════════════════════════════════════════════════════════════
const TRANSITION_HINTS = {
  // Signs that end near the face transition quickly to other face signs
  'HELLO→THANK YOU':  { blendStart: 0.75, duration: 0.30 },
  'THANK YOU→PLEASE': { blendStart: 0.70, duration: 0.32 },
  'SORRY→PLEASE':     { blendStart: 0.72, duration: 0.28 },
  'YES→NO':           { blendStart: 0.65, duration: 0.22 },
  'NO→YES':           { blendStart: 0.65, duration: 0.22 },

  // Large body-space signs need more time
  'AMBULANCE→EMERGENCY': { blendStart: 0.80, duration: 0.60 },
  'FIRE→EMERGENCY':      { blendStart: 0.78, duration: 0.55 },
  'BIG→SMALL':           { blendStart: 0.72, duration: 0.50 },

  // Signs that start and end in similar arm positions blend smoothly
  'HAPPY→SAD':     { blendStart: 0.68, duration: 0.38 },
  'SAD→CRY':       { blendStart: 0.65, duration: 0.35 },
  'HUNGRY→EAT':    { blendStart: 0.60, duration: 0.30 },
  'THIRSTY→DRINK': { blendStart: 0.60, duration: 0.30 },

  // Fingerspelling transitions — very fast
  '_FINGERSPELL': { blendStart: 0.55, duration: 0.14 },
};

const DEFAULT_TRANSITION = { blendStart: 0.70, duration: 0.40 };

/**
 * Look up transition hints for a sign pair.
 * Falls back gracefully to defaults.
 */
function getTransitionHint(fromSign, toSign) {
  if (!fromSign || !toSign) return DEFAULT_TRANSITION;
  if (fromSign.isFingerspell || toSign.isFingerspell) {
    return TRANSITION_HINTS['_FINGERSPELL'];
  }
  const key = `${fromSign.name}→${toSign.name}`;
  return TRANSITION_HINTS[key] || DEFAULT_TRANSITION;
}

// ═══════════════════════════════════════════════════════════════════
// SECTION 7 — POSE UTILITIES
// Helpers to convert a pose definition to quaternions and back.
// ═══════════════════════════════════════════════════════════════════

/**
 * Convert a raw arm pose {sh, el, wr} (Euler) to a quaternion pose.
 * This is done once when signs are loaded — not every frame.
 */
function armToQuat(arm) {
  return {
    sh: eulerToQuat(arm.sh),
    el: eulerToQuat(arm.el),
    wr: eulerToQuat(arm.wr),
  };
}

/**
 * Linearly interpolate a single finger's curl values [mcp, pip, dip].
 * Fingers don't need full SLERP — they're essentially 1D joints.
 * Joint limits are applied per-joint after interpolation.
 */
function lerpFingerCurl(a, b, t, limits) {
  const result = [];
  for (let i = 0; i < a.length; i++) {
    const limitKey = i === 0 ? 'finger_MCP' : i === 1 ? 'finger_PIP' : 'finger_DIP';
    const lim = limits ? JOINT_LIMITS[limitKey] : null;
    let v = a[i] + (b[i] - a[i]) * t;
    if (lim) v = clamp(v, lim.minX, lim.maxX);
    result.push(v);
  }
  return result;
}

/**
 * Interpolate a full hand shape between two HS presets.
 * Returns a new handshape object at blend position t.
 */
function lerpHandShape(hsA, hsB, t) {
  return {
    i: lerpFingerCurl(hsA.i, hsB.i, t, true),
    m: lerpFingerCurl(hsA.m, hsB.m, t, true),
    r: lerpFingerCurl(hsA.r, hsB.r, t, true),
    p: lerpFingerCurl(hsA.p, hsB.p, t, true),
    t: lerpFingerCurl(hsA.t, hsB.t, t, false), // thumb uses different limits
  };
}

/**
 * Interpolate two arm quaternion poses with SLERP + joint limits.
 * Returns Euler angles ready to apply to Three.js bones.
 */
function slerpArmPose(qA, qB, t, side) {
  const s = side === 'R' ? 'R' : 'L';
  const shQ = slerp(qA.sh, qB.sh, t);
  const elQ = slerp(qA.el, qB.el, t);
  const wrQ = slerp(qA.wr, qB.wr, t);

  return {
    sh: applyJointLimits(quatToEuler(shQ), JOINT_LIMITS[`${s}_sh`]),
    el: applyJointLimits(quatToEuler(elQ), JOINT_LIMITS[`${s}_el`]),
    wr: applyJointLimits(quatToEuler(wrQ), JOINT_LIMITS[`${s}_wr`]),
  };
}

/**
 * Interpolate between two keyframe objects using pre-baked quaternions.
 * Mirrors slerpArmPose() but reads _Rq/_Lq from keyframe entries.
 */
function slerpBetweenFrames(frameA, frameB, t) {
  const R = slerpArmPose(frameA._Rq, frameB._Rq, t, 'R');
  R.hand = lerpHandShape(frameA.R.hand, frameB.R.hand, t);
  const L = slerpArmPose(frameA._Lq, frameB._Lq, t, 'L');
  L.hand = lerpHandShape(frameA.L.hand, frameB.L.hand, t);
  return { R, L };
}

// ═══════════════════════════════════════════════════════════════════
// SECTION 8 — SIGN BUILDER
// sign() is extended to store both startPose and endPose.
// For simple signs with no gross movement, they are equal.
// For signs with motion (COME, GIVE, TELL), they differ.
//
// NEW PARAMETER: startPose (optional)
//   If omitted, startPose === endPose (static hold sign).
//   If provided, the avatar moves FROM startPose TO endPose
//   during the sign's own duration (separate from inter-sign transitions).
// ═══════════════════════════════════════════════════════════════════
function sign(name, shape, desc, conf, Rsh, Rel, Rwr, Rhand, Lsh, Lel, Lwr, Lhand, osc, startOverride) {
  const endPoseRaw = {
    R: { sh:Rsh, el:Rel, wr:Rwr, hand:Rhand },
    L: { sh:Lsh, el:Lel, wr:Lwr, hand:Lhand },
  };

  // startOverride lets motion signs define a different start position
  const startPoseRaw = startOverride || endPoseRaw;

  // Pre-convert to quaternions for efficient runtime blending
  return {
    name, shape, desc, conf,
    // endPose: where this sign resolves to (used for transition OUT)
    R: endPoseRaw.R,
    L: endPoseRaw.L,
    // Quaternion versions — pre-baked for the engine
    _Rq: { end: armToQuat(endPoseRaw.R), start: armToQuat(startPoseRaw.R) },
    _Lq: { end: armToQuat(endPoseRaw.L), start: armToQuat(startPoseRaw.L) },
    osc,
    isFingerspell: false,
  };
}

/**
 * Pre-bake quaternions for a keyframe array in-place.
 * Call once when creating a keyframed sign — not every frame.
 * @param {Array} frames — array of {t, R, L} keyframe objects
 */
function prebakeFrameQuats(frames) {
  for (let i = 0; i < frames.length; i++) {
    const f = frames[i];
    f._Rq = armToQuat(f.R);
    f._Lq = armToQuat(f.L);
  }
}

/**
 * Binary-search the keyframe array for the pair bracketing t [0..1].
 * @param {Array}  frames — keyframe array (must be sorted by t, pre-baked)
 * @param {number} t      — normalized time [0..1]
 * @returns {{ a, b, localT }} — adjacent frames and local blend factor
 */
function findFrame(frames, t) {
  let lo = 0, hi = frames.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].t < t) lo = mid + 1;
    else hi = mid;
  }
  if (hi === 0) return { a: frames[0], b: frames[0], localT: 0 };
  const a = frames[hi - 1], b = frames[hi];
  const span = b.t - a.t;
  const localT = span < 1e-6 ? 1.0 : (t - a.t) / span;
  return { a, b, localT };
}

/**
 * Factory for keyframed signs (real motion-capture or recorded data).
 * The first/last frames are copied to the top-level R/L/_Rq/_Lq so
 * the inter-sign coarticulation path in TransitionEngine continues to work.
 *
 * @param {string}  name
 * @param {string}  shape      — handshape description
 * @param {string}  desc       — human description
 * @param {number}  conf       — confidence 1–5
 * @param {Array}   frames     — [{t, R:{sh,el,wr,hand}, L:{sh,el,wr,hand}}, ...]
 * @param {number}  durationMs — sign play duration in ms
 * @param {Object}  [nmm]      — non-manual markers {browLift,browFurrow,mouthOpen,headShake,headNod}
 */
function signWithFrames(name, shape, desc, conf, frames, durationMs, nmm) {
  if (!frames || frames.length < 2) {
    throw new Error(`signWithFrames("${name}"): need at least 2 keyframes`);
  }
  prebakeFrameQuats(frames);
  const first = frames[0];
  const last  = frames[frames.length - 1];
  return {
    name, shape, desc, conf,
    frames,
    duration: durationMs,
    nmm: nmm || null,
    // Top-level R/L = final pose (for hold display and coarticulation blending out)
    R: last.R,
    L: last.L,
    // Top-level quaternions: start = first frame, end = last frame
    _Rq: { start: first._Rq, end: last._Rq },
    _Lq: { start: first._Lq, end: last._Lq },
    osc: null,
    isFingerspell: false,
  };
}

// ═══════════════════════════════════════════════════════════════════
// SECTION 9 — THE TRANSITION ENGINE
// Call TransitionEngine.begin() when moving to a new sign.
// Call TransitionEngine.tick() every animation frame.
// ═══════════════════════════════════════════════════════════════════
const TransitionEngine = {
  _from:     null,  // sign object we're leaving
  _to:       null,  // sign object we're heading to
  _next:     null,  // sign queued after _to (for coarticulation look-ahead)
  _elapsed:  0,
  _duration: DEFAULT_TRANSITION.duration,
  _blendStart: DEFAULT_TRANSITION.blendStart,
  _easing:   Easing.easeInOutCubic,
  _done:     true,
  _onComplete: null,
  // Keyframe playback state (used when _to.frames is present)
  _inSignPhase:  false,
  _signElapsed:  0,
  _signDuration: 0,

  /**
   * Begin a transition from one sign to another.
   * @param {Object} fromSign  — the sign currently being displayed
   * @param {Object} toSign    — the sign to transition into
   * @param {Object} nextSign  — (optional) sign after toSign for coarticulation
   * @param {Function} onComplete — called when transition finishes
   */
  begin(fromSign, toSign, nextSign, onComplete) {
    this._from      = fromSign;
    this._to        = toSign;
    this._next      = nextSign || null;
    this._elapsed   = 0;
    this._done      = false;
    this._onComplete = onComplete || null;

    const hint = getTransitionHint(fromSign, toSign);
    this._duration   = hint.duration;
    this._blendStart = hint.blendStart;

    // Use snappier easing for fingerspelling, smoother for full signs
    this._easing = (fromSign && fromSign.isFingerspell)
      ? Easing.easeOutQuad
      : Easing.easeInOutCubic;

    // Keyframe mode: if toSign has real motion data, play through its frames
    if (toSign && toSign.frames && toSign.frames.length >= 2 && toSign.duration) {
      this._inSignPhase  = true;
      this._signElapsed  = 0;
      this._signDuration = toSign.duration / 1000;  // ms → s
    } else {
      this._inSignPhase = false;
    }
  },

  /**
   * Advance the transition by deltaTime seconds.
   * Returns a fully interpolated pose { R: {sh,el,wr,hand}, L: {sh,el,wr,hand} }
   * ready to apply to your Three.js skeleton.
   *
   * @param {number} deltaTime — seconds since last frame (e.g. 1/60)
   * @returns {Object} interpolated pose
   */
  tick(deltaTime) {
    if (this._done || !this._from || !this._to) {
      return this._to ? this._buildPose(this._to, 1.0) : null;
    }

    // ── KEYFRAME PATH ─────────────────────────────────────────────
    // When the destination sign has real motion-capture keyframes,
    // play through them before handing off to the inter-sign transition.
    if (this._inSignPhase) {
      this._signElapsed += deltaTime;
      const signT = Math.min(this._signElapsed / this._signDuration, 1.0);
      const { a, b, localT } = findFrame(this._to.frames, signT);
      const pose = slerpBetweenFrames(a, b, this._easing(localT));
      if (signT >= 1.0) {
        this._inSignPhase = false;  // keyframe playback done; start inter-sign phase
        this._elapsed     = 0;
      }
      return pose;
    }

    // ── EXISTING SLERP PATH ────────────────────────────────────────
    this._elapsed += deltaTime;
    const rawT = Math.min(this._elapsed / this._duration, 1.0);

    // Coarticulation: once past blendStart, also pull toward _next sign
    // This is what makes the avatar start reaching for the NEXT sign
    // before fully finishing the current one — matching real signer behaviour.
    let blendT;
    if (rawT >= this._blendStart && this._next) {
      const coarticProgress = (rawT - this._blendStart) / (1 - this._blendStart);
      const easedMain = this._easing(rawT);
      const coarticPull = Easing.easeInQuad(coarticProgress) * 0.25;
      blendT = Math.min(easedMain + coarticPull, 1.0);
    } else {
      blendT = this._easing(rawT);
    }

    if (rawT >= 1.0) {
      this._done = true;
      if (this._onComplete) this._onComplete();
      return this._buildPose(this._to, 1.0);
    }

    return this._interpolate(this._from, this._to, blendT);
  },

  /** Is the current transition complete? */
  isDone() { return this._done; },

  /**
   * Build a full pose for a single sign at completion (t=1).
   * Used when no transition is active.
   */
  _buildPose(sign, t) {
    return {
      R: {
        sh:   sign.R.sh,
        el:   sign.R.el,
        wr:   sign.R.wr,
        hand: sign.R.hand,
      },
      L: {
        sh:   sign.L.sh,
        el:   sign.L.el,
        wr:   sign.L.wr,
        hand: sign.L.hand,
      },
    };
  },

  /**
   * Interpolate between two signs at blend position t [0..1].
   * Uses SLERP for arm joints and linear interp for finger curls.
   * Joint limits are applied after SLERP.
   */
  _interpolate(fromSign, toSign, t) {
    // Right arm — SLERP between end pose of fromSign and start pose of toSign
    const R = slerpArmPose(fromSign._Rq.end, toSign._Rq.start, t, 'R');
    R.hand = lerpHandShape(fromSign.R.hand, toSign.R.hand, t);

    // Left arm
    const L = slerpArmPose(fromSign._Lq.end, toSign._Lq.start, t, 'L');
    L.hand = lerpHandShape(fromSign.L.hand, toSign.L.hand, t);

    return { R, L };
  },
};

// ═══════════════════════════════════════════════════════════════════
// SECTION 10 — THE SIGN LIBRARY
// All signs from v1 are preserved exactly.
// v2 adds startOverride for motion signs (see COME, GIVE, TELL, etc.)
// ═══════════════════════════════════════════════════════════════════

const SIGN_LIBRARY = {

  // ── GREETINGS & BASIC CONVERSATION ──────────────────────────────

  'HELLO': sign('HELLO','Hand waves away from head','Move hand away from head — universal greeting',5,
    {x:-1.35,y:0,z:-0.18},{x:0.05,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'z', amp:0.35, freq:1.8}),

  'GOODBYE': sign('GOODBYE','Wave hand side to side','Open hand waves from side to side — farewell',5,
    {x:-1.30,y:0,z:-0.15},{x:0.05,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'z', amp:0.45, freq:2.2}),

  'HOW ARE YOU': sign('HOW ARE YOU','Flat hands sweep out then thumbs up','Hands sweep outward then change to thumbs up',4,
    {x:-0.55,y:0,z:-0.30},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    {x:-0.55,y:0,z:0.30},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    {j:'both_sh', ax:'z', amp:0.25, freq:1.4}),

  "I'M FINE": sign("I'M FINE",'Hand moves up from flat-hand','Hand rises upward — I am fine',4,
    {x:-0.80,y:0,z:-0.20},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.10, freq:1.2}),

  'PLEASE': sign('PLEASE','B-hand circles on chest','Flat open hand circles on chest — polite request',4,
    {x:-0.28,y:0,z:-0.68},{x:-0.20,y:0,z:0},{x:0.18,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.26, freq:1.6}),

  'THANK YOU': sign('THANK YOU','Flat hand chin outward','Open hand at chin, sweeps forward and down',5,
    {x:-1.25,y:0,z:-0.08},{x:0.05,y:0,z:0},{x:-0.12,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.10, freq:1.4}),

  'SORRY': sign('SORRY','A-hand slides on cheek','Slide A-hand forwards and backwards on lower cheek',5,
    {x:-1.20,y:0,z:-0.15},{x:-0.10,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.08, freq:2.0}),

  'YES': sign('YES','S-hand fist nods','Tight closed fist — wrist nods up and down',5,
    {x:-0.45,y:0,z:-0.10},{x:-0.95,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'x', amp:0.38, freq:3.8}),

  'NO': sign('NO','H-hand wags side to side','Index and middle fingers extended, wag side to side',5,
    {x:-0.50,y:0,z:-0.14},{x:-0.88,y:0,z:0},{x:0,y:0.3,z:0}, HS.vhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.44, freq:3.5}),

  'HELP': sign('HELP','A-hand on flat palm · both raise','Fist (thumb extended) resting on open palm — rise together',5,
    {x:-1.28,y:0,z:-0.30},{x:-0.50,y:0,z:0},{x:0.12,y:0,z:0}, HS.fist_A,
    {x:-1.20,y:0,z:0.28},{x:-0.25,y:0,z:0},{x:-0.65,y:0.3,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.16, freq:2.3}),

  'WAIT': sign('WAIT','Both 5-hands palms out','Both open hands, palms forward, fingers wiggle',5,
    {x:-0.70,y:0,z:-0.24},{x:-1.28,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.70,y:0,z:0.24},{x:-1.28,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_el', ax:'z', amp:0.14, freq:2.8}),

  'STOP': sign('STOP','Both flat-hands push forward','Move both flat-hands forward simultaneously',5,
    {x:-0.60,y:0,z:-0.18},{x:-1.10,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.60,y:0,z:0.18},{x:-1.10,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    null),

  'REPEAT': sign('REPEAT','A-hand circles over flat palm','Dominant fist circles above non-dominant open hand',3,
    {x:-0.48,y:0,z:-0.22},{x:-0.78,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {x:-0.55,y:0,z:0.35},{x:-0.40,y:0,z:0},{x:-0.55,y:0.2,z:0}, HS.flat,
    {j:'R_sh', ax:'y', amp:1.55, freq:1.9}),

  'UNDERSTAND': sign('UNDERSTAND','Index at temple flicks up','Index finger at temple, flicks upward',5,
    {x:-1.50,y:0,z:-0.06},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'x', amp:0.20, freq:2.8}),

  'WATER': sign('WATER','W-hand taps chin','Index+middle+ring up (W-shape), taps chin twice',4,
    {x:-1.38,y:0,z:-0.08},{x:-0.22,y:0,z:0},{x:0,y:0,z:0}, HS.whand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.09, freq:2.5}),

  'PAIN': sign('PAIN','Both index fingers jab inward','Index fingers pointing inward, jabbing toward each other',4,
    {x:-0.32,y:0,z:-0.56},{x:-0.85,y:0,z:0.24},{x:0,y:0,z:0}, HS.point1,
    {x:-0.32,y:0,z:0.56},{x:-0.85,y:0,z:-0.24},{x:0,y:0,z:0}, HS.point1,
    {j:'both_el', ax:'x', amp:0.13, freq:4.2}),

  // ── MEDICAL & EMERGENCY ─────────────────────────────────────────

  'DOCTOR': sign('DOCTOR','Stethoscope on chest','Mimic putting stethoscope on chest',5,
    {x:-0.90,y:0,z:-0.55},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {x:-0.90,y:0,z:0.55},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {j:'both_sh', ax:'z', amp:0.10, freq:1.5}),

  'NURSE': sign('NURSE','U-hands over shoulders outward','Show badges on nurse uniform',4,
    {x:-1.00,y:0,z:-0.45},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.uhand,
    {x:-1.00,y:0,z:0.45},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.uhand,
    {j:'both_sh', ax:'z', amp:0.15, freq:1.4}),

  'HOSPITAL': sign('HOSPITAL','U-hand on upper arm moves forward','Index finger of U-hand touches upper arm then moves forward',5,
    {x:-1.10,y:0,z:-0.45},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.uhand,
    {x:-0.40,y:0,z:0.30},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.08, freq:1.5}),

  'SICK': sign('SICK','Both middle fingers touch forehead and tummy','Touch forehead and tummy simultaneously with middle fingers',5,
    {x:-1.45,y:0,z:-0.10},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    {x:-0.22,y:0,z:0.38},{x:-0.25,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    null),

  'AMBULANCE': sign('AMBULANCE','Claw-hands twist at sides of head','Twist claw-hands at sides of head — ambulance lights',4,
    {x:-1.30,y:0,z:-0.35},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {x:-1.30,y:0,z:0.35},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {j:'both_wr', ax:'y', amp:0.6, freq:3.0}),

  'FIRE': sign('FIRE','Open-5-hands flicker upward','Open hands move up and down alternately, flutter fingers — flames',5,
    {x:-0.80,y:0,z:-0.20},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.80,y:0,z:0.20},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'x', amp:0.25, freq:2.5}),

  'DANGEROUS': sign('DANGEROUS','Index fingers flick up sharply','No.1 fingers pointing forward then flick up quickly',5,
    {x:-0.55,y:0,z:-0.18},{x:-0.85,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {x:-0.55,y:0,z:0.18},{x:-0.85,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {j:'both_el', ax:'x', amp:0.4, freq:2.0}),

  'CAREFUL': sign('CAREFUL','Open-5-hands rotate forward alternately','Rotate open-5-hands forward alternately',5,
    {x:-0.70,y:0,z:-0.25},{x:-0.85,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.70,y:0,z:0.25},{x:-0.85,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'y', amp:0.3, freq:2.0}),

  'SAFE': sign('SAFE','Cup-hand slides over flat-hand','Slide cup-hand towards you over flat-hand',4,
    {x:-0.55,y:0,z:-0.35},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {x:-0.45,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'z', amp:0.08, freq:1.5}),

  'MEDICINE': sign('MEDICINE','M-hand taps palm','M-handshape taps on open palm — medication',4,
    {x:-0.65,y:0,z:-0.30},{x:-0.75,y:0,z:0},{x:0,y:0,z:0}, HS.whand,
    {x:-0.45,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.12, freq:2.2}),

  'HURT': sign('HURT','Hands flick open repeatedly','Flick hands open and closed — throbbing pain motion',5,
    {x:-0.65,y:0,z:-0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.65,y:0,z:0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_el', ax:'z', amp:0.35, freq:3.5}),

  'EMERGENCY': sign('EMERGENCY','Claw-hands at sides of head','Claw-hands twist at sides of head — emergency alert',5,
    {x:-1.25,y:0,z:-0.38},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {x:-1.25,y:0,z:0.38},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {j:'both_wr', ax:'y', amp:0.7, freq:4.0}),

  // ── EMOTIONS & FEELINGS ─────────────────────────────────────────

  'HAPPY': sign('HAPPY','Y-hand twists at mouth','Twist Y-hand wrist to and fro in front of mouth',5,
    {x:-1.28,y:0,z:-0.12},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.45, freq:2.5}),

  'SAD': sign('SAD','C-fingers move down mouth','C-shape fingers move downward at mouth',5,
    {x:-1.22,y:0,z:-0.10},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.06, freq:1.0}),

  'ANGRY': sign('ANGRY','Claw-hand rises hip to shoulder','Move claw-hand up diagonally from hip to shoulder',4,
    {x:-0.20,y:0,z:-0.40},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.5, freq:1.8}),

  'SCARED': sign('SCARED','Claw-hands twist at mouth','Claw-hands in front of mouth, wrists twist quickly',4,
    {x:-1.15,y:0,z:-0.20},{x:-0.25,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {x:-1.15,y:0,z:0.20},{x:-0.25,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {j:'both_wr', ax:'y', amp:0.5, freq:4.5}),

  'LOVE': sign('LOVE','S-hands cross over chest','Cross S-hands over chest and rock side to side',5,
    {x:-0.95,y:0,z:-0.40},{x:-0.20,y:0,z:0.35},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.95,y:0,z:0.40},{x:-0.20,y:0,z:-0.35},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_sh', ax:'z', amp:0.10, freq:1.2}),

  'I LOVE YOU': sign('I LOVE YOU','Y-hand with index extended','Extend thumb, index and pinky — combines I, L, Y',5,
    {x:-0.90,y:0,z:-0.20},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.20, freq:1.5}),

  'EXCITED': sign('EXCITED','Claw-hands alternate on chest','Move claw-hands up and down alternately on sides of chest',4,
    {x:-0.80,y:0,z:-0.40},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {x:-0.80,y:0,z:0.40},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {j:'both_sh', ax:'x', amp:0.25, freq:2.8}),

  'TIRED': sign('TIRED','T-hands drop down sides','Move T-hands downward simultaneously on both sides of body',4,
    {x:-0.55,y:0,z:-0.35},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.thand,
    {x:-0.55,y:0,z:0.35},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.thand,
    {j:'both_sh', ax:'x', amp:0.15, freq:1.0}),

  'HUNGRY': sign('HUNGRY','Flat-hand rubs tummy','Rub tummy with flat-hand',5,
    {x:-0.22,y:0,z:-0.45},{x:-0.30,y:0,z:0},{x:0.10,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.25, freq:2.0}),

  'THIRSTY': sign('THIRSTY','Thumb moves down throat','Move thumb and bent index finger down throat',5,
    {x:-1.30,y:0,z:-0.08},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.ghand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.08, freq:1.8}),

  'WORRIED': sign('WORRIED','Claw-hand circles on chest','Circle claw-hand on chest',4,
    {x:-0.85,y:0,z:-0.45},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.30, freq:1.8}),

  'PROUD': sign('PROUD','Thumbs hook under armpits','Hook thumbs under armpits — push chest out proud',3,
    {x:-0.75,y:0,z:-0.80},{x:0.05,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {x:-0.75,y:0,z:0.80},{x:0.05,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    null),

  'CONFUSED': sign('CONFUSED','Claw-hand circles at head','Claw-hand makes circles at side of head',4,
    {x:-1.38,y:0,z:-0.15},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.35, freq:2.2}),

  // ── QUESTION WORDS ───────────────────────────────────────────────

  'WHO': sign('WHO','B-hand taps chin','B-hand taps on chin twice',5,
    {x:-1.18,y:0,z:-0.10},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.08, freq:2.2}),

  'WHAT': sign('WHAT','Index finger waves at shoulder','Slightly wave index finger at side of shoulder',5,
    {x:-0.90,y:0,z:-0.20},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.30, freq:2.0}),

  'WHERE': sign('WHERE','Open-5-hands move in and out','Move open-5-hands in and out questioning',5,
    {x:-0.70,y:0,z:-0.28},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.70,y:0,z:0.28},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'z', amp:0.20, freq:1.8}),

  'WHEN': sign('WHEN','Claw fingers gallop over jaw','Claw-hand fingers gallop over jaw line',4,
    {x:-1.15,y:0,z:-0.12},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'z', amp:0.20, freq:2.8}),

  'WHY': sign('WHY','Index crosses chest','Cross index finger over chest questioningly',5,
    {x:-0.95,y:0,z:-0.55},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    null),

  'HOW': sign('HOW','Open-5-hand flips over','Flip open-5-hand from palm down to palm up',5,
    {x:-0.60,y:0,z:-0.25},{x:-0.75,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.8, freq:1.5}),

  'WHICH': sign('WHICH','Y-hand twists side to side','Twist Y-hand slightly from side to side',4,
    {x:-0.75,y:0,z:-0.20},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.30, freq:1.8}),

  // ── PRONOUNS ─────────────────────────────────────────────────────

  'I': sign('I','Index points to self','Index finger points to yourself',5,
    {x:-0.85,y:0,z:-0.62},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL, null),

  'YOU': sign('YOU','Index points to person','Index finger pointing to the other person',5,
    {x:-0.65,y:0,z:-0.15},{x:-0.90,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL, null),

  'WE': sign('WE','Index sweeps from self outward','Index finger sweeps from chest outward — inclusive',4,
    {x:-0.90,y:0,z:-0.55},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.4, freq:1.5}),

  'THEY': sign('THEY','Index swings in front','Swing index finger slightly in front',4,
    {x:-0.62,y:0,z:-0.18},{x:-0.85,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.35, freq:1.5}),

  // ── VERBS & INSTRUCTIONS — motion signs with startOverride ──────
  // COME: hand starts extended forward, moves toward body
  'COME': sign('COME','Cup-hand draws toward body','Move cup-hand towards your body — beckoning',5,
    {x:-0.65,y:0,z:-0.18},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_el', ax:'x', amp:0.25, freq:2.0},
    // startOverride: arm more extended at sign onset
    { R: { sh:{x:-0.50,y:0,z:-0.14}, el:{x:-1.05,y:0,z:0}, wr:{x:0,y:0,z:0}, hand:HS.chand },
      L: { sh:IL.sh, el:IL.el, wr:IL.wr, hand:NL } }),

  // GO: hand starts neutral, flicks upward and forward
  'GO': sign('GO','Flat-hand flicks up and forward','Hold flat-hand in front then flick it up',5,
    {x:-0.58,y:0,z:-0.15},{x:-0.95,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'x', amp:0.45, freq:1.5},
    { R: { sh:{x:-0.50,y:0,z:-0.15}, el:{x:-0.80,y:0,z:0}, wr:{x:0,y:0,z:0}, hand:HS.flat },
      L: { sh:IL.sh, el:IL.el, wr:IL.wr, hand:NL } }),

  'LISTEN': sign('LISTEN','V-hand moves to ear','Move V-hand towards ear, change to bent V',5,
    {x:-1.32,y:0,z:-0.20},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.08, freq:1.5}),

  'LOOK': sign('LOOK','V-hand under eyes points out','V-hand under eyes, point to what you are looking at',5,
    {x:-1.38,y:0,z:-0.10},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.10, freq:1.5}),

  'KNOW': sign('KNOW','Cup-hand taps temple','Cup-hand touches temple several times',5,
    {x:-1.42,y:0,z:-0.10},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.07, freq:2.0}),

  'WANT': sign('WANT','Open-5 draws down chest','Move open-5-hand down chest',5,
    {x:-0.90,y:0,z:-0.45},{x:-0.20,y:0,z:0},{x:0.15,y:0,z:0}, HS.open5,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.5, freq:1.5}),

  // GIVE: starts with hand held toward body, extends outward
  'GIVE': sign('GIVE','Closed hands extend forward and open','Mimic handing something over',5,
    {x:-0.65,y:0,z:-0.18},{x:-0.85,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.18, freq:1.5},
    { R: { sh:{x:-0.45,y:0,z:-0.35}, el:{x:-0.50,y:0,z:0}, wr:{x:0,y:0,z:0}, hand:HS.fist_A },
      L: { sh:IL.sh, el:IL.el, wr:IL.wr, hand:NL } }),

  'EAT': sign('EAT','Closed-5-hand to mouth','Mimic putting food in mouth',5,
    {x:-1.38,y:0,z:-0.08},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.12, freq:2.5}),

  'DRINK': sign('DRINK','C-hand tips to mouth','Mimic holding a cup and drinking',5,
    {x:-1.32,y:0,z:-0.10},{x:-0.18,y:0,z:0},{x:0.25,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.15, freq:2.0}),

  'SLEEP': sign('SLEEP','Flat-hands on cheek · tilt','Put flat-hands together on cheek — tilt head',5,
    {x:-1.28,y:0,z:-0.12},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL, null),

  'SIT': sign('SIT','A-hand taps flat-hand','Bang A-hand onto flat-hand',5,
    {x:-0.55,y:0,z:-0.30},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {x:-0.45,y:0,z:0.35},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.12, freq:2.2}),

  'STAND': sign('STAND','V-hand stands on flat-hand','Show legs standing',5,
    {x:-0.55,y:0,z:-0.30},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    {x:-0.45,y:0,z:0.35},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    null),

  'WALK': sign('WALK','V-hand walks forward','V-hand palm down walks forward',5,
    {x:-0.55,y:0,z:-0.18},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.18, freq:2.5}),

  'RUN': sign('RUN','S-hands swing alternately','Swing S-hands backwards and forwards alternately',4,
    {x:-0.55,y:0,z:-0.22},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.55,y:0,z:0.22},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_sh', ax:'x', amp:0.30, freq:3.5}),

  'WORK': sign('WORK','B-hands tap each other','Tap B-hands on each other at an angle',5,
    {x:-0.65,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.65,y:0,z:0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.15, freq:2.5}),

  'WASH': sign('WASH','A-hands rub together','Rub A-hands together — washing motion',4,
    {x:-0.60,y:0,z:-0.30},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {x:-0.60,y:0,z:0.30},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {j:'both_sh', ax:'y', amp:0.35, freq:2.5}),

  'OPEN': sign('OPEN','Flat-hand swings open','Show a door opening — flat-hand swings outward',4,
    {x:-0.65,y:0,z:-0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.65,y:0,z:0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'z', amp:0.35, freq:1.5}),

  'CLOSE': sign('CLOSE','Flat-hand closes onto other','Move flat-hand onto back of other flat-hand',4,
    {x:-0.65,y:0,z:-0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.65,y:0,z:0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'z', amp:-0.30, freq:1.5}),

  'WRITE': sign('WRITE','T-hand mimics writing','Mimic writing with T-hand on flat palm',4,
    {x:-0.60,y:0,z:-0.28},{x:-0.75,y:0,z:0},{x:0,y:0,z:0}, HS.thand,
    {x:-0.45,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_wr', ax:'y', amp:0.25, freq:2.5}),

  'READ': sign('READ','V-hand moves over flat-hand','Move V-hand up and down over flat-hand — reading a book',4,
    {x:-0.60,y:0,z:-0.28},{x:-0.75,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    {x:-0.45,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.12, freq:2.0}),

  'SIGN': sign('SIGN','Open-5-hands circle alternately','Circle open-5-hands alternately forward — sign language',5,
    {x:-0.70,y:0,z:-0.28},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.70,y:0,z:0.28},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'y', amp:0.5, freq:2.0}),

  // TELL: hand starts at chin, moves forward
  'TELL': sign('TELL','L-hand from chin moves forward','L-hand thumb touches chin then moves forward',5,
    {x:-1.22,y:0,z:-0.10},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.12, freq:1.5},
    { R: { sh:{x:-1.30,y:0,z:-0.10}, el:{x:-0.10,y:0,z:0}, wr:{x:0,y:0,z:0}, hand:HS.lhand },
      L: { sh:IL.sh, el:IL.el, wr:IL.wr, hand:NL } }),

  'LAUGH': sign('LAUGH','L-hand moves at mouth','Show big smile — move L-hand up and down at mouth',4,
    {x:-1.20,y:0,z:-0.12},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.20, freq:3.0}),

  'CRY': sign('CRY','Index fingers trail down cheeks','Move index fingers down cheeks',4,
    {x:-1.30,y:0,z:-0.18},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {x:-1.30,y:0,z:0.18},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {j:'both_sh', ax:'x', amp:0.06, freq:1.5}),

  'HUG': sign('HUG','S-hands cross over chest twist','Cross S-hands over chest and twist body side to side',5,
    {x:-0.95,y:0,z:-0.40},{x:-0.20,y:0,z:0.35},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.95,y:0,z:0.40},{x:-0.20,y:0,z:-0.35},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_sh', ax:'z', amp:0.08, freq:1.5}),

  // ── DESCRIPTIONS ─────────────────────────────────────────────────

  'GOOD': sign('GOOD','Flat-hand from chin sweeps down','Put flat-hand on chin then sweep downward and forward',5,
    {x:-1.18,y:0,z:-0.10},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.10, freq:1.5}),

  'BAD': sign('BAD','Flat-hand from mouth flips down','Flat-hand at mouth flips downward',5,
    {x:-1.15,y:0,z:-0.10},{x:-0.12,y:0,z:0},{x:0.30,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.5, freq:1.5}),

  'BIG': sign('BIG','Both hands spread apart','Show something big — spread both hands apart widely',5,
    {x:-0.65,y:0,z:-0.55},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.65,y:0,z:0.55},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'z', amp:0.20, freq:1.3}),

  'SMALL': sign('SMALL','Cup-hands close together','Bring cup-hands close together — showing small size',5,
    {x:-0.65,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {x:-0.65,y:0,z:0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {j:'both_sh', ax:'z', amp:-0.15, freq:1.5}),

  'HOT': sign('HOT','Flick index off forehead','Mimic wiping sweat off forehead — it is hot',4,
    {x:-1.45,y:0,z:-0.08},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.35, freq:2.0}),

  'COLD': sign('COLD','A-hands shake at chest','Mimic shivering — shake A-hands in and out at chest',5,
    {x:-0.75,y:0,z:-0.38},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {x:-0.75,y:0,z:0.38},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {j:'both_sh', ax:'z', amp:0.15, freq:5.0}),

  'QUIET': sign('QUIET','Index on lips — shh','Put index finger on lips — quiet please',5,
    {x:-1.32,y:0,z:-0.08},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL, null),

  'FAST': sign('FAST','Index fingers snap forward','Both index fingers pointing, snap forward quickly',4,
    {x:-0.62,y:0,z:-0.18},{x:-0.88,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {x:-0.62,y:0,z:0.18},{x:-0.88,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {j:'both_sh', ax:'x', amp:0.25, freq:3.0}),

  'SLOW': sign('SLOW','Claw-hand slides slowly over open-5','Claw-hand moves slowly over open-5-hand from fingers to wrist',4,
    {x:-0.60,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {x:-0.48,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'R_sh', ax:'x', amp:0.10, freq:0.8}),

  // ── PLACES & OCCUPATIONS ─────────────────────────────────────────

  'SCHOOL': sign('SCHOOL','Book sign · taps little fingers','Show book — tap little fingers together twice',5,
    {x:-0.62,y:0,z:-0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.62,y:0,z:0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.10, freq:2.2}),

  'HOME': sign('HOME','F-hands link together','Link F-hands — home/family place',5,
    {x:-0.68,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    {x:-0.68,y:0,z:0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    null),

  'CHURCH': sign('CHURCH','Hands together as in prayer','Put hands together as if praying',4,
    {x:-1.00,y:0,z:-0.15},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-1.00,y:0,z:0.15},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    null),

  'POLICE': sign('POLICE','F-hand badge on forehead','Show badge on hat — F-hand on forehead',4,
    {x:-1.45,y:0,z:-0.06},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    IL.sh,IL.el,IL.wr, NL, null),

  'TEACHER': sign('TEACHER','Index taps left then right','Mimic a teacher — tap index finger left then right',5,
    {x:-1.10,y:0,z:-0.35},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.35, freq:2.0}),

  // ── MONEY ────────────────────────────────────────────────────────

  'MONEY': sign('MONEY','Closed-5 rubs fingers together','Mimic rubbing coins — rub closed-5 fingers',5,
    {x:-0.65,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.25, freq:2.5}),

  'FREE': sign('FREE','V-hand fingers cross then open out','Cross V-hand fingers then move outwards',4,
    {x:-0.65,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    {x:-0.65,y:0,z:0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    {j:'both_sh', ax:'z', amp:0.35, freq:1.5}),

  'EXPENSIVE': sign('EXPENSIVE','Flat-hand moves into neck','Flat-hand moves up into neck — too expensive',4,
    {x:-0.80,y:0,z:-0.20},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.20, freq:1.5}),

  // ── FAMILY ───────────────────────────────────────────────────────

  'FAMILY': sign('FAMILY','Closed-5 circles above other closed-5','Circle closed-5-hand above other closed-5',5,
    {x:-0.75,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {x:-0.65,y:0,z:0.28},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {j:'R_sh', ax:'y', amp:0.5, freq:1.8}),

  'MOM': sign('MOM','B-hand slides across chest','Show mother — B-hand slides across chest',5,
    {x:-0.90,y:0,z:-0.50},{x:-0.20,y:0,z:0},{x:0.15,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.35, freq:1.5}),

  'DAD': sign('DAD','Index rubs down thumb at mouth','Mimic moustache — rub index down thumb at side of mouth',5,
    {x:-1.22,y:0,z:-0.15},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.thand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.20, freq:2.2}),

  'BABY': sign('BABY','Arms rock a baby','Mimic rocking a baby — swing arms gently side to side',5,
    {x:-0.85,y:0,z:-0.35},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.85,y:0,z:0.35},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'z', amp:0.20, freq:1.2}),

  'FRIEND': sign('FRIEND','B-hands clasp and shake','Mimic friend handshake — clasp B-hands and shake',5,
    {x:-0.68,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.68,y:0,z:0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.20, freq:2.5}),

  'CHILD': sign('CHILD','Flat-hand shows height of child','Show the size of the child',4,
    {x:-0.42,y:0,z:-0.28},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL, null),

  'PERSON': sign('PERSON','C-hand moves downward','Show the shape of a person — C-hand moves downward',4,
    {x:-0.68,y:0,z:-0.20},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.15, freq:1.5}),

  // ── NATURE & WEATHER ─────────────────────────────────────────────

  'RAIN': sign('RAIN','Open-5-hands flutter downward','Flutter fingers of open-5-hands as you move hands downward',5,
    {x:-0.55,y:0,z:-0.22},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.55,y:0,z:0.22},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'x', amp:0.20, freq:3.0}),

  'SUN': sign('SUN','S-hand flicks open above head','Flick S-hand open above side of head',4,
    {x:-1.38,y:0,z:-0.22},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'z', amp:0.6, freq:1.5}),

  'WIND': sign('WIND','Open-5-hands blow side to side','Move open-5-hands simultaneously left and right',4,
    {x:-0.68,y:0,z:-0.25},{x:-0.75,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.68,y:0,z:0.25},{x:-0.75,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'z', amp:0.35, freq:2.0}),

  'TREE': sign('TREE','Elbow on flat-hand · wave open-5','Place elbow on flat-hand, wave top open-5 — tree leaves',4,
    {x:-1.15,y:0,z:-0.12},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.38,y:0,z:0.28},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_wr', ax:'z', amp:0.30, freq:2.0}),

  // ── FOOD ─────────────────────────────────────────────────────────

  'FOOD': sign('FOOD','Closed hand to mouth','Mimic putting food into your mouth',5,
    {x:-1.38,y:0,z:-0.08},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.10, freq:2.5}),

  'BREAD': sign('BREAD','Flat-hand slices over flat-hand','Show slices of bread',4,
    {x:-0.60,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.48,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.15, freq:2.5}),

  // ── TRANSPORT ────────────────────────────────────────────────────

  'CAR': sign('CAR','S-hands steer wheel','Mimic holding steering wheel and driving',5,
    {x:-0.70,y:0,z:-0.35},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.70,y:0,z:0.35},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_sh', ax:'y', amp:0.25, freq:1.8}),

  'TAXI': sign('TAXI','Cross S-hands then flick index','Cross wrists of S-hands then flick index fingers up',4,
    {x:-0.65,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.65,y:0,z:0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_wr', ax:'x', amp:0.5, freq:2.0}),

  'BUS': sign('BUS','A-hands move forward and backward','Move A-hands alternately forwards and backwards at sides of head',4,
    {x:-1.28,y:0,z:-0.35},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {x:-1.28,y:0,z:0.35},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {j:'both_sh', ax:'x', amp:0.20, freq:2.2}),

  // ── RIGHTS & LEGAL ───────────────────────────────────────────────

  'RIGHTS': sign('RIGHTS','R-hand on flat palm','Show the letter R resting on flat palm',4,
    {x:-0.62,y:0,z:-0.28},{x:-0.72,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    {x:-0.48,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    null),

  'LAW': sign('LAW','L-hand taps flat palm','L-hand taps onto flat palm',4,
    {x:-0.62,y:0,z:-0.28},{x:-0.72,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    {x:-0.48,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.10, freq:2.0}),

  'EQUAL': sign('EQUAL','Both flat-hands level out','Level both flat-hands at same height',5,
    {x:-0.65,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.65,y:0,z:0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    null),

  'SHARE': sign('SHARE','Top flat-hand sweeps over bottom','Top flat-hand sweeps forward and out over bottom flat-hand',4,
    {x:-0.62,y:0,z:-0.28},{x:-0.72,y:0,z:0},{x:0.10,y:0,z:0}, HS.flat,
    {x:-0.48,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'z', amp:0.20, freq:2.0}),

  // ── TIME ─────────────────────────────────────────────────────────

  'TODAY': sign('TODAY','Now sign — both Y-hands drop down','Both Y-hands drop downward',5,
    {x:-0.62,y:0,z:-0.28},{x:-0.72,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    {x:-0.62,y:0,z:0.28},{x:-0.72,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    {j:'both_sh', ax:'x', amp:0.20, freq:2.0}),

  'NOW': sign('NOW','Y-hands drop downward','Both Y-hands drop down simultaneously',5,
    {x:-0.62,y:0,z:-0.28},{x:-0.72,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    {x:-0.62,y:0,z:0.28},{x:-0.72,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    {j:'both_sh', ax:'x', amp:0.25, freq:2.0}),

  'YESTERDAY': sign('YESTERDAY','Y-hand arcs backward from cheek','Y-hand at cheek moves backward — yesterday',4,
    {x:-1.10,y:0,z:-0.08},{x:-0.08,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:-0.18, freq:1.4}),

  'TOMORROW': sign('TOMORROW','Y-hand arcs forward from cheek','Y-hand at cheek moves forward — tomorrow',4,
    {x:-1.10,y:0,z:-0.08},{x:-0.05,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.18, freq:1.4}),

  'LATER': sign('LATER','L-hand points, right moves forward','Right L-hand glides forward from chin — later / after',4,
    {x:-0.62,y:0,z:-0.30},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    {x:-0.55,y:0,z:0.40},{x:-0.35,y:0,z:0},{x:0,y:0.30,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:-0.12, freq:1.3}),

  'MORNING': sign('MORNING','Flat-hand rises at forearm crook','Show sun rising — flat hand rises from elbow crook',4,
    {x:-0.45,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.80,y:0,z:-0.40},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.18, freq:1.2}),

  'NIGHT': sign('NIGHT','Bent hands show sun setting','Bent hands arc downward — nighttime',4,
    {x:-0.50,y:0,z:-0.28},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.50,y:0,z:0.28},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.15, freq:1.2}),

  // ── GRAMMAR MARKERS (SASL aspect / modal / negation) ──────────────

  'FINISH': sign('FINISH','Both flat-hands sweep outward','Both flat-hands brush out from body — done / already / past',5,
    {x:-0.55,y:0,z:-0.42},{x:-0.20,y:0,z:0},{x:0.12,y:0,z:0}, HS.flat,
    {x:-0.55,y:0,z:0.42},{x:-0.20,y:0,z:0},{x:0.12,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'z', amp:0.15, freq:1.6}),

  'WILL': sign('WILL','Flat-hand sweeps forward from face','Open hand at cheek sweeps forward — future / will',4,
    {x:-1.18,y:0,z:-0.10},{x:-0.05,y:0,z:0},{x:0,y:-0.15,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:-0.10, freq:1.2}),

  'NOT': sign('NOT','A-hand sweeps from chin outward','A-hand at chin sweeps forward and down — negation',5,
    {x:-1.20,y:0,z:-0.12},{x:-0.08,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:-0.12, freq:2.2}),

  'CAN': sign('CAN','Both S-hands push down','Both S-hands push firmly downward — ability / can',4,
    {x:-0.52,y:0,z:-0.35},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.52,y:0,z:0.35},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_sh', ax:'x', amp:0.15, freq:2.0}),

  'MUST': sign('MUST','X-hand bends downward','Right X-hand rotates firmly downward — obligation / must',4,
    {x:-0.45,y:0,z:-0.22},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.xhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_el', ax:'x', amp:0.18, freq:2.0}),

  'VERY': sign('VERY','Both V-hands spread apart','V-hands separate from each other — intensifier',4,
    {x:-0.52,y:0,z:-0.35},{x:-0.28,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    {x:-0.52,y:0,z:0.35},{x:-0.28,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    {j:'both_sh', ax:'z', amp:0.22, freq:1.5}),

  'ALSO': sign('ALSO','Both index fingers point and align','Both index fingers tap together — also / too / and',4,
    {x:-0.52,y:0,z:-0.22},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {x:-0.52,y:0,z:0.22},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {j:'R_sh', ax:'y', amp:0.22, freq:1.8}),

  // ── NEW / OLD ────────────────────────────────────────────────────

  'NEW': sign('NEW','Curved hand brushes flat palm','Curved right hand sweeps forward over flat left palm',4,
    {x:-0.65,y:0,z:-0.38},{x:-0.22,y:0,z:0},{x:0.12,y:0,z:0}, HS.chand,
    {x:-0.58,y:0,z:0.38},{x:-0.38,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.12, freq:1.5}),

  'OLD': sign('OLD','C-hand at chin pulls downward','Right C-hand at chin draws downward — beard gesture',4,
    {x:-1.18,y:0,z:-0.12},{x:-0.08,y:0,z:0},{x:-0.15,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.14, freq:1.3}),

  // ══════════════════════════════════════════════════════════════════
  // SECTION 10.7 — EXTENDED VOCABULARY
  // Source: Einstein Hands SASL Dictionary (Wits Centre for Deaf Studies)
  //         van Zijl SASL-MT (2006) medical domain
  //         de Villiers (2014) Stellenbosch vocabulary
  // ══════════════════════════════════════════════════════════════════

  // ── COLOURS ──────────────────────────────────────────────────────
  // Colours are commonly used in clinic/school settings.
  // Most SASL colours use a handshape near the face/chin area.

  'RED': sign('RED','Index finger brushes lips','Index fingertip brushes down across lips — colour red',4,
    {x:-1.18,y:0,z:-0.10},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL, null),

  'BLUE': sign('BLUE','B-hand shakes at side of face','Flat hand (B) shakes slightly at side of face — colour blue',4,
    {x:-1.10,y:0,z:-0.16},{x:-0.14,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.05, freq:3.0}),

  'GREEN': sign('GREEN','G-hand twists at chin','G-hand (index + thumb pinched) twists at chin — colour green',4,
    {x:-1.14,y:0,z:-0.12},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.ghand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.18, freq:2.0}),

  'YELLOW': sign('YELLOW','Y-hand shakes forward','Y-hand (thumb + pinky) shakes forward at chest — colour yellow',4,
    {x:-0.52,y:0,z:-0.18},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.20, freq:2.5}),

  'BLACK': sign('BLACK','Index draws across forehead','Index finger draws horizontally across forehead — colour black',4,
    {x:-1.45,y:0,z:-0.08},{x:-0.16,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL, null),

  'WHITE': sign('WHITE','Open hand pulls from chest','Open-5 hand draws from chest outward closing to flat — colour white',4,
    {x:-0.42,y:0,z:-0.50},{x:-0.20,y:0,z:0},{x:0.10,y:0,z:0}, HS.open5,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.10, freq:1.2}),

  'ORANGE': sign('ORANGE','C-hand squeezes at chin','C-hand squeezes open-shut at chin (squeezing orange) — colour orange',4,
    {x:-1.14,y:0,z:-0.12},{x:-0.14,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.12, freq:2.5}),

  'PINK': sign('PINK','P-hand brushes chin','Middle finger of P-hand brushes down chin — colour pink',4,
    {x:-1.18,y:0,z:-0.10},{x:-0.10,y:0,z:0},{x:0,y:0,z:0}, HS.p_hs,
    IL.sh,IL.el,IL.wr, NL, null),

  'PURPLE': sign('PURPLE','P-hand shakes at side','P-hand shakes at side of face — colour purple',4,
    {x:-1.08,y:0,z:-0.16},{x:-0.14,y:0,z:0},{x:0,y:0,z:0}, HS.p_hs,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.06, freq:3.0}),

  'BROWN': sign('BROWN','B-hand brushes cheek downward','Flat B-hand brushes down cheek — colour brown',4,
    {x:-1.10,y:0,z:-0.14},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL, null),

  // ── DAYS OF THE WEEK ─────────────────────────────────────────────
  // SASL days use initial-letter handshapes at chest/forward position.
  // Sources: Einstein Hands Days & Calendar category (pp.67–76)

  'MONDAY': sign('MONDAY','M-hand circles at chest','M-hand (W-shape) circles at forward chest — Monday',4,
    {x:-0.50,y:0,z:-0.20},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.whand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.10, freq:1.5}),

  'TUESDAY': sign('TUESDAY','T-hand circles at chest','T-hand circles at forward chest — Tuesday',4,
    {x:-0.50,y:0,z:-0.20},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.thand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.10, freq:1.5}),

  'WEDNESDAY': sign('WEDNESDAY','W-hand circles at chest','W-hand (3 fingers) circles at forward chest — Wednesday',4,
    {x:-0.50,y:0,z:-0.20},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.whand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.12, freq:1.5}),

  'THURSDAY': sign('THURSDAY','H-hand circles at chest','H-hand (index+middle side-by-side) circles — Thursday',4,
    {x:-0.50,y:0,z:-0.20},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.uhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.10, freq:1.5}),

  'FRIDAY': sign('FRIDAY','F-hand circles at chest','F-hand circles at forward chest — Friday',4,
    {x:-0.50,y:0,z:-0.20},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.10, freq:1.5}),

  'SATURDAY': sign('SATURDAY','S-hand circles at chest','S-hand (fist) circles at forward chest — Saturday',4,
    {x:-0.50,y:0,z:-0.20},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.10, freq:1.5}),

  'SUNDAY': sign('SUNDAY','Both open hands spread outward','Both open-5 hands spread outward from chest — Sunday / rest day',4,
    {x:-0.52,y:0,z:-0.45},{x:-0.22,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.52,y:0,z:0.45},{x:-0.22,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'z', amp:0.18, freq:1.2}),

  'WEEK': sign('WEEK','Index slides across flat palm','Right index slides across flat left palm — one week',4,
    {x:-0.60,y:0,z:-0.35},{x:-0.30,y:0,z:0},{x:0.10,y:0,z:0}, HS.point1,
    {x:-0.58,y:0,z:0.35},{x:-0.38,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    null),

  'MONTH': sign('MONTH','Index slides down index','Right index slides down left upright index finger — month',4,
    {x:-0.55,y:0,z:-0.30},{x:-0.45,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {x:-0.55,y:0,z:0.30},{x:-0.45,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    null),

  'YEAR': sign('YEAR','Fist rolls over fist','Right fist rolls forward over left fist — year',4,
    {x:-0.52,y:0,z:-0.30},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.52,y:0,z:0.30},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'R_sh', ax:'y', amp:0.22, freq:1.5}),

  'BIRTHDAY': sign('BIRTHDAY','Middle finger taps chin then flat','Middle finger taps chin, then flat hands brush apart — birthday',4,
    {x:-1.16,y:0,z:-0.12},{x:-0.14,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_el', ax:'x', amp:-0.10, freq:1.5}),

  'HOLIDAY': sign('HOLIDAY','Thumbs hook into chest','Both thumbs hook into chest/collar with a small bounce — holiday / vacation',4,
    {x:-0.45,y:0,z:-0.42},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    {x:-0.45,y:0,z:0.42},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    {j:'both_sh', ax:'x', amp:0.08, freq:2.0}),

  // ── ANIMALS ──────────────────────────────────────────────────────
  // Source: Einstein Hands Animals category (pp.21–36)

  'CAT': sign('CAT','Claw at cheek moves outward','Fingertips drag outward from cheeks — cat whiskers',4,
    {x:-1.06,y:0,z:-0.18},{x:-0.16,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {x:-1.06,y:0,z:0.18},{x:-0.16,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {j:'both_sh', ax:'z', amp:0.14, freq:1.5}),

  'DOG': sign('DOG','Flat hand taps throat','Flat right hand taps throat (collar) — dog',4,
    {x:-1.20,y:0,z:-0.10},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_el', ax:'x', amp:-0.08, freq:2.0}),

  'FISH': sign('FISH','Flat hand wiggles sideways','Flat right hand wiggles while moving sideways — fish swimming',4,
    {x:-0.50,y:0,z:-0.14},{x:-0.88,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.22, freq:3.0}),

  'BIRD': sign('BIRD','G-hand at cheek opens and closes','G-hand (beak) at cheek opens and shuts — bird',4,
    {x:-1.08,y:0,z:-0.14},{x:-0.14,y:0,z:0},{x:0,y:0,z:0}, HS.ghand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.12, freq:2.5}),

  'ELEPHANT': sign('ELEPHANT','Arm swings outward like trunk','Extended arm swings slowly left to right, head tilts — elephant trunk',4,
    {x:-0.45,y:0,z:-0.55},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.25, freq:0.8}),

  'LION': sign('LION','Claw on head slides back','Claw-hand on head moves backward — lion mane',4,
    {x:-1.38,y:0,z:-0.22},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.10, freq:1.0}),

  'HORSE': sign('HORSE','Fists stack and bounce','Both S-fists stacked, bounce up and down — horse riding',4,
    {x:-0.48,y:0,z:-0.25},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.48,y:0,z:0.25},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_sh', ax:'x', amp:0.15, freq:2.0}),

  'COW': sign('COW','Y-hands at sides of head','Y-hands (horns) held at sides of head — cow',4,
    {x:-1.32,y:0,z:-0.40},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    {x:-1.32,y:0,z:0.40},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    null),

  'RABBIT': sign('RABBIT','Flat hands on head bounce','Both flat-hands on top of head move up and down — rabbit ears',4,
    {x:-1.42,y:0,z:-0.28},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-1.42,y:0,z:0.28},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.12, freq:2.0}),

  'SNAKE': sign('SNAKE','Bent-V hand wiggles forward','Bent V-hand (tongue flicker) wiggles forward — snake',4,
    {x:-0.50,y:0,z:-0.14},{x:-0.85,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.18, freq:3.5}),

  'BUTTERFLY': sign('BUTTERFLY','Thumbs hooked, fingers flap','Both flat-hands with thumbs hooked, fingers wave forward — butterfly',4,
    {x:-0.55,y:0,z:-0.45},{x:-0.22,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.55,y:0,z:0.45},{x:-0.22,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.14, freq:2.5}),

  'MONKEY': sign('MONKEY','Claw-hands scratch under arms','Both claw-hands scratch alternately under armpits — monkey',4,
    {x:-0.38,y:0,z:-0.50},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {x:-0.38,y:0,z:0.50},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {j:'both_sh', ax:'x', amp:0.12, freq:2.0}),

  'CROCODILE': sign('CROCODILE','Extended claw-arms clap','Both claw-arms extended forward slam together — crocodile jaws',4,
    {x:-0.52,y:0,z:-0.42},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {x:-0.52,y:0,z:0.42},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {j:'both_sh', ax:'z', amp:0.20, freq:1.5}),

  'BEAR': sign('BEAR','C-hands at sides of head tilt','C-hands at head (ears) tilt side to side — bear',4,
    {x:-1.30,y:0,z:-0.48},{x:-0.25,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {x:-1.30,y:0,z:0.48},{x:-0.25,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {j:'both_sh', ax:'z', amp:0.08, freq:1.0}),

  'CHICKEN': sign('CHICKEN','T-hand pecks on flat palm','T-hand pecks repeatedly onto flat left palm — chicken pecking',4,
    {x:-0.50,y:0,z:-0.30},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.thand,
    {x:-0.55,y:0,z:0.35},{x:-0.38,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_el', ax:'x', amp:-0.14, freq:2.5}),

  'FROG': sign('FROG','V-hands jump forward from chin','V-hands flick out from chin (frog tongue) — frog',4,
    {x:-1.10,y:0,z:-0.20},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:-0.14, freq:1.5}),

  'PIG': sign('PIG','Fist twists at nose','S-fist twists under nose — pig snout',4,
    {x:-1.22,y:0,z:-0.10},{x:-0.10,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.15, freq:2.5}),

  'DUCK': sign('DUCK','C-hand at mouth snaps open-shut','C-hand at chin opens and closes (duck beak) — duck',4,
    {x:-1.14,y:0,z:-0.12},{x:-0.14,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.14, freq:2.5}),

  // ── BATH & HYGIENE ────────────────────────────────────────────────
  // Source: Einstein Hands Bath Routine category (pp.37–42)

  'SHOWER': sign('SHOWER','Claw-hand above head rains down','Open claw-hand above head showers downward — shower',4,
    {x:-1.45,y:0,z:-0.12},{x:-0.22,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.12, freq:1.5}),

  'BATH': sign('BATH','Both A-hands scrub up and down chest','Both A-fists scrub up and down torso — having a bath',4,
    {x:-0.38,y:0,z:-0.48},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {x:-0.38,y:0,z:0.48},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {j:'both_sh', ax:'x', amp:0.18, freq:1.8}),

  'SOAP': sign('SOAP','Cup-hands rub together','Cup-hands (holding a bar of soap) rub together — soap',4,
    {x:-0.55,y:0,z:-0.32},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {x:-0.55,y:0,z:0.32},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {j:'both_sh', ax:'y', amp:0.10, freq:2.0}),

  'TOOTHBRUSH': sign('TOOTHBRUSH','Index brushes teeth side-to-side','Index finger moves to and fro in front of teeth — toothbrush',4,
    {x:-1.14,y:0,z:-0.12},{x:-0.14,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'z', amp:0.18, freq:3.0}),

  'TOWEL': sign('TOWEL','Fists pull towel back and forth','S-fists alternately pull towel back and forth behind back — towel',4,
    {x:-0.30,y:0,z:-0.50},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.30,y:0,z:0.50},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_sh', ax:'y', amp:0.22, freq:1.8}),

  'TOILET': sign('TOILET','H-hands cross and tap twice','H-hands crossed at wrists tap together twice — toilet',4,
    {x:-0.52,y:0,z:-0.30},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.uhand,
    {x:-0.52,y:0,z:0.30},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.uhand,
    {j:'both_sh', ax:'x', amp:0.10, freq:2.5}),

  // ── FOOD & DRINK ──────────────────────────────────────────────────
  // Source: Einstein Hands Food category (pp.128–164)
  // van Zijl medical domain — common clinic/hospital food items

  'MILK': sign('MILK','C-hand squeezes repeatedly','C-hand squeezes open and closed at chest — milking/milk',4,
    {x:-0.48,y:0,z:-0.28},{x:-0.32,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.14, freq:2.5}),

  'APPLE': sign('APPLE','X-hand twists at cheek','Bent X-hand (knuckle) twists at cheek — apple',4,
    {x:-1.08,y:0,z:-0.14},{x:-0.14,y:0,z:0},{x:0,y:0,z:0}, HS.xhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.14, freq:2.0}),

  'BANANA': sign('BANANA','One hand peels other index finger','Right hand peels down left upright index — banana',4,
    {x:-0.58,y:0,z:-0.28},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    {x:-0.55,y:0,z:0.28},{x:-0.42,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {j:'R_sh', ax:'x', amp:0.12, freq:1.5}),

  'EGG': sign('EGG','H-hands crack apart','Both H-hands crack open at chest — egg cracking',4,
    {x:-0.52,y:0,z:-0.30},{x:-0.38,y:0,z:0},{x:0,y:0,z:0}, HS.uhand,
    {x:-0.52,y:0,z:0.30},{x:-0.38,y:0,z:0},{x:0,y:0,z:0}, HS.uhand,
    {j:'both_sh', ax:'z', amp:0.12, freq:1.5}),

  'RICE': sign('RICE','R-hand taps lips','R-hand (crossed index+middle) taps lips — rice',4,
    {x:-1.14,y:0,z:-0.10},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.r_hs,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_el', ax:'x', amp:-0.08, freq:2.0}),

  'MEAT': sign('MEAT','F-hand pinches back of hand','F-hand pinches the back of left hand — meat / flesh',4,
    {x:-0.62,y:0,z:-0.30},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    {x:-0.58,y:0,z:0.35},{x:-0.38,y:0,z:0},{x:-0.30,y:0,z:0}, HS.flat,
    null),

  'CAKE': sign('CAKE','C-hand slices flat palm','C-hand slides forward across flat left palm — slice of cake',4,
    {x:-0.62,y:0,z:-0.32},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {x:-0.58,y:0,z:0.38},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    null),

  'COFFEE': sign('COFFEE','S-hands grind in circles','Both S-fists rotate in circles (grinding coffee) — coffee',4,
    {x:-0.52,y:0,z:-0.28},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.52,y:0,z:0.28},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'R_sh', ax:'y', amp:0.18, freq:2.0}),

  'TEA': sign('TEA','F-hand lifts teacup to mouth','F-hand (holding teacup pinch) lifts toward mouth — tea',4,
    {x:-1.08,y:0,z:-0.14},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_el', ax:'x', amp:-0.12, freq:1.5}),

  'FRUIT': sign('FRUIT','F-hand twists at cheek','F-hand twists at cheek (tasting fruit) — fruit',4,
    {x:-1.08,y:0,z:-0.14},{x:-0.14,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.16, freq:2.0}),

  'SUGAR': sign('SUGAR','Middle finger strokes chin twice','Middle finger strokes chin — sweet / sugar',4,
    {x:-1.16,y:0,z:-0.10},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_el', ax:'x', amp:-0.08, freq:2.5}),

  'SWEET': sign('SWEET','Middle finger taps chin','Middle finger of right hand taps chin — sweet / nice taste',4,
    {x:-1.16,y:0,z:-0.10},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_el', ax:'x', amp:-0.10, freq:2.0}),

  'VEGETABLE': sign('VEGETABLE','V-hand twists at cheek','V-hand twists at cheek — vegetable',4,
    {x:-1.08,y:0,z:-0.14},{x:-0.14,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.14, freq:2.0}),

  // ── CLOTHING ─────────────────────────────────────────────────────
  // Source: Einstein Hands Clothing category (pp.52–59)

  'SHIRT': sign('SHIRT','Both hands pull at collar','Both flat-hands grip and pull at shirt collar — shirt',4,
    {x:-0.52,y:0,z:-0.48},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.52,y:0,z:0.48},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.08, freq:2.0}),

  'SHOES': sign('SHOES','S-hands knock together','Both S-fists knock together at sides — shoes',4,
    {x:-0.22,y:0,z:-0.38},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.22,y:0,z:0.38},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_sh', ax:'z', amp:0.14, freq:2.5}),

  'HAT': sign('HAT','Flat hand pats top of head','Flat right hand pats down on top of head — hat',4,
    {x:-1.55,y:0,z:-0.10},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_el', ax:'x', amp:-0.10, freq:2.0}),

  'DRESS': sign('DRESS','Both hands slide down torso','Both open hands brush down sides of body — dress',4,
    {x:-0.42,y:0,z:-0.50},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.42,y:0,z:0.50},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'x', amp:0.14, freq:1.2}),

  'JACKET': sign('JACKET','Both hands grab lapels','Both hands grab lapels of jacket — jacket / coat',4,
    {x:-0.48,y:0,z:-0.48},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {x:-0.48,y:0,z:0.48},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    null),

  'UNIFORM': sign('UNIFORM','Both hands brush shoulders','Both flat-hands brush both shoulders — uniform',4,
    {x:-0.55,y:0,z:-0.52},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.55,y:0,z:0.52},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    null),

  // ── NUMBERS ──────────────────────────────────────────────────────
  // SASL uses one-handed cardinal numbers 1-10.
  // Signed at forward chest/finger-spelling position.

  'ONE': sign('ONE','Index finger extended up','Single index finger pointing up — number one',5,
    {x:-0.85,y:0,z:-0.28},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL, null),

  'TWO': sign('TWO','Two fingers extended','Index and middle fingers extended (V-hand) — number two',5,
    {x:-0.85,y:0,z:-0.28},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    IL.sh,IL.el,IL.wr, NL, null),

  'THREE': sign('THREE','Three fingers extended','Index, middle, ring extended (W-hand) — number three',5,
    {x:-0.85,y:0,z:-0.28},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.whand,
    IL.sh,IL.el,IL.wr, NL, null),

  'FOUR': sign('FOUR','Four fingers extended','Four fingers extended, thumb folded — number four',5,
    {x:-0.85,y:0,z:-0.28},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    IL.sh,IL.el,IL.wr, NL, null),

  'FIVE': sign('FIVE','Open hand — all fingers extended','Open-5 hand, all fingers spread — number five',5,
    {x:-0.85,y:0,z:-0.28},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    IL.sh,IL.el,IL.wr, NL, null),

  'SIX': sign('SIX','Pinky and thumb extended','Y-hand (pinky + thumb) — number six',5,
    {x:-0.85,y:0,z:-0.28},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    IL.sh,IL.el,IL.wr, NL, null),

  'SEVEN': sign('SEVEN','Ring and thumb touch','Ring finger touches thumb, others extended — number seven',5,
    {x:-0.85,y:0,z:-0.28},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    IL.sh,IL.el,IL.wr, NL, null),

  'EIGHT': sign('EIGHT','Middle and thumb touch','Middle finger touches thumb, others extended — number eight',5,
    {x:-0.85,y:0,z:-0.28},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.thand,
    IL.sh,IL.el,IL.wr, NL, null),

  'NINE': sign('NINE','Index curves to touch thumb','Bent index (X-hand) touches thumb — number nine',5,
    {x:-0.85,y:0,z:-0.28},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.xhand,
    IL.sh,IL.el,IL.wr, NL, null),

  'TEN': sign('TEN','A-hand shakes with thumb up','A-fist shakes with thumb extended — number ten',5,
    {x:-0.85,y:0,z:-0.28},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.14, freq:2.5}),

  // ── TRANSPORT ─────────────────────────────────────────────────────
  // Source: Einstein Hands Transport category (pp.253–261)

  'TRAIN': sign('TRAIN','H-hands slide along rails','Both H-hands (rails) move forward together — train',4,
    {x:-0.52,y:0,z:-0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.uhand,
    {x:-0.52,y:0,z:0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.uhand,
    {j:'both_sh', ax:'x', amp:0.10, freq:2.0}),

  'AEROPLANE': sign('AEROPLANE','Y-hand flies forward','Y-hand (wings spread) moves upward and forward — aeroplane',4,
    {x:-0.85,y:0,z:-0.30},{x:-0.48,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:-0.12, freq:0.8}),

  'BICYCLE': sign('BICYCLE','Fists rotate alternately','Both fists rotate alternately forward — pedalling a bicycle',4,
    {x:-0.52,y:0,z:-0.32},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.52,y:0,z:0.32},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_sh', ax:'y', amp:0.25, freq:2.0}),

  // ── SPORT ─────────────────────────────────────────────────────────
  // Source: Einstein Hands Sport category (pp.241–246)

  'SOCCER': sign('SOCCER','Foot kick — index flicks forward','Right index flicks forward from low position — soccer kick',4,
    {x:-0.20,y:0,z:-0.20},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:-0.15, freq:1.5}),

  'SWIMMING': sign('SWIMMING','Both arms crawl forward alternately','Both arms move in alternating forward crawl — swimming',4,
    {x:-0.52,y:0,z:-0.35},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.52,y:0,z:0.35},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.22, freq:1.5}),

  'CRICKET': sign('CRICKET','Fist swings like bat','Right fist swings horizontally (batting) — cricket',4,
    {x:-0.38,y:0,z:-0.52},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.30, freq:1.2}),

  // ── BASIC CONVERSATION ────────────────────────────────────────────
  // Source: Einstein Hands Basic Conversation (pp.293–302)
  // van Zijl SASL-MT critical vocabulary

  'DEAF': sign('DEAF','Index touches ear then mouth','Index finger touches ear then moves to mouth corner — Deaf',5,
    {x:-1.30,y:0,z:-0.18},{x:-0.14,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.10, freq:1.0}),

  'HEARING': sign('HEARING','Index circles at ear','Index finger circles at ear — hearing person',5,
    {x:-1.30,y:0,z:-0.18},{x:-0.14,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.08, freq:2.0}),

  'NAME': sign('NAME','H-hands tap together twice','Both H-hands (index+middle) tap together at chest — name',5,
    {x:-0.52,y:0,z:-0.28},{x:-0.45,y:0,z:0},{x:0,y:0,z:0}, HS.uhand,
    {x:-0.52,y:0,z:0.28},{x:-0.45,y:0,z:0},{x:0,y:0,z:0}, HS.uhand,
    {j:'both_sh', ax:'x', amp:0.10, freq:2.5}),

  'GOOD MORNING': sign('GOOD MORNING','Flat hand rises from elbow','Flat right hand rises from forearm level upward — good morning',5,
    {x:-0.48,y:0,z:-0.50},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.48,y:0,z:0.50},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:-0.16, freq:1.0}),

  'GOOD NIGHT': sign('GOOD NIGHT','Flat hand sets like sun downward','Flat hand descends from raised position — good night',5,
    {x:-0.70,y:0,z:-0.35},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.14, freq:0.8}),

  'SIGN LANGUAGE': sign('SIGN LANGUAGE','Both index fingers rotate together','Both index fingers circle around each other at forward position — sign language',5,
    {x:-0.55,y:0,z:-0.32},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {x:-0.55,y:0,z:0.32},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {j:'both_sh', ax:'y', amp:0.22, freq:2.0}),

  // ── ADDITIONAL MEDICAL VOCABULARY ────────────────────────────────
  // Source: van Zijl (2006) SASL-MT clinic/hospital domain (highest priority)

  'PREGNANT': sign('PREGNANT','Curved hand in front of belly','Right curved hand moves away from lower abdomen — pregnant',5,
    {x:-0.22,y:0,z:-0.35},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.10, freq:1.0}),

  'BLOOD': sign('BLOOD','Index drips down from wrist','Left index points up, right index drips downward from it — blood',5,
    {x:-0.55,y:0,z:-0.28},{x:-0.45,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {x:-0.55,y:0,z:0.28},{x:-0.45,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {j:'R_sh', ax:'x', amp:0.14, freq:1.0}),

  'FEVER': sign('FEVER','Flat hand on forehead','Flat right hand presses forehead — fever / temperature',5,
    {x:-1.48,y:0,z:-0.08},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL, null),

  'DIZZY': sign('DIZZY','Index circles at temple','Index finger circles at side of head — dizzy',5,
    {x:-1.30,y:0,z:-0.18},{x:-0.16,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.10, freq:3.0}),

  'BROKEN': sign('BROKEN','Both fists break apart','Both S-fists snap apart with wrist rotation — broken',5,
    {x:-0.52,y:0,z:-0.30},{x:-0.38,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.52,y:0,z:0.30},{x:-0.38,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_sh', ax:'z', amp:0.20, freq:1.5}),

  'BREATHE': sign('BREATHE','Both hands move in and out on chest','Both open hands move away from and toward chest — breathing',5,
    {x:-0.42,y:0,z:-0.48},{x:-0.22,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.42,y:0,z:0.48},{x:-0.22,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'z', amp:0.18, freq:1.2}),

  'CHEST': sign('CHEST','Both hands on chest','Both flat-hands rest on chest — chest (body part)',5,
    {x:-0.42,y:0,z:-0.50},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.42,y:0,z:0.50},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    null),

  'VOMIT': sign('VOMIT','Both hands arc forward from mouth','Both open hands sweep forward from mouth — vomit / nausea',5,
    {x:-1.08,y:0,z:-0.22},{x:-0.22,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-1.08,y:0,z:0.22},{x:-0.22,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'x', amp:-0.18, freq:1.0}),

  'HEADACHE': sign('HEADACHE','Both index fingers point to temples','Both index fingers point toward each side of head — headache',5,
    {x:-1.32,y:0,z:-0.22},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {x:-1.32,y:0,z:0.22},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    null),

  'ALLERGY': sign('ALLERGY','Index points to nose and sneezes','Index touches nose then hand flicks away — allergy / sneeze',4,
    {x:-1.22,y:0,z:-0.10},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:-0.12, freq:1.5}),

  'INJECTION': sign('INJECTION','Thumb pushes syringe at arm','Right thumb pushes downward at left forearm — injection / shot',5,
    {x:-0.55,y:0,z:-0.28},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    {x:-0.55,y:0,z:0.32},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_el', ax:'x', amp:-0.10, freq:1.5}),

  'OPERATION': sign('OPERATION','Index slides along other forearm','Right index slides along top of left forearm — operation / surgery',5,
    {x:-0.55,y:0,z:-0.28},{x:-0.45,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {x:-0.55,y:0,z:0.32},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    null),

  // ── EMOTIONS (EXTENDED) ───────────────────────────────────────────
  // Source: Einstein Hands Emotions & Feelings (pp.106–116)

  'BORED': sign('BORED','Index taps side of nose','Index finger taps the side of the nose — bored',4,
    {x:-1.20,y:0,z:-0.12},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_el', ax:'x', amp:-0.08, freq:2.0}),

  'JEALOUS': sign('JEALOUS','X-hand hooks at corner of mouth','Bent index (X) hooks at corner of mouth — jealous / envious',4,
    {x:-1.14,y:0,z:-0.12},{x:-0.14,y:0,z:0},{x:0,y:0,z:0}, HS.xhand,
    IL.sh,IL.el,IL.wr, NL, null),

  'DISAPPOINTED': sign('DISAPPOINTED','Index taps chin, droops down','Index touches chin and drops — disappointed',4,
    {x:-1.16,y:0,z:-0.10},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.12, freq:1.0}),

  'EMBARRASSED': sign('EMBARRASSED','Both hands wave in front of face','Both hands wave alternately in front of face — embarrassed / shame',4,
    {x:-1.08,y:0,z:-0.28},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-1.08,y:0,z:0.28},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'z', amp:0.10, freq:1.5}),

  'NERVOUS': sign('NERVOUS','Fingers shake at chest','Both open-5 hands tremble at chest — nervous / anxious',4,
    {x:-0.45,y:0,z:-0.45},{x:-0.22,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.45,y:0,z:0.45},{x:-0.22,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'x', amp:0.08, freq:4.0}),

  'PAIN': sign('PAIN','Both index fingers jab toward each other','Both index fingers jab together repeatedly — pain / hurt',5,
    {x:-0.52,y:0,z:-0.32},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {x:-0.52,y:0,z:0.32},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {j:'both_sh', ax:'z', amp:0.12, freq:2.0}),

  // ── DESCRIPTIONS (EXTENDED) ───────────────────────────────────────

  'BEAUTIFUL': sign('BEAUTIFUL','Open hand circles face then closes','Open hand circles face then closes to fist — beautiful',4,
    {x:-1.12,y:0,z:-0.22},{x:-0.16,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.18, freq:1.2}),

  'UGLY': sign('UGLY','X-hand near nose sweeps away','Bent X-hand at nose flicks downward — ugly',4,
    {x:-1.18,y:0,z:-0.12},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.xhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.12, freq:1.5}),

  'CLEAN': sign('CLEAN','Flat hand wipes across flat palm','Flat hand slides across upturned flat left palm — clean',4,
    {x:-0.62,y:0,z:-0.32},{x:-0.28,y:0,z:0},{x:0.12,y:0,z:0}, HS.flat,
    {x:-0.58,y:0,z:0.38},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.10, freq:1.5}),

  'DIRTY': sign('DIRTY','Claw-hand wiggles under chin','Claw-hand shakes under chin — dirty / messy',4,
    {x:-1.14,y:0,z:-0.12},{x:-0.14,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.14, freq:2.5}),

  'HEAVY': sign('HEAVY','Both cupped hands drop downward','Both cupped hands drop — heavy weight',4,
    {x:-0.42,y:0,z:-0.45},{x:-0.25,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {x:-0.42,y:0,z:0.45},{x:-0.25,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {j:'both_sh', ax:'x', amp:0.16, freq:1.0}),

  'LIGHT': sign('LIGHT','Both hands rise upward open','Both hands rise and open upward — light weight',4,
    {x:-0.68,y:0,z:-0.38},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.68,y:0,z:0.38},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'x', amp:-0.14, freq:1.0}),

  'FULL': sign('FULL','Flat hand sweeps across throat','Flat right hand sweeps horizontally across throat — full / enough',4,
    {x:-1.22,y:0,z:-0.14},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL, null),

  // ── PLACES (EXTENDED) ─────────────────────────────────────────────

  'MARKET': sign('MARKET','C-hands wave side to side','Both C-hands wave from side-to-side — busy market',4,
    {x:-0.52,y:0,z:-0.42},{x:-0.25,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {x:-0.52,y:0,z:0.42},{x:-0.25,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {j:'both_sh', ax:'z', amp:0.16, freq:1.5}),

  'SHOP': sign('SHOP','Both hands move forward like pushing trolley','Both flat-hands push forward — shop / store',4,
    {x:-0.55,y:0,z:-0.40},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.55,y:0,z:0.40},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:-0.12, freq:1.2}),

  'CLINIC': sign('CLINIC','C-hand at shoulder (cross/badge)','C-hand at shoulder area — clinic (medical cross reference)',5,
    {x:-0.58,y:0,z:-0.48},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL, null),

  'PRISON': sign('PRISON','V-hands form cage bars','Both V-hands crossed make cage bars — prison',4,
    {x:-0.52,y:0,z:-0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    {x:-0.52,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    null),

  // ── VERBS (EXTENDED) ─────────────────────────────────────────────

  'BRING': sign('BRING','Both flat hands carry forward','Both flat hands carry object forward — bring',4,
    {x:-0.52,y:0,z:-0.38},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.52,y:0,z:0.38},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:-0.12, freq:1.2}),

  'COOK': sign('COOK','Both hands toss food in pan','Both flat-hands toss upward alternately — cooking',4,
    {x:-0.52,y:0,z:-0.40},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.52,y:0,z:0.40},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:-0.15, freq:1.8}),

  'BUY': sign('BUY','Flat hand scoops from palm','Flat hand scoops forward from flat left palm (paying) — buy',4,
    {x:-0.62,y:0,z:-0.30},{x:-0.32,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.58,y:0,z:0.38},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:-0.10, freq:1.5}),

  'CALL': sign('CALL','Y-hand at ear (phone)','Y-hand (thumb at ear, pinky at mouth) — phone call',5,
    {x:-1.28,y:0,z:-0.20},{x:-0.16,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    IL.sh,IL.el,IL.wr, NL, null),

  'THANK': sign('THANK','Flat hand at chin moves forward','Flat hand at chin, sweeps forward — thank (less formal)',4,
    {x:-1.12,y:0,z:-0.10},{x:-0.10,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:-0.12, freq:1.0}),

  'PRAY': sign('PRAY','Both flat hands pressed together at chest','Both flat-hands pressed together at chest — pray / prayer',4,
    {x:-0.55,y:0,z:-0.20},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.55,y:0,z:0.20},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.06, freq:1.5}),

  'THINK': sign('THINK','Index circles at temple','Index finger circles at temple — think / consider',4,
    {x:-1.28,y:0,z:-0.18},{x:-0.16,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.08, freq:2.5}),

  'REMEMBER': sign('REMEMBER','Both thumbs touch forehead then sternum','Thumb touches forehead then chest — remember',4,
    {x:-1.42,y:0,z:-0.10},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.16, freq:1.0}),

  'FORGET': sign('FORGET','Flat hand wipes forehead outward','Flat hand wipes across forehead and flicks away — forget',4,
    {x:-1.42,y:0,z:-0.14},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.18, freq:1.2}),

  'LEARN': sign('LEARN','Fingers gather from palm to forehead','Open hand on flat palm, gather to forehead — learn',4,
    {x:-1.38,y:0,z:-0.12},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.58,y:0,z:0.38},{x:-0.38,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:-0.12, freq:1.0}),

  'TEACH': sign('TEACH','Both hands push knowledge outward','Both hands at temples push forward — teach / explain',4,
    {x:-1.30,y:0,z:-0.28},{x:-0.25,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    {x:-1.30,y:0,z:0.28},{x:-0.25,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    {j:'both_sh', ax:'x', amp:-0.14, freq:1.2}),

  'FIND': sign('FIND','F-hand pinches upward from palm','F-hand picks up from flat palm — find / discover',4,
    {x:-0.62,y:0,z:-0.30},{x:-0.32,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    {x:-0.58,y:0,z:0.38},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:-0.10, freq:1.5}),

  'LOSE': sign('LOSE','Both open hands drop open','Both flat-hands drop opening downward — lose / lost',4,
    {x:-0.52,y:0,z:-0.38},{x:-0.28,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.52,y:0,z:0.38},{x:-0.28,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.14, freq:1.0}),

  // ── RIGHTS & SOCIAL JUSTICE (extended) ──────────────────────────
  // Source: Einstein Hands Safety/Rights categories

  'VOTE': sign('VOTE','F-hand drops into slot','F-hand drops downward (voting in ballot box) — vote',4,
    {x:-0.55,y:0,z:-0.28},{x:-0.45,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.14, freq:1.2}),

  'PROTECT': sign('PROTECT','Both fists cross at chest','Both S-fists cross at wrists at chest — protect / shield',4,
    {x:-0.55,y:0,z:-0.28},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.55,y:0,z:0.28},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    null),

  'ABUSE': sign('ABUSE','Fist strikes down on palm','Right fist strikes down on left flat palm — abuse / violence',4,
    {x:-0.55,y:0,z:-0.28},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.58,y:0,z:0.38},{x:-0.42,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.18, freq:1.5}),

  'ACCEPT': sign('ACCEPT','Both hands pull inward to chest','Both open hands pull inward toward chest — accept',4,
    {x:-0.52,y:0,z:-0.40},{x:-0.28,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.52,y:0,z:0.40},{x:-0.28,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'z', amp:-0.16, freq:1.0}),

  'REFUSE': sign('REFUSE','A-fist sweeps outward sharply','A-fist sweeps outward from chin — refuse / reject',5,
    {x:-1.18,y:0,z:-0.12},{x:-0.10,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:-0.18, freq:1.5}),

};

// ═══════════════════════════════════════════════════════════════════
// SECTION 10.5 — MOTION ENHANCEMENTS
// ─────────────────────────────────────────────────────────────────
// Many SASL signs require a specific movement path — not just a
// static held pose. These are linguistically required:
//
//   tap    — one contact and return (PLEASE, THANK YOU touch body)
//   arc    — parabolic path peaking at midpoint (HELP lifts up)
//   circle — closed loop over the hold duration (SORRY, THINK)
//
// Applied on top of the pose in avatar.js HOLDING state.
// ═══════════════════════════════════════════════════════════════════
;(function _applyMotionEnhancements() {
  const M = {
    // PLEASE: flat palm circles on chest — circle on shoulder y+z
    'PLEASE':    { type: 'circle', joint: 'R_sh',    axis: 'y', amp: 0.10, freq: 1.2 },
    // THANK YOU: flat palm sweeps from chin forward — single forward arc
    'THANK YOU': { type: 'arc',    joint: 'R_sh',    axis: 'x', amp:-0.14, freq: 1.0 },
    // SORRY: A-hand rubs circles on cheek — circle on shoulder x+z
    'SORRY':     { type: 'circle', joint: 'R_sh',    axis: 'x', amp: 0.07, freq: 1.2 },
    // HELP: fist on palm, both arms lift in arc upward
    'HELP':      { type: 'arc',    joint: 'both_sh', axis: 'x', amp:-0.20, freq: 1.0 },
    // EAT: hand moves toward mouth — tap elbow (forearm raises toward face)
    'EAT':       { type: 'tap',    joint: 'R_el',    axis: 'x', amp:-0.15, freq: 1.0 },
    // DRINK: cup hand tilts toward mouth
    'DRINK':     { type: 'tap',    joint: 'R_el',    axis: 'x', amp:-0.18, freq: 1.0 },
    // MORNING: forearm rises from horizontal — upward arc
    'MORNING':   { type: 'arc',    joint: 'R_sh',    axis: 'x', amp:-0.16, freq: 1.0 },
    // WASH: both hands rub together — circle on both wrists
    'WASH':      { type: 'circle', joint: 'both_wr', axis: 'y', amp: 0.18, freq: 1.5 },
    // HUG: arms draw in — arc both shoulders inward
    'HUG':       { type: 'arc',    joint: 'both_sh', axis: 'z', amp: 0.12, freq: 1.0 },
    // WRITE: index traces on palm — circle on wrist
    'WRITE':     { type: 'circle', joint: 'R_wr',    axis: 'y', amp: 0.14, freq: 2.0 },
    // KNOW: tap fingertips to forehead
    'KNOW':         { type: 'tap',    joint: 'R_el',    axis: 'x', amp:-0.10, freq: 1.0 },
    // THINK: index at temple circles
    'THINK':        { type: 'circle', joint: 'R_sh',    axis: 'z', amp: 0.05, freq: 2.0 },
    // TEA: cup lifts to mouth — tap forearm up
    'TEA':          { type: 'tap',    joint: 'R_el',    axis: 'x', amp:-0.14, freq: 1.0 },
    // REMEMBER: tap forehead then chest — arc shoulder down
    'REMEMBER':     { type: 'arc',    joint: 'R_sh',    axis: 'x', amp: 0.18, freq: 1.0 },
    // LEARN: fingers gather from palm to forehead — arc shoulder up
    'LEARN':        { type: 'arc',    joint: 'R_sh',    axis: 'x', amp:-0.14, freq: 1.0 },
    // TEACH: push forward from temples
    'TEACH':        { type: 'arc',    joint: 'both_sh', axis: 'x', amp:-0.16, freq: 1.0 },
    // PRAY: press and gentle rock
    'PRAY':         { type: 'circle', joint: 'R_sh',    axis: 'y', amp: 0.05, freq: 1.2 },
    // COOK: tossing motion
    'COOK':         { type: 'circle', joint: 'both_wr', axis: 'x', amp: 0.15, freq: 1.8 },
    // SOAP: rub both hands together
    'SOAP':         { type: 'circle', joint: 'both_wr', axis: 'y', amp: 0.14, freq: 2.0 },
    // SHOWER: rain down from above
    'SHOWER':       { type: 'arc',    joint: 'R_sh',    axis: 'x', amp: 0.14, freq: 1.5 },
    // BATH: scrubbing up and down torso
    'BATH':         { type: 'circle', joint: 'both_sh', axis: 'x', amp: 0.16, freq: 1.8 },
    // BREATHE: slow in-out arc
    'BREATHE':      { type: 'arc',    joint: 'both_sh', axis: 'z', amp:-0.12, freq: 1.2 },
    // VOTE: drop into ballot box
    'VOTE':         { type: 'tap',    joint: 'R_sh',    axis: 'x', amp: 0.16, freq: 1.2 },
    // BUY: scoop from palm
    'BUY':          { type: 'tap',    joint: 'R_sh',    axis: 'x', amp:-0.12, freq: 1.5 },
    // BRING: carry forward arc
    'BRING':        { type: 'arc',    joint: 'both_sh', axis: 'x', amp:-0.14, freq: 1.0 },
    // GOOD MORNING: arm rises
    'GOOD MORNING': { type: 'arc',    joint: 'R_sh',    axis: 'x', amp:-0.18, freq: 1.0 },
    // GOOD NIGHT: arm settles down
    'GOOD NIGHT':   { type: 'arc',    joint: 'R_sh',    axis: 'x', amp: 0.16, freq: 0.8 },
    // FORGET: wipe across forehead
    'FORGET':       { type: 'arc',    joint: 'R_sh',    axis: 'z', amp: 0.20, freq: 1.2 },
    // FIND: pinch lift from palm
    'FIND':         { type: 'tap',    joint: 'R_sh',    axis: 'x', amp:-0.12, freq: 1.5 },
  };
  Object.keys(M).forEach(function (k) {
    if (SIGN_LIBRARY[k]) SIGN_LIBRARY[k].motion = M[k];
  });
}());

// ═══════════════════════════════════════════════════════════════════
// SECTION 10.6 — HAND ROLES
// ─────────────────────────────────────────────────────────────────
// Many SASL signs use one hand as a static BASE and the other as
// the ACTIVE hand doing the movement. The base hand should hold
// its position with only minimal breathing-level motion — not the
// full oscillation intended for the active hand.
//
//   active  — dominant hand, executes full motion
//   base    — non-dominant hand, holds reference position (minimal osc)
//   passive — both hands move, but one leads
// ═══════════════════════════════════════════════════════════════════
;(function _applyHandRoles() {
  const HR = {
    'HELP':        { R: 'active', L: 'base'    },
    'LEARN':       { R: 'active', L: 'base'    },
    'WORK':        { R: 'active', L: 'base'    },
    'WRITE':       { R: 'active', L: 'base'    },
    'READ':        { R: 'active', L: 'base'    },
    'SHARE':       { R: 'active', L: 'base'    },
    'GIVE':        { R: 'active', L: 'passive' },
    'TEACH':       { R: 'active', L: 'base'    },
    'MAKE':        { R: 'active', L: 'base'    },
    'OPEN':        { R: 'active', L: 'base'    },
    'CLOSE':       { R: 'active', L: 'base'    },
    // New verbs
    'FIND':        { R: 'active', L: 'base'    },
    'BUY':         { R: 'active', L: 'base'    },
    'BANANA':      { R: 'active', L: 'base'    },
    'MEAT':        { R: 'active', L: 'base'    },
    'CAKE':        { R: 'active', L: 'base'    },
    'INJECTION':   { R: 'active', L: 'base'    },
    'OPERATION':   { R: 'active', L: 'base'    },
    'BLOOD':       { R: 'active', L: 'base'    },
    'WEEK':        { R: 'active', L: 'base'    },
    'MONTH':       { R: 'active', L: 'base'    },
    'CHICKEN':     { R: 'active', L: 'base'    },
    'ABUSE':       { R: 'active', L: 'base'    },
    'BRING':       { R: 'passive', L: 'passive' },
    'COOK':        { R: 'passive', L: 'passive' },
  };
  Object.keys(HR).forEach(function (k) {
    if (SIGN_LIBRARY[k]) SIGN_LIBRARY[k].hand_roles = HR[k];
  });
}());

// ═══════════════════════════════════════════════════════════════════
// SECTION 11 — FINGERSPELLING
// ═══════════════════════════════════════════════════════════════════
const FINGERSPELL_POSITION = {
  sh:{x:-0.85,y:0,z:-0.28}, el:{x:-0.50,y:0,z:0}, wr:{x:0,y:0,z:0}
};

const ALPHABET = {
  // Each letter must map to a visually distinct handshape — no two letters share a shape.
  'A': HS.fist_A, 'B': HS.flat,   'C': HS.chand,
  'D': HS.d_hs,   'E': HS.claw,   'F': HS.fhand,
  'G': HS.ghand,  'H': HS.uhand,  'I': HS.i_hs,
  'J': HS.i_hs,   'K': HS.k_hs,   'L': HS.lhand,
  'M': HS.whand,  'N': HS.n_hs,   'O': HS.chand,
  'P': HS.p_hs,   'Q': HS.ghand,  'R': HS.r_hs,
  'S': HS.fist_S, 'T': HS.thand,  'U': HS.uhand,
  'V': HS.vhand,  'W': HS.whand,  'X': HS.xhand,
  'Y': HS.yhand,  'Z': HS.point1,
};

// ═══════════════════════════════════════════════════════════════════
// SECTION 12 — WORD NORMALISATION MAP (unchanged from v1)
// ═══════════════════════════════════════════════════════════════════
const WORD_MAP = {
  // Greetings
  'hi': 'HELLO', 'hey': 'HELLO', 'greetings': 'HELLO', 'howzit': 'HELLO',
  'bye': 'GOODBYE', 'see you': 'GOODBYE', 'take care': 'GOODBYE', 'farewell': 'GOODBYE',
  'thanks': 'THANK YOU', 'thank': 'THANK YOU', 'cheers': 'THANK YOU',
  'please': 'PLEASE', 'pls': 'PLEASE',
  'ok': 'YES', 'okay': 'YES', 'yep': 'YES', 'yup': 'YES', 'correct': 'YES', 'right': 'YES', 'affirmative': 'YES',
  'nope': 'NO', 'nah': 'NO', 'not': 'NO',
  'sorry': 'SORRY', 'apologies': 'SORRY', 'my bad': 'SORRY',

  // Medical
  'doctor': 'DOCTOR', 'dr': 'DOCTOR', 'physician': 'DOCTOR',
  'nurse': 'NURSE', 'nursing': 'NURSE',
  'hospital': 'HOSPITAL', 'emergency room': 'HOSPITAL',
  'sick': 'SICK', 'ill': 'SICK', 'unwell': 'SICK', 'nauseous': 'SICK',
  'pain': 'PAIN', 'painful': 'PAIN', 'sore': 'PAIN', 'hurt': 'HURT', 'hurts': 'HURT', 'ache': 'PAIN',
  'ambulance': 'AMBULANCE',
  'medicine': 'MEDICINE', 'medication': 'MEDICINE', 'pills': 'MEDICINE', 'tablet': 'MEDICINE',
  'fire': 'FIRE', 'burning': 'FIRE',
  'dangerous': 'DANGEROUS', 'danger': 'DANGEROUS', 'hazard': 'DANGEROUS',
  'careful': 'CAREFUL', 'caution': 'CAREFUL', 'watch out': 'CAREFUL',
  'safe': 'SAFE', 'safety': 'SAFE',
  'emergency': 'EMERGENCY',
  'help': 'HELP', 'assist': 'HELP', 'assistance': 'HELP',

  // Emotions
  'happy': 'HAPPY', 'joyful': 'HAPPY', 'glad': 'HAPPY', 'joy': 'HAPPY', 'cheerful': 'HAPPY',
  'sad': 'SAD', 'unhappy': 'SAD', 'upset': 'SAD', 'depressed': 'SAD', 'miserable': 'SAD',
  'angry': 'ANGRY', 'mad': 'ANGRY', 'furious': 'ANGRY', 'annoyed': 'ANGRY',
  'scared': 'SCARED', 'afraid': 'SCARED', 'frightened': 'SCARED', 'fear': 'SCARED',
  'love': 'LOVE', 'loving': 'LOVE',
  'i love you': 'I LOVE YOU',
  'excited': 'EXCITED', 'exciting': 'EXCITED',
  'tired': 'TIRED', 'exhausted': 'TIRED', 'sleepy': 'TIRED', 'fatigue': 'TIRED',
  'hungry': 'HUNGRY', 'starving': 'HUNGRY',
  'thirsty': 'THIRSTY',
  'worried': 'WORRIED', 'anxious': 'WORRIED', 'nervous': 'WORRIED', 'stress': 'WORRIED',
  'proud': 'PROUD', 'confidence': 'PROUD',
  'confused': 'CONFUSED', 'confusing': 'CONFUSED',

  // Questions
  'who': 'WHO', 'what': 'WHAT', 'where': 'WHERE', 'when': 'WHEN', 'why': 'WHY', 'how': 'HOW', 'which': 'WHICH',

  // Pronouns
  'i': 'I', 'me': 'I', 'my': 'I', 'mine': 'I', 'myself': 'I',
  'you': 'YOU', 'your': 'YOU', 'yours': 'YOU',
  'we': 'WE', 'us': 'WE', 'our': 'WE',
  'they': 'THEY', 'them': 'THEY', 'their': 'THEY',

  // Actions
  'come': 'COME', 'comes': 'COME', 'coming': 'COME',
  'go': 'GO', 'going': 'GO', 'went': 'GO',
  'stop': 'STOP', 'halt': 'STOP',
  'wait': 'WAIT', 'hold on': 'WAIT',
  'repeat': 'REPEAT', 'again': 'REPEAT', 'say again': 'REPEAT',
  'understand': 'UNDERSTAND', 'understood': 'UNDERSTAND', 'got it': 'UNDERSTAND',
  'listen': 'LISTEN', 'hear': 'LISTEN',
  'look': 'LOOK', 'see': 'LOOK', 'watch': 'LOOK',
  'know': 'KNOW', 'knew': 'KNOW', 'knowledge': 'KNOW',
  'want': 'WANT', 'need': 'WANT', 'needs': 'WANT', 'require': 'WANT',
  'give': 'GIVE', 'gave': 'GIVE',
  'eat': 'EAT', 'eating': 'EAT', 'ate': 'EAT', 'food': 'FOOD',
  'drink': 'DRINK', 'drinking': 'DRINK', 'drank': 'DRINK', 'water': 'WATER',
  'sleep': 'SLEEP', 'sleeping': 'SLEEP', 'slept': 'SLEEP',
  'sit': 'SIT', 'sitting': 'SIT', 'sat': 'SIT', 'seat': 'SIT',
  'stand': 'STAND', 'standing': 'STAND', 'stood': 'STAND',
  'walk': 'WALK', 'walking': 'WALK', 'walked': 'WALK',
  'run': 'RUN', 'running': 'RUN', 'ran': 'RUN',
  'work': 'WORK', 'working': 'WORK', 'worked': 'WORK', 'job': 'WORK',
  'wash': 'WASH', 'washing': 'WASH',
  'write': 'WRITE', 'writing': 'WRITE', 'wrote': 'WRITE',
  'read': 'READ', 'reading': 'READ',
  'open': 'OPEN', 'opened': 'OPEN',
  'close': 'CLOSE', 'closed': 'CLOSE', 'shut': 'CLOSE',
  'tell': 'TELL', 'told': 'TELL', 'say': 'TELL', 'said': 'TELL', 'speak': 'TELL', 'talk': 'TELL',
  'laugh': 'LAUGH', 'laughing': 'LAUGH',
  'cry': 'CRY', 'crying': 'CRY', 'tears': 'CRY',
  'hug': 'HUG', 'hugging': 'HUG',
  'sign': 'SIGN', 'signing': 'SIGN',

  // Descriptions
  'good': 'GOOD', 'great': 'GOOD', 'nice': 'GOOD', 'fine': 'GOOD', 'well': 'GOOD',
  "i'm fine": "I'M FINE", 'im fine': "I'M FINE",
  'bad': 'BAD', 'terrible': 'BAD', 'awful': 'BAD', 'wrong': 'BAD',
  'big': 'BIG', 'large': 'BIG', 'huge': 'BIG',
  'small': 'SMALL', 'little': 'SMALL', 'tiny': 'SMALL',
  'hot': 'HOT', 'warm': 'HOT',
  'cold': 'COLD', 'cool': 'COLD', 'freezing': 'COLD',
  'quiet': 'QUIET', 'silent': 'QUIET', 'shh': 'QUIET',
  'fast': 'FAST', 'quick': 'FAST', 'quickly': 'FAST',
  'slow': 'SLOW', 'slowly': 'SLOW',
  'yes': 'YES', 'no': 'NO',

  // Places
  'school': 'SCHOOL', 'class': 'SCHOOL', 'classroom': 'SCHOOL',
  'home': 'HOME', 'house': 'HOME',
  'church': 'CHURCH',
  'police': 'POLICE', 'cop': 'POLICE',
  'teacher': 'TEACHER', 'instructor': 'TEACHER',

  // Family
  'family': 'FAMILY',
  'mom': 'MOM', 'mother': 'MOM', 'mama': 'MOM', 'mum': 'MOM',
  'dad': 'DAD', 'father': 'DAD', 'papa': 'DAD',
  'baby': 'BABY', 'infant': 'BABY',
  'friend': 'FRIEND', 'buddy': 'FRIEND', 'mate': 'FRIEND',
  'child': 'CHILD', 'kid': 'CHILD', 'children': 'CHILD',
  'person': 'PERSON', 'people': 'PERSON', 'man': 'PERSON', 'woman': 'PERSON',

  // Nature
  'rain': 'RAIN', 'raining': 'RAIN', 'rainy': 'RAIN',
  'sun': 'SUN', 'sunny': 'SUN', 'sunshine': 'SUN',
  'wind': 'WIND', 'windy': 'WIND',
  'tree': 'TREE', 'trees': 'TREE',

  // Money
  'money': 'MONEY', 'cash': 'MONEY', 'rand': 'MONEY', 'cost': 'MONEY', 'pay': 'MONEY',
  'free': 'FREE', 'no charge': 'FREE',
  'expensive': 'EXPENSIVE', 'costly': 'EXPENSIVE',

  // Transport
  'car': 'CAR', 'vehicle': 'CAR', 'drive': 'CAR',
  'taxi': 'TAXI', 'minibus': 'TAXI', 'uber': 'TAXI',
  'bus': 'BUS',

  // Rights
  'rights': 'RIGHTS', 'right': 'RIGHTS',
  'law': 'LAW', 'legal': 'LAW', 'legislation': 'LAW',
  'equal': 'EQUAL', 'equality': 'EQUAL', 'fair': 'EQUAL',
  'share': 'SHARE', 'sharing': 'SHARE',

  // Time
  'today': 'TODAY', 'now': 'NOW', 'currently': 'NOW',
  'yesterday': 'YESTERDAY', 'last night': 'YESTERDAY', 'the other day': 'YESTERDAY',
  'tomorrow': 'TOMORROW', 'next day': 'TOMORROW',
  'later': 'LATER', 'after': 'LATER', 'soon': 'LATER', 'eventually': 'LATER',
  'morning': 'MORNING', 'afternoon': 'MORNING', 'evening': 'NIGHT',
  'night': 'NIGHT', 'tonight': 'NIGHT',

  // Grammar markers
  'finish': 'FINISH', 'finished': 'FINISH', 'done': 'FINISH',
  'already': 'FINISH', 'complete': 'FINISH', 'completed': 'FINISH',
  'will': 'WILL', 'future': 'WILL', 'shall': 'WILL',
  'not': 'NOT', "don't": 'NOT', 'dont': 'NOT',
  'never': 'NOT', 'cannot': 'NOT', "can't": 'NOT', 'cant': 'NOT',
  'can': 'CAN', 'able': 'CAN', 'could': 'CAN', 'capable': 'CAN',
  'must': 'MUST', 'should': 'MUST', 'have to': 'MUST',
  'very': 'VERY', 'really': 'VERY', 'extremely': 'VERY',
  'also': 'ALSO', 'too': 'ALSO', 'as well': 'ALSO',

  // Descriptions
  'new': 'NEW', 'novel': 'NEW', 'fresh': 'NEW', 'modern': 'NEW',
  'old': 'OLD', 'elderly': 'OLD', 'aged': 'OLD', 'ancient': 'OLD',

  // Greetings continued
  "how are you": 'HOW ARE YOU', 'howzit': 'HOW ARE YOU',

  // ── Colours ─────────────────────────────────────────────────────────
  'red': 'RED', 'colour red': 'RED',
  'blue': 'BLUE', 'colour blue': 'BLUE',
  'green': 'GREEN', 'colour green': 'GREEN',
  'yellow': 'YELLOW', 'colour yellow': 'YELLOW',
  'black': 'BLACK', 'colour black': 'BLACK',
  'white': 'WHITE', 'colour white': 'WHITE',
  'orange': 'ORANGE', 'colour orange': 'ORANGE',
  'pink': 'PINK', 'colour pink': 'PINK',
  'purple': 'PURPLE', 'colour purple': 'PURPLE', 'violet': 'PURPLE',
  'brown': 'BROWN', 'colour brown': 'BROWN',

  // ── Days of the week ─────────────────────────────────────────────────
  'monday': 'MONDAY', 'mon': 'MONDAY',
  'tuesday': 'TUESDAY', 'tue': 'TUESDAY', 'tues': 'TUESDAY',
  'wednesday': 'WEDNESDAY', 'wed': 'WEDNESDAY',
  'thursday': 'THURSDAY', 'thu': 'THURSDAY', 'thur': 'THURSDAY',
  'friday': 'FRIDAY', 'fri': 'FRIDAY',
  'saturday': 'SATURDAY', 'sat': 'SATURDAY',
  'sunday': 'SUNDAY', 'sun': 'SUNDAY',
  'week': 'WEEK', 'weekly': 'WEEK',
  'month': 'MONTH', 'monthly': 'MONTH',
  'year': 'YEAR', 'yearly': 'YEAR', 'annual': 'YEAR',
  'birthday': 'BIRTHDAY', 'born': 'BIRTHDAY', 'bday': 'BIRTHDAY',
  'holiday': 'HOLIDAY', 'vacation': 'HOLIDAY', 'leave': 'HOLIDAY',

  // ── Animals ──────────────────────────────────────────────────────────
  'cat': 'CAT', 'kitten': 'CAT', 'kitty': 'CAT',
  'dog': 'DOG', 'puppy': 'DOG', 'hound': 'DOG',
  'fish': 'FISH', 'fishes': 'FISH',
  'bird': 'BIRD', 'birds': 'BIRD',
  'elephant': 'ELEPHANT', 'elephants': 'ELEPHANT',
  'lion': 'LION', 'lions': 'LION',
  'horse': 'HORSE', 'horses': 'HORSE',
  'cow': 'COW', 'bull': 'COW', 'cows': 'COW',
  'rabbit': 'RABBIT', 'bunny': 'RABBIT', 'hare': 'RABBIT',
  'snake': 'SNAKE', 'snakes': 'SNAKE',
  'butterfly': 'BUTTERFLY', 'butterflies': 'BUTTERFLY',
  'monkey': 'MONKEY', 'ape': 'MONKEY',
  'crocodile': 'CROCODILE', 'croc': 'CROCODILE', 'alligator': 'CROCODILE',
  'bear': 'BEAR', 'bears': 'BEAR',
  'chicken': 'CHICKEN', 'hen': 'CHICKEN', 'rooster': 'CHICKEN',
  'frog': 'FROG', 'frogs': 'FROG',
  'pig': 'PIG', 'pigs': 'PIG', 'piglet': 'PIG',
  'duck': 'DUCK', 'ducks': 'DUCK',

  // ── Bath & Hygiene ───────────────────────────────────────────────────
  'shower': 'SHOWER', 'showering': 'SHOWER',
  'bath': 'BATH', 'bathing': 'BATH', 'bathe': 'BATH',
  'soap': 'SOAP', 'lather': 'SOAP',
  'toothbrush': 'TOOTHBRUSH', 'brush teeth': 'TOOTHBRUSH', 'toothpaste': 'TOOTHBRUSH',
  'towel': 'TOWEL', 'dry off': 'TOWEL',
  'toilet': 'TOILET', 'bathroom': 'TOILET', 'restroom': 'TOILET', 'loo': 'TOILET',

  // ── Food & Drink ─────────────────────────────────────────────────────
  'milk': 'MILK',
  'apple': 'APPLE', 'apples': 'APPLE',
  'banana': 'BANANA', 'bananas': 'BANANA',
  'egg': 'EGG', 'eggs': 'EGG',
  'rice': 'RICE',
  'meat': 'MEAT', 'beef': 'MEAT', 'chicken meat': 'MEAT', 'pork': 'MEAT',
  'cake': 'CAKE', 'cakes': 'CAKE',
  'coffee': 'COFFEE',
  'tea': 'TEA',
  'fruit': 'FRUIT', 'fruits': 'FRUIT',
  'sugar': 'SUGAR', 'sugary': 'SUGAR',
  'sweet': 'SWEET', 'sweets': 'SWEET', 'candy': 'SWEET', 'lollipop': 'SWEET',
  'vegetable': 'VEGETABLE', 'vegetables': 'VEGETABLE', 'veggie': 'VEGETABLE', 'veggies': 'VEGETABLE',

  // ── Clothing ─────────────────────────────────────────────────────────
  'shirt': 'SHIRT', 'blouse': 'SHIRT', 't-shirt': 'SHIRT', 'tshirt': 'SHIRT',
  'shoes': 'SHOES', 'shoe': 'SHOES', 'boots': 'SHOES', 'sneakers': 'SHOES',
  'hat': 'HAT', 'cap': 'HAT', 'beanie': 'HAT',
  'dress': 'DRESS', 'skirt': 'DRESS', 'gown': 'DRESS',
  'jacket': 'JACKET', 'coat': 'JACKET', 'jersey': 'JACKET',
  'uniform': 'UNIFORM', 'school uniform': 'UNIFORM',

  // ── Numbers ──────────────────────────────────────────────────────────
  'one': 'ONE', '1': 'ONE',
  'two': 'TWO', '2': 'TWO',
  'three': 'THREE', '3': 'THREE',
  'four': 'FOUR', '4': 'FOUR',
  'five': 'FIVE', '5': 'FIVE',
  'six': 'SIX', '6': 'SIX',
  'seven': 'SEVEN', '7': 'SEVEN',
  'eight': 'EIGHT', '8': 'EIGHT',
  'nine': 'NINE', '9': 'NINE',
  'ten': 'TEN', '10': 'TEN',

  // ── Transport ────────────────────────────────────────────────────────
  'train': 'TRAIN', 'trains': 'TRAIN', 'railway': 'TRAIN', 'metro': 'TRAIN',
  'aeroplane': 'AEROPLANE', 'airplane': 'AEROPLANE', 'plane': 'AEROPLANE', 'flight': 'AEROPLANE',
  'bicycle': 'BICYCLE', 'bike': 'BICYCLE', 'cycle': 'BICYCLE',

  // ── Sport ────────────────────────────────────────────────────────────
  'soccer': 'SOCCER', 'football': 'SOCCER',
  'swimming': 'SWIMMING', 'swim': 'SWIMMING',
  'cricket': 'CRICKET',

  // ── Basic conversation ───────────────────────────────────────────────
  'deaf': 'DEAF', 'hard of hearing': 'DEAF',
  'hearing': 'HEARING', 'hearing person': 'HEARING',
  'name': 'NAME', 'named': 'NAME', 'called': 'NAME',
  'good morning': 'GOOD MORNING', 'morning greeting': 'GOOD MORNING',
  'good night': 'GOOD NIGHT', 'goodnight': 'GOOD NIGHT',
  'sign language': 'SIGN LANGUAGE', 'sasl': 'SIGN LANGUAGE', 'asl': 'SIGN LANGUAGE',

  // ── Medical (extended) ───────────────────────────────────────────────
  'pregnant': 'PREGNANT', 'pregnancy': 'PREGNANT', 'expecting': 'PREGNANT',
  'blood': 'BLOOD', 'bleeding': 'BLOOD',
  'fever': 'FEVER', 'temperature': 'FEVER', 'high temperature': 'FEVER',
  'dizzy': 'DIZZY', 'dizziness': 'DIZZY', 'lightheaded': 'DIZZY', 'faint': 'DIZZY',
  'broken': 'BROKEN', 'fracture': 'BROKEN', 'fractured': 'BROKEN',
  'breathe': 'BREATHE', 'breathing': 'BREATHE', 'breath': 'BREATHE',
  'chest': 'CHEST', 'chest pain': 'CHEST',
  'vomit': 'VOMIT', 'vomiting': 'VOMIT', 'nausea': 'VOMIT', 'throw up': 'VOMIT',
  'headache': 'HEADACHE', 'head pain': 'HEADACHE', 'migraine': 'HEADACHE',
  'allergy': 'ALLERGY', 'allergic': 'ALLERGY', 'sneeze': 'ALLERGY',
  'injection': 'INJECTION', 'shot': 'INJECTION', 'vaccine': 'INJECTION', 'vaccinated': 'INJECTION',
  'operation': 'OPERATION', 'surgery': 'OPERATION', 'operate': 'OPERATION',

  // ── Emotions (extended) ──────────────────────────────────────────────
  'bored': 'BORED', 'boring': 'BORED', 'boredom': 'BORED',
  'jealous': 'JEALOUS', 'envy': 'JEALOUS', 'envious': 'JEALOUS',
  'disappointed': 'DISAPPOINTED', 'disappointment': 'DISAPPOINTED', 'let down': 'DISAPPOINTED',
  'embarrassed': 'EMBARRASSED', 'embarrassing': 'EMBARRASSED', 'shame': 'EMBARRASSED', 'ashamed': 'EMBARRASSED',
  'nervous': 'NERVOUS', 'nerves': 'NERVOUS',

  // ── Descriptions (extended) ──────────────────────────────────────────
  'beautiful': 'BEAUTIFUL', 'pretty': 'BEAUTIFUL', 'gorgeous': 'BEAUTIFUL', 'lovely': 'BEAUTIFUL',
  'ugly': 'UGLY', 'unattractive': 'UGLY',
  'clean': 'CLEAN', 'neat': 'CLEAN', 'tidy': 'CLEAN',
  'dirty': 'DIRTY', 'messy': 'DIRTY', 'filthy': 'DIRTY',
  'heavy': 'HEAVY', 'overweight': 'HEAVY',
  'light': 'LIGHT', 'lightweight': 'LIGHT',
  'full': 'FULL', 'stuffed': 'FULL',

  // ── Places (extended) ────────────────────────────────────────────────
  'market': 'MARKET', 'marketplace': 'MARKET', 'bazaar': 'MARKET',
  'shop': 'SHOP', 'store': 'SHOP', 'shopping': 'SHOP',
  'clinic': 'CLINIC', 'health clinic': 'CLINIC', 'medical centre': 'CLINIC',
  'prison': 'PRISON', 'jail': 'PRISON',

  // ── Verbs (extended) ─────────────────────────────────────────────────
  'bring': 'BRING', 'brought': 'BRING', 'bringing': 'BRING',
  'cook': 'COOK', 'cooking': 'COOK', 'cooked': 'COOK', 'bake': 'COOK', 'baking': 'COOK',
  'buy': 'BUY', 'bought': 'BUY', 'purchase': 'BUY', 'purchasing': 'BUY',
  'call': 'CALL', 'phone': 'CALL', 'ring': 'CALL', 'calling': 'CALL',
  'pray': 'PRAY', 'prayer': 'PRAY', 'praying': 'PRAY',
  'think': 'THINK', 'thinking': 'THINK', 'thought': 'THINK',
  'remember': 'REMEMBER', 'remembering': 'REMEMBER', 'recall': 'REMEMBER',
  'forget': 'FORGET', 'forgot': 'FORGET', 'forgetting': 'FORGET',
  'learn': 'LEARN', 'learning': 'LEARN', 'study': 'LEARN', 'studying': 'LEARN',
  'teach': 'TEACH', 'teaching': 'TEACH', 'taught': 'TEACH', 'explain': 'TEACH',
  'find': 'FIND', 'found': 'FIND', 'discover': 'FIND',
  'lose': 'LOSE', 'lost': 'LOSE', 'missing': 'LOSE',

  // ── Rights & social justice ──────────────────────────────────────────
  'vote': 'VOTE', 'voting': 'VOTE', 'election': 'VOTE',
  'protect': 'PROTECT', 'protection': 'PROTECT', 'shield': 'PROTECT',
  'abuse': 'ABUSE', 'abused': 'ABUSE', 'violence': 'ABUSE',
  'accept': 'ACCEPT', 'accepted': 'ACCEPT', 'approve': 'ACCEPT',
  'refuse': 'REFUSE', 'refused': 'REFUSE', 'reject': 'REFUSE', 'rejected': 'REFUSE',
};

// ═══════════════════════════════════════════════════════════════════
// SECTION 13 — SENTENCE PARSER (unchanged from v1)
// ═══════════════════════════════════════════════════════════════════

function sentenceToSigns(text) {
  if (!text) return [];
  const result = [];
  const lower = text.toLowerCase().trim();
  const words = lower
    .replace(/[^a-z0-9'\s]/g, ' ')
    .split(/\s+/)
    .filter(w => w.length > 0);

  let i = 0;
  while (i < words.length) {
    if (i + 2 < words.length) {
      const phrase3 = words.slice(i, i+3).join(' ');
      const key3 = WORD_MAP[phrase3];
      if (key3 && SIGN_LIBRARY[key3]) { result.push(SIGN_LIBRARY[key3]); i += 3; continue; }
    }
    if (i + 1 < words.length) {
      const phrase2 = words.slice(i, i+2).join(' ');
      const key2 = WORD_MAP[phrase2];
      if (key2 && SIGN_LIBRARY[key2]) { result.push(SIGN_LIBRARY[key2]); i += 2; continue; }
    }
    const word = words[i];
    if (['the','a','an','is','are','was','were','be','been',
         'of','to','in','for','on','with','at','by','as',
         'it','its','this','that','and','but','or','so',
         'um','uh','ah','oh','hmm'].includes(word)) { i++; continue; }
    const mapped = WORD_MAP[word];
    if (mapped && SIGN_LIBRARY[mapped]) { result.push(SIGN_LIBRARY[mapped]); i++; continue; }
    const upper = word.toUpperCase();
    if (SIGN_LIBRARY[upper]) { result.push(SIGN_LIBRARY[upper]); i++; continue; }
    result.push(...fingerspell(word));
    i++;
  }
  return result;
}

function fingerspell(word) {
  const result = [];
  const fsBase = {
    sh: FINGERSPELL_POSITION.sh,
    el: FINGERSPELL_POSITION.el,
    wr: FINGERSPELL_POSITION.wr,
  };
  for (const char of word.toUpperCase()) {
    if (ALPHABET[char]) {
      const hand = ALPHABET[char];
      result.push({
        name: char,
        shape: `Letter ${char}`,
        desc: `Fingerspelling: ${char}`,
        conf: 3,
        R: { sh:fsBase.sh, el:fsBase.el, wr:fsBase.wr, hand },
        L: { sh:ARM.idle_L.sh, el:ARM.idle_L.el, wr:ARM.idle_L.wr, hand:HS.rest },
        _Rq: { end: armToQuat(fsBase), start: armToQuat(fsBase) },
        _Lq: { end: armToQuat(ARM.idle_L), start: armToQuat(ARM.idle_L) },
        osc: null,
        isFingerspell: true,
      });
    }
  }
  return result;
}

function getSign(word) {
  if (!word) return null;
  const lower = word.toLowerCase().trim();
  const mapped = WORD_MAP[lower];
  if (mapped) return SIGN_LIBRARY[mapped] || null;
  return SIGN_LIBRARY[word.toUpperCase().trim()] || null;
}

function getAllSignNames() { return Object.keys(SIGN_LIBRARY); }

function getSignsByCategory(category) {
  const categories = {
    MEDICAL:      ['DOCTOR','NURSE','HOSPITAL','SICK','PAIN','AMBULANCE','MEDICINE','HURT','EMERGENCY','CAREFUL','DANGEROUS','SAFE','FIRE'],
    GREETINGS:    ['HELLO','GOODBYE','HOW ARE YOU',"I'M FINE",'PLEASE','THANK YOU','SORRY','YES','NO'],
    EMOTIONS:     ['HAPPY','SAD','ANGRY','SCARED','LOVE','I LOVE YOU','EXCITED','TIRED','HUNGRY','THIRSTY','WORRIED','PROUD','CONFUSED'],
    QUESTIONS:    ['WHO','WHAT','WHERE','WHEN','WHY','HOW','WHICH'],
    ACTIONS:      ['HELP','WAIT','STOP','REPEAT','UNDERSTAND','COME','GO','LISTEN','LOOK','KNOW','WANT','GIVE','EAT','DRINK','SLEEP','SIT','STAND','WALK','RUN','WORK','WASH','WRITE','READ','SIGN','TELL','LAUGH','CRY','HUG','OPEN','CLOSE'],
    DESCRIPTIONS: ['GOOD','BAD','BIG','SMALL','HOT','COLD','QUIET','FAST','SLOW','WATER','NEW','OLD','VERY'],
    GRAMMAR:      ['FINISH','WILL','NOT','CAN','MUST','ALSO','YESTERDAY','TOMORROW','TODAY','NOW','LATER'],
    PLACES:       ['SCHOOL','HOME','HOSPITAL','CHURCH','POLICE'],
    FAMILY:       ['FAMILY','MOM','DAD','BABY','FRIEND','CHILD','PERSON'],
    RIGHTS:       ['RIGHTS','LAW','EQUAL','SHARE','FREE'],
    TRANSPORT:    ['CAR','TAXI','BUS'],
  };
  return (categories[category] || []).map(name => SIGN_LIBRARY[name]).filter(Boolean);
}

// ═══════════════════════════════════════════════════════════════════
// SECTION 14 — EXAMPLE: HOW TO USE TRANSITIONENGINE IN THREE.JS
// ═══════════════════════════════════════════════════════════════════
/**
 * Drop-in usage example for your Three.js animation loop.
 * Replace applyPoseToSkeleton() with your actual bone-setting code.
 *
 *   const signs = sentenceToSigns("Thank you please help");
 *   let signIndex = 0;
 *
 *   // Kick off the first transition from rest
 *   const restSign = { name:'rest', R:{sh:ARM.idle_R.sh,el:ARM.idle_R.el,wr:ARM.idle_R.wr,hand:HS.rest},
 *                      L:{sh:ARM.idle_L.sh,el:ARM.idle_L.el,wr:ARM.idle_L.wr,hand:HS.rest},
 *                      _Rq:{end:armToQuat(ARM.idle_R),start:armToQuat(ARM.idle_R)},
 *                      _Lq:{end:armToQuat(ARM.idle_L),start:armToQuat(ARM.idle_L)},
 *                      osc:null, isFingerspell:false };
 *
 *   TransitionEngine.begin(restSign, signs[0], signs[1], onTransitionDone);
 *
 *   function onTransitionDone() {
 *     signIndex++;
 *     if (signIndex < signs.length) {
 *       TransitionEngine.begin(
 *         signs[signIndex - 1],
 *         signs[signIndex],
 *         signs[signIndex + 1] || null,
 *         onTransitionDone
 *       );
 *     }
 *   }
 *
 *   // In your Three.js render loop:
 *   function animate() {
 *     requestAnimationFrame(animate);
 *     const delta = clock.getDelta();          // THREE.Clock
 *     const pose = TransitionEngine.tick(delta);
 *     if (pose) applyPoseToSkeleton(skeleton, pose);
 *     renderer.render(scene, camera);
 *   }
 *
 *   function applyPoseToSkeleton(skeleton, pose) {
 *     // Right arm
 *     skeleton.getBoneByName('RightArm').rotation.set(pose.R.sh.x, pose.R.sh.y, pose.R.sh.z);
 *     skeleton.getBoneByName('RightForeArm').rotation.set(pose.R.el.x, pose.R.el.y, pose.R.el.z);
 *     skeleton.getBoneByName('RightHand').rotation.set(pose.R.wr.x, pose.R.wr.y, pose.R.wr.z);
 *     // Left arm (same pattern)
 *     // Fingers: use pose.R.hand.i[0..2], .m[0..2], .r[0..2], .p[0..2], .t[0..1]
 *   }
 */

// ═══════════════════════════════════════════════════════════════════
// SECTION 15 — EXPORTS
// ═══════════════════════════════════════════════════════════════════
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    // Data
    SIGN_LIBRARY, WORD_MAP, ALPHABET, HS, ARM,
    JOINT_LIMITS, TRANSITION_HINTS,
    // Functions — core
    sentenceToSigns, fingerspell, getSign, getAllSignNames, getSignsByCategory,
    // Functions — transition engine (new in v2)
    TransitionEngine, getTransitionHint,
    // Functions — keyframe support (new in v3)
    signWithFrames, prebakeFrameQuats, findFrame, slerpBetweenFrames,
    // Functions — math utils (exposed for custom use)
    eulerToQuat, quatToEuler, slerp, normaliseQuat,
    lerpHandShape, slerpArmPose, armToQuat,
    Easing, applyJointLimits,
  };
}

if (typeof window !== 'undefined') {
  window.AMANDLA_SIGNS = {
    SIGN_LIBRARY, WORD_MAP, ALPHABET, HS, ARM,
    JOINT_LIMITS, TRANSITION_HINTS,
    sentenceToSigns, fingerspell, getSign, getAllSignNames, getSignsByCategory,
    TransitionEngine, getTransitionHint,
    signWithFrames, prebakeFrameQuats, findFrame, slerpBetweenFrames,
    eulerToQuat, quatToEuler, slerp, normaliseQuat,
    lerpHandShape, slerpArmPose, armToQuat,
    Easing, applyJointLimits,
  };
}
