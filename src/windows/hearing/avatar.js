// AMANDLA Avatar — Three.js bone skeleton
// Powers both hearing (preview) and deaf (full display) windows
// Reads pose data from signs_library.js (window.AMANDLA_SIGNS)

(function () {
  'use strict';

  // ── STATE ─────────────────────────────────────────────────
  let scene, camera, renderer, animFrameId
  let avatarBones = {}
  let signQueue = []
  let currentSign = null
  let signProgress = 0
  const SIGN_DURATION = 0.55   // seconds per sign
  const SIGN_GAP = 0.12        // pause between signs
  let gapTimer = 0
  let isInGap = false
  let oscTime = 0
  let lastFrameTime = performance.now()
  let initialized = false

  // ── INIT ──────────────────────────────────────────────────
  function initAvatar(containerId) {
    containerId = containerId || 'avatar-canvas'
    const container = document.getElementById(containerId)
    if (!container) {
      console.error('[Avatar] container not found:', containerId)
      return
    }
    if (initialized) return
    initialized = true

    if (typeof THREE === 'undefined') {
      console.error('[Avatar] THREE.js not loaded — check script load order')
      return
    }

    const W = container.clientWidth || 480
    const H = container.clientHeight || 420

    scene = new THREE.Scene()
    scene.background = new THREE.Color(0x111111)

    camera = new THREE.PerspectiveCamera(48, W / H, 0.1, 100)
    camera.position.set(0, 0.9, 3.8)
    camera.lookAt(0, 0.4, 0)

    renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(W, H, false)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    const canvas = renderer.domElement
    canvas.style.display = 'block'
    canvas.style.width   = '100%'
    canvas.style.height  = '100%'
    container.appendChild(canvas)

    // Sync renderer to actual container dimensions after first layout tick
    requestAnimationFrame(function () {
      const rw = container.clientWidth, rh = container.clientHeight
      if (rw > 0 && rh > 0) {
        camera.aspect = rw / rh
        camera.updateProjectionMatrix()
        renderer.setSize(rw, rh, false)
      }
    })

    // Lighting
    scene.add(new THREE.AmbientLight(0xffffff, 0.7))
    const key = new THREE.DirectionalLight(0xffeedd, 0.9)
    key.position.set(1.5, 3, 2)
    scene.add(key)
    const fill = new THREE.DirectionalLight(0x8B6FD4, 0.35)
    fill.position.set(-2, 0, -1)
    scene.add(fill)

    buildAvatarSkeleton()
    applyIdlePose()
    animate()

    window.addEventListener('resize', function () {
      const W2 = container.clientWidth
      const H2 = container.clientHeight
      camera.aspect = W2 / H2
      camera.updateProjectionMatrix()
      renderer.setSize(W2, H2, false)
    })

    console.log('[Avatar] initialized on container:', containerId)
  }

  // ── SKELETON BUILD ────────────────────────────────────────
  function buildAvatarSkeleton() {
    const mat = {
      skin:   new THREE.MeshLambertMaterial({ color: 0xC8A07A }),
      teal:   new THREE.MeshLambertMaterial({ color: 0x2EA880 }),
      purple: new THREE.MeshLambertMaterial({ color: 0x8B6FD4 }),
      dark:   new THREE.MeshLambertMaterial({ color: 0x1A1A2E }),
    }

    // Torso
    const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.28, 1.0, 10), mat.dark)
    torso.position.set(0, -0.1, 0)
    scene.add(torso)

    // Head
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.22, 14, 10), mat.skin)
    head.position.set(0, 0.72, 0)
    scene.add(head)

    // Eyes
    const eyeGeo = new THREE.SphereGeometry(0.03, 6, 6)
    const eyeMat = new THREE.MeshLambertMaterial({ color: 0x111111 })
    const eyeL = new THREE.Mesh(eyeGeo, eyeMat)
    eyeL.position.set(-0.09, 0.76, 0.20)
    scene.add(eyeL)
    const eyeR = new THREE.Mesh(eyeGeo, eyeMat)
    eyeR.position.set(0.09, 0.76, 0.20)
    scene.add(eyeR)

    // Arms
    avatarBones.R = buildArm('R', -0.36, mat)
    avatarBones.L = buildArm('L',  0.36, mat)
  }

  function buildArm(side, torsoX, mat) {
    const isRight = side === 'R'
    const fingerMat = isRight ? mat.teal : mat.purple

    // Shoulder pivot
    const shoulder = new THREE.Group()
    shoulder.position.set(torsoX, 0.35, 0)
    scene.add(shoulder)

    // Upper arm mesh
    const upperArm = new THREE.Mesh(
      new THREE.CylinderGeometry(0.07, 0.065, 0.36, 8), mat.skin
    )
    upperArm.position.set(0, -0.18, 0)
    shoulder.add(upperArm)

    // Elbow pivot
    const elbow = new THREE.Group()
    elbow.position.set(0, -0.36, 0)
    shoulder.add(elbow)

    // Forearm mesh
    const forearm = new THREE.Mesh(
      new THREE.CylinderGeometry(0.055, 0.050, 0.32, 8), mat.skin
    )
    forearm.position.set(0, -0.16, 0)
    elbow.add(forearm)

    // Wrist pivot
    const wrist = new THREE.Group()
    wrist.position.set(0, -0.32, 0)
    elbow.add(wrist)

    // Palm
    const palm = new THREE.Mesh(
      new THREE.BoxGeometry(0.12, 0.16, 0.04), mat.skin
    )
    palm.position.set(0, -0.10, 0)
    wrist.add(palm)

    // Fingers
    const fingers = buildFingers(wrist, fingerMat, isRight)

    return {
      shoulder, elbow, wrist, fingers,
      baseSh: { x: 0, y: 0, z: 0 },
      baseEl: { x: 0, y: 0, z: 0 },
      baseWr: { x: 0, y: 0, z: 0 }
    }
  }

  function buildFingers(wristGroup, mat, isRight) {
    const fingers = []
    const xOff = isRight
      ? [-0.065, -0.032, 0.000, 0.032, 0.064]
      : [ 0.065,  0.032, 0.000,-0.032,-0.064]
    const segLengths = [0.036, 0.030, 0.026]
    const thumbScale = 0.85

    for (let f = 0; f < 5; f++) {
      const isThumb = f === 0
      const fingerGroup = new THREE.Group()
      fingerGroup.position.set(xOff[f], -0.20, 0)
      wristGroup.add(fingerGroup)

      const segments = []
      let yOff = 0
      for (let s = 0; s < 3; s++) {
        const segLen = segLengths[s] * (isThumb ? thumbScale : 1)
        const pivot = new THREE.Group()
        pivot.position.set(0, -yOff, 0)
        if (s === 0) fingerGroup.add(pivot)
        else segments[s - 1].pivot.add(pivot)

        const mesh = new THREE.Mesh(
          new THREE.CylinderGeometry(0.013 - s * 0.002, 0.015 - s * 0.002, segLen, 6),
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
    const signs = window.AMANDLA_SIGNS
    const idle = {
      R: {
        sh:   { x: 0.05, y: 0, z: -0.22 },
        el:   { x: 0.08, y: 0, z: 0 },
        wr:   { x: 0, y: 0, z: 0 },
        hand: signs ? signs.HS.rest : null
      },
      L: {
        sh:   { x: 0.05, y: 0, z:  0.22 },
        el:   { x: 0.08, y: 0, z: 0 },
        wr:   { x: 0, y: 0, z: 0 },
        hand: signs ? signs.HS.rest : null
      },
      osc: null
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
    const speed = Math.min(t * 1.5, 1.0)
    obj.rotation.x += (target.x - obj.rotation.x) * speed
    obj.rotation.y += (target.y - obj.rotation.y) * speed
    obj.rotation.z += (target.z - obj.rotation.z) * speed
  }

  function applyHandshape(fingers, hs, t) {
    // hs = { i:[mcp,pip,dip], m:[...], r:[...], p:[...], t:[a,b] }
    const keys = ['t', 'i', 'm', 'r', 'p']
    for (let f = 0; f < 5; f++) {
      const segs = hs[keys[f]]
      if (!segs || !fingers[f]) continue
      for (let s = 0; s < 3 && s < segs.length; s++) {
        const seg = fingers[f].segments[s]
        if (!seg) continue
        const target = segs[s] || 0
        seg.pivot.rotation.x += (target - seg.pivot.rotation.x) * Math.min(t * 1.5, 1.0)
      }
    }
  }

  function applyOscillation(signObj, time) {
    if (!signObj || !signObj.osc) return
    const { j, ax, amp, freq } = signObj.osc
    const val = Math.sin(time * freq * Math.PI * 2) * amp

    if (j === 'R_wr' && avatarBones.R) {
      avatarBones.R.wrist.rotation[ax] = val
    } else if (j === 'L_wr' && avatarBones.L) {
      avatarBones.L.wrist.rotation[ax] = val
    } else if (j === 'R_sh' && avatarBones.R) {
      avatarBones.R.shoulder.rotation[ax] += val * 0.04
    } else if (j === 'R_el' && avatarBones.R) {
      avatarBones.R.elbow.rotation[ax] += val * 0.04
    } else if (j === 'both_sh') {
      if (avatarBones.R) avatarBones.R.shoulder.rotation[ax] += val * 0.04
      if (avatarBones.L) avatarBones.L.shoulder.rotation[ax] += val * 0.04
    } else if (j === 'both_el') {
      if (avatarBones.R) avatarBones.R.elbow.rotation[ax] += val * 0.04
      if (avatarBones.L) avatarBones.L.elbow.rotation[ax] += val * 0.04
    } else if (j === 'both_wr') {
      if (avatarBones.R) avatarBones.R.wrist.rotation[ax] = val
      if (avatarBones.L) avatarBones.L.wrist.rotation[ax] = val
    }
  }

  // ── SIGN QUEUE ────────────────────────────────────────────
  function resolveSign(item) {
    if (!item) return null
    if (typeof item === 'object') return item
    // string name — look up in library
    const lib = window.AMANDLA_SIGNS
    if (lib && lib.SIGN_LIBRARY && lib.SIGN_LIBRARY[item]) {
      return lib.SIGN_LIBRARY[item]
    }
    // single letter fingerspell — return minimal sign with fingerspell flag
    if (item.length === 1) {
      const alpha = lib && lib.SIGN_LIBRARY && lib.SIGN_LIBRARY[item.toUpperCase()]
      return alpha || { name: item.toUpperCase(), isFingerspell: true, desc: 'Letter ' + item.toUpperCase(), R: null, L: null, osc: null }
    }
    return { name: item, isFingerspell: false, desc: item, R: null, L: null, osc: null }
  }

  function queueSign(signObj) {
    signQueue.push(resolveSign(signObj))
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
    const s = resolveSign(signNameOrObj)
    if (s) {
      signQueue.push(s)
      updateLabel(s.name)
    }
  }

  function updateLabel(text) {
    const el = document.getElementById('avatar-sign-label')
    if (el) el.textContent = text || ''
  }

  // ── ANIMATION LOOP ────────────────────────────────────────
  function animate() {
    animFrameId = requestAnimationFrame(animate)
    if (document.hidden) return
    if (!renderer) return

    const now = performance.now()
    const dt = Math.min((now - lastFrameTime) / 1000, 0.05)
    lastFrameTime = now
    oscTime += dt

    // Determine duration based on fingerspell flag
    const duration = currentSign && currentSign.isFingerspell ? 0.28 : SIGN_DURATION
    const gap      = currentSign && currentSign.isFingerspell ? 0.08 : SIGN_GAP

    if (isInGap) {
      gapTimer -= dt
      if (gapTimer <= 0) {
        isInGap = false
        if (signQueue.length > 0) {
          currentSign = signQueue.shift()
          signProgress = 0
          updateLabel(currentSign ? currentSign.name : '')
        } else {
          currentSign = null
          applyIdlePose()
          updateLabel('')
        }
      }
    } else if (currentSign) {
      signProgress += dt / duration
      try {
        if (signProgress >= 1.0) {
          signProgress = 1.0
          applySignPose(currentSign, 1.0)
          isInGap = true
          gapTimer = gap
        } else {
          applySignPose(currentSign, easeInOut(signProgress))
          applyOscillation(currentSign, oscTime)
        }
      } catch (e) {
        console.warn('[Avatar] Sign error, skipping:', currentSign && currentSign.name, e.message)
        currentSign = null
        isInGap = false
      }
    } else if (signQueue.length > 0) {
      currentSign = signQueue.shift()
      signProgress = 0
      updateLabel(currentSign ? currentSign.name : '')
    }

    // Gentle idle sway when not signing
    if (!currentSign && !isInGap && avatarBones.R) {
      const sway = Math.sin(oscTime * 0.4) * 0.015
      avatarBones.R.shoulder.rotation.z = -0.22 + sway
      avatarBones.L.shoulder.rotation.z =  0.22 - sway
    }

    renderer.render(scene, camera)
  }

  function easeInOut(t) {
    return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t
  }

  function destroyAvatar() {
    if (animFrameId) cancelAnimationFrame(animFrameId)
    if (renderer) renderer.dispose()
    initialized = false
  }

  // ── PUBLIC API ────────────────────────────────────────────
  const AmandlaAvatar = {
    initAvatar:     initAvatar,
    queueSign:      queueSign,
    queueSentence:  queueSentence,
    playSignNow:    playSignNow,
    destroyAvatar:  destroyAvatar
  }

  window.AmandlaAvatar = AmandlaAvatar

  // Backward-compatible aliases used by existing deaf/index.html
  window.avatarInit = function () { initAvatar('avatar-canvas') }
  window.avatarPlaySigns = function (signs, text) {
    if (!initialized) initAvatar('avatar-canvas')
    if (Array.isArray(signs)) signs.forEach(function (s) { queueSign(s) })
    updateLabel(text || (signs && signs[0]) || '')
  }

})();