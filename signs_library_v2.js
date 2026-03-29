/**
 * signs_library_v2.js — AMANDLA Sign Library Extension
 * =====================================================
 * Loaded AFTER signs_library.js.
 * Adds:
 *   1. BONE_MAP  — Mixamo GLB bone-name → AMANDLA semantic key
 *   2. armToQuat shim guard (if lib loaded out of order)
 *   3. Exports AMANDLA_SIGNS_V2 (superset of AMANDLA_SIGNS)
 *
 * All sign pose data + TransitionEngine live in signs_library.js.
 * This file only extends the namespace — do not duplicate sign entries here.
 */

(function () {
  'use strict';

  // ── BONE MAP ──────────────────────────────────────────────────────────
  // Canonical mapping: AMANDLA semantic joint → Mixamo bone name in GLB.
  // Used by AvatarDriver and avatar.js loadHumanAvatar().
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

    // Face morph mesh: try these names in order (RPM → CC4 → generic)
    faceMorphNames: ['Wolf3D_Head', 'CC_Base_Body', 'Head', 'head', 'Body'],
  };

  // ── ATTACH TO AMANDLA_SIGNS ───────────────────────────────────────────
  function attach () {
    const lib = (typeof window !== 'undefined' && window.AMANDLA_SIGNS)
             || (typeof global  !== 'undefined' && global.AMANDLA_SIGNS);

    if (!lib) {
      // Wait for signs_library.js to finish executing
      if (typeof setTimeout !== 'undefined') {
        setTimeout(attach, 80);
      }
      return;
    }

    lib.BONE_MAP = BONE_MAP;

    // AMANDLA_SIGNS_V2 is a superset reference — no data duplication
    const v2 = Object.assign({}, lib, { BONE_MAP, _v2: true });

    if (typeof window !== 'undefined') {
      window.AMANDLA_SIGNS      = lib;   // keep primary reference intact
      window.AMANDLA_SIGNS_V2   = v2;
    }
    if (typeof module !== 'undefined' && module.exports) {
      module.exports = v2;
    }
  }

  attach();

})();