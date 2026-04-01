---
name: performance-optimization
description: >
  Identifies and fixes performance bottlenecks in Python backends, JavaScript frontends, Three.js/WebGL
  avatar rendering, WebSocket communication, and Electron apps. Activate when the user says "it's slow",
  "the avatar lags", "the app is freezing", "high CPU usage", "memory leak", "optimize this", "performance issue",
  "it takes too long", "the animation stutters", or when profiling reveals bottlenecks.
  Never optimize without first measuring — premature optimization wastes time on the wrong things.
---

# Performance Optimization Skill

**Rule #1: Measure first, optimize second. Never guess at bottlenecks.**

Optimizing the wrong thing is worse than not optimizing at all — it adds complexity without benefit.
Profile, find the actual bottleneck, fix it, measure again.

---

## The Optimization Process

```
1. MEASURE  → Profile the code, find the actual slow part
2. ANALYZE  → Understand WHY it's slow
3. FIX      → Apply the minimum change that solves the root cause
4. MEASURE  → Verify the improvement is real
5. CHECK    → Did the fix break anything? Did it introduce new issues?
```

---

## Part 1 — Python Backend Profiling

### Finding Slow Code
```python
# Add timing to suspicious functions
import time
import logging

logger = logging.getLogger(__name__)

async def translate_text(text: str) -> list[str]:
    """Translates text to SASL signs."""
    start_time = time.perf_counter()
    
    result = await _run_sasl_pipeline(text)
    
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    if elapsed_ms > 100:  # Flag anything over 100ms
        logger.warning(f"Slow translation: {elapsed_ms:.1f}ms for {len(text)} chars")
    
    return result
```

**In Claude Code (terminal) — profile Python:**
```bash
# Profile the full backend startup and a test request
python -m cProfile -o profile.stats backend/main.py &
# Make a test request
curl -X POST http://localhost:8000/speech -d '{"text": "hello"}'
# Analyze results
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

### Common Python Performance Issues

| Problem | Symptom | Fix |
|---------|---------|-----|
| Blocking I/O in async | All requests freeze when one is slow | Use `run_in_executor()` for blocking calls |
| Repeated Ollama calls | Same phrase translated multiple times | Add an LRU cache |
| Large Whisper model | Slow transcription startup | Use `WHISPER_MODEL=small` for dev |
| N+1 loop problem | Loop making one HTTP call per item | Batch the calls outside the loop |

### Add LRU Cache for Repeated Translations
```python
from functools import lru_cache

# Cache the 500 most recent translations — deaf/emergency phrases repeat often
@lru_cache(maxsize=500)
def get_signs_for_phrase(text: str) -> tuple[str, ...]:
    """
    Returns cached SASL signs for a phrase.
    Uses tuple (not list) because lru_cache requires hashable arguments.
    """
    signs = _run_sasl_pipeline(text)
    return tuple(signs)
```

---

## Part 2 — Three.js / Avatar Performance

### Target Frame Rate
The avatar should render at 30+ FPS. Below 20 FPS feels choppy.

### Check FPS in Real Time
```javascript
// Add FPS counter during development (remove before production)
const stats = new Stats();  // npm install stats.js
document.body.appendChild(stats.dom);

function animate() {
    stats.begin();
    // ... your render code
    stats.end();
    requestAnimationFrame(animate);
}
```

### Common Three.js Performance Issues

| Problem | Fix |
|---------|-----|
| Creating new objects every frame | Create once, reuse (Object pooling) |
| Too many draw calls | Merge geometries that don't move |
| High-poly model causing GPU stress | Use Level of Detail (LOD) or simplify model |
| Shadows enabled unnecessarily | `renderer.shadowMap.enabled = false` unless needed |
| Texture too large | Compress textures to WebP, max 1024x1024 for avatar |
| Animation mixer running when not needed | Pause mixer when avatar is hidden |

### Don't Create New Objects in the Animation Loop
```javascript
// ❌ Bad — allocates new Vector3 every frame (60fps = 3600 allocations/minute)
function animate() {
    const position = new THREE.Vector3(0, 1, 0);  // ← New object every frame!
    avatar.position.copy(position);
    requestAnimationFrame(animate);
}

// ✅ Good — create once, reuse
const STANDING_POSITION = new THREE.Vector3(0, 1, 0);

function animate() {
    avatar.position.copy(STANDING_POSITION);
    requestAnimationFrame(animate);
}
```

---

## Part 3 — WebSocket Performance

### Don't Send Large Payloads Unnecessarily
```python
# ❌ Sending the full sign object when only the name is needed
await websocket.send_json({
    "type": "signs",
    "signs": [
        {"name": "HELLO", "keyframes": [...100 keyframes...], "metadata": {...}}
    ]
})

# ✅ Send only what the receiver needs — frontend already has the full sign data
await websocket.send_json({
    "type": "signs",
    "signs": ["HELLO", "WORLD"],  # Just the names — frontend looks up the rest
    "original_text": "Hello world"
})
```

### Debounce Rapid User Input
```javascript
// ❌ Sends a message to backend on every keystroke
input.addEventListener('input', (e) => {
    window.amandla.send({ type: 'text', text: e.target.value });
});

// ✅ Wait until user pauses typing (500ms) before sending
let debounceTimer;
input.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        window.amandla.send({ type: 'text', text: e.target.value });
    }, 500);
});
```

---

## Part 4 — Electron / Memory Management

### Detect Memory Leaks
```javascript
// In main.js — log memory usage periodically during development
setInterval(() => {
    const usage = process.memoryUsage();
    console.log(`Memory: RSS=${Math.round(usage.rss/1024/1024)}MB, Heap=${Math.round(usage.heapUsed/1024/1024)}MB`);
}, 30000);  // Log every 30 seconds
```

### Common Memory Leak Patterns
```javascript
// ❌ Event listener added but never removed → memory leak
window.amandla.onMessage((msg) => { ... });

// ✅ Remove listener when the page is unloaded
window.amandla.onMessage((msg) => { ... });
window.addEventListener('unload', () => {
    window.amandla.offMessage();
});

// ❌ Three.js resources not disposed → GPU memory leak
scene.remove(oldAvatar);  // Removes from scene but doesn't free GPU memory

// ✅ Dispose Three.js resources properly
function removeAvatar(avatar) {
    avatar.traverse((child) => {
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
            if (Array.isArray(child.material)) {
                child.material.forEach(m => m.dispose());
            } else {
                child.material.dispose();
            }
        }
    });
    scene.remove(avatar);
}
```

---

## Part 5 — Performance Budget

Set targets before optimizing — so you know when you're done:

| Metric | Target for Amandla |
|--------|-------------------|
| App startup time | < 3 seconds to first interactive |
| Text → first sign displayed | < 500ms |
| Avatar FPS | 30+ FPS consistently |
| WebSocket round-trip | < 200ms |
| Memory usage | < 500MB after 1 hour of use |
| Audio transcription | < 3 seconds for 10-second clip |

---

## Environment Notes

**In Claude Code (terminal):**
```bash
# Python — find the slowest endpoints
pip install py-spy --break-system-packages
py-spy top --pid $(pgrep -f uvicorn)

# JavaScript — check for memory leaks
# Open Chrome DevTools → Memory tab → Take heap snapshots
```

**In Claude.ai (browser):** Ask the user what feels slow and get specifics.
"How slow?" and "what exactly happens?" before suggesting any fix.
Profile first — always.
