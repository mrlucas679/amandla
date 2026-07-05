# TalkingHead API Quick Reference

Source: https://github.com/met4citizen/TalkingHead (v1.7)

## Import

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
<script type="module">
  import { TalkingHead } from "talkinghead";
</script>
```

## Constructor Options

```javascript
const head = new TalkingHead(domElement, {
  modelFPS: 30,                    // Target frame rate
  cameraView: "full",              // "full" | "mid" | "upper" | "head"
  cameraDistance: 0,               // Offset in meters
  avatarMood: "neutral",           // Initial mood
  avatarIdleEyeContact: 0.2,       // 0–1, proportion of eye contact while idle
  avatarSpeakingHeadMove: 0.5,     // 0–1, head movement while speaking
  lightAmbientIntensity: 2,
  lightDirectIntensity: 30,
});
```

## showAvatar Options

```javascript
await head.showAvatar({
  url: "./avatars/amandla-avatar.glb",  // REQUIRED — path to GLB
  body: "F",                            // "F" female | "M" male
  avatarMood: "neutral",
  lipsyncLang: "en",
  baseline: {
    headRotateX: -0.04,                 // Correct Avaturn head tilt
    eyeBlinkLeft: 0.1,                  // Slight natural lid droop
    eyeBlinkRight: 0.1,
  },
  retarget: {
    // Bone name corrections for Avaturn T2 skeleton
    Neck: { ry: 0 },
    LeftShoulder: { rz: 0.1 },
    RightShoulder: { rz: -0.1 },
  },
});
```

## Key Methods

```javascript
// Gestures (for SASL signs)
head.playGesture(name, durationSecs, mirror, transitionMs)
// name: key in head.gestureTemplates
// durationSecs: how long to hold
// mirror: true = use right hand instead of left
// transitionMs: blend time

head.stopGesture(transitionMs)
// Return to idle pose

// Moods
head.setMood("neutral" | "happy" | "angry" | "sad" | "fear" | "disgust" | "love" | "sleep")

// Poses (full body)
head.playPose(fbxUrl, onprogress, durationSecs)
head.stopPose()

// Animations (Mixamo FBX)
head.playAnimation(fbxUrl, onprogress, durationSecs)
head.stopAnimation()

// Eye contact
head.lookAt(x, y, durationMs)        // Look at screen position
head.lookAtCamera(durationMs)         // Look at viewer
head.makeEyeContact(durationMs)

// Speaking (not used for SASL signing)
head.speakText(text, options)
head.speakAudio(audioBuffer, options)
```

## gestureTemplates Format

```javascript
// Each template is a flat object: "BoneName.rotation": { x, y, z }
// Bone names: Mixamo names WITHOUT the "mixamorig" prefix
// TalkingHead strips "mixamorig" automatically, but templates use the short name

head.gestureTemplates["MY_SIGN"] = {
  "LeftShoulder.rotation": { x: 1.62, y: -0.17, z: -1.61 },
  "LeftArm.rotation":      { x: 1.28, y: 0.54,  z: -0.09 },
  "LeftForeArm.rotation":  { x: 0,    y: 0,      z: 0.30 },
  "LeftHand.rotation":     { x: -0.23, y: -0.15, z: 0.11 },
  // Finger bones follow the same pattern
  "LeftHandThumb1.rotation": { x: 0.44, y: -0.04, z: 0.46 },
  "LeftHandIndex1.rotation": { x: 0.22, y: 0.01,  z: -0.08 },
  // ... etc
};
```

## Available Bone Names (Mixamo, without prefix)

```
Hips, Spine, Spine1, Spine2, Neck, Head
LeftShoulder, LeftArm, LeftForeArm, LeftHand
  LeftHandThumb1–3
  LeftHandIndex1–3
  LeftHandMiddle1–3
  LeftHandRing1–3
  LeftHandPinky1–3
RightShoulder, RightArm, RightForeArm, RightHand
  RightHandThumb1–3 ... (same pattern)
LeftUpLeg, LeftLeg, LeftFoot, LeftToeBase
RightUpLeg, RightLeg, RightFoot, RightToeBase
```

## Amandla Sign Library → gestureTemplate Conversion

The existing `signs_library.js` uses this format:
```javascript
animations.push(["mixamorigLeftForeArm", "rotation", "x", Math.PI/2, "+"]);
// [boneName, property, axis, value, direction]
```

Converting to gestureTemplate:
```javascript
// Strip "mixamorig" prefix, add ".rotation" suffix
// Use the value directly as the axis value
"LeftForeArm.rotation": { x: Math.PI/2, y: 0, z: 0 }
```

The `"+"` / `"-"` direction field in the original format indicates additive vs absolute.
In gestureTemplates, values are **absolute** bone rotations (Euler XYZ in radians).
For most signs, the final keyframe phase value is what you want.
