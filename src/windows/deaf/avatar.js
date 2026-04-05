// AMANDLA Avatar — Deaf window only
// v3.0: Mixamo GLB + TransitionEngine — SLERP quaternions, coarticulation,
//       blendshape NMMs, lifelike idle, signing space, forearm twist fix.
//
// Pipeline:
//   signs_library.js → TransitionEngine → pose object
//   pose object      → AvatarDriver (BONE_MAP + remap) → Mixamo bones
//   Three.js render loop → screen
//
// Requirement sources:
//   SignON D5.2 | VLibras WebMedia 2025 | de Villiers Stellenbosch 2014
//   van Zijl ASSETS 2006 | Czech SL MoCap LREC 2020 | Sign-Kit ISL Toolkit

(function () {
  'use strict';

  // ── CONSTANTS (Czech MoCap: 0.38s continuous signing pace) ─────────
  const SIGN_HOLD    = 0.32   // was 0.38 — matches conversational signing
  const SIGN_FS_HOLD = 0.19   // was 0.22 — fingerspell ~5 chars/sec
  const SIGN_GAP     = 0.10   // was 0.18 — tighter coarticulation gap

  // ── STATE ───────────────────────────────────────────────────────────
  let scene, camera, renderer, animFrameId
  let avatarBones   = {}
  let signQueue     = []
  let currentSign   = null
  let finalPose     = null
  let idleSign      = null
  let animState     = 'idle'  // 'idle' | 'transitioning' | 'holding' | 'gap'
  let holdTimer     = 0
  let gapTimer      = 0
  let oscTime       = 0
  let lastFrameTime = performance.now()
  let initialized   = false
  let usingGLTFAvatar = false  // true once GLB loaded successfully

  let targetHeadZ   = 0
  let targetHeadX   = 0

  // ── NMM STATE ──────────────────────────────────────────────────────
  let nmmActive          = []
  let nmmDuration        = 0
  let nmmElapsed         = 0
  let nmmOscTime         = 0
  let nmBrowLiftTarget   = 0
  let nmBrowFurrowTarget = 0
  let nmBrowLiftCur      = 0
  let nmBrowFurrowCur    = 0
  let nmMouthOpenTarget  = 0
  let nmMouthOpenCur     = 0
  let nmHeadShake        = false
  let nmHeadNod          = false

  // ── MOTION STATE ───────────────────────────────────────────────────
  let holdTotal    = 0.32
  let holdStartOsc = 0

  // ── LIFELIKE IDLE STATE ────────────────────────────────────────────
  let eyeGazeTimer    = 2.0
  let eyeGazeTargetX  = 0
  let eyeGazeTargetY  = 0
  let eyeBlinkTimer   = 3.5
  let eyeBlinkPhase   = 0   // 0=open, 1=closing, 2=opening
  let _idleRetries    = 0

  // ── INIT ────────────────────────────────────────────────────────────
  function initAvatar (containerId) {
    containerId = containerId || 'avatar-canvas'
    const container = document.getElementById(containerId)
    if (!container) { console.error('[Avatar] container not found:', containerId); return }
    if (initialized) return
    initialized = true

    if (typeof THREE === 'undefined') { console.error('[Avatar] THREE.js not loaded'); return }

    const W = container.clientWidth  || 480
    const H = container.clientHeight || 500

    scene = new THREE.Scene()
    scene.background = new THREE.Color(0x050810)
    scene.fog = new THREE.FogExp2(0x050810, 0.18)

    camera = new THREE.PerspectiveCamera(46, W / H, 0.1, 100)
    camera.position.set(0, 0.85, 4.0)
    camera.lookAt(0, 0.35, 0)

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    renderer.setSize(W, H, false)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled    = true
    renderer.shadowMap.type       = THREE.PCFSoftShadowMap
    renderer.outputEncoding       = THREE.sRGBEncoding
    renderer.toneMapping          = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure  = 1.1
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

    // ── Lighting ─────────────────────────────────────────────────
    scene.add(new THREE.AmbientLight(0x8090C8, 0.40))

    const key = new THREE.DirectionalLight(0xFFF5E8, 1.3)
    key.position.set(1.5, 3.5, 2.5)
    key.castShadow = true
    key.shadow.mapSize.width  = 1024
    key.shadow.mapSize.height = 1024
    key.shadow.camera.near    = 0.5
    key.shadow.camera.far     = 20
    key.shadow.radius         = 3
    scene.add(key)

    const fill = new THREE.DirectionalLight(0xB06EF3, 0.55)
    fill.position.set(-2.5, 0.8, 1.5)
    scene.add(fill)

    const rim = new THREE.DirectionalLight(0x00D4A3, 0.45)
    rim.position.set(0, -0.5, -3)
    scene.add(rim)

    const under = new THREE.DirectionalLight(0xF0B429, 0.18)
    under.position.set(0, -3, 1)
    scene.add(under)

    window.addEventListener('resize', function () {
      const W2 = container.clientWidth, H2 = container.clientHeight
      camera.aspect = W2 / H2
      camera.updateProjectionMatrix()
      renderer.setSize(W2, H2, false)
    })

    // Load GLB; fallback to procedural skeleton on error
    loadHumanAvatar(container)

    console.log('[Avatar] v3 initialized — deaf window')
  }

  // ── LOAD HUMAN AVATAR (GLTFLoader) ──────────────────────────────────
  // Req 1 (SignON D5.2): Replace procedural skeleton with GLTF human avatar.
  // Req 11 (SignON D5.2): Mobile URL support.
  function loadHumanAvatar (container) {
    if (typeof THREE.GLTFLoader === 'undefined') {
      console.warn('[Avatar] THREE.GLTFLoader not available — falling back to procedural skeleton.')
      buildAvatarSkeleton()
      buildIdleSign()
      animate()
      return
    }

    // Mobile optimization (SignON D5.2 §4.2)
    const isMobile = /iPhone|iPad|Android|Mobile/i.test(navigator.userAgent)
    const cfg      = window.AMANDLA_CONFIG || {}
    const avatarUrl = isMobile
      ? (cfg.avatarUrlMobile || 'assets/models/avatar_mobile.glb')
      : (cfg.avatarUrl       || 'assets/models/avatar.glb')

    // Show skeleton loading state
    if (container) container.classList.add('skeleton')

    const loader = new THREE.GLTFLoader()
    loader.load(
      avatarUrl,

      // onLoad
      function (gltf) {
        const model = gltf.scene

        // ── Scale and centre model ──────────────────────────────
        model.position.set(0, -1.2, 0)

        // ── Traverse: shadows + skin tone ─────────────────────
        model.traverse(function (node) {
          if (!node.isMesh) return
          node.castShadow    = true
          node.receiveShadow = true

          const mat = node.material
          if (!mat) return
          const n = (mat.name || '').toLowerCase()
          if (n.includes('skin') || n.includes('body') || n.includes('head')) {
            mat.roughness = 0.72
            mat.metalness = 0.0
            // Warm South African medium-brown skin tone (preserved from v2 for cultural accuracy)
            mat.color = new THREE.Color(0xA8734A)
          }
        })

        scene.add(model)

        // ── Bind bones via AvatarDriver ─────────────────────────
        if (window.AvatarDriver) {
          window.AvatarDriver.bindBonesFromGLTF(model, avatarBones)
        } else {
          _bindBonesFallback(model)
        }

        usingGLTFAvatar = true
        if (container) container.classList.remove('skeleton')

        buildIdleSign()
        animate()
        console.log('[Avatar] GLB loaded:', avatarUrl)
      },

      // onProgress
      function (xhr) {
        if (xhr.total > 0) {
          const pct = Math.round(xhr.loaded / xhr.total * 100)
          console.log('[Avatar] loading…', pct + '%')
        }
      },

      // onError
      function (err) {
        console.warn('[Avatar] Failed to load GLB model. Falling back to procedural skeleton.', err)
        if (container) container.classList.remove('skeleton')
        buildAvatarSkeleton()
        buildIdleSign()
        animate()
      }
    )
  }

  // Inline bone binding in case AvatarDriver script didn't load
  function _bindBonesFallback (model) {
    const get = function (name) { return model.getObjectByName(name) || null }
    avatarBones.head  = get('mixamorigHead')
    avatarBones.torso = get('mixamorigSpine1')

    const sides = ['R', 'L']
    const names = {
      R: { sh:'mixamorigRightArm', el:'mixamorigRightForeArm', wr:'mixamorigRightHand' },
      L: { sh:'mixamorigLeftArm',  el:'mixamorigLeftForeArm',  wr:'mixamorigLeftHand'  },
    }
    sides.forEach(function (side) {
      const n = names[side]
      avatarBones[side] = {
        shoulder: get(n.sh), elbow: get(n.el), wrist: get(n.wr),
        fingers: _mapFingersFallback(model, side), _twistBone: null,
      }
    })

    let faceMorphMesh = null
    model.traverse(function (node) {
      if (!faceMorphMesh && node.isMesh && node.morphTargetDictionary) {
        faceMorphMesh = node
      }
    })
    avatarBones.faceMorphMesh = faceMorphMesh
    avatarBones.face = { browL: null, browR: null, mouth: null }
  }

  function _mapFingersFallback (model, side) {
    const S     = side === 'R' ? 'Right' : 'Left'
    const names = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']
    return names.map(function (f) {
      const segs = [1, 2, 3].map(function (i) {
        const bone = model.getObjectByName('mixamorig' + S + 'Hand' + f + i)
        return { pivot: bone || { rotation: { x: 0, y: 0, z: 0 } } }
      })
      return { segments: segs }
    })
  }

  // ── IDLE SIGN — v2-compatible pose object ───────────────────────────
  // Req 9: Infinite retry guard
  function buildIdleSign () {
    const lib = window.AMANDLA_SIGNS
    if (!lib || !lib.armToQuat) {
      if (++_idleRetries > 80) {
        console.error('[Avatar] AMANDLA_SIGNS never loaded after 8s. Check script order.')
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
      osc: null, isFingerspell: false,
    }
    applyPoseDirect({
      R: { sh:idleR.sh, el:idleR.el, wr:idleR.wr, hand:lib.HS.rest },
      L: { sh:idleL.sh, el:idleL.el, wr:idleL.wr, hand:lib.HS.rest },
    })
  }

  // ── PROCEDURAL SKELETON (fallback) ──────────────────────────────────
  // Kept intact per Req 1 — used when GLB is unavailable.
  function buildAvatarSkeleton () {
    const mat = {
      skin:   new THREE.MeshStandardMaterial({ color: 0xA8734A, roughness: 0.72, metalness: 0.0 }),
      shirt:  new THREE.MeshStandardMaterial({ color: 0x0B0E1A, roughness: 0.88, metalness: 0.06 }),
      teal:   new THREE.MeshStandardMaterial({ color: 0x00D4A3, roughness: 0.28, metalness: 0.18,
                emissive: new THREE.Color(0x00D4A3), emissiveIntensity: 0.14 }),
      purple: new THREE.MeshStandardMaterial({ color: 0xB06EF3, roughness: 0.28, metalness: 0.18,
                emissive: new THREE.Color(0xB06EF3), emissiveIntensity: 0.14 }),
    }

    const torsoGroup = new THREE.Group()
    torsoGroup.position.set(0, -0.1, 0)
    scene.add(torsoGroup)

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
    const eyeMat = new THREE.MeshStandardMaterial({ color: 0x0A0A14, roughness: 0.15, metalness: 0.6 })
    const eyeL = new THREE.Mesh(eyeGeo, eyeMat)
    eyeL.position.set(-0.085, 0.04, 0.18)
    headGroup.add(eyeL)
    const eyeR = new THREE.Mesh(eyeGeo, eyeMat)
    eyeR.position.set( 0.085, 0.04, 0.18)
    headGroup.add(eyeR)

    const browGeo = new THREE.BoxGeometry(0.082, 0.013, 0.013)
    const browMat = new THREE.MeshStandardMaterial({ color: 0x2A1A0E, roughness: 0.9, metalness: 0.0 })

    const browLGroup = new THREE.Group()
    browLGroup.position.set(-0.075, 0.092, 0.170)
    headGroup.add(browLGroup)
    browLGroup.add(new THREE.Mesh(browGeo, browMat))

    const browRGroup = new THREE.Group()
    browRGroup.position.set(0.075, 0.092, 0.170)
    headGroup.add(browRGroup)
    browRGroup.add(new THREE.Mesh(browGeo, browMat))

    const mouthGeo = new THREE.BoxGeometry(0.090, 0.018, 0.011)
    const mouthMat = new THREE.MeshStandardMaterial({ color: 0x8B3A3A, roughness: 0.65, metalness: 0.0 })
    const mouthGroup = new THREE.Group()
    mouthGroup.position.set(0, -0.065, 0.183)
    headGroup.add(mouthGroup)
    mouthGroup.add(new THREE.Mesh(mouthGeo, mouthMat))

    avatarBones.face = { browL: browLGroup, browR: browRGroup, mouth: mouthGroup }
    avatarBones.faceMorphMesh = null

    avatarBones.R = buildArm('R', -0.34, mat, torsoGroup)
    avatarBones.L = buildArm('L',  0.34, mat, torsoGroup)
  }

  function buildArm (side, torsoX, mat, parent) {
    const isRight   = side === 'R'
    const fingerMat = isRight ? mat.teal : mat.purple

    const shoulder = new THREE.Group()
    shoulder.position.set(torsoX, 0.36, 0)
    parent.add(shoulder)

    const upperArm = new THREE.Mesh(
      new THREE.CylinderGeometry(0.068, 0.062, 0.36, 10), mat.skin)
    upperArm.position.set(0, -0.18, 0)
    shoulder.add(upperArm)

    const elbow = new THREE.Group()
    elbow.position.set(0, -0.36, 0)
    shoulder.add(elbow)

    const forearm = new THREE.Mesh(
      new THREE.CylinderGeometry(0.053, 0.048, 0.32, 10), mat.skin)
    forearm.position.set(0, -0.16, 0)
    elbow.add(forearm)

    const wrist = new THREE.Group()
    wrist.position.set(0, -0.32, 0)
    elbow.add(wrist)

    const palm = new THREE.Mesh(
      new THREE.BoxGeometry(0.11, 0.15, 0.045), mat.skin)
    palm.position.set(0, -0.10, 0)
    wrist.add(palm)

    const fingers = buildFingers(wrist, fingerMat, isRight)

    return { shoulder, elbow, wrist, fingers }
  }

  function buildFingers (wristGroup, mat, isRight) {
    const fingers = []
    const xOff = isRight
      ? [-0.062, -0.030, 0.001, 0.032, 0.062]
      : [ 0.062,  0.030,-0.001,-0.032,-0.062]
    const segLengths = [0.036, 0.030, 0.026]

    for (let f = 0; f < 5; f++) {
      const isThumb    = f === 0
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
          new THREE.CylinderGeometry(0.013 - s * 0.002, 0.015 - s * 0.002, segLen, 7), mat)
        mesh.position.set(0, -segLen / 2, 0)
        pivot.add(mesh)
        segments.push({ pivot, length: segLen })
        yOff += segLen
      }
      fingers.push({ group: fingerGroup, segments })
    }
    return fingers
  }

  // ── POSE APPLICATION ────────────────────────────────────────────────
  // Req 2: remapPoseForMixamo applied when using GLB.
  function applyPoseDirect (pose) {
    if (!pose || !avatarBones.R) return

    if (usingGLTFAvatar) {
      // Delegate axis remapping to AvatarDriver (or inline fallback)
      if (window.AvatarDriver) {
        window.AvatarDriver.remapPoseForMixamo(pose, avatarBones)
      } else {
        _remapPoseInline(pose)
      }
      // Handshapes — Mixamo fingers curl on .z
      for (const side of ['R', 'L']) {
        const data = pose[side]
        const arm  = avatarBones[side]
        if (data && data.hand && arm && arm.fingers) {
          if (window.AvatarDriver) {
            window.AvatarDriver.applyHandshapeGLTF(arm.fingers, data.hand)
          } else {
            applyHandshapeDirect(arm.fingers, data.hand)
          }
        }
      }
    } else {
      // Procedural rig — direct Euler set
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

  // Inline remap (used if avatar_driver.js didn't load)
  function _remapPoseInline (pose) {
    for (const side of ['R', 'L']) {
      const src = pose[side]
      const arm = avatarBones[side]
      if (!src || !arm) continue
      const sign = side === 'R' ? 1 : -1
      if (src.sh && arm.shoulder) arm.shoulder.rotation.set(src.sh.x||0, src.sh.y||0, src.sh.z||0)
      if (src.el && arm.elbow)    arm.elbow.rotation.set(0, (src.el.x||0)*sign, src.el.z||0)
      if (src.wr && arm.wrist)    arm.wrist.rotation.set(src.wr.x||0, src.wr.y||0, src.wr.z||0)
    }
  }

  // Req 2: finger curl — procedural rig uses .x, Mixamo uses .z
  function applyHandshapeDirect (fingers, hs) {
    if (!hs) return
    const keys = ['t', 'i', 'm', 'r', 'p']
    const axis = usingGLTFAvatar ? 'z' : 'x'
    for (let f = 0; f < 5; f++) {
      const segs = hs[keys[f]]
      if (!segs || !fingers[f]) continue
      for (let s = 0; s < 3 && s < segs.length; s++) {
        const seg = fingers[f].segments[s]
        if (!seg) continue
        seg.pivot.rotation[axis] = segs[s] || 0
      }
    }
  }

  // ── OSCILLATION ──────────────────────────────────────────────────────
  function applyOscillation (signObj, time) {
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

  // ── MOTION (arc / tap / circle) ──────────────────────────────────────
  function applyMotion (signObj, holdProgress) {
    if (!signObj || !signObj.motion) return
    const { type, joint, axis, amp, freq } = signObj.motion
    const f = freq || 1.0
    let val = 0

    if (type === 'tap' || type === 'arc') {
      val = Math.sin(holdProgress * Math.PI) * amp
    } else if (type === 'circle') {
      const angle = holdProgress * f * Math.PI * 2
      val = Math.sin(angle) * amp
      const perpAxis = (axis === 'x') ? 'z' : 'x'
      _addJointDelta(joint, perpAxis, Math.cos(angle) * amp * 0.55)
    }
    _addJointDelta(joint, axis, val)
  }

  function _addJointDelta (joint, axis, val) {
    if      (joint === 'R_sh'   && avatarBones.R) avatarBones.R.shoulder.rotation[axis] += val
    else if (joint === 'L_sh'   && avatarBones.L) avatarBones.L.shoulder.rotation[axis] += val
    else if (joint === 'R_el'   && avatarBones.R) avatarBones.R.elbow.rotation[axis]    += val
    else if (joint === 'L_el'   && avatarBones.L) avatarBones.L.elbow.rotation[axis]    += val
    else if (joint === 'R_wr'   && avatarBones.R) avatarBones.R.wrist.rotation[axis]    += val
    else if (joint === 'L_wr'   && avatarBones.L) avatarBones.L.wrist.rotation[axis]    += val
    else if (joint === 'both_sh') {
      if (avatarBones.R) avatarBones.R.shoulder.rotation[axis] += val
      if (avatarBones.L) avatarBones.L.shoulder.rotation[axis] += val
    } else if (joint === 'both_el') {
      if (avatarBones.R) avatarBones.R.elbow.rotation[axis] += val
      if (avatarBones.L) avatarBones.L.elbow.rotation[axis] += val
    } else if (joint === 'both_wr') {
      if (avatarBones.R) avatarBones.R.wrist.rotation[axis] += val
      if (avatarBones.L) avatarBones.L.wrist.rotation[axis] += val
    }
  }

  // ── NMM APPLICATION ──────────────────────────────────────────────────
  // Req 3: blendshape-based NMMs when faceMorphMesh available.
  function applyNMMs (dt) {
    if (nmmActive.length > 0) {
      nmmElapsed += dt
      nmmOscTime += dt
      if (nmmElapsed >= nmmDuration + 0.40) nmmActive = []
    }

    let env = 0
    if (nmmActive.length > 0) {
      const fadeIn  = Math.min(nmmElapsed / 0.20, 1.0)
      const fadeOut = nmmDuration > 0
        ? Math.max(0, 1.0 - Math.max(0, nmmElapsed - nmmDuration) / 0.30)
        : 1.0
      env = fadeIn * fadeOut
    }

    const lerp = Math.min(7.0 * dt, 1.0)
    nmBrowLiftCur   += (nmBrowLiftTarget   * env - nmBrowLiftCur)   * lerp
    nmBrowFurrowCur += (nmBrowFurrowTarget * env - nmBrowFurrowCur) * lerp
    nmMouthOpenCur  += (nmMouthOpenTarget  * env - nmMouthOpenCur)  * lerp

    // ── Procedural face bones (fallback) ─────────────────────────
    const f = avatarBones.face
    if (f) {
      if (f.browL) {
        f.browL.position.y = 0.092 + nmBrowLiftCur
        f.browL.rotation.z = -nmBrowFurrowCur
      }
      if (f.browR) {
        f.browR.position.y = 0.092 + nmBrowLiftCur
        f.browR.rotation.z =  nmBrowFurrowCur
      }
      if (f.mouth) {
        f.mouth.position.y = -0.065 + nmMouthOpenCur
      }
    }

    // ── Blendshape NMMs (Req 3 — SignON D5.2 Annex II FACS AUs) ─────
    const morph = avatarBones.faceMorphMesh
    if (morph && morph.morphTargetInfluences && morph.morphTargetDictionary) {
      const d = morph.morphTargetDictionary

      function setMorph (names, value) {
        for (let i = 0; i < names.length; i++) {
          if (d[names[i]] !== undefined) {
            morph.morphTargetInfluences[d[names[i]]] = Math.max(0, Math.min(1, value))
            return
          }
        }
      }

      // AU1+AU2 (raised brows — yes/no question)
      setMorph(['browInnerUp',   'Eyebrow_Arch_Left'],   nmBrowLiftCur * 12)
      setMorph(['browOuterUpLeft','Eyebrow_Arch_Right'], nmBrowLiftCur * 12)
      // AU4 (furrowed brows — wh-question)
      setMorph(['browDownLeft',  'Eyebrow_Frown_Left'],  nmBrowFurrowCur * 5)
      setMorph(['browDownRight', 'Eyebrow_Frown_Right'], nmBrowFurrowCur * 5)
      // AU27 (jaw open — emphasis / puffed cheeks)
      setMorph(['jawOpen',       'Mouth_Stretch'],       Math.abs(nmMouthOpenCur * 40))

      // ── Automatic eye blinks (lifelike idle — AU45) ────────────
      eyeBlinkTimer -= dt
      if (eyeBlinkTimer <= 0 && eyeBlinkPhase === 0) {
        eyeBlinkPhase = 1
        eyeBlinkTimer = 0.06  // 60ms close
      }
      if (eyeBlinkPhase > 0) {
        const bv = eyeBlinkPhase === 1
          ? (1.0 - eyeBlinkTimer / 0.06)
          : (eyeBlinkTimer / 0.06)
        setMorph(['eyeBlinkLeft',  'Eye_Blink_Left'],  Math.min(1, Math.max(0, bv)))
        setMorph(['eyeBlinkRight', 'Eye_Blink_Right'], Math.min(1, Math.max(0, bv)))
        if (eyeBlinkTimer <= 0) {
          if (eyeBlinkPhase === 1) { eyeBlinkPhase = 2; eyeBlinkTimer = 0.08 }
          else                     { eyeBlinkPhase = 0; eyeBlinkTimer = 3.0 + Math.random() * 4.0 }
        }
      }
    }

    // Head shake — grammatical negation
    if (nmHeadShake && env > 0.05 && avatarBones.head) {
      avatarBones.head.rotation.y = Math.sin(nmmOscTime * 5.5 * Math.PI * 2) * 0.10 * env
    }

    // Head nod — affirmation
    if (nmHeadNod && env > 0.05 && avatarBones.head) {
      avatarBones.head.rotation.x = Math.sin(nmmOscTime * 3.0 * Math.PI * 2) * 0.07 * env + targetHeadX
    }
  }

  // ── SET NMMs ─────────────────────────────────────────────────────────
  // Req 4: full SASL grammar markers (van Zijl 2006, de Villiers 2014)
  function setNMMs (nmms, durationSecs) {
    if (!nmms || nmms.length === 0) return
    nmmActive          = nmms
    nmmDuration        = durationSecs || 1.5
    nmmElapsed         = 0
    nmmOscTime         = 0
    nmBrowLiftTarget   = 0
    nmBrowFurrowTarget = 0
    nmMouthOpenTarget  = 0
    nmHeadShake        = false
    nmHeadNod          = false

    for (let i = 0; i < nmms.length; i++) {
      const n = nmms[i].toLowerCase()

      // Yes/no question — raised eyebrows
      if (n.includes('raised eyebrows') || n.includes('eyebrows up')) {
        nmBrowLiftTarget = 0.026
      }
      // Wh-question — furrowed brows
      if (n.includes('furrowed') || n.includes('wh-question') || n.includes('wh question')) {
        nmBrowFurrowTarget = 0.22
        nmBrowLiftTarget   = -0.005
      }
      // Negation
      if (n.includes('head shake') || n.includes('negation') || n.includes('negative')) {
        nmHeadShake = true
      }
      // Affirmation
      if (n.includes('head nod') || n.includes('affirmation') || n.includes('nodding')) {
        nmHeadNod = true
      }
      // Mouth shape
      if (n.includes('mouth open') || n.includes('puffed') || n.includes('cha')) {
        nmMouthOpenTarget = -0.010
      }
      // Head tilt forward
      if (n.includes('head tilt forward') || n.includes('lean forward')) {
        targetHeadX = Math.max(targetHeadX, 0.08)
      }
      // SASL: Topicalization (de Villiers 2014)
      if (n.includes('topic') || n.includes('topicalization') || n.includes('about')) {
        nmBrowLiftTarget = Math.max(nmBrowLiftTarget, 0.018)
        targetHeadX      = Math.max(targetHeadX, 0.05)
      }
      // SASL: Rhetorical question
      if (n.includes('rhetorical')) {
        nmBrowFurrowTarget = 0.16
      }
      // SASL: Intensifier / emphasis (van Zijl 2006)
      if (n.includes('intensifier') || n.includes('very') || n.includes('extreme') || n.includes('strong')) {
        targetHeadX      = Math.max(targetHeadX, 0.09)
        nmBrowLiftTarget = Math.max(nmBrowLiftTarget, 0.015)
      }
      // SASL: Conditional / if-clause
      if (n.includes('conditional') || n.includes('if-clause')) {
        nmBrowLiftTarget = Math.max(nmBrowLiftTarget, 0.022)
      }
      // SASL: Negative incorporation (van Zijl 2006 — NOT, NONE, NEVER, REFUSE)
      if (n.includes('not') || n.includes('none') || n.includes('never') || n.includes('refuse')) {
        nmHeadShake        = true
        nmBrowFurrowTarget = Math.max(nmBrowFurrowTarget, 0.12)
      }
      // SASL: Surprise / exclamation
      if (n.includes('surprise') || n.includes('exclamation') || n.includes('wow')) {
        nmBrowLiftTarget  = Math.max(nmBrowLiftTarget, 0.030)
        nmMouthOpenTarget = Math.min(nmMouthOpenTarget, -0.014)
      }
    }
  }

  // ── SIGNING SPACE (Req 5 — van Zijl 2006 §3) ────────────────────────
  // Establishes spatial loci for entities; generates pointing signs.
  const SigningSpace = (function () {
    const loci = {}

    function establish (entity, xPos) {
      loci[entity.toUpperCase()] = { x: xPos, y: 0, z: 0 }
    }

    function getPointingSign (entity) {
      const loc = loci[entity.toUpperCase()]
      if (!loc) return null
      const lib  = window.AMANDLA_SIGNS
      const shZ  = -(loc.x * 0.5)
      const Rarm = { sh:{x:-0.35,y:0,z:shZ}, el:{x:0.6,y:0,z:0}, wr:{x:0,y:0,z:0} }
      const Larm = { sh:{x:0.05,y:0,z:0.24}, el:{x:0.08,y:0,z:0}, wr:{x:0,y:0,z:0} }
      return {
        name: 'POINT-' + entity,
        R: { ...Rarm, hand: lib && lib.HS ? lib.HS.point : null },
        L: { ...Larm, hand: lib && lib.HS ? lib.HS.rest  : null },
        _Rq: lib && lib.armToQuat ? { end: lib.armToQuat(Rarm), start: lib.armToQuat(Rarm) } : null,
        _Lq: lib && lib.armToQuat ? { end: lib.armToQuat(Larm), start: lib.armToQuat(Larm) } : null,
        isFingerspell: false, osc: null,
      }
    }

    function clear () { Object.keys(loci).forEach(function (k) { delete loci[k] }) }

    return { establish, getPointingSign, clear }
  })()

  // ── SIGN-KIT CONVERTER (Req 6) ───────────────────────────────────────
  // Converts Sign-Kit ISL Toolkit animation phases → AMANDLA v2 sign object.
  function convertSignKitSign (name, phases, handshapeR, handshapeL) {
    const lib    = window.AMANDLA_SIGNS
    const phase  = (phases && phases.length > 1) ? phases[1] : (phases && phases[0]) || []

    const R = { sh:{x:0,y:0,z:0}, el:{x:0,y:0,z:0}, wr:{x:0,y:0,z:0} }
    const L = { sh:{x:0,y:0,z:0}, el:{x:0,y:0,z:0}, wr:{x:0,y:0,z:0} }

    phase.forEach(function (entry) {
      const [bone, , axis, value] = entry
      if (bone === 'mixamorigRightArm') {
        if (axis === 'x') R.sh.x = -value
        if (axis === 'z') R.sh.z = -value
      } else if (bone === 'mixamorigRightForeArm') {
        if (axis === 'y') R.el.x = value
        if (axis === 'z') R.el.z = value
      } else if (bone === 'mixamorigLeftArm') {
        if (axis === 'x') L.sh.x = -value
        if (axis === 'z') L.sh.z = -value
      } else if (bone === 'mixamorigLeftForeArm') {
        if (axis === 'y') L.el.x = -value
        if (axis === 'z') L.el.z = value
      }
    })

    const hsR = handshapeR || (lib && lib.HS ? lib.HS.flat : null)
    const hsL = handshapeL || (lib && lib.HS ? lib.HS.flat : null)

    return {
      name:          name,
      R:             { sh:R.sh, el:R.el, wr:R.wr, hand:hsR },
      L:             { sh:L.sh, el:L.el, wr:L.wr, hand:hsL },
      _Rq:           lib && lib.armToQuat ? { end: lib.armToQuat(R), start: lib.armToQuat(R) } : null,
      _Lq:           lib && lib.armToQuat ? { end: lib.armToQuat(L), start: lib.armToQuat(L) } : null,
      osc:           null,
      isFingerspell: false,
    }
  }

  // Register Sign-Kit signs when AMANDLA_SIGNS ready
  function registerConvertedSigns () {
    const lib = window.AMANDLA_SIGNS
    if (!lib || !lib.armToQuat) { setTimeout(registerConvertedSigns, 150); return }
    if (!lib.SIGN_LIBRARY) return

    // HOME sign (Sign-Kit ISL Toolkit — both arms raised, forearms rotated inward)
    lib.SIGN_LIBRARY['HOME'] = convertSignKitSign('HOME', [
      [
        ['mixamorigRightArm',     'rotation', 'x', -Math.PI / 6],
        ['mixamorigRightForeArm', 'rotation', 'y',  Math.PI / 2.5],
        ['mixamorigRightForeArm', 'rotation', 'z',  Math.PI / 7],
        ['mixamorigLeftArm',      'rotation', 'x', -Math.PI / 6],
        ['mixamorigLeftForeArm',  'rotation', 'y', -Math.PI / 2.5],
        ['mixamorigLeftForeArm',  'rotation', 'z', -Math.PI / 7],
      ]
    ], lib.HS.flat, lib.HS.flat)
  }
  registerConvertedSigns()

  // ── LIFELIKE IDLE (Req 7 — SignON D5.2 §4.1, VLibras 2025) ─────────
  function applyLifelikeIdle (dt) {
    // 1. Chest breathing (ribcage expansion — physiologically correct)
    if (avatarBones.torso) {
      const breathIn = Math.sin(oscTime * 0.25 * Math.PI * 2)
      avatarBones.torso.scale.set(
        1.0 + breathIn * 0.015,
        1.0 + breathIn * 0.005,
        1.0 + breathIn * 0.020
      )
    }

    // 2. Subtle arm breathing (halved from original — not a shrug)
    if (avatarBones.R && avatarBones.L && animState === 'idle') {
      const sway = Math.sin(oscTime * 0.40) * 0.008
      avatarBones.R.shoulder.rotation.z = lerpVal(avatarBones.R.shoulder.rotation.z, -0.24 + sway, 0.05)
      avatarBones.L.shoulder.rotation.z = lerpVal(avatarBones.L.shoulder.rotation.z,  0.24 - sway, 0.05)
    }

    // 3. Eye saccades — humans never stare perfectly still
    eyeGazeTimer -= dt
    if (eyeGazeTimer <= 0) {
      eyeGazeTargetX = (Math.random() - 0.5) * 0.04
      eyeGazeTargetY = (Math.random() - 0.5) * 0.015
      eyeGazeTimer   = 1.5 + Math.random() * 2.5
    }
    // Apply eye rotation if bones available
    const leftEyeBone  = avatarBones.R ? null : null  // resolved via scene traversal if needed
    const rightEyeBone = null
    if (scene) {
      const lEye = scene.getObjectByName ? scene.getObjectByName('mixamorigLeftEye')  : null
      const rEye = scene.getObjectByName ? scene.getObjectByName('mixamorigRightEye') : null
      if (lEye) {
        lEye.rotation.y += (eyeGazeTargetX - lEye.rotation.y) * 0.08
        lEye.rotation.x += (eyeGazeTargetY - lEye.rotation.x) * 0.08
      }
      if (rEye) {
        rEye.rotation.y = lEye ? lEye.rotation.y : 0
        rEye.rotation.x = lEye ? lEye.rotation.x : 0
      }
    }
  }

  // ── FOREARM TWIST BONES (Req 8 — candy-wrapper fix) ─────────────────
  function updateTwistBones () {
    if (!usingGLTFAvatar) return
    if (window.AvatarDriver) {
      window.AvatarDriver.updateTwistBones(scene, avatarBones)
      return
    }
    // Inline fallback
    for (const side of ['R', 'L']) {
      const arm = avatarBones[side]
      if (!arm || !arm.wrist) continue
      if (!arm._twistBone && scene) {
        const tname = 'mixamorig' + (side === 'R' ? 'Right' : 'Left') + 'ForeArmTwist'
        scene.traverse(function (n) { if (n.name === tname) arm._twistBone = n })
      }
      if (arm._twistBone) arm._twistBone.rotation.y = arm.wrist.rotation.y * 0.5
    }
  }

  // ── HELPERS ──────────────────────────────────────────────────────────
  function lerpVal (cur, target, t) {
    return cur + (target - cur) * Math.min(t * 1.6, 1.0)
  }

  function computeHeadTarget (signObj) {
    if (!signObj || !signObj.R || !signObj.R.sh) { targetHeadZ = 0; targetHeadX = 0; return }
    const rUp = signObj.R.sh.x < -0.3
    const lUp = signObj.L && signObj.L.sh && signObj.L.sh.x < -0.3
    if      (rUp && !lUp) { targetHeadZ =  0.09; targetHeadX = 0.04 }
    else if (lUp && !rUp) { targetHeadZ = -0.09; targetHeadX = 0.04 }
    else if (rUp && lUp)  { targetHeadZ =  0;    targetHeadX = 0.06 }
    else                  { targetHeadZ =  0;    targetHeadX = 0 }
  }

  // ── SIGN QUEUE ────────────────────────────────────────────────────────
  function resolveSign (item) {
    if (!item) return null
    if (typeof item === 'object' && item._Rq) return item
    const lib  = window.AMANDLA_SIGNS
    if (!lib) return null
    const name = typeof item === 'string' ? item : item.name || ''
    if (lib.SIGN_LIBRARY && lib.SIGN_LIBRARY[name])              return lib.SIGN_LIBRARY[name]
    if (lib.SIGN_LIBRARY && lib.SIGN_LIBRARY[name.toUpperCase()]) return lib.SIGN_LIBRARY[name.toUpperCase()]
    if (lib.fingerspell) {
      const fs = lib.fingerspell(name)
      if (fs && fs.length > 0) return fs[0]
    }
    return null
  }

  function queueSign (signObj) {
    if (typeof signObj === 'string') {
      const lib = window.AMANDLA_SIGNS
      if (lib && lib.sentenceToSigns) {
        lib.sentenceToSigns(signObj).forEach(function (s) { signQueue.push(s) })
        return
      }
    }
    const s = resolveSign(signObj)
    if (s) signQueue.push(s)
  }

  function queueSentence (text) {
    const lib = window.AMANDLA_SIGNS
    if (!lib) return
    const signs = lib.sentenceToSigns(text)
    signs.forEach(function (s) { signQueue.push(s) })
    updateLabel(signs.length > 0 ? signs[0].name : '')
  }

  function playSignNow (signNameOrObj) {
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

  function updateLabel (text) {
    const el = document.getElementById('avatar-sign-label')
    if (el) el.textContent = text || ''
  }

  function buildNMMMarkers (nmm) {
    const out = []
    if (nmm.browLift   > 0)  out.push('raised eyebrows')
    if (nmm.browFurrow > 0)  out.push('furrowed brows')
    if (nmm.mouthOpen  > 0)  out.push('mouth open')
    if (nmm.headShake)       out.push('head shake')
    if (nmm.headNod)         out.push('head nod')
    return out
  }

  function startNextTransition (fromOverride) {
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

    // Apply sign-level non-manual markers if the sign data includes them
    if (currentSign && currentSign.nmm) {
      const markers = buildNMMMarkers(currentSign.nmm)
      const signDur = currentSign.duration ? currentSign.duration / 1000 : SIGN_HOLD
      if (markers.length > 0) setNMMs(markers, signDur)
    }
  }

  // ── ANIMATION LOOP ────────────────────────────────────────────────────
  function animate () {
    animFrameId = requestAnimationFrame(animate)
    if (document.hidden || !renderer) return

    const now = performance.now()
    const dt  = Math.min((now - lastFrameTime) / 1000, 0.05)
    lastFrameTime = now
    oscTime += dt

    const TE = window.AMANDLA_SIGNS && window.AMANDLA_SIGNS.TransitionEngine

    // ── Sign state machine ───────────────────────────────────────
    if (animState === 'transitioning' && TE) {
      const pose = TE.tick(dt)
      if (pose) applyPoseDirect(pose)
      if (TE.isDone()) {
        finalPose    = pose
        const isFS   = currentSign && currentSign.isFingerspell
        holdTotal    = currentSign && currentSign.duration
          ? (currentSign.duration / 1000)
          : (isFS ? SIGN_FS_HOLD : SIGN_HOLD)
        holdTimer    = holdTotal
        holdStartOsc = oscTime
        animState    = 'holding'
      }

    } else if (animState === 'holding') {
      if (finalPose) applyPoseDirect(finalPose)
      if (currentSign) applyOscillation(currentSign, oscTime)
      if (currentSign && currentSign.motion) {
        const holdProgress = holdTotal > 0 ? Math.min(1.0 - holdTimer / holdTotal, 1.0) : 0
        applyMotion(currentSign, holdProgress)
      }
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
      if (finalPose) applyPoseDirect(finalPose)
      gapTimer -= dt
      if (gapTimer <= 0) {
        if (TE && idleSign && currentSign) {
          TE.begin(currentSign, idleSign, null)
          animState   = 'transitioning'
          currentSign = idleSign
        } else {
          animState = 'idle'
        }
        updateLabel('')
        targetHeadZ = 0
        targetHeadX = 0
      }

    } else {
      // Req 7: lifelike idle (replaces simple shoulder sway)
      applyLifelikeIdle(dt)
      if (signQueue.length > 0 && idleSign && TE) {
        startNextTransition(idleSign)
      }
    }

    // ── Forearm twist (Req 8) ────────────────────────────────────
    updateTwistBones()

    // ── Head tilt — always smooth ─────────────────────────────────
    if (avatarBones.head) {
      avatarBones.head.rotation.z = lerpVal(avatarBones.head.rotation.z, targetHeadZ, 0.06)
      if (!nmHeadNod || nmmActive.length === 0) {
        avatarBones.head.rotation.x = lerpVal(avatarBones.head.rotation.x, targetHeadX, 0.06)
      }
      if (!nmHeadShake || nmmActive.length === 0) {
        avatarBones.head.rotation.y = Math.sin(oscTime * 0.19 * Math.PI * 2) * 0.012
      }
    }

    // ── NMMs ──────────────────────────────────────────────────────
    applyNMMs(dt)

    renderer.render(scene, camera)
  }

  // ── CLEANUP ───────────────────────────────────────────────────────────
  function destroyAvatar () {
    if (animFrameId) cancelAnimationFrame(animFrameId)
    if (renderer) renderer.dispose()
    initialized = false
  }

  // ── PUBLIC API (Req 12) ───────────────────────────────────────────────
  window.AmandlaAvatar = {
    initAvatar:    initAvatar,
    queueSign:     queueSign,
    queueSentence: queueSentence,
    playSignNow:   playSignNow,
    setNMMs:       setNMMs,
    destroyAvatar: destroyAvatar,
    signingSpace:  SigningSpace,          // Req 5
    isGLTF:        function () { return usingGLTFAvatar },
    convertSignKitSign: convertSignKitSign,  // Req 6
  }

  window.avatarInit = function () { initAvatar('avatar-canvas') }

  window.avatarPlaySigns = function (signs, text, nmms) {
    if (!initialized) initAvatar('avatar-canvas')
    if (Array.isArray(nmms) && nmms.length > 0) {
      const n = Array.isArray(signs) ? signs.length : 1
      const phraseDur = n * (SIGN_HOLD + SIGN_GAP) + SIGN_GAP
      setNMMs(nmms, phraseDur)
    }
    if (Array.isArray(signs)) signs.forEach(function (s) { queueSign(s) })
    updateLabel(text || (signs && signs[0]) || '')
  }

})();