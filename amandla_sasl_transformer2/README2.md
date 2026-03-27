# SASL Transformer — English → South African Sign Language

**For the Amandla desktop app** — converts English sentences from Whisper STT
into South African Sign Language (SASL) gloss notation.

## What this does

Instead of signing word-by-word in English order, this module:

1. Takes the English sentence from Whisper
2. Restructures it into **SASL grammar** (SOV word order, time-first, no articles, base-form verbs)
3. Returns the **SASL gloss text** for display (so the deaf user can read it)
4. Returns **ordered tokens** for the avatar animation queue
5. Flags which words need **fingerspelling** vs full signs

### Example

```
English input:  "I went to the store yesterday to buy some milk"
SASL gloss out: "YESTERDAY STORE MILK BUY I GO FINISH"
```

The deaf user sees "YESTERDAY STORE MILK BUY I GO FINISH" on screen — this
is how SASL structures the sentence, and it's what makes sense to them.

---

## Setup

### 1. Install dependencies

```bash
cd backend/
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 3. Copy the module into your backend

Copy the `sasl_transformer/` folder into your Amandla `backend/` directory:

```
backend/
├── sasl_transformer/        ← this module
│   ├── __init__.py
│   ├── config.py
│   ├── grammar_rules.py
│   ├── models.py
│   ├── routes.py
│   ├── sign_library.py
│   ├── transformer.py
│   └── websocket_handler.py
├── data/
│   └── sign_library.json    ← your sign library
├── .env                     ← your environment variables
├── requirements.txt
└── main.py                  ← your existing FastAPI app
```

---

## Integration

### Option A: REST API (simplest)

Add the SASL routes to your existing FastAPI app:

```python
# In your main.py or app.py
from fastapi import FastAPI
from sasl_transformer.routes import router as sasl_router

app = FastAPI()

# ... your existing routes ...

# Add SASL translation endpoints
app.include_router(sasl_router, prefix="/api/sasl")
```

Now your frontend can call:

```javascript
// After Whisper gives you the English text:
const response = await fetch('/api/sasl/translate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    english_text: whisperResult.text,
    include_non_manual: true
  })
});

const saslData = await response.json();

// 1. Display the SASL gloss text on screen
subtitleElement.textContent = saslData.gloss_text;
// Shows: "YESTERDAY STORE MILK BUY I GO FINISH"

// 2. Feed tokens to the avatar animation queue
for (const token of saslData.tokens) {
  if (token.in_library) {
    avatar.playSignAnimation(token.gloss);
  } else if (token.sign_type === 'fingerspell') {
    avatar.fingerspell(token.gloss);
  } else if (token.sign_type === 'number') {
    avatar.signNumber(token.gloss);
  }
}

// 3. Apply non-manual markers to the avatar
for (const marker of saslData.non_manual_markers) {
  avatar.applyNonManualMarker(marker);
}
```

### Option B: WebSocket (real-time, recommended)

Integrate with your existing WebSocket setup:

```python
# In your WebSocket handler
from fastapi import WebSocket
from sasl_transformer.websocket_handler import SASLWebSocketHandler

sasl_handler = SASLWebSocketHandler()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async for message in websocket.iter_text():
        # Try SASL translation handler first
        if await sasl_handler.handle_message(websocket, message):
            continue

        # Otherwise, pass to your existing handlers
        data = json.loads(message)
        if data["type"] == "audio":
            await handle_audio(websocket, data)
        elif data["type"] == "avatar_command":
            await handle_avatar(websocket, data)
```

Frontend WebSocket usage:

```javascript
// Send translation request via WebSocket
ws.send(JSON.stringify({
  type: 'translate',
  english_text: whisperResult.text,
  include_non_manual: true,
  context: previousSentence  // optional, for better context
}));

// Receive translation
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'sasl_translation') {
    // Display SASL gloss text
    subtitleElement.textContent = data.gloss_text;

    // Feed tokens to avatar
    data.tokens.forEach(token => {
      avatarQueue.push(token);
    });
  }
};
```

---

## SASL Grammar Rules Applied

| Rule | English | SASL Gloss |
|------|---------|-----------|
| SOV word order | "I like dogs" | DOG I LIKE |
| Time markers first | "I went yesterday" | YESTERDAY I GO FINISH |
| Drop articles | "The big cat" | CAT BIG |
| Drop auxiliary verbs | "She is happy" | SHE HAPPY |
| Base form verbs | "He was running" | HE RUN |
| Adjectives after nouns | "The red car" | CAR RED |
| Questions at end | "Where do you live?" | YOU LIVE WHERE |
| Negation after concept | "I don't understand" | I UNDERSTAND NOT |
| FINISH = past tense | "I already ate" | FOOD I EAT FINISH |
| WILL = future | "I will go" | I GO WILL |

---

## Sign Library

The sign library (`data/sign_library.json`) maps SASL gloss words to your
avatar's animation IDs. The starter library includes ~90 common signs.

### Adding new signs

When you create a new sign animation for the avatar, add it to the library:

```json
{
  "STORE": {
    "animation_id": "sign_store",
    "category": "places",
    "variants": ["SHOP"]
  }
}
```

Or add at runtime via the API:

```python
transformer.sign_library.add_sign(
    "STORE", "sign_store", "places", ["SHOP"]
)
```

### What happens with unknown words

If a word in the SASL gloss is NOT in your sign library:
- The token's `sign_type` is set to `"fingerspell"`
- The token's `in_library` is set to `false`
- The word appears in the `unknown_words` list
- Your avatar fingerspells it letter by letter

As you add more signs to the library, fewer words get fingerspelled.

---

## API Reference

### POST `/api/sasl/translate`

Translate English to SASL gloss.

**Request:**
```json
{
  "english_text": "I went to the store yesterday to buy milk",
  "include_non_manual": true,
  "context": ""
}
```

**Response:**
```json
{
  "original_english": "I went to the store yesterday to buy milk",
  "gloss_text": "YESTERDAY STORE MILK BUY I GO FINISH",
  "tokens": [
    {
      "gloss": "YESTERDAY",
      "original_english": "yesterday",
      "sign_type": "sign",
      "in_library": true,
      "position": 0,
      "notes": ""
    },
    {
      "gloss": "STORE",
      "original_english": "store",
      "sign_type": "fingerspell",
      "in_library": false,
      "position": 1,
      "notes": ""
    }
  ],
  "non_manual_markers": [],
  "unknown_words": ["STORE"],
  "translation_notes": "Time marker moved to front. Articles dropped."
}
```

### GET `/api/sasl/health`

Health check — returns service status.

### GET `/api/sasl/library/stats`

Returns sign library statistics.

### POST `/api/sasl/cache/clear`

Clears the translation cache.

---

## Testing

```bash
# Run all tests (no API key needed for these)
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=sasl_transformer -v
```

---

## Architecture

```
Whisper STT → English text
                  ↓
         SASL Transformer (Claude API)
                  ↓
            SASL Gloss Output
              ↓           ↓
    Avatar Animation    SASL Text Display
    (signs in SASL      (deaf user reads
     word order)         SASL grammar)
```

The Claude API handles the complex grammar transformation. A rule-based
fallback activates automatically if the API is temporarily unavailable
(less accurate but keeps the app working).

---

## Files

| File | Purpose |
|------|---------|
| `config.py` | Environment variable configuration |
| `grammar_rules.py` | SASL grammar rules + Claude system prompt |
| `models.py` | Pydantic data models (request/response) |
| `transformer.py` | Core translation engine (Claude API + fallback) |
| `sign_library.py` | Sign library manager |
| `routes.py` | FastAPI REST endpoints |
| `websocket_handler.py` | WebSocket real-time handler |
