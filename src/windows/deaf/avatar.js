// AMANDLA Avatar — Deaf window only
// v2.0: TransitionEngine — SLERP quaternions, coarticulation, joint limits
// Three-phase replaced with: TRANSITIONING → HOLDING → GAP → IDLE

(function () {
  'use strict'

  // ── CONSTANTS ─────────────────────────────────────────────
  const SIGN_HOLD    = 0.38   // seconds to hold a sign at full pose
  const SIGN_FS_HOLD = 0.08   // hold for fingerspelling
  const SIGN_GAP     = 0.18   // pause after last sign before returning to idle

  // ── STATE ─────────────────────────────────────────────────
  let scene, camera, renderer, animFrameId
  let avatarBones = {}    // { R, L, head, torso }
  let signQueue   = []
  let currentSign = null
  let finalPose   = null  // last pose from TransitionEngine, applied during HOLDING
  let idleSign    = null  // idle pose as v2-compatible sign (has _Rq, _Lq)
  let animState   = 'idle' // 'idle' | 'transitioning' | 'holding' | 'gap'
  let holdTimer   = 0
  let gapTimer    = 0
  let oscTime     = 0
  let lastFrameTime = performance.now()
  let initialized = false

  // FEAT-2: GLB avatar mode — when true, pose application uses AvatarDriver remapping
  let useGLBRig = false
  // References to the procedural skeleton meshes so we can hide them when GLB loads
  let proceduralGroup = null

  // UX-2: Sign progress tracking
  let signProgressCallback = null
  let totalSignCount = 0
  let currentSignIndex = 0

  let targetHeadZ = 0
  let targetHeadX = 0

  // ── INIT ──────────────────────────────────────────────────
  function initAvatar(containerId) {
    containerId = containerId || 'avatar-canvas'
    const container = document.getElementById(containerId)
    if (!container) { console.error('[Avatar] container not found:', containerId); return }
    if (initialized) return
    initialized = true

    if (typeof THREE === 'undefined') { console.error('[Avatar] THREE.js not loaded'); return }

    const W = container.clientWidth  || 480
    const H = container.clientHeight || 500

    scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0d0d0d)

    camera = new THREE.PerspectiveCamera(46, W / H, 0.1, 100)
    camera.position.set(0, 0.85, 4.0)
    camera.lookAt(0, 0.35, 0)

    renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(W, H, false)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    const canvas = renderer.domElement
    canvas.style.display = 'block'
    canvas.style.width   = '100%'
    canvas.style.height  = '100%'
    container.appendChild(canvas)

    requestAnimationFrame(function () {
      const rw = container.clientWidth, rh = container.clientHeight
      if (rw > 0 && rh > 0) {
        camera.aspect = rw / rh
        camera.updateProjectionMatrix()
        renderer.setSize(rw, rh, false)
      }
    })

    // ── Lighting ──────────────────────────────────────────
    scene.add(new THREE.AmbientLight(0xffffff, 0.55))

    const key = new THREE.DirectionalLight(0xfff5e8, 1.1)
    key.position.set(1.5, 3.5, 2.5)
    key.castShadow = true
    scene.add(key)

    const fill = new THREE.DirectionalLight(0x8B6FD4, 0.45)
    fill.position.set(-2, 0.5, -1)
    scene.add(fill)

    const rim = new THREE.DirectionalLight(0x2EA880, 0.30)
    rim.position.set(0, -1, -3)
    scene.add(rim)

    buildAvatarSkeleton()
    // FEAT-2: Try loading GLB avatar model — falls back to procedural skeleton on failure
    tryLoadGLBModel()
    buildIdleSign()
    animate()

    window.addEventListener('resize', function () {
      const W2 = container.clientWidth, H2 = container.clientHeight
      camera.aspect = W2 / H2
      camera.updateProjectionMatrix()
      renderer.setSize(W2, H2, false)
    })

    console.log('[Avatar] v2 initialized — deaf window')
  }

  // ── IDLE SIGN — v2-compatible pose object ─────────────────
  function buildIdleSign() {
    const lib = window.AMANDLA_SIGNS
    if (!lib || !lib.armToQuat) {
      setTimeout(buildIdleSign, 100)
      return
    }
    const idleR = { sh:{x:0.05,y:0,z:-0.24}, el:{x:0.08,y:0,z:0}, wr:{x:0,y:0,z:0} }
    const idleL = { sh:{x:0.05,y:0,z: 0.24}, el:{x:0.08,y:0,z:0}, wr:{x:0,y:0,z:0} }
    idleSign = {
      name: 'IDLE',
      R: { sh:idleR.sh, el:idleR.el, wr:idleR.wr, hand:lib.HS.rest },
      L: { sh:idleL.sh, el:idleL.el, wr:idleL.wr, hand:lib.HS.rest },
      _Rq: { end: lib.armToQuat(idleR), start: lib.armToQuat(idleR) },
      _Lq: { end: lib.armToQuat(idleL), start: lib.armToQuat(idleL) },
      osc: null,
      isFingerspell: false,
    }
    // Apply initial idle pose to bones
    applyPoseDirect({
      R: { sh:idleR.sh, el:idleR.el, wr:idleR.wr, hand:lib.HS.rest },
      L: { sh:idleL.sh, el:idleL.el, wr:idleL.wr, hand:lib.HS.rest },
    })
  }

  // ── SKELETON BUILD ────────────────────────────────────────
  function buildAvatarSkeleton() {
    const mat = {
      skin:   new THREE.MeshPhongMaterial({ color: 0xC8A07A, shininess: 20 }),
      shirt:  new THREE.MeshPhongMaterial({ color: 0x1A1A2E, shininess: 10 }),
      teal:   new THREE.MeshPhongMaterial({ color: 0x2EA880, shininess: 30 }),
      purple: new THREE.MeshPhongMaterial({ color: 0x8B6FD4, shininess: 30 }),
    }

    // FEAT-2: Wrap procedural skeleton in a group so we can hide it if GLB loads
    proceduralGroup = new THREE.Group()
    scene.add(proceduralGroup)

    const torsoGroup = new THREE.Group()
    torsoGroup.position.set(0, -0.1, 0)
    proceduralGroup.add(torsoGroup)

    const torsoMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.30, 0.26, 1.05, 12), mat.shirt)
    torsoGroup.add(torsoMesh)
    avatarBones.torso = torsoGroup

    const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.10, 0.14, 8), mat.skin)
    neck.position.set(0, 0.60, 0)
    torsoGroup.add(neck)

    const headGroup = new THREE.Group()
    headGroup.position.set(0, 0.78, 0)
    torsoGroup.add(headGroup)

    const headMesh = new THREE.Mesh(new THREE.SphereGeometry(0.21, 16, 12), mat.skin)
    headGroup.add(headMesh)
    avatarBones.head = headGroup

    const eyeGeo = new THREE.SphereGeometry(0.028, 8, 8)
    const eyeMat = new THREE.MeshPhongMaterial({ color: 0x111111 })
    const eyeL = new THREE.Mesh(eyeGeo, eyeMat)
    eyeL.position.set(-0.085, 0.04, 0.18)
    headGroup.add(eyeL)
    const eyeR = new THREE.Mesh(eyeGeo, eyeMat)
    eyeR.position.set( 0.085, 0.04, 0.18)
    headGroup.add(eyeR)

    avatarBones.R = buildArm('R', -0.34, mat, torsoGroup)
    avatarBones.L = buildArm('L',  0.34, mat, torsoGroup)
  }

  // ── FEAT-2: GLB MODEL LOADER ──────────────────────────────
  // Attempts to load a GLB avatar model and bind its bones via AvatarDriver.
  // On success: hides procedural skeleton, uses GLB rig for pose application.
  // On failure: keeps the procedural skeleton (graceful fallback).
  function tryLoadGLBModel() {
    // Guard: GLTFLoader and AvatarDriver must both be available
    if (typeof THREE.GLTFLoader === 'undefined') {
      console.log('[Avatar] GLTFLoader not available — using procedural skeleton')
      return
    }
    if (typeof window.AvatarDriver === 'undefined') {
      console.log('[Avatar] AvatarDriver not available — using procedural skeleton')
      return
    }

    var loader = new THREE.GLTFLoader()
    var glbPath = '../../../assets/models/avatar.glb'

    loader.load(
      glbPath,
      function (gltf) {
        console.log('[Avatar] GLB model loaded successfully')
        var model = gltf.scene

        // Scale and position the GLB model to match the procedural skeleton's framing
        model.scale.set(1.0, 1.0, 1.0)
        model.position.set(0, -0.9, 0)

        // Enable shadows on all meshes in the loaded model
        model.traverse(function (node) {
          if (node.isMesh) {
            node.castShadow = true
            node.receiveShadow = true
          }
        })

        // Bind GLB bones → avatarBones dict via AvatarDriver
        var savedBones = {
          R: avatarBones.R,
          L: avatarBones.L,
          head: avatarBones.head,
          torso: avatarBones.torso,
        }

        window.AvatarDriver.bindBonesFromGLTF(model, avatarBones)

        // Verify at least the shoulder bones were found
        if (!avatarBones.R || !avatarBones.R.shoulder) {
          console.warn('[Avatar] GLB rig binding incomplete — keeping procedural skeleton')
          // Restore the procedural bone references
          avatarBones.R = savedBones.R
          avatarBones.L = savedBones.L
          avatarBones.head = savedBones.head
          avatarBones.torso = savedBones.torso
          return
        }

        // Success: add GLB to scene and hide procedural skeleton
        scene.add(model)
        if (proceduralGroup) {
          proceduralGroup.visible = false
        }
        useGLBRig = true
        console.log('[Avatar] Switched to GLB rig — procedural skeleton hidden')

        // Re-apply idle pose to the new GLB bones
        buildIdleSign()
      },
      function (progress) {
        // Loading progress — log percentage for debugging large models
        if (progress.total > 0) {
          var pct = Math.round((progress.loaded / progress.total) * 100)
          if (pct % 25 === 0) console.log('[Avatar] GLB loading: ' + pct + '%')
        }
      },
      function (error) {
        console.warn('[Avatar] GLB model load failed — keeping procedural skeleton:', error)
      }
    )
  }

  function buildArm(side, torsoX, mat, parent) {
    const isRight   = side === 'R'
    const fingerMat = isRight ? mat.teal : mat.purple

    const shoulder = new THREE.Group()
    shoulder.position.set(torsoX, 0.36, 0)
    parent.add(shoulder)

    const upperArm = new THREE.Mesh(
      new THREE.CylinderGeometry(0.068, 0.062, 0.36, 10), mat.skin
    )
    upperArm.position.set(0, -0.18, 0)
    shoulder.add(upperArm)

    const elbow = new THREE.Group()
    elbow.position.set(0, -0.36, 0)
    shoulder.add(elbow)

    const forearm = new THREE.Mesh(
      new THREE.CylinderGeometry(0.053, 0.048, 0.32, 10), mat.skin
    )
    forearm.position.set(0, -0.16, 0)
    elbow.add(forearm)

    const wrist = new THREE.Group()
    wrist.position.set(0, -0.32, 0)
    elbow.add(wrist)

    const palm = new THREE.Mesh(
      new THREE.BoxGeometry(0.11, 0.15, 0.045), mat.skin
    )
    palm.position.set(0, -0.10, 0)
    wrist.add(palm)

    const fingers = buildFingers(wrist, fingerMat, isRight)

    return { shoulder, elbow, wrist, fingers }
  }

  function buildFingers(wristGroup, mat, isRight) {
    const fingers = []
    const xOff = isRight
      ? [-0.062, -0.030, 0.001, 0.032, 0.062]
      : [ 0.062,  0.030,-0.001,-0.032,-0.062]
    const segLengths = [0.036, 0.030, 0.026]

    for (let f = 0; f < 5; f++) {
      const isThumb = f === 0
      const fingerGroup = new THREE.Group()
      fingerGroup.position.set(xOff[f], -0.20, 0)
      wristGroup.add(fingerGroup)

      const segments = []
      let yOff = 0
      for (let s = 0; s < 3; s++) {
        const segLen = segLengths[s] * (isThumb ? 0.82 : 1)
        const pivot  = new THREE.Group()
        pivot.position.set(0, -yOff, 0)
        if (s === 0) fingerGroup.add(pivot)
        else segments[s - 1].pivot.add(pivot)

        const mesh = new THREE.Mesh(
          new THREE.CylinderGeometry(0.013 - s * 0.002, 0.015 - s * 0.002, segLen, 7),
          mat
        )
        mesh.position.set(0, -segLen / 2, 0)
        pivot.add(mesh)
        segments.push({ pivot, length: segLen })
        yOff += segLen
      }
      fingers.push({ group: fingerGroup, segments })
    }
    return fingers
  }

  // ── POSE APPLICATION ──────────────────────────────────────
  // Direct-set from TransitionEngine output — no lerp, engine handles blending
  // FEAT-2: When GLB rig is active, uses AvatarDriver for Mixamo axis remapping
  function applyPoseDirect(pose) {
    if (!pose || !avatarBones.R) return

    if (useGLBRig && window.AvatarDriver) {
      // GLB mode: use AvatarDriver for proper Mixamo bone axis mapping
      window.AvatarDriver.remapPoseForMixamo(pose, avatarBones)
      // Apply handshapes using GLB finger axis (.z instead of .x)
      for (var s = 0; s < 2; s++) {
        var side = s === 0 ? 'R' : 'L'
        var data = pose[side]
        var arm  = avatarBones[side]
        if (data && data.hand && arm && arm.fingers) {
          window.AvatarDriver.applyHandshapeGLTF(arm.fingers, data.hand)
        }
      }
      // Distribute wrist twist to prevent candy-wrapper deformation
      window.AvatarDriver.updateTwistBones(scene, avatarBones)
    } else {
      // Procedural mode: direct Euler rotation set
      for (const side of ['R', 'L']) {
        const arm  = avatarBones[side]
        const data = pose[side]
        if (!arm || !data) continue
        if (data.sh) arm.shoulder.rotation.set(data.sh.x, data.sh.y, data.sh.z)
        if (data.el) arm.elbow.rotation.set(data.el.x, data.el.y, data.el.z)
        if (data.wr) arm.wrist.rotation.set(data.wr.x, data.wr.y, data.wr.z)
        if (data.hand) applyHandshapeDirect(arm.fingers, data.hand)
      }
    }
  }

  function applyHandshapeDirect(fingers, hs) {
    if (!hs) return
    const keys = ['t', 'i', 'm', 'r', 'p']
    for (let f = 0; f < 5; f++) {
      const segs = hs[keys[f]]
      if (!segs || !fingers[f]) continue
      for (let s = 0; s < 3 && s < segs.length; s++) {
        const seg = fingers[f].segments[s]
        if (!seg) continue
        seg.pivot.rotation.x = segs[s] || 0
      }
    }
  }

  // ── OSCILLATION ───────────────────────────────────────────
  function applyOscillation(signObj, time) {
    if (!signObj || !signObj.osc) return
    const { j, ax, amp, freq } = signObj.osc
    const val = Math.sin(time * freq * Math.PI * 2) * amp

    if      (j === 'R_wr'    && avatarBones.R) avatarBones.R.wrist.rotation[ax]    = val
    else if (j === 'L_wr'    && avatarBones.L) avatarBones.L.wrist.rotation[ax]    = val
    else if (j === 'R_sh'    && avatarBones.R) avatarBones.R.shoulder.rotation[ax] += val * 0.5
    else if (j === 'R_el'    && avatarBones.R) avatarBones.R.elbow.rotation[ax]    += val * 0.5
    else if (j === 'both_sh') {
      if (avatarBones.R) avatarBones.R.shoulder.rotation[ax] += val * 0.5
      if (avatarBones.L) avatarBones.L.shoulder.rotation[ax] += val * 0.5
    } else if (j === 'both_el') {
      if (avatarBones.R) avatarBones.R.elbow.rotation[ax] += val * 0.5
      if (avatarBones.L) avatarBones.L.elbow.rotation[ax] += val * 0.5
    } else if (j === 'both_wr') {
      if (avatarBones.R) avatarBones.R.wrist.rotation[ax] = val
      if (avatarBones.L) avatarBones.L.wrist.rotation[ax] = val
    }
  }

  function lerpVal(cur, target, t) {
    return cur + (target - cur) * Math.min(t * 1.6, 1.0)
  }

  // ── HEAD TILT ─────────────────────────────────────────────
  function computeHeadTarget(signObj) {
    if (!signObj || !signObj.R || !signObj.R.sh) { targetHeadZ = 0; targetHeadX = 0; return }
    const rUp = signObj.R.sh.x < -0.3
    const lUp = signObj.L && signObj.L.sh && signObj.L.sh.x < -0.3
    if      (rUp && !lUp) { targetHeadZ =  0.09; targetHeadX = 0.04 }
    else if (lUp && !rUp) { targetHeadZ = -0.09; targetHeadX = 0.04 }
    else if (rUp && lUp)  { targetHeadZ =  0;    targetHeadX = 0.06 }
    else                  { targetHeadZ =  0;    targetHeadX = 0 }
  }

  // ── SIGN QUEUE ────────────────────────────────────────────
  function resolveSign(item) {
    if (!item) return null
    if (typeof item === 'object' && item._Rq) return item  // already v2 sign
    const lib = window.AMANDLA_SIGNS
    if (!lib) return null
    // Try library lookup first
    const name = typeof item === 'string' ? item : item.name || ''
    if (lib.SIGN_LIBRARY && lib.SIGN_LIBRARY[name])       return lib.SIGN_LIBRARY[name]
    if (lib.SIGN_LIBRARY && lib.SIGN_LIBRARY[name.toUpperCase()]) return lib.SIGN_LIBRARY[name.toUpperCase()]
    // Fall back to fingerspell (returns v2-compatible signs with _Rq/_Lq)
    if (lib.fingerspell) {
      const fs = lib.fingerspell(name)
      if (fs && fs.length > 0) return fs[0]
    }
    return null
  }

  function queueSign(signObj) {
    if (typeof signObj === 'string') {
      // May be a multi-letter word — use sentenceToSigns for proper lookup + fingerspell
      const lib = window.AMANDLA_SIGNS
      if (lib && lib.sentenceToSigns) {
        lib.sentenceToSigns(signObj).forEach(function (s) { signQueue.push(s) })
        return
      }
    }
    const s = resolveSign(signObj)
    if (s) signQueue.push(s)
  }
  function queueSentence(text) {
    const lib = window.AMANDLA_SIGNS
    if (!lib) return
    const signs = lib.sentenceToSigns(text)
    signs.forEach(function (s) { signQueue.push(s) })
    updateLabel(signs.length > 0 ? signs[0].name : '')
  }
  function playSignNow(signNameOrObj) {
    signQueue = []
    const lib = window.AMANDLA_SIGNS
    if (lib && typeof signNameOrObj === 'string') {
      const signs = lib.sentenceToSigns(signNameOrObj)
      if (signs.length > 0) {
        signs.forEach(function (s) { signQueue.push(s) })
        updateLabel(signs[0].name)
        return
      }
    }
    const s = resolveSign(signNameOrObj)
    if (s) { signQueue.push(s); updateLabel(s.name) }
  }

  function updateLabel(text) {
    const el = document.getElementById('avatar-sign-label')
    if (el) el.textContent = text || ''
  }

  // ── START NEXT TRANSITION ─────────────────────────────────
  function startNextTransition(fromOverride) {
    const TE = window.AMANDLA_SIGNS && window.AMANDLA_SIGNS.TransitionEngine
    if (!TE || signQueue.length === 0) return
    const from = fromOverride || currentSign || idleSign
    if (!from) return
    currentSign = signQueue.shift()
    const next  = signQueue[0] || null
    TE.begin(from, currentSign, next)
    animState = 'transitioning'
    updateLabel(currentSign ? currentSign.name : '')
    computeHeadTarget(currentSign)

    // UX-2: Notify progress listener each time a sign begins
    currentSignIndex++
    if (signProgressCallback) {
      try { signProgressCallback(currentSignIndex, totalSignCount) } catch (_) { /* ignore */ }
    }
  }

  // ── ANIMATION LOOP ────────────────────────────────────────
  function animate() {
    animFrameId = requestAnimationFrame(animate)
    if (document.hidden || !renderer) return

    const now = performance.now()
    const dt  = Math.min((now - lastFrameTime) / 1000, 0.05)
    lastFrameTime = now
    oscTime += dt

    const TE = window.AMANDLA_SIGNS && window.AMANDLA_SIGNS.TransitionEngine

    // ── Sign state machine ─────────────────────────────────
    if (animState === 'transitioning' && TE) {
      const pose = TE.tick(dt)
      if (pose) applyPoseDirect(pose)
      if (TE.isDone()) {
        finalPose = pose
        const isFS = currentSign && currentSign.isFingerspell
        holdTimer = isFS ? SIGN_FS_HOLD : SIGN_HOLD
        animState = 'holding'
      }

    } else if (animState === 'holding') {
      if (finalPose) applyPoseDirect(finalPose)
      if (currentSign) applyOscillation(currentSign, oscTime)
      holdTimer -= dt
      if (holdTimer <= 0) {
        if (signQueue.length > 0) {
          startNextTransition()
        } else {
          animState = 'gap'
          gapTimer  = SIGN_GAP
        }
      }

    } else if (animState === 'gap') {
      // Hold last pose during gap (no oscillation)
      if (finalPose) applyPoseDirect(finalPose)
      gapTimer -= dt
      if (gapTimer <= 0) {
        // Transition back to idle
        if (TE && idleSign && currentSign) {
          TE.begin(currentSign, idleSign, null)
          animState = 'transitioning'
          currentSign = idleSign
        } else {
          animState = 'idle'
        }
        updateLabel('')
        targetHeadZ = 0
        targetHeadX = 0
      }

    } else { // idle
      if (signQueue.length > 0 && idleSign && TE) {
        startNextTransition(idleSign)
      }
    }

    // ── Idle breathing/sway — only when idle ──────────────
    if (animState === 'idle' && avatarBones.R) {
      const sway   = Math.sin(oscTime * 0.40) * 0.016
      const breathY = Math.sin(oscTime * 0.26 * Math.PI * 2) * 0.008
      avatarBones.R.shoulder.rotation.z = lerpVal(avatarBones.R.shoulder.rotation.z, -0.24 + sway, 0.08)
      avatarBones.L.shoulder.rotation.z = lerpVal(avatarBones.L.shoulder.rotation.z,  0.24 - sway, 0.08)
      avatarBones.R.shoulder.rotation.x = lerpVal(avatarBones.R.shoulder.rotation.x, 0.05 + breathY, 0.06)
      avatarBones.L.shoulder.rotation.x = lerpVal(avatarBones.L.shoulder.rotation.x, 0.05 + breathY, 0.06)
    }

    // ── Head tilt — always smooth ──────────────────────────
    if (avatarBones.head) {
      avatarBones.head.rotation.z = lerpVal(avatarBones.head.rotation.z, targetHeadZ, 0.06)
      avatarBones.head.rotation.x = lerpVal(avatarBones.head.rotation.x, targetHeadX, 0.06)
      avatarBones.head.rotation.y = Math.sin(oscTime * 0.19 * Math.PI * 2) * 0.012
    }

    renderer.render(scene, camera)
  }

  // ── CLEANUP ───────────────────────────────────────────────
  function destroyAvatar() {
    if (animFrameId) cancelAnimationFrame(animFrameId)
    if (renderer) renderer.dispose()
    initialized = false
  }

  // ── PUBLIC API ────────────────────────────────────────────
  window.AmandlaAvatar = {
    initAvatar:    initAvatar,
    queueSign:     queueSign,
    queueSentence: queueSentence,
    playSignNow:   playSignNow,
    destroyAvatar: destroyAvatar,
    // UX-2: Register a callback fired each time a sign begins animating.
    // Callback signature: function(currentIndex, totalCount)
    onSignProgress: function (cb) { signProgressCallback = cb }
  }

  window.avatarInit = function () { initAvatar('avatar-canvas') }
  window.avatarPlaySigns = function (signs, text) {
    if (!initialized) initAvatar('avatar-canvas')
    // UX-2: Reset progress counters for the new batch
    currentSignIndex = 0
    totalSignCount = Array.isArray(signs) ? signs.length : 0
    if (Array.isArray(signs)) signs.forEach(function (s) { queueSign(s) })
    updateLabel(text || (signs && signs[0]) || '')
  }

})();
