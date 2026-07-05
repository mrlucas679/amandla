# AMANDLA — Precise Rebuild Plan (Based on Full Codebase Audit)

---

## WHAT TO KEEP (Already Good)

These components are production-grade and should NOT be rewritten:


| Component              | File(s)                                  | Why it's solid                                        |
| ---------------------- | ---------------------------------------- | ----------------------------------------------------- |
| WebSocket architecture | `handler.py`, `helpers.py`, `preload.js` | Clean dispatch, auth, reconnect, promise system       |
| Debounce system        | `sign_reconstruction.py`                 | 1.5s debounce + flush works correctly                 |
| Rate limiting & auth   | `shared.py`, `middleware.py`             | Per-IP, per-session, constant-time token compare      |
| Session management     | `session.py`, `shared.py`                | Reaper, cleanup, concurrent session cap               |
| History DB             | `history_db.py`                          | WAL mode, async, auto-migration, 90-day retention     |
| Whisper STT            | `whisper_service.py`                     | ffmpeg conversion, lazy loading, executor-based async |
| Electron shell         | `main.js`                                | CSP, IPC, dual windows, auto-updater                  |
| Preload bridge         | `preload.js`                             | Clean contextBridge, promise registry, reconnect      |
| Rights system          | `claude_service.py`                      | SA legal framework, template fallback                 |
| Quick-sign UI          | `deaf.js` categories                     | 5 categories, 35 signs, validation against library    |
| Assist mode            | `mode_controller.js`                     | 44-phrase AAC, fuzzy search, speech recognition       |
| Ollama pool            | `ollama_pool.py`                         | Shared httpx client, proper lifecycle                 |
| Design system          | `design-system.css`, `animations.css`    | Consistent theming                                    |

---

## WHAT'S ACTUALLY BROKEN (Root Causes)

### Problem 1: Translation adds/removes wrong words

**Root cause:** The LLM tier (Tier 1) runs BEFORE phrase detection. Your `PHRASE_MAP` has `"how are you" → ["HOW ARE YOU"]` but `sasl_pipeline.py` calls `SASLTransformer.translate()` (Ollama) first. Ollama doesn't know about PHRASE_MAP, so it decomposes "how are you" into individual words and applies rules incorrectly.

**The fix is NOT a new model.** The fix is reordering the pipeline:

```
CURRENT (broken):
  Input → Ollama LLM (hallucinates) → rule-based fallback → raw word map

FIXED:
  Input → Phrase detection (PHRASE_MAP) → Remaining words → Rule-based transform → Ollama only for ambiguous cases
```

### Problem 2: Animation is unrecognizable

**Root cause:** The 100+ signs in `signs_library.js` are hand-authored Euler angles that were never validated by a SASL signer. The TransitionEngine (SLERP, coarticulation, joint limits) is actually well-built — the problem is the INPUT DATA, not the engine.

**The fix is NOT a new avatar library.** The fix is:

1. Get correct pose data from real SASL reference (video → extract → validate)
2. Add multi-frame motion sequences for signs that involve movement
3. Have a Deaf SASL user validate each sign

---

## PHASE 1: FIX TRANSLATION (Weeks 1-2)

### Task 1.1: Reorder the pipeline in `sasl_pipeline.py`

**File:** `backend/services/sasl_pipeline.py`

Change `text_to_sasl_signs()` to:

```python
async def text_to_sasl_signs(text: str, language: str = None) -> dict:
    text = sanitise_text(text)
    if not text:
        return _EMPTY_RESULT

    # Step 0: Pre-translate non-English
    if language and language.lower() not in {"en", "english"}:
        text = await _translate_to_english(text, language)

    # Step 1: Normalize informal English BEFORE any translation
    text = _normalize_informal(text)

    # Step 2: Extract known phrases FIRST (deterministic, no hallucination)
    signs, remaining_text = _extract_phrases(text)

    # Step 3: If everything matched phrases, we're done
    if not remaining_text.strip():
        gloss = " ".join(signs)
        return {"signs": signs, "text": gloss, "original_english": text, ...}

    # Step 4: For remaining text, try rule-based BEFORE LLM
    try:
        rule_result = _sasl_transformer.translate_with_rules(
            TranslationRequest(english_text=remaining_text)
        )
        remaining_signs = [t.gloss for t in rule_result.tokens]
    except Exception:
        remaining_signs = sentence_to_sign_names(remaining_text)

    # Step 5: Merge phrase signs + remaining signs in correct order
    all_signs = _merge_ordered(text, signs, remaining_signs)

    # Step 6: Only use LLM for complex/ambiguous sentences (>8 words remaining)
    # This is optional — the rule-based system handles most cases
    ...
```

### Task 1.2: Add `_normalize_informal()` function

**File:** `backend/services/sasl_pipeline.py` (new function)

```python
_CONTRACTIONS = {
    "i'm": "i am", "i'll": "i will", "i've": "i have", "i'd": "i would",
    "you're": "you are", "you'll": "you will", "you've": "you have",
    "he's": "he is", "she's": "she is", "it's": "it is",
    "we're": "we are", "we'll": "we will", "we've": "we have",
    "they're": "they are", "they'll": "they will", "they've": "they have",
    "don't": "do not", "doesn't": "does not", "didn't": "did not",
    "won't": "will not", "wouldn't": "would not", "couldn't": "could not",
    "shouldn't": "should not", "can't": "cannot", "isn't": "is not",
    "aren't": "are not", "wasn't": "was not", "weren't": "were not",
    "haven't": "have not", "hasn't": "has not", "hadn't": "had not",
    "gonna": "going to", "wanna": "want to", "gotta": "got to",
    "howzit": "hello how are you", "eish": "", "yoh": "",
    "lekker": "good", "sharp": "okay", "ja": "yes", "nee": "no",
}

def _normalize_informal(text: str) -> str:
    words = text.lower().split()
    result = []
    for w in words:
        result.append(_CONTRACTIONS.get(w, w))
    return " ".join(result)
```

### Task 1.3: Add `_extract_phrases()` that runs BEFORE any LLM

**File:** `backend/services/sasl_pipeline.py` (new function)

```python
def _extract_phrases(text: str) -> tuple[list[str], str]:
    """Extract known phrases from text, return (signs_found, remaining_text)."""
    from backend.services.sign_maps import PHRASE_MAP
    text_lower = text.lower()
    signs = []
    remaining = text_lower

    # Sort phrases by length (longest first) for greedy matching
    sorted_phrases = sorted(PHRASE_MAP.keys(), key=len, reverse=True)

    for phrase in sorted_phrases:
        if phrase in remaining:
            signs.extend(PHRASE_MAP[phrase])
            remaining = remaining.replace(phrase, " ", 1).strip()

    return signs, remaining
```

### Task 1.4: Expand PHRASE_MAP in `sign_maps.py`

**File:** `backend/services/sign_maps.py`

Your PHRASE_MAP has only 17 entries. The most common multi-word expressions that break translation need to be added:

```python
PHRASE_MAP = {
    # Existing 17 entries...

    # Common greetings/social
    "how are you doing": ["HOW ARE YOU"],
    "how is it going": ["HOW ARE YOU"],
    "nice to meet you": ["NICE MEET YOU"],
    "see you later": ["SEE LATER"],
    "good morning": ["GOOD MORNING"],
    "good afternoon": ["GOOD AFTERNOON"],
    "good evening": ["GOOD EVENING"],
    "good night": ["GOOD NIGHT"],

    # Common needs
    "i need help": ["I", "HELP", "WANT"],
    "i don't understand": ["I", "UNDERSTAND", "NOT"],
    "i don't know": ["I", "KNOW", "NOT"],
    "can you help me": ["YOU", "CAN", "HELP"],
    "i am sorry": ["SORRY"],
    "excuse me": ["SORRY"],
    "i want to go": ["I", "GO", "WANT"],
    "i am sick": ["I", "SICK"],
    "i am hungry": ["I", "HUNGRY"],
    "i am thirsty": ["I", "THIRSTY"],

    # Medical
    "i am in pain": ["I", "PAIN"],
    "call an ambulance": ["AMBULANCE", "CALL"],
    "i need a doctor": ["DOCTOR", "I", "WANT"],
    "i need medicine": ["MEDICINE", "I", "WANT"],

    # SA slang
    "how's it": ["HOW ARE YOU"],
    "is it": ["YES"],  # SA "is it?" = "really?"
    "just now": ["WAIT"],
    "now now": ["SOON"],
    "no ways": ["NO"],
}
```

### Task 1.5: Fix rule-based transformer order in `grammar_rules.py`

**File:** `sasl_transformer/transformer.py` → `_translate_with_rules()`

The current rule-based path has a bug: it applies aspect markers (FINISH/WILL) even to phrases like "how are you doing" because "doing" looks like a present progressive verb. Fix:

```python
def _translate_with_rules(self, request):
    text = request.english_text.lower()

    # Skip grammar transforms for known complete phrases
    from backend.services.sign_maps import PHRASE_MAP
    if text.strip() in PHRASE_MAP:
        signs = PHRASE_MAP[text.strip()]
        return TranslationResponse(
            tokens=[GlossToken(gloss=s) for s in signs],
            gloss_text=" ".join(signs)
        )

    # Continue with existing rule-based logic for non-phrase text...
```

---

## PHASE 2: FIX ANIMATION DATA (Weeks 2-5)

### The TransitionEngine is fine. The sign data is wrong.

Your `signs_library.js` has good infrastructure:

- 17+ handshape presets (HS_FIST, HS_OPEN, HS_INDEX_POINT, etc.)
- 10+ arm position presets (ARM_NEUTRAL, ARM_CHEST, etc.)
- SLERP with cubic easing and 70% coarticulation
- Oscillation system for repetitive motions
- Joint limits clamping
- DIP-PIP tendon coupling at 0.67×

**What needs to change:** The actual Euler angle values in each sign definition.

### Task 2.1: Create a validation tool

Build a simple HTML page that:

1. Loads the VRM/GLB avatar
2. Plays each sign one at a time
3. Shows a reference video of the correct SASL sign alongside
4. Has thumbs up/down buttons
5. Exports a report of which signs are wrong

**File:** `tools/sign_validator.html` (standalone, not part of the app)

### Task 2.2: Get SASL reference material

You need reference videos or images for each of the 100+ signs. Sources:


| Source                    | URL                 | What it has                    |
| ------------------------- | ------------------- | ------------------------------ |
| SASL Dictionary (Deaf SA) | deafsa.co.za        | Official SASL signs with video |
| SignGenius SASL           | saslconnect.co.za   | SASL dictionary app            |
| SASL Connect              | saslconnect.co.za   | Educational SASL videos        |
| YouTube SASL channels     | search "SASL signs" | Community videos               |

### Task 2.3: Correct sign data systematically

For each sign flagged as wrong in Task 2.1:

1. Watch the reference video
2. Pause at the key poses (start, peak, end)
3. Estimate the Euler angles for shoulder, elbow, wrist
4. Identify the correct handshape preset (or create a new one)
5. Update the sign in `signs_library.js`
6. Test in the validator tool
7. Mark as verified

**Priority order:** Fix the 35 quick-sign button signs first (MEDICAL + GREETINGS + EMOTIONS + ACTIONS + RIGHTS), then expand.

### Task 2.4: Add motion sequences for movement signs

Many SASL signs involve movement that can't be captured by start→end poses. For these, add a `path` array:

```javascript
// Current (broken for movement signs):
sign("GO", { R: { startPose: ARM_FORWARD, endPose: ARM_FORWARD_FAR } })

// Better (multi-keyframe):
sign("GO", {
  R: {
    keyframes: [
      { t: 0.0, arm: ARM_CHEST, hand: HS_INDEX_POINT },
      { t: 0.3, arm: ARM_FORWARD, hand: HS_INDEX_POINT },
      { t: 0.7, arm: ARM_FORWARD_FAR, hand: HS_INDEX_POINT },
      { t: 1.0, arm: ARM_FORWARD_FAR, hand: HS_INDEX_POINT },
    ]
  }
})
```

This requires a small change to `avatar.js` — instead of `slerpArmPose(startPose, endPose, t)`, do multi-segment interpolation.

### Task 2.5: Add non-manual markers to ALL question and negation signs

Your `setNMMs()` system exists and works (maps to ARKit AUs). But most signs in the library don't specify `nmm`. At minimum:

- All question words (WHO, WHAT, WHERE, WHEN, WHY, HOW): `nmm: ["raised eyebrows", "head tilt forward"]`
- All negation (NOT, NO, NEVER): `nmm: ["head shake", "furrowed brows"]`
- All affirmative (YES, GOOD, THANK YOU): `nmm: ["head nod"]`
- All emotional signs: appropriate face expression

---

## PHASE 3: ADD VECTOR DB FOR TRANSLATION MEMORY (Weeks 5-7)

### Task 3.1: Add ChromaDB

**New file:** `backend/services/translation_memory.py`

```python
import chromadb
from pathlib import Path

_client = None
_collection = None

def init_translation_memory():
    global _client, _collection
    _client = chromadb.PersistentClient(path=str(Path("data/translation_memory")))
    _collection = _client.get_or_create_collection(
        name="sasl_translations",
        metadata={"hnsw:space": "cosine"}
    )
    _seed_from_maps()

def _seed_from_maps():
    """Populate with all existing PHRASE_MAP and WORD_MAP entries."""
    from backend.services.sign_maps import PHRASE_MAP, WORD_MAP
    ids, documents, metadatas = [], [], []

    for phrase, signs in PHRASE_MAP.items():
        id_ = f"phrase_{phrase.replace(' ', '_')}"
        ids.append(id_)
        documents.append(phrase)
        metadatas.append({"sasl_gloss": " ".join(signs), "source": "phrase_map", "verified": True})

    for word, signs in WORD_MAP.items():
        id_ = f"word_{word}"
        ids.append(id_)
        documents.append(word)
        metadatas.append({"sasl_gloss": " ".join(signs), "source": "word_map", "verified": True})

    # Upsert (idempotent)
    _collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

def find_similar(text: str, n: int = 5) -> list[dict]:
    """Find the most similar previously-translated sentences."""
    results = _collection.query(query_texts=[text], n_results=n)
    return [
        {"english": doc, "sasl": meta["sasl_gloss"], "verified": meta.get("verified", False)}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]

def store_translation(english: str, sasl_gloss: str, verified: bool = False):
    """Store a new translation for future retrieval."""
    id_ = f"trans_{hash(english) & 0xFFFFFFFF}"
    _collection.upsert(
        ids=[id_],
        documents=[english],
        metadatas=[{"sasl_gloss": sasl_gloss, "source": "runtime", "verified": verified}]
    )
```

### Task 3.2: Wire into pipeline

**File:** `backend/services/sasl_pipeline.py`

Before calling Ollama (Tier 1), retrieve similar translations:

```python
from backend.services.translation_memory import find_similar

async def text_to_sasl_signs(text, language=None):
    # ... normalize, extract phrases ...

    # Retrieve similar past translations as context
    similar = find_similar(remaining_text, n=5)
    examples = "\n".join(
        f'  "{s["english"]}" → {s["sasl"]}' for s in similar if s["verified"]
    )

    # If calling Ollama, include examples in the prompt
    if examples:
        enhanced_prompt = f"Similar translations:\n{examples}\n\nNow translate: {remaining_text}"
    ...
```

### Task 3.3: Add `chromadb` to requirements.txt

```
chromadb>=0.5.0
```

### Task 3.4: Initialize in FastAPI lifespan

**File:** `backend/main.py`

```python
from backend.services.translation_memory import init_translation_memory

async def _lifespan(app):
    init_db()
    init_translation_memory()  # NEW
    ...
```

---

## PHASE 4: IMPROVE SIGN DATA PIPELINE (Weeks 7-10)

### Task 4.1: Build video-to-pose extraction tool

Record SASL signs on video → extract pose data → convert to `signs_library.js` format.

**New file:** `tools/extract_poses.py`

Uses MediaPipe Holistic (already a dependency via `@mediapipe/hands`) to extract:

- 33 body landmarks (pose)
- 21 hand landmarks per hand
- 468 face landmarks

Convert MediaPipe landmarks → Euler angles for shoulder/elbow/wrist → `signs_library.js` format.

### Task 4.2: Record priority signs

Record the 35 quick-sign button signs + 50 most common signs from WORD_MAP. Store videos in `data/sasl_reference/`.

### Task 4.3: Build motion clip format

For signs with complex motion, store as multi-keyframe clips:

**New file:** `data/motion_clips.json`

```json
{
  "WATER": {
    "fps": 30,
    "frames": 18,
    "keyframes": [
      {"t": 0, "R": {"sh": [0,0,0], "el": [0,-1.2,0], "wr": [0,0,0]}, "hand": "HS_W"},
      {"t": 0.33, "R": {"sh": [0,0,0], "el": [0,-1.0,0], "wr": [0.2,0,0]}, "hand": "HS_W"},
      {"t": 0.66, "R": {"sh": [0,0,0], "el": [0,-1.2,0], "wr": [-0.2,0,0]}, "hand": "HS_W"},
      {"t": 1.0, "R": {"sh": [0,0,0], "el": [0,-1.0,0], "wr": [0,0,0]}, "hand": "HS_W"}
    ]
  }
}
```

### Task 4.4: Update `avatar.js` to support keyframe clips

Add a `_playKeyframeSign()` method alongside the existing `_playStaticSign()`:

```javascript
async _playKeyframeSign(signData, duration) {
    const keyframes = signData.keyframes;
    const startTime = performance.now();
    const totalMs = duration * 1000;

    return new Promise(resolve => {
        const animate = () => {
            const elapsed = performance.now() - startTime;
            const t = Math.min(elapsed / totalMs, 1.0);

            // Find surrounding keyframes
            let k0 = 0, k1 = 1;
            for (let i = 0; i < keyframes.length - 1; i++) {
                if (t >= keyframes[i].t && t <= keyframes[i+1].t) {
                    k0 = i; k1 = i + 1; break;
                }
            }

            // Local t between the two keyframes
            const localT = (t - keyframes[k0].t) / (keyframes[k1].t - keyframes[k0].t);
            const easedT = localT * localT * (3 - 2 * localT); // cubic ease

            // Interpolate arm + hand between k0 and k1
            this._applyInterpolatedPose(keyframes[k0], keyframes[k1], easedT);

            if (t < 1.0) requestAnimationFrame(animate);
            else resolve();
        };
        requestAnimationFrame(animate);
    });
}
```

---

## PHASE 5: TYPESCRIPT MIGRATION (Weeks 10-12)

### What to migrate first (highest value):

1. `signs_library.js` → `signs_library.ts` — type-safe sign definitions, catch missing fields
2. `avatar.js` → `avatar.ts` — type-safe bone references, keyframe data
3. `deaf.js` → `deaf.ts` — type-safe WebSocket messages
4. `mode_controller.js` → `mode_controller.ts`

### What to keep as JS (lower value):

- `hearing.js` — simple DOM manipulation, types won't help much
- `preload.js` — Electron constraints make TS harder here

### Setup:

```bash
npm install -D typescript @types/three
```

Add `tsconfig.json` targeting ES2020, moduleResolution: bundler, strict: true.

Use `esbuild` (fast, zero-config) to compile `.ts` → `.js` for Electron.

---

## SUMMARY: What Changes vs What Stays


| Area                   | Current State                                                            | Action                                            | Effort    |
| ---------------------- | ------------------------------------------------------------------------ | ------------------------------------------------- | --------- |
| Pipeline order         | LLM first, phrases last                                                  | **Reverse it** — phrases first, LLM last         | 1 day     |
| Informal English       | No normalization                                                         | **Add contractions + SA slang map**               | 1 day     |
| PHRASE_MAP             | 17 entries                                                               | **Expand to 60+**                                 | 2 days    |
| Rule-based transformer | Applied after LLM fails                                                  | **Make it the primary path**                      | 1 day     |
| Ollama role            | Primary trans<br /><br /><br /><br /><br /><br /><br /><br /><br />lator | **Demote to ambiguous-sentence-only**             | 1 day     |
| Translation memory     | None                                                                     | **Add ChromaDB**                                  | 3 days    |
| Sign pose data         | Hand-authored, unverified                                                | **Validate + correct with SASL reference**        | 2-3 weeks |
| Multi-frame motion     | Only start/end + oscillation                                             | **Add keyframe clips for movement signs**         | 1 week    |
| Non-manual markers     | System exists, few signs use it                                          | **Add NMMs to all question/negation signs**       | 2 days    |
| Avatar library         | TalkingHead v3 + custom engine                                           | **Keep** (it works, data is the problem)          | 0         |
| VRM migration          | Not needed yet                                                           | **Defer** — fix data first, evaluate later       | 0         |
| WebSocket/backend      | Solid                                                                    | **Keep as-is**                                    | 0         |
| TypeScript             | Plain JS                                                                 | **Gradual migration** starting with signs_library | 1 week    |
| Dedicated NMT model    | None                                                                     | **Defer to Phase 5+** — fix pipeline order first | Future    |
| Video→pose pipeline   | None                                                                     | **Build extraction tool**                         | 1 week    |

### Total estimated effort: 6-8 weeks to transform the app

The critical insight: **you don't need to strip the project down.** The architecture is sound. The two problems are (1) pipeline ordering (fixable in 2 days) and (2) sign pose accuracy (fixable in 2-3 weeks with reference validation). Everything else is enhancement.
