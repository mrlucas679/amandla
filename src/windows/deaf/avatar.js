// AMANDLA Avatar — Deaf window only
// v2.1: R1 — GLB human avatar primary, procedural skeleton fallback
// TransitionEngine — SLERP quaternions, coarticulation, joint limits
// State machine: TRANSITIONING → HOLDING → GAP → IDLE

(function () {
  'use strict'

  // ── CONSTANTS ─────────────────────────────────────────────
  // Timing calibrated to fluent SASL conversational pace (Czech MoCap, LREC 2020:
  // avg sign duration 0.38s continuous signing; VLibras 2025: tighter gaps = more natural)
  const SIGN_HOLD    = 0.32   // seconds to hold a sign at full pose (was 0.38 — dictionary pace)
  const SIGN_FS_HOLD = 0.19   // hold for fingerspelling (~5 chars/sec readable pace)
  const SIGN_GAP     = 0.10   // pause after last sign before returning to idle (tighter coarticulation)

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

  // R1: GLB avatar mode — true when human GLB model loaded successfully
  // When true, pose application uses AvatarDriver for Mixamo axis remapping
  let useGLBRig = false
  // References to the procedural skeleton meshes (built only as fallback)
  let proceduralGroup = null

  // UX-2: Sign progress tracking
  let signProgressCallback = null
  let totalSignCount = 0
  let currentSignIndex = 0

  let targetHeadZ = 0
  let targetHeadX = 0

  // ── NMM STATE — Non-Manual Markers (SASL grammar: obligatory, not decorative) ──
  // Sources: de Villiers PhD Stellenbosch 2014, van Zijl ASSETS 2006
  let nmBrowLiftTarget   = 0   // raised brows (yes/no question, topic, conditional)
  let nmBrowLiftCur      = 0
  let nmBrowFurrowTarget = 0   // furrowed brows (wh-question, rhetorical)
  let nmBrowFurrowCur    = 0
  let nmMouthOpenTarget  = 0   // mouth open (exclamation, emphasis)
  let nmMouthOpenCur     = 0
  let nmHeadShake        = false  // negation — head shake
  let nmHeadNod          = false  // affirmation — head nod
  let nmShakePhase       = 0     // oscillation phase for shake/nod

  // ── LIFELIKE IDLE STATE ────────────────────────────────────
  // Sources: SignON D5.2 (avatar quality), VLibras 2025 (realism)
  let eyeBlinkTimer    = 3.5   // seconds until next blink
  let eyeBlinkPhase    = 0     // 0=open, 1=closing, 2=opening
  let eyeBlinkDuration = 0     // remaining time in current blink phase
  let eyeGazeTimer     = 0     // seconds until next saccade
  let eyeGazeTargetX   = 0     // horizontal micro-gaze offset
  let eyeGazeTargetY   = 0     // vertical micro-gaze offset

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
    // R1: GLB human avatar is the primary renderer — procedural skeleton is fallback only.
    // loadHumanAvatar() will hide the procedural skeleton on GLB success,
    // or keep it visible if the GLB fails to load.
    loadHumanAvatar(container)
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
  let _idleRetries = 0
  function buildIdleSign() {
    const lib = window.AMANDLA_SIGNS
    if (!lib || !lib.armToQuat) {
      if (++_idleRetries > 80) {
        console.error('[Avatar] AMANDLA_SIGNS library never loaded after 8s — check script order in index.html')
        return
      }
      setTimeout(buildIdleSign, 100)
      return
    }
    _idleRetries = 0
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

  // ── SKELETON BUILD (FALLBACK) ────────────────────────────
  // Procedural cylinder/sphere skeleton — used when GLB model fails to load.
  // Built immediately for instant visual feedback; hidden if GLB loads successfully.
  function buildAvatarSkeleton() {
    const mat = {
      skin:   new THREE.MeshPhongMaterial({ color: 0xC8A07A, shininess: 20 }),
      shirt:  new THREE.MeshPhongMaterial({ color: 0x1A1A2E, shininess: 10 }),
      teal:   new THREE.MeshPhongMaterial({ color: 0x2EA880, shininess: 30 }),
      purple: new THREE.MeshPhongMaterial({ color: 0x8B6FD4, shininess: 30 }),
    }

    // R1: Wrap procedural skeleton in a group so we can hide it if GLB loads
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

  // ── R1: GLB HUMAN AVATAR LOADER ─────────────────────────────
  // Primary renderer path — loads a Mixamo-rigged GLB human avatar.
  // On success: hides procedural skeleton, uses GLB rig for all pose application.
  // On failure: keeps the procedural skeleton (graceful fallback).
  //
  // Sources: SignON D5.2 (bone mapping layer), VLibras 2025 (human avatar = 62% higher
  //          acceptance vs primitives), de Villiers PhD 2014 (5 sign parameters need
  //          human proportions for spatial accuracy).
  //
  // GLB SOURCING GUIDE — SASL AVATAR
  // ─────────────────────────────────
  // Option 1 (RECOMMENDED — Free, 5 minutes):
  //   1. Go to https://readyplayer.me
  //   2. Create avatar, choose warm brown skin tone for SASL cultural accuracy
  //   3. Export URL: https://models.readyplayer.me/[ID].glb?morphTargets=ARKit&lod=0
  //   4. This gives you: full finger rig + 52 ARKit blendshapes for NMMs
  //   5. Bone names: mixamorigHead, mixamorigRightArm, etc. (Mixamo standard)
  //
  // Option 2 (Mixamo.com — Free with Adobe account):
  //   Upload any character mesh → auto-rig → download FBX → convert to GLB via Blender
  //
  // Option 3 (Character Creator 4 → Blender → Mixamo pipeline):
  //   Per SignON D5.2: CC4 → export FBX → Blender → Mixamo (auto-rig) → GLB
  //   Highest quality but takes ~15 minutes per avatar.
  function loadHumanAvatar(container) {
    // Show loading indicator while GLB downloads (33+ MB file)
    if (container) container.classList.add('avatar-loading')

    // Configurable avatar URL via window.AMANDLA_CONFIG (allows runtime avatar swap)
    var glbUrl = (window.AMANDLA_CONFIG && window.AMANDLA_CONFIG.avatarUrl)
      || '../../../assets/models/avatar.glb'

    // Guard: GLTFLoader and AvatarDriver must both be available
    if (typeof THREE.GLTFLoader === 'undefined') {
      console.log('[Avatar] GLTFLoader not available — using procedural skeleton')
      if (container) container.classList.remove('avatar-loading')
      return
    }
    if (typeof window.AvatarDriver === 'undefined') {
      console.log('[Avatar] AvatarDriver not available — using procedural skeleton')
      if (container) container.classList.remove('avatar-loading')
      return
    }

    var loader = new THREE.GLTFLoader()

    loader.load(
      glbUrl,
      function onGLBLoaded(gltf) {
        console.log('[Avatar] GLB model loaded — binding rig to AMANDLA engine')
        var model = gltf.scene

        // Position and scale to match scene framing
        model.scale.set(1.0, 1.0, 1.0)
        model.position.set(0, -0.9, 0)

        // Enable shadows + apply warm South African skin tone (0xA8734A)
        // Per research: culturally appropriate representation matters for SASL users
        model.traverse(function (node) {
          if (!node.isMesh) return
          node.castShadow = true
          node.receiveShadow = true
          // Apply skin material properties if no baked texture map exists
          if (node.material) {
            var matName = (node.material.name || node.name || '').toLowerCase()
            var isSkin = matName.includes('skin') || matName.includes('body')
              || matName.includes('head') || matName.includes('face')
            if (isSkin) {
              node.material.roughness = 0.72
              node.material.metalness = 0.0
              // Only override colour if the material has no baked texture
              if (!node.material.map) {
                node.material.color = new THREE.Color(0xA8734A)
              }
            }
          }
        })

        // Save procedural bone references in case GLB rig binding fails
        var savedBones = {
          R: avatarBones.R,
          L: avatarBones.L,
          head: avatarBones.head,
          torso: avatarBones.torso,
        }

        // Bind GLB bones → avatarBones dict via AvatarDriver
        window.AvatarDriver.bindBonesFromGLTF(model, avatarBones)

        // Verify at least the shoulder bones were found — rig must be usable
        if (!avatarBones.R || !avatarBones.R.shoulder) {
          console.warn('[Avatar] GLB rig binding incomplete — keeping procedural skeleton')
          avatarBones.R = savedBones.R
          avatarBones.L = savedBones.L
          avatarBones.head = savedBones.head
          avatarBones.torso = savedBones.torso
          if (container) container.classList.remove('avatar-loading')
          return
        }

        // Success: add GLB to scene and hide procedural skeleton
        scene.add(model)
        if (proceduralGroup) {
          proceduralGroup.visible = false
        }
        useGLBRig = true
        if (container) container.classList.remove('avatar-loading')
        console.log('[Avatar] R1: GLB human avatar active — AMANDLA engine driving Mixamo rig')

        // Re-apply idle pose to the newly bound GLB bones
        buildIdleSign()
      },
      function onGLBProgress(progress) {
        // Loading progress — log percentage for debugging large models
        if (progress.total > 0) {
          var pct = Math.round((progress.loaded / progress.total) * 100)
          if (pct % 25 === 0) console.log('[Avatar] GLB loading: ' + pct + '%')
        }
      },
      function onGLBError(error) {
        console.warn('[Avatar] GLB load failed — keeping procedural skeleton:', error.message || error)
        if (container) container.classList.remove('avatar-loading')
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
  // R1: When GLB rig is active, uses AvatarDriver for Mixamo axis remapping
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

  // ── NMM CONTROL — set non-manual markers for current sign ──
  // Called by the sign pipeline when a sign has NMM data.
  // nmms: array of lowercase NMM descriptor strings (e.g. ['wh-question', 'head-shake'])
  // duration: how long the NMMs should stay active (seconds)
  // Sources: van Zijl ASSETS 2006 — NMMs are grammatically obligatory in SASL
  //          de Villiers PhD 2014 — 5 sign parameters, NMMs = prosody analogue
  function setNMMs(nmms, duration) {
    // Reset all NMM targets before applying new ones
    nmBrowLiftTarget   = 0
    nmBrowFurrowTarget = 0
    nmMouthOpenTarget  = 0
    nmHeadShake        = false
    nmHeadNod          = false

    if (!nmms || !Array.isArray(nmms)) return

    for (let idx = 0; idx < nmms.length; idx++) {
      var n = (nmms[idx] || '').toLowerCase()

      // Yes/No question — raised eyebrows
      if (n.includes('yn') || n.includes('yes-no') || n.includes('raised-brow')) {
        nmBrowLiftTarget = Math.max(nmBrowLiftTarget, 0.020)
      }
      // Wh-question — furrowed brows
      if (n.includes('wh') || n.includes('furrowed') || n.includes('squint')) {
        nmBrowFurrowTarget = Math.max(nmBrowFurrowTarget, 0.14)
      }
      // Negation — head shake + brow furrow
      if (n.includes('negat') || n.includes('head-shake') || n.includes('not') || n.includes('none') || n.includes('never')) {
        nmHeadShake = true
        nmBrowFurrowTarget = Math.max(nmBrowFurrowTarget, 0.12)
      }
      // Affirmation — head nod
      if (n.includes('affirm') || n.includes('head-nod') || n.includes('yes')) {
        nmHeadNod = true
      }
      // Topicalization — raised brows + slight head tilt forward
      if (n.includes('topic') || n.includes('topicalization') || n.includes('about')) {
        nmBrowLiftTarget = Math.max(nmBrowLiftTarget, 0.018)
        targetHeadX = Math.max(targetHeadX, 0.05)
      }
      // Rhetorical question — furrowed brows without mouth open
      if (n.includes('rhetorical')) {
        nmBrowFurrowTarget = Math.max(nmBrowFurrowTarget, 0.16)
      }
      // Intensifier / emphasis — lean forward, bigger brow
      if (n.includes('intensifier') || n.includes('very') || n.includes('strong') || n.includes('extreme')) {
        targetHeadX = Math.max(targetHeadX, 0.09)
        nmBrowLiftTarget = Math.max(nmBrowLiftTarget, 0.015)
      }
      // Conditional / if-clause — raised brows held
      if (n.includes('conditional') || n.includes('if-clause') || n.includes('if')) {
        nmBrowLiftTarget = Math.max(nmBrowLiftTarget, 0.022)
      }
      // Surprise / exclamation — raised brows + mouth open
      if (n.includes('surprise') || n.includes('exclamation') || n.includes('wow')) {
        nmBrowLiftTarget = Math.max(nmBrowLiftTarget, 0.030)
        nmMouthOpenTarget = -0.014
      }
      // Mouth open
      if (n.includes('mouth-open') || n.includes('open-mouth')) {
        nmMouthOpenTarget = -0.014
      }
    }
  }

  // ── APPLY NMMs — update brow/mouth/head each frame ────────
  // Smoothly interpolates NMM state toward targets (box geometry + blendshapes).
  function applyNMMs(dt) {
    var smoothRate = 4.0 * dt

    // Lerp current NMM values toward targets
    nmBrowLiftCur   += (nmBrowLiftTarget   - nmBrowLiftCur)   * smoothRate
    nmBrowFurrowCur += (nmBrowFurrowTarget - nmBrowFurrowCur) * smoothRate
    nmMouthOpenCur  += (nmMouthOpenTarget  - nmMouthOpenCur)  * smoothRate

    // ── Box-geometry fallback (procedural skeleton) ──────────
    if (avatarBones.face) {
      if (avatarBones.face.browL) {
        avatarBones.face.browL.position.y = nmBrowLiftCur * 12 - nmBrowFurrowCur * 5
      }
      if (avatarBones.face.browR) {
        avatarBones.face.browR.position.y = nmBrowLiftCur * 12 - nmBrowFurrowCur * 5
      }
      if (avatarBones.face.mouth) {
        avatarBones.face.mouth.position.y = nmMouthOpenCur * 40
      }
    }

    // ── Blendshape NMMs (GLB avatar with morph targets) ─────
    if (avatarBones.faceMorphMesh && avatarBones.faceMorphMesh.morphTargetDictionary) {
      var mesh = avatarBones.faceMorphMesh
      var dict = mesh.morphTargetDictionary

      // Helper: try multiple blendshape names (ARKit → CC4 → generic)
      function setMorph(names, value) {
        var clamped = Math.max(0, Math.min(1, value))
        for (var i = 0; i < names.length; i++) {
          if (dict[names[i]] !== undefined) {
            mesh.morphTargetInfluences[dict[names[i]]] = clamped
            return
          }
        }
      }

      // Brow lift (yes/no question, topic, conditional)
      setMorph(['browInnerUp', 'Eyebrow_Arch_Left'],    nmBrowLiftCur * 12)
      setMorph(['browOuterUpLeft', 'Eyebrow_Arch_Right'], nmBrowLiftCur * 12)

      // Brow furrow (wh-question, rhetorical, negation)
      setMorph(['browDownLeft',  'Eyebrow_Frown_Left'],  nmBrowFurrowCur * 5)
      setMorph(['browDownRight', 'Eyebrow_Frown_Right'], nmBrowFurrowCur * 5)

      // Mouth open (exclamation, emphasis)
      setMorph(['jawOpen', 'Mouth_Stretch'], Math.abs(nmMouthOpenCur * 40))
    }

    // ── Head shake (negation) — sinusoidal Y rotation ────────
    if (nmHeadShake && avatarBones.head) {
      nmShakePhase += dt * 8.0
      var shakeEnvelope = Math.min(nmShakePhase * 0.5, 1.0) // ramp up
      avatarBones.head.rotation.y += Math.sin(nmShakePhase) * 0.12 * shakeEnvelope
    }

    // ── Head nod (affirmation) — sinusoidal X rotation ───────
    if (nmHeadNod && avatarBones.head) {
      nmShakePhase += dt * 6.0
      var nodEnvelope = Math.min(nmShakePhase * 0.5, 1.0)
      avatarBones.head.rotation.x += Math.sin(nmShakePhase) * 0.08 * nodEnvelope
    }

    // Reset shake phase when neither shake nor nod is active
    if (!nmHeadShake && !nmHeadNod) {
      nmShakePhase = 0
    }
  }

  // ── LIFELIKE IDLE — chest breathing, eye blink, eye saccades ──
  // Sources: SignON D5.2 Section 4.1 (avatar quality realism),
  //          VLibras 2025 (lack of fluidity = rejection reason),
  //          Czech MoCap 2020 (physiological idle observation)
  function applyLifelikeIdle(dt) {
    // 1. Chest breathing via torso scale (physiologically correct — ribs expand on inhale)
    if (avatarBones.torso && useGLBRig) {
      var breathIn = Math.sin(oscTime * 0.25 * Math.PI * 2)
      avatarBones.torso.scale.set(
        1.0 + breathIn * 0.015,  // ribs expand sideways
        1.0 + breathIn * 0.005,  // chest lifts slightly
        1.0 + breathIn * 0.020   // chest pushes forward
      )
    }

    // 2. Subtle arm sway (halved from original — breathing, not shrugging)
    if (avatarBones.R && avatarBones.L) {
      var sway    = Math.sin(oscTime * 0.40) * 0.012
      var breathY = Math.sin(oscTime * 0.26 * Math.PI * 2) * 0.006
      avatarBones.R.shoulder.rotation.z = lerpVal(avatarBones.R.shoulder.rotation.z, -0.24 + sway, 0.06)
      avatarBones.L.shoulder.rotation.z = lerpVal(avatarBones.L.shoulder.rotation.z,  0.24 - sway, 0.06)
      avatarBones.R.shoulder.rotation.x = lerpVal(avatarBones.R.shoulder.rotation.x, 0.05 + breathY, 0.05)
      avatarBones.L.shoulder.rotation.x = lerpVal(avatarBones.L.shoulder.rotation.x, 0.05 + breathY, 0.05)
    }

    // 3. Automatic eye blinks — every 3-7 seconds, 60ms close + 80ms open
    eyeBlinkTimer -= dt
    if (eyeBlinkTimer <= 0 && eyeBlinkPhase === 0) {
      eyeBlinkPhase = 1
      eyeBlinkDuration = 0.06  // 60ms close
      eyeBlinkTimer = 0        // will reset after full blink cycle
    }
    if (eyeBlinkPhase > 0 && avatarBones.faceMorphMesh && avatarBones.faceMorphMesh.morphTargetDictionary) {
      var dict = avatarBones.faceMorphMesh.morphTargetDictionary
      var blinkNames = ['eyeBlinkLeft', 'eyeBlinkRight', 'Eye_Blink_Left', 'Eye_Blink_Right']
      var blinkValue = (eyeBlinkPhase === 1)
        ? (1.0 - eyeBlinkDuration / 0.06)    // closing: 0→1
        : (eyeBlinkDuration / 0.08)           // opening: 1→0
      for (var bi = 0; bi < blinkNames.length; bi++) {
        if (dict[blinkNames[bi]] !== undefined) {
          avatarBones.faceMorphMesh.morphTargetInfluences[dict[blinkNames[bi]]] = Math.max(0, Math.min(1, blinkValue))
        }
      }
      eyeBlinkDuration -= dt
      if (eyeBlinkDuration <= 0) {
        if (eyeBlinkPhase === 1) {
          eyeBlinkPhase = 2
          eyeBlinkDuration = 0.08  // 80ms open
        } else {
          eyeBlinkPhase = 0
          eyeBlinkTimer = 3.0 + Math.random() * 4.0  // next blink in 3-7s
        }
      }
    }

    // 4. Eye saccades — humans never stare perfectly still (micro movements every 1-3s)
    eyeGazeTimer -= dt
    if (eyeGazeTimer <= 0) {
      eyeGazeTargetX = (Math.random() - 0.5) * 0.04
      eyeGazeTargetY = (Math.random() - 0.5) * 0.015
      eyeGazeTimer = 1.5 + Math.random() * 2.5
    }
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
        // Reset NMMs when returning to idle — facial expressions should not persist
        setNMMs(null)
      }

    } else { // idle
      applyLifelikeIdle(dt)
      if (signQueue.length > 0 && idleSign && TE) {
        startNextTransition(idleSign)
      }
    }

    // ── Apply NMMs every frame (smoothly interpolated) ─────
    applyNMMs(dt)

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
    // NMM system — set non-manual markers (SASL grammar: brow, mouth, head shake/nod)
    // nmms: array of descriptor strings, e.g. ['wh-question', 'head-shake']
    // duration: seconds to hold the NMMs (optional, NMMs persist until next setNMMs call)
    setNMMs:       setNMMs,
    // R1: Check whether the GLB human avatar is active (true) or procedural fallback (false)
    isGLBAvatar: function () { return useGLBRig },
    // R1: Set a custom avatar URL (takes effect on next initAvatar() call)
    setAvatarUrl: function (url) {
      window.AMANDLA_CONFIG = window.AMANDLA_CONFIG || {}
      window.AMANDLA_CONFIG.avatarUrl = url
    },
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
