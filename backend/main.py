"""Minimal AMANDLA backend

Provides:
- GET /health
- WebSocket at /ws/{sessionId}/{role}
- POST /speech (placeholder)

This is a minimal scaffold for local development and smoke-testing.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import JSONResponse
from typing import Dict, Any

app = FastAPI()

# Per-session state (in-memory). Keys: sessionId -> { users: {role: ws}, queue: [] }
sessions: Dict[str, Dict[str, Any]] = {}


@app.get('/health')
async def health():
    return JSONResponse({'ok': True})


@app.post('/speech')
async def upload_speech(audio: UploadFile = File(...)):
    """Placeholder endpoint for receiving uploaded speech audio.

    Currently returns a placeholder response. Integrate Whisper + Ollama in services later.
    """
    # Save uploaded file temporarily (async) if needed; for now just acknowledge receipt
    content = await audio.read()
    size = len(content)
    print(f"[Backend] Received speech upload: filename={audio.filename} size={size}")
    return {'signs': [], 'text': '', 'size': size}


@app.websocket('/ws/{sessionId}/{role}')
async def websocket_endpoint(websocket: WebSocket, sessionId: str, role: str):
    await websocket.accept()
    print(f"[Backend] WS connect session={sessionId} role={role}")

    # Create session if missing
    session = sessions.setdefault(sessionId, {'users': {}, 'queue': []})
    session['users'][role] = websocket

    # Notify connected user
    try:
        await websocket.send_json({'type': 'status', 'status': 'connected', 'session_id': sessionId})

        while True:
            data = await websocket.receive_text()
            print(f"[Backend] WS recv session={sessionId} role={role} data={data}")

            # Try to parse incoming JSON
            import json
            try:
                msg = json.loads(data)
            except Exception:
                # Not JSON — forward raw
                msg = {'type': 'raw', 'data': data}

            # If hearing user sent text, run a simple sentence->signs mapping (mock pipeline)
            if msg.get('type') == 'text' and role == 'hearing':
                text = msg.get('text', '')
                sign_names = sentence_to_sign_names(text)
                out = {'type': 'signs', 'signs': sign_names, 'text': text, 'session_id': sessionId}

                # Send to all connected users except sender
                for r, ws in list(session['users'].items()):
                    try:
                        if ws is not websocket:
                            await ws.send_json(out)
                    except Exception:
                        pass
                continue

            # Otherwise broadcast to other role(s) as-is
            for r, ws in list(session['users'].items()):
                try:
                    if ws is not websocket:
                        # send JSON if possible
                        try:
                            await ws.send_text(json.dumps(msg))
                        except Exception:
                            await ws.send_text(str(msg))
                except Exception:
                    pass

    except WebSocketDisconnect:
        print(f"[Backend] WS disconnect session={sessionId} role={role}")
    except Exception as e:
        print(f"[Backend] WS error session={sessionId} role={role} error={e}")
    finally:
        # Cleanup
        try:
            session['users'].pop(role, None)
            if not session['users'] and not session['queue']:
                sessions.pop(sessionId, None)
                print(f"[Backend] Session {sessionId} cleaned up")
        except Exception:
            pass


def sentence_to_sign_names(text: str):
    """A minimal mock sentence->signs converter.

    Returns a list of sign names (strings) that the frontend avatar can map to full sign objects.
    This is intentionally lightweight and only covers common phrases and words.
    """
    if not text:
        return []

    lower = text.lower()

    # Phrase-level mapping
    phrases = {
        "how are you": ["HOW ARE YOU"],
        "i'm fine": ["I'M FINE"],
        "im fine": ["I'M FINE"],
        "i love you": ["I LOVE YOU"],
    }
    for p, signs in phrases.items():
        if p in lower:
            return signs

    # Word-level mapping
    word_map = {
        'hi': 'HELLO', 'hello': 'HELLO', 'hey': 'HELLO',
        'bye': 'GOODBYE', 'goodbye': 'GOODBYE', 'thanks': 'THANK YOU', 'thank': 'THANK YOU',
        'please': 'PLEASE', 'yes': 'YES', 'no': 'NO', 'help': 'HELP', 'stop': 'STOP', 'wait': 'WAIT',
        'what': 'WHAT', 'who': 'WHO', 'where': 'WHERE', 'when': 'WHEN', 'why': 'WHY', 'how': 'HOW',
        'eat': 'EAT', 'drink': 'DRINK', 'sleep': 'SLEEP', 'sit': 'SIT', 'stand': 'STAND',
        'walk': 'WALK', 'run': 'RUN', 'work': 'WORK', 'wash': 'WASH', 'open': 'OPEN', 'close': 'CLOSE'
    }

    # tokenize
    import re
    words = re.sub(r"[^a-z0-9\s]", ' ', lower).split()
    result = []
    for w in words:
        if w in ('the','a','an','is','are','was','were','be','been','of','to','in','for','on','with','at','by','as','it','its','this','that','and','but','or','so','um','uh','ah','oh','hmm'):
            continue
        if w in word_map:
            result.append(word_map[w])
        else:
            # fallback: letters as fingerspelling (single-letter sign names)
            for ch in w.upper():
                if 'A' <= ch <= 'Z':
                    result.append(ch)
    return result


