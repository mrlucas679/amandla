// Lightweight avatar placeholder for AMANDLA
// Exposes: window.avatarInit(), window.avatarPlaySigns(signs, text)

(function(){
  const display = document.getElementById('display')
  let queue = []
  let playing = false

  function resolveSignObject(item) {
    // item may be a string sign name, a single-letter for fingerspelling, or a full sign object
    if (!item) return null
    if (typeof item === 'string') {
      // If the full sign library is available, map name -> sign object
      if (window.AMANDLA_SIGNS && window.AMANDLA_SIGNS.SIGN_LIBRARY && window.AMANDLA_SIGNS.SIGN_LIBRARY[item]) {
        return window.AMANDLA_SIGNS.SIGN_LIBRARY[item]
      }
      // single-letter fingerspell fallback: return minimal object
      return { name: item, shape: 'fingerspell', desc: 'Letter ' + item }
    }
    // already an object
    return item
  }

  async function playNext() {
    if (playing) return
    if (!queue.length) return
    playing = true
    const sign = queue.shift()
    const s = resolveSignObject(sign)
    if (!s) {
      playing = false
      setTimeout(playNext, 50)
      return
    }

    // Display sign name and description in the display box
    try {
      display.textContent = s.name + (s.desc ? ' — ' + s.desc : '')
    } catch (e) {
      display.textContent = s.name
    }

    // Simple timing: show each sign for 600ms, gap 120ms
    await new Promise(r => setTimeout(r, 600))
    display.textContent = ''
    await new Promise(r => setTimeout(r, 120))

    playing = false
    // continue
    setTimeout(playNext, 0)
  }

  function avatarInit() {
    queue = []
    playing = false
    if (display) display.textContent = 'Avatar ready'
    console.log('[Avatar] initialized')
  }

  function avatarPlaySigns(signs, text) {
    // signs may be array of names or objects
    if (!Array.isArray(signs)) return
    for (const s of signs) queue.push(s)
    // if provided, show original text briefly
    if (text && display) {
      display.textContent = text
      setTimeout(() => { if (!playing) display.textContent = '' }, 600)
    }
    playNext()
  }

  window.avatarInit = avatarInit
  window.avatarPlaySigns = avatarPlaySigns
})();

