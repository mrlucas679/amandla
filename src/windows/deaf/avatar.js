// AMANDLA Avatar — Deaf window only
// Three-phase animation: APPROACH → HOLD → RELEASE
// Spring easing with gentle overshoot, head tilt, breathing idle

(function () {
  'use strict';

  // ── CONSTANTS ─────────────────────────────────────────────
  const SIGN_DURATION   = 0.72   // seconds per full sign cycle
  const SIGN_GAP        = 0.22   // pause between signs
  const SIGN_FS_DUR     = 0.32   // fingerspell duration
  const SIGN_FS_GAP     = 0.10   // fingerspell gap

  // Fraction of SIGN_DURATION for each phase
  const PHASE_APPROACH  = 0.38   // 0→38%: move into sign pose
  const PHASE_HOLD      = 0.68   // 38→68%: hold sign (oscillation runs here)
  // 68→100%: slight release / prep for next

  // ── STATE ─────────────────────────────────────────────────
  let scene, camera, renderer, animFrameId
  let avatarBones = {}           // { R, L, head, torso }
  let signQueue   = []
  let currentSign = null
  let signProgress = 0
  let gapTimer    = 0
  let isInGap     = false
  let oscTime     = 0
  let lastFrameTime = performance.now()
  let initialized = false

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
    applyIdlePose()
    animate()

    window.addEventListener('resize', function () {
      const W2 = container.clientWidth, H2 = container.clientHeight
      camera.aspect = W2 / H2
      camera.updateProjectionMatrix()
      renderer.setSize(W2, H2, false)
    })

    console.log('[Avatar] initialized — deaf window')
  }

  // ── SKELETON BUILD ────────────────────────────────────────
  function buildAvatarSkeleton() {
    const mat = {
      skin:   new THREE.MeshPhongMaterial({ color: 0xC8A07A, shininess: 20 }),
      shirt:  new THREE.MeshPhongMaterial({ color: 0x1A1A2E, shininess: 10 }),
      teal:   new THREE.MeshPhongMaterial({ color: 0x2EA880, shininess: 30 }),
      purple: new THREE.MeshPhongMaterial({ color: 0x8B6FD4, shininess: 30 }),
    }

    // Torso (pivots slightly for body lean)
    const torsoGroup = new THREE.Group()
    torsoGroup.position.set(0, -0.1, 0)
    scene.add(torsoGroup)

    const torsoMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.30, 0.26, 1.05, 12), mat.shirt)
    torsoGroup.add(torsoMesh)
    avatarBones.torso = torsoGroup

    // Neck
    const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.10, 0.14, 8), mat.skin)
    neck.position.set(0, 0.60, 0)
    torsoGroup.add(neck)

    // Head (pivots for head tilt/nod)
    const headGroup = new THREE.Group()
    headGroup.position.set(0, 0.78, 0)
    torsoGroup.add(headGroup)

    const headMesh = new THREE.Mesh(new THREE.SphereGeometry(0.21, 16, 12), mat.skin)
    headGroup.add(headMesh)
    avatarBones.head = headGroup

    // Eyes
    const eyeGeo = new THREE.SphereGeometry(0.028, 8, 8)
    const eyeMat = new THREE.MeshPhongMaterial({ color: 0x111111 })
    const eyeL = new THREE.Mesh(eyeGeo, eyeMat)
    eyeL.position.set(-0.085, 0.04, 0.18)
    headGroup.add(eyeL)
    const eyeR = new THREE.Mesh(eyeGeo, eyeMat)
    eyeR.position.set( 0.085, 0.04, 0.18)
    headGroup.add(eyeR)

    // Arms (attached to torsoGroup so body lean carries arms)
    avatarBones.R = buildArm('R', -0.34, mat, torsoGroup)
    avatarBones.L = buildArm('L',  0.34, mat, torsoGroup)
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
  function applyIdlePose() {
    const hs = window.AMANDLA_SIGNS ? window.AMANDLA_SIGNS.HS.rest : null
    const idle = {
      R: { sh: { x: 0.05, y: 0, z: -0.24 }, el: { x: 0.08, y: 0, z: 0 }, wr: { x: 0, y: 0, z: 0 }, hand: hs },
      L: { sh: { x: 0.05, y: 0, z:  0.24 }, el: { x: 0.08, y: 0, z: 0 }, wr: { x: 0, y: 0, z: 0 }, hand: hs },
    }
    applySignPose(idle, 1.0)
  }

  function applySignPose(signObj, t) {
    if (!signObj || !avatarBones.R) return
    for (const side of ['R', 'L']) {
      const arm  = avatarBones[side]
      const data = signObj[side]
      if (!arm || !data) continue
      lerpRotation(arm.shoulder, data.sh, t)
      lerpRotation(arm.elbow,    data.el, t)
      lerpRotation(arm.wrist,    data.wr, t)
      if (data.hand) applyHandshape(arm.fingers, data.hand, t)
    }
  }

  function lerpRotation(obj, target, t) {
    if (!obj || !target) return
    const s = Math.min(t * 1.6, 1.0)
    obj.rotation.x += (target.x - obj.rotation.x) * s
    obj.rotation.y += (target.y - obj.rotation.y) * s
    obj.rotation.z += (target.z - obj.rotation.z) * s
  }

  function lerpVal(cur, target, t) {
    return cur + (target - cur) * Math.min(t * 1.6, 1.0)
  }

  function applyHandshape(fingers, hs, t) {
    const keys = ['t', 'i', 'm', 'r', 'p']
    for (let f = 0; f < 5; f++) {
      const segs = hs[keys[f]]
      if (!segs || !fingers[f]) continue
      for (let s = 0; s < 3 && s < segs.length; s++) {
        const seg = fingers[f].segments[s]
        if (!seg) continue
        seg.pivot.rotation.x += ((segs[s] || 0) - seg.pivot.rotation.x) * Math.min(t * 1.6, 1.0)
      }
    }
  }

  function applyOscillation(signObj, time) {
    if (!signObj || !signObj.osc) return
    const { j, ax, amp, freq } = signObj.osc
    const val = Math.sin(time * freq * Math.PI * 2) * amp

    // Full amplitude — was incorrectly multiplied by 0.04 before
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

  // ── EASING ────────────────────────────────────────────────
  // Approach phase: easeOutBack — smooth with gentle overshoot/snap
  function easeOutBack(t) {
    const c1 = 1.28
    const c3 = c1 + 1
    return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2)
  }

  // ── SIGN QUEUE ────────────────────────────────────────────
  function resolveSign(item) {
    if (!item) return null
    if (typeof item === 'object') return item
    const lib = window.AMANDLA_SIGNS
    if (lib && lib.SIGN_LIBRARY && lib.SIGN_LIBRARY[item]) return lib.SIGN_LIBRARY[item]
    if (item.length === 1) {
      const alpha = lib && lib.SIGN_LIBRARY && lib.SIGN_LIBRARY[item.toUpperCase()]
      return alpha || { name: item.toUpperCase(), isFingerspell: true, desc: 'Letter ' + item.toUpperCase(), R: null, L: null, osc: null }
    }
    return { name: item, isFingerspell: false, desc: item, R: null, L: null, osc: null }
  }

  function queueSign(signObj)       { signQueue.push(resolveSign(signObj)) }
  function queueSentence(text)      {
    const lib = window.AMANDLA_SIGNS
    if (!lib) return
    const signs = lib.sentenceToSigns(text)
    signs.forEach(function (s) { signQueue.push(s) })
    updateLabel(signs.length > 0 ? signs[0].name : '')
  }
  function playSignNow(signNameOrObj) {
    signQueue = []
    const s = resolveSign(signNameOrObj)
    if (s) { signQueue.push(s); updateLabel(s.name) }
  }

  function updateLabel(text) {
    const el = document.getElementById('avatar-sign-label')
    if (el) el.textContent = text || ''
  }

  // ── HEAD TILT ─────────────────────────────────────────────
  // Tilt toward dominant signing hand based on shoulder z
  let targetHeadZ = 0
  let targetHeadX = 0

  function computeHeadTarget(signObj) {
    if (!signObj || !signObj.R || !signObj.R.sh) { targetHeadZ = 0; targetHeadX = 0; return }
    // Right arm raised (sh.x negative = up) → head tilts right (z positive)
    const rUp = signObj.R.sh.x < -0.3
    const lUp = signObj.L && signObj.L.sh && signObj.L.sh.x < -0.3
    if (rUp && !lUp) { targetHeadZ =  0.09; targetHeadX = 0.04 }
    else if (lUp && !rUp) { targetHeadZ = -0.09; targetHeadX = 0.04 }
    else if (rUp && lUp)  { targetHeadZ =  0;    targetHeadX = 0.06 }
    else                  { targetHeadZ =  0;    targetHeadX = 0 }
  }

  // ── ANIMATION LOOP ────────────────────────────────────────
  function animate() {
    animFrameId = requestAnimationFrame(animate)
    if (document.hidden || !renderer) return

    const now = performance.now()
    const dt  = Math.min((now - lastFrameTime) / 1000, 0.05)
    lastFrameTime = now
    oscTime += dt

    const isFS    = currentSign && currentSign.isFingerspell
    const dur     = isFS ? SIGN_FS_DUR : SIGN_DURATION
    const gap     = isFS ? SIGN_FS_GAP : SIGN_GAP

    // ── Sign queue state machine ─────────────────────────
    if (isInGap) {
      gapTimer -= dt
      if (gapTimer <= 0) {
        isInGap = false
        if (signQueue.length > 0) {
          currentSign  = signQueue.shift()
          signProgress = 0
          updateLabel(currentSign ? currentSign.name : '')
          computeHeadTarget(currentSign)
        } else {
          currentSign = null
          applyIdlePose()
          updateLabel('')
          targetHeadZ = 0
          targetHeadX = 0
        }
      }
    } else if (currentSign) {
      signProgress += dt / dur

      if (signProgress >= 1.0) {
        signProgress = 1.0
        applySignPose(currentSign, 1.0)
        isInGap  = true
        gapTimer = gap
      } else {
        const t = signProgress

        if (t < PHASE_APPROACH) {
          // Phase 1: Approach — spring into sign pose
          const local = t / PHASE_APPROACH
          applySignPose(currentSign, easeOutBack(local))

        } else if (t < PHASE_HOLD) {
          // Phase 2: Hold — maintain pose fully, run oscillation
          applySignPose(currentSign, 1.0)
          applyOscillation(currentSign, oscTime)

        } else {
          // Phase 3: Release — slight softening, continue oscillation
          const local = (t - PHASE_HOLD) / (1.0 - PHASE_HOLD)
          applySignPose(currentSign, 1.0 - local * 0.12)
          applyOscillation(currentSign, oscTime)
        }
      }

    } else if (signQueue.length > 0) {
      currentSign  = signQueue.shift()
      signProgress = 0
      updateLabel(currentSign ? currentSign.name : '')
      computeHeadTarget(currentSign)
    }

    // ── Idle motion (only when not actively signing approach) ─
    const signing = currentSign && signProgress < PHASE_HOLD
    if (!signing && avatarBones.R) {
      const sway   = Math.sin(oscTime * 0.40) * 0.016
      const breathY = Math.sin(oscTime * 0.26 * Math.PI * 2) * 0.008  // breathing
      avatarBones.R.shoulder.rotation.z = lerpVal(
        avatarBones.R.shoulder.rotation.z, -0.24 + sway, 0.08
      )
      avatarBones.L.shoulder.rotation.z = lerpVal(
        avatarBones.L.shoulder.rotation.z,  0.24 - sway, 0.08
      )
      // Subtle shoulder lift with breath
      avatarBones.R.shoulder.rotation.x = lerpVal(
        avatarBones.R.shoulder.rotation.x, 0.05 + breathY, 0.06
      )
      avatarBones.L.shoulder.rotation.x = lerpVal(
        avatarBones.L.shoulder.rotation.x, 0.05 + breathY, 0.06
      )
    }

    // ── Head tilt — always smoothly interpolated ───────────
    if (avatarBones.head) {
      avatarBones.head.rotation.z = lerpVal(avatarBones.head.rotation.z, targetHeadZ, 0.06)
      avatarBones.head.rotation.x = lerpVal(avatarBones.head.rotation.x, targetHeadX, 0.06)
      // Micro head oscillation for life
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
    destroyAvatar: destroyAvatar
  }

  window.avatarInit = function () { initAvatar('avatar-canvas') }
  window.avatarPlaySigns = function (signs, text) {
    if (!initialized) initAvatar('avatar-canvas')
    if (Array.isArray(signs)) signs.forEach(function (s) { queueSign(s) })
    updateLabel(text || (signs && signs[0]) || '')
  }

})();