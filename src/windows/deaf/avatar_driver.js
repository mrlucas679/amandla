/**
 * avatar_driver.js — AMANDLA Avatar Driver
 * ==========================================
 * Bridges AMANDLA sign pose data ↔ Mixamo GLB skeleton bones.
 *
 * Pipeline:
 *   signs_library.js  →  TransitionEngine.tick()  →  pose object
 *   pose object       →  AvatarDriver              →  bone rotations
 *   bone rotations    →  Three.js render loop      →  screen
 *
 * Must load after signs_library.js and three.js, before avatar.js.
 */

(function () {
  'use strict';

  // ── BONE MAP ──────────────────────────────────────────────────────────
  // Maps AMANDLA semantic joint names → Mixamo bone names inside the GLB.
  // The app uses window.AMANDLA_SIGNS_V2.BONE_MAP when signs_library_v2.js
  // is loaded; this is a self-contained fallback copy.
  const BONE_MAP = {
    head:  'mixamorigHead',
    neck:  'mixamorigNeck',
    torso: 'mixamorigSpine1',
    hips:  'mixamorigHips',

    R: {
      shoulder:    'mixamorigRightArm',
      elbow:       'mixamorigRightForeArm',
      wrist:       'mixamorigRightHand',
      forearmTwist:'mixamorigRightForeArmTwist',
      eye:         'mixamorigRightEye',
      fingers: {
        thumb:  ['mixamorigRightHandThumb1',  'mixamorigRightHandThumb2',  'mixamorigRightHandThumb3'],
        index:  ['mixamorigRightHandIndex1',  'mixamorigRightHandIndex2',  'mixamorigRightHandIndex3'],
        middle: ['mixamorigRightHandMiddle1', 'mixamorigRightHandMiddle2', 'mixamorigRightHandMiddle3'],
        ring:   ['mixamorigRightHandRing1',   'mixamorigRightHandRing2',   'mixamorigRightHandRing3'],
        pinky:  ['mixamorigRightHandPinky1',  'mixamorigRightHandPinky2',  'mixamorigRightHandPinky3'],
      },
    },

    L: {
      shoulder:    'mixamorigLeftArm',
      elbow:       'mixamorigLeftForeArm',
      wrist:       'mixamorigLeftHand',
      forearmTwist:'mixamorigLeftForeArmTwist',
      eye:         'mixamorigLeftEye',
      fingers: {
        thumb:  ['mixamorigLeftHandThumb1',  'mixamorigLeftHandThumb2',  'mixamorigLeftHandThumb3'],
        index:  ['mixamorigLeftHandIndex1',  'mixamorigLeftHandIndex2',  'mixamorigLeftHandIndex3'],
        middle: ['mixamorigLeftHandMiddle1', 'mixamorigLeftHandMiddle2', 'mixamorigLeftHandMiddle3'],
        ring:   ['mixamorigLeftHandRing1',   'mixamorigLeftHandRing2',   'mixamorigLeftHandRing3'],
        pinky:  ['mixamorigLeftHandPinky1',  'mixamorigLeftHandPinky2',  'mixamorigLeftHandPinky3'],
      },
    },

    faceMorphNames: ['Wolf3D_Head', 'CC_Base_Body', 'Head', 'head', 'Body'],
  };

  // ── MAP MIXAMO FINGERS FROM GLB ────────────────────────────────────
  // Returns the same finger array shape as buildFingers() in procedural rig.
  // fingers[0..4] = thumb/index/middle/ring/pinky, each with segments[0..2].pivot = bone.
  // boneMap parameter: pass the resolved (namespaced) bone map for the loaded rig.
  function mapMixamoFingers (model, side, boneMap) {
    var resolvedMap = boneMap || BONE_MAP;
    var order  = ['thumb', 'index', 'middle', 'ring', 'pinky'];
    var bMap   = resolvedMap[side].fingers;
    var NOOP   = { rotation: { x: 0, y: 0, z: 0 } };

    return order.map(function (name) {
      var boneNames = bMap[name];
      var segments  = boneNames.map(function (bn) {
        var bone = model.getObjectByName(bn);
        if (!bone) console.warn('[AvatarDriver] bone not found in GLB:', bn);
        return { pivot: bone || NOOP };
      });
      return { segments: segments };
    });
  }

  // ── BONE MAP: GALTIS RIG (SG ASL ADHD FBX — custom rig, not Mixamo) ──
  // From FBX inspection: Blender 3.6, 4.08s SASL animation, 60fps, 42,906 keyframes.
  // Has FK+IK dual chains and palm-level finger bones.
  // AMANDLA maps only the FK chain (Collar→Bicep→Forearm→Hand→fingers).
  const BONE_MAP_GALTIS = {
    head:  'Head',
    torso: 'Chest_2',
    hips:  'Hip',
    R: {
      shoulder:    'Bicep_R',
      elbow:       'Elbow_R',
      wrist:       'Hand_R',
      forearmTwist: null,   // Galtis rig has no twist bone
      fingers: {
        thumb:  ['Thumb1_R',  'Thumb2_R',  'Thumb3_R'],
        index:  ['Index1_R',  'Index2_R',  'Index3_R'],
        middle: ['Middle1_R', 'Middle2_R', 'Middle3_R'],
        ring:   ['Ring1_R',   'Ring2_R',   'Ring3_R'],
        pinky:  ['Pinky1_R',  'Pinky2_R',  'Pinky3_R'],
      },
    },
    L: {
      shoulder:    'Bicep_L',
      elbow:       'Elbow_L',
      wrist:       'Hand_L',
      forearmTwist: null,
      fingers: {
        thumb:  ['Thumb1_L',  'Thumb2_L',  'Thumb3_L'],
        index:  ['Index1_L',  'Index2_L',  'Index3_L'],
        middle: ['Middle1_L', 'Middle2_L', 'Middle3_L'],
        ring:   ['Ring1_L',   'Ring2_L',   'Ring3_L'],
        pinky:  ['Pinky1_L',  'Pinky2_L',  'Pinky3_L'],
      },
    },
    faceMorphNames: [],
  };

  // ── DETECT RIG TYPE FROM MODEL ─────────────────────────────────────
  // Inspects loaded GLTF model to determine which bone naming convention it uses.
  // Returns: 'mixamorig' | 'mixamorig2' | 'galtis' | 'unknown'
  function detectRigType (model) {
    var found = 'unknown';
    model.traverse(function (node) {
      if (found !== 'unknown') return;
      var n = node.name || '';
      if (n === 'mixamorigHips')          { found = 'mixamorig';  }
      else if (n === 'mixamorig2:Hips')   { found = 'mixamorig2'; }
      else if (n === 'Hip' || n === 'Galtis_Rig') { found = 'galtis'; }
    });
    return found;
  }

  // ── BUILD NAMESPACED BONE MAP ─────────────────────────────────────
  // Mixamo exports with namespace prefix (e.g. "mixamorig2:RightArm").
  // Re-writes all name strings in BONE_MAP to use the detected prefix.
  function namespacedBoneMap (rigType) {
    if (rigType === 'galtis')     return BONE_MAP_GALTIS;
    if (rigType === 'mixamorig2') {
      // Prefix every bone name with "mixamorig2:"
      return _prefixBoneMap(BONE_MAP, 'mixamorig2:');
    }
    return BONE_MAP; // standard mixamorig: — names already match
  }

  function _prefixBoneMap (map, prefix) {
    function prefixVal (v) {
      if (typeof v === 'string')  return prefix + v.replace(/^mixamorig:?/, '');
      if (Array.isArray(v))       return v.map(prefixVal);
      if (v && typeof v === 'object') {
        var out = {};
        Object.keys(v).forEach(function (k) { out[k] = prefixVal(v[k]); });
        return out;
      }
      return v;
    }
    return prefixVal(map);
  }

  // ── BIND BONES FROM LOADED GLTF ───────────────────────────────────
  // Populates avatarBones dict in-place from a loaded GLTF model.
  // Auto-detects rig type (mixamorig / mixamorig2 / galtis).
  function bindBonesFromGLTF (model, avatarBones) {
    var rigType  = detectRigType(model);
    var boneMap  = namespacedBoneMap(rigType);
    console.log('[AvatarDriver] detected rig:', rigType);

    // ── Core skeleton ──────────────────────────────────────────────
    avatarBones.head  = model.getObjectByName(boneMap.head)  || null;
    avatarBones.torso = model.getObjectByName(boneMap.torso) || null;
    avatarBones.hips  = model.getObjectByName(boneMap.hips)  || null;
    avatarBones._rigType = rigType;

    // ── Arms ───────────────────────────────────────────────────────
    for (var s = 0; s < 2; s++) {
      var side = s === 0 ? 'R' : 'L';
      var m    = boneMap[side];
      avatarBones[side] = {
        shoulder:   model.getObjectByName(m.shoulder)    || null,
        elbow:      model.getObjectByName(m.elbow)       || null,
        wrist:      model.getObjectByName(m.wrist)       || null,
        fingers:    mapMixamoFingers(model, side, boneMap),
        _twistBone: null,
      };
    }

    // ── Face morph mesh ─────────────────────────────────────────────
    var faceMorphMesh = null;
    var namedSet = new Set(boneMap.faceMorphNames || []);

    model.traverse(function (node) {
      if (!node.isMesh || !node.morphTargetDictionary) return;
      if (namedSet.has(node.name)) { faceMorphMesh = node; }
      else if (!faceMorphMesh)     { faceMorphMesh = node; }
    });

    avatarBones.faceMorphMesh = faceMorphMesh;
    avatarBones.face = { browL: null, browR: null, mouth: null };

    return avatarBones;
  }

  // ── REMAP POSE FOR MIXAMO ─────────────────────────────────────────
  // AMANDLA engine outputs Euler rotations with its own convention.
  // Mixamo bone axes differ:
  //   AMANDLA sh.x  → Mixamo shoulder .x  (elevation, same direction)
  //   AMANDLA sh.z  → Mixamo shoulder .z  (adduction, same direction)
  //   AMANDLA el.x  → Mixamo ForeArm  .y  (elbow bend; mirrored for left)
  //   AMANDLA wr.*  → Mixamo Hand.*        (direct map)
  // Returns nothing — modifies avatarBones rotations directly.
  function remapPoseForMixamo (pose, avatarBones) {
    if (!pose || !avatarBones) return;

    for (var s = 0; s < 2; s++) {
      var side    = s === 0 ? 'R' : 'L';
      var src     = pose[side];
      var arm     = avatarBones[side];
      if (!src || !arm) continue;

      // Shoulder — direct
      if (src.sh && arm.shoulder) {
        arm.shoulder.rotation.x = src.sh.x || 0;
        arm.shoulder.rotation.y = src.sh.y || 0;
        arm.shoulder.rotation.z = src.sh.z || 0;
      }

      // Elbow — AMANDLA el.x becomes Mixamo ForeArm rotation.y
      // Left arm is mirrored, so negate
      if (src.el && arm.elbow) {
        var elbowSign = (side === 'R') ? 1 : -1;
        arm.elbow.rotation.x = 0;
        arm.elbow.rotation.y = (src.el.x || 0) * elbowSign;
        arm.elbow.rotation.z = src.el.z || 0;
      }

      // Wrist — direct
      if (src.wr && arm.wrist) {
        arm.wrist.rotation.x = src.wr.x || 0;
        arm.wrist.rotation.y = src.wr.y || 0;
        arm.wrist.rotation.z = src.wr.z || 0;
      }
    }
  }

  // ── APPLY HANDSHAPE (GLTF) ────────────────────────────────────────
  // In Mixamo rigs, finger curl axis is .z (not .x as in procedural rig).
  function applyHandshapeGLTF (fingers, hs) {
    if (!hs || !fingers) return;
    var keys = ['t', 'i', 'm', 'r', 'p'];
    for (var f = 0; f < 5; f++) {
      var segs = hs[keys[f]];
      if (!segs || !fingers[f]) continue;
      for (var seg = 0; seg < 3 && seg < segs.length; seg++) {
        var joint = fingers[f].segments[seg];
        if (!joint || !joint.pivot) continue;
        joint.pivot.rotation.z = segs[seg] || 0;
      }
    }
  }

  // ── FOREARM TWIST UPDATE ──────────────────────────────────────────
  // Prevents "candy-wrapper" wrist twisting by sharing 50% of wrist
  // roll with the dedicated ForeArmTwist bone.
  function updateTwistBones (scene, avatarBones) {
    if (!avatarBones) return;
    for (var s = 0; s < 2; s++) {
      var side    = s === 0 ? 'R' : 'L';
      var arm     = avatarBones[side];
      if (!arm || !arm.wrist) continue;

      if (!arm._twistBone && scene) {
        var twistName = BONE_MAP[side].forearmTwist;
        scene.traverse(function (n) {
          if (n.name === twistName) arm._twistBone = n;
        });
      }

      if (arm._twistBone && arm.wrist) {
        arm._twistBone.rotation.y = arm.wrist.rotation.y * 0.5;
      }
    }
  }

  // ── EXPORTS ───────────────────────────────────────────────────────
  var AvatarDriver = {
    BONE_MAP:            BONE_MAP,
    mapMixamoFingers:    mapMixamoFingers,
    bindBonesFromGLTF:   bindBonesFromGLTF,
    remapPoseForMixamo:  remapPoseForMixamo,
    applyHandshapeGLTF:  applyHandshapeGLTF,
    updateTwistBones:    updateTwistBones,
  };

  if (typeof window !== 'undefined') window.AvatarDriver = AvatarDriver;
  if (typeof module !== 'undefined' && module.exports) module.exports = AvatarDriver;

  console.log('[AvatarDriver] loaded — BONE_MAP ready');

})();