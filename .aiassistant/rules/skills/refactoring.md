---
name: refactoring
description: >
  Guides safe, incremental code refactoring: improving code structure without changing behavior,
  removing duplication, extracting functions, applying design patterns, and cleaning up technical debt.
  Activate when the user says "clean this up", "this is messy", "refactor", "improve the structure",
  "there's a lot of duplication", "this function is too long", "technical debt", "it works but it's ugly",
  or when a file has grown beyond 200 lines or a function beyond 30 lines. Never refactor without tests first.
---

# Refactoring Skill

Refactoring = improving the code's internal structure without changing what it does.
The goal is code that is easier to understand, test, and extend — not just code that looks nicer.

**The Golden Rule: Never refactor code that doesn't have tests. Write tests first, then refactor.**

---

## Phase 1 — Before Touching Anything

1. **Understand what the code does** — fully, not just approximately
2. **Write tests** (or verify existing tests pass) — these are your safety net
3. **Commit the current state** — so you can always go back
4. **Agree on scope** — refactor one thing at a time, not everything at once

```bash
# Create a safety commit before refactoring
git add .
git commit -m "chore: save state before refactoring sign_maps.py"
```

---

## Part 1 — Code Smells (What to Look For)

### Long Functions (> 30 lines)
```python
# ❌ This function does 4 things — split it
async def handle_text_message(session_id, message, websocket):
    # 1. Validate
    if len(message.get('text', '')) > 5000:
        ...
    # 2. Translate if needed
    if message.get('language') != 'en':
        text = await ollama_service.translate(...)
    # 3. Convert to SASL
    signs = sasl_transformer.transform(text)
    # 4. Broadcast
    await broadcast_to_session(session_id, {'type': 'signs', 'signs': signs})
    
# ✅ Extract each step into its own function
async def handle_text_message(session_id, message, websocket):
    text = await _validate_and_translate(message)
    signs = _convert_to_sasl(text)
    await _broadcast_signs(session_id, signs)
```

### Duplicated Code (DRY violation)
```python
# ❌ Same validation logic in two places
def handle_hearing_message(msg):
    if 'type' not in msg:
        return error_response("Missing type")
    if msg['type'] not in VALID_TYPES:
        return error_response(f"Unknown type: {msg['type']}")
    ...

def handle_deaf_message(msg):
    if 'type' not in msg:        # ← DUPLICATE
        return error_response("Missing type")
    if msg['type'] not in VALID_TYPES:  # ← DUPLICATE
        return error_response(f"Unknown type: {msg['type']}")
    ...

# ✅ Extract the shared logic
def validate_message_type(msg: dict) -> tuple[bool, str | None]:
    """Validates that a message has a known type field."""
    if 'type' not in msg:
        return False, "Missing type"
    if msg['type'] not in VALID_TYPES:
        return False, f"Unknown type: {msg['type']}"
    return True, None

def handle_hearing_message(msg):
    is_valid, error = validate_message_type(msg)
    if not is_valid:
        return error_response(error)
    ...
```

### Magic Numbers
```python
# ❌ What does 5000 mean? What about 10 * 1024 * 1024?
if len(text) > 5000:
    raise ValueError("Too long")
if audio_size > 10 * 1024 * 1024:
    raise ValueError("Too large")

# ✅ Named constants explain the intent
MAX_TEXT_CHARACTERS = 5000
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB

if len(text) > MAX_TEXT_CHARACTERS:
    raise ValueError(f"Text exceeds maximum of {MAX_TEXT_CHARACTERS} characters")
if audio_size > MAX_AUDIO_BYTES:
    raise ValueError("Audio file too large (maximum 10 MB)")
```

### Deep Nesting (> 3 levels)
```python
# ❌ Hard to read — 4 levels deep
def process_message(msg):
    if msg:
        if msg.get('type'):
            if msg['type'] == 'text':
                if msg.get('text'):
                    # Finally do something
                    return translate(msg['text'])

# ✅ Early returns flatten the nesting
def process_message(msg):
    if not msg:
        return None
    if not msg.get('type'):
        return None
    if msg['type'] != 'text':
        return None
    if not msg.get('text'):
        return None
    return translate(msg['text'])
```

---

## Part 2 — Refactoring Patterns

### Extract Function
When a block of code can be named and has a single purpose:
```python
# Before
async def handle_websocket(...):
    # Lots of code to validate session
    if not session_id or not re.match(r'^amandla-\d+-[a-f0-9]+$', session_id):
        await websocket.close(code=4002)
        return

# After
def _is_valid_session_id(session_id: str) -> bool:
    """Returns True if session_id matches the amandla-[timestamp]-[hex] format."""
    return bool(re.match(r'^amandla-\d+-[a-f0-9]+$', session_id or ''))

async def handle_websocket(...):
    if not _is_valid_session_id(session_id):
        await websocket.close(code=4002)
        return
```

### Extract Constant
```python
# Before
if role not in ["hearing", "deaf", "rights"]:

# After
VALID_ROLES = frozenset({"hearing", "deaf", "rights"})

if role not in VALID_ROLES:
```

### Replace Conditional with Dispatch Table
```python
# ❌ Long if/elif chain for message types
if message['type'] == 'text':
    await handle_text(session_id, message)
elif message['type'] == 'speech_upload':
    await handle_speech(session_id, message)
elif message['type'] == 'sign':
    await handle_sign(session_id, message)
elif message['type'] == 'emergency':
    await handle_emergency(session_id, message)
# ... 8 more elif blocks

# ✅ Dispatch table — adding new types doesn't require editing this logic
MESSAGE_HANDLERS = {
    'text': handle_text,
    'speech_upload': handle_speech,
    'sign': handle_sign,
    'emergency': handle_emergency,
}

handler = MESSAGE_HANDLERS.get(message['type'])
if handler:
    await handler(session_id, message)
else:
    logger.warning(f"Unknown message type: {message['type']}")
```

---

## Part 3 — Safe Refactoring Steps

Follow this order. Don't skip steps.

```
1. Write a test for the current behavior (even a simple "does it run without error")
2. Run tests — confirm they pass
3. Make ONE small change (extract one function, rename one variable, etc.)
4. Run tests again — confirm they still pass
5. Commit: "refactor: extract validate_message_type from handle_hearing_message"
6. Repeat from step 3
```

This approach means:
- If tests break, you know exactly which change caused it
- Each commit is a safe checkpoint you can return to
- Small commits are easy to review and understand

---

## Part 4 — What NOT to Refactor

Don't refactor:
- Code you don't fully understand — understand it first
- Code without tests — write tests first
- Working code "just because it looks messy" — if it works and is rarely changed, leave it
- Multiple things at once — one refactoring per commit

---

## Environment Notes

**In Claude Code (terminal):**
```bash
# Find long functions in Python (> 30 lines approximation)
awk '/^def |^async def /{if (count > 30) print prev_func, ":", count, "lines"; count=0; prev_func=$0} {count++}' backend/main.py

# Find duplicated code patterns
# Install: pip install pylint --break-system-packages
pylint backend/ --disable=all --enable=duplicate-code

# Check for magic numbers
grep -rn "[^=!<>] [0-9]\{4,\}" backend/ --include="*.py"
```

**In Claude.ai (browser):** Share the code and I'll identify the smells.
Always present the refactoring as a plan first — list every function being extracted,
every constant being named, every duplication being removed. Wait for approval before changing anything.
