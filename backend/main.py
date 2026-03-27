"""AMANDLA backend — FastAPI server

Provides:
- GET  /health              — liveness check
- GET  /api/status          — AI service health (Ollama + Whisper)
- POST /speech              — audio upload → Whisper transcription → sign names
- POST /rights/analyze      — incident description → rights analysis (Claude)
- POST /rights/letter       — full details → formal complaint letter (Claude)
- WS   /ws/{sessionId}/{role} — main real-time communication channel
"""
import sys
import os
import json
import re
import logging

# Ensure project root is in sys.path regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AMANDLA Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Per-session state (in-memory). sessionId → { users: {role: ws}, queue: [] }
sessions: Dict[str, Dict[str, Any]] = {}


# ── HEALTH ────────────────────────────────────────────────

@app.get("/health")
async def health():
    return JSONResponse({"ok": True})


@app.get("/api/status")
async def api_status():
    """Returns health of AI services for status-dot polling."""
    qwen_alive = await _check_ollama()
    whisper_ok = _check_whisper()
    return {
        "status": "ok",
        "qwen": "alive" if qwen_alive else "dead",
        "whisper": "ready" if whisper_ok else "unavailable",
        "sessions": len(sessions)
    }


async def _check_ollama() -> bool:
    try:
        import httpx
        from dotenv import load_dotenv
        load_dotenv()
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model_name = os.getenv("OLLAMA_MODEL", "amandla")
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{base}/api/tags")
            if r.status_code != 200:
                return False
            tags = r.json().get("models", [])
            return any(model_name in m.get("name", "") for m in tags)
    except Exception:
        return False


def _check_whisper() -> bool:
    """Check whether the Whisper model is already loaded (does not trigger load)."""
    try:
        from backend.services import whisper_service
        return whisper_service._model is not None
    except Exception:
        return False


# ── SPEECH → SIGNS ────────────────────────────────────────

@app.post("/speech")
async def upload_speech(
    audio: UploadFile = File(...),
    mime_type: str = Form(default="audio/webm")
):
    """
    Receives audio upload, transcribes with Whisper, converts to sign names.
    Returns: { text, signs, language, confidence }
    """
    content = await audio.read()
    logger.info(f"[Speech] Received {audio.filename} size={len(content)} mime={mime_type}")

    try:
        from backend.services.whisper_service import transcribe_audio
        result = await transcribe_audio(content, mime_type)

        if result.get("error") and not result.get("text"):
            logger.warning(f"[Speech] Transcription returned error: {result['error']}")

        text = result.get("text", "").strip()
        signs = sentence_to_sign_names(text) if text else []

        return {
            "text": text,
            "signs": signs,
            "language": result.get("language", "en"),
            "confidence": result.get("confidence", 0.0)
        }
    except Exception as e:
        logger.error(f"[Speech] Transcription error: {e}")
        return {"text": "", "signs": [], "language": "en", "confidence": 0.0, "error": str(e)}


# ── RIGHTS ENDPOINTS ──────────────────────────────────────

class AnalyseRequest(BaseModel):
    description: str
    incident_type: str = "workplace"


class LetterRequest(BaseModel):
    description: str
    user_name: str = "The Complainant"
    employer_name: str
    incident_date: str
    analysis: Optional[dict] = None


@app.post("/rights/analyze")
async def rights_analyze(req: AnalyseRequest):
    """Analyse an incident and return relevant rights / laws."""
    from backend.services.claude_service import analyse_incident
    result = await analyse_incident(req.description, req.incident_type)
    return result


@app.post("/rights/letter")
async def rights_letter(req: LetterRequest):
    """Generate a formal complaint letter."""
    from backend.services.claude_service import generate_rights_letter
    result = await generate_rights_letter(
        incident_description=req.description,
        user_name=req.user_name,
        employer_name=req.employer_name,
        incident_date=req.incident_date,
        analysis=req.analysis
    )
    return result


# ── WEBSOCKET ─────────────────────────────────────────────

@app.websocket("/ws/{sessionId}/{role}")
async def websocket_endpoint(websocket: WebSocket, sessionId: str, role: str):
    await websocket.accept()
    logger.info(f"[WS] connect session={sessionId} role={role}")

    session = sessions.setdefault(sessionId, {"users": {}, "queue": []})
    session["users"][role] = websocket

    try:
        await websocket.send_json({"type": "status", "status": "connected", "session_id": sessionId})

        while True:
            data = await websocket.receive_text()
            logger.debug(f"[WS] recv session={sessionId} role={role} len={len(data)}")

            try:
                msg = json.loads(data)
            except Exception:
                msg = {"type": "raw", "data": data}

            # Hearing user sends text → convert to signs → broadcast to deaf
            if msg.get("type") in ("text", "speech_text") and role == "hearing":
                text     = msg.get("text", "")
                language = msg.get("language")   # Whisper-detected language code, e.g. "zu"
                sign_names = sentence_to_sign_names(text)
                out = {
                    "type":       "signs",
                    "signs":      sign_names,
                    "text":       text,
                    "language":   language,
                    "session_id": sessionId
                }
                await _broadcast(session, websocket, out)
                # Also echo turn indicator to both sides
                await _broadcast_all(session, {"type": "turn", "speaker": "hearing"})
                continue

            # Deaf window sent MediaPipe landmarks → ask Ollama to recognise the sign
            if msg.get("type") == "landmarks" and role == "deaf":
                landmarks = msg.get("landmarks", [])
                handedness = msg.get("handedness", "Right")
                if landmarks:
                    try:
                        from backend.services.ollama_service import recognize_sign
                        result = await recognize_sign({
                            "landmarks": landmarks,
                            "handedness": handedness
                        })
                        sign_name   = result.get("sign", "UNKNOWN")
                        confidence  = result.get("confidence", 0.0)
                        if sign_name != "UNKNOWN" and confidence >= 0.5:
                            sign_out = {
                                "type":       "sign",
                                "text":       sign_name,
                                "confidence": confidence,
                                "sender":     "deaf",
                                "source":     "mediapipe"
                            }
                            # Send to hearing window
                            await _broadcast(session, websocket, sign_out)
                            # Echo back to deaf window so it can show ✓ confirmation
                            try:
                                await websocket.send_json(sign_out)
                            except Exception:
                                pass
                            # Turn indicator to both windows
                            await _broadcast_all(session, {"type": "turn", "speaker": "deaf"})
                    except Exception as e:
                        logger.warning(f"[WS] Landmark recognition error: {e}")
                continue

            # Deaf quick-sign button → echo turn indicator
            if msg.get("type") == "sign" and role == "deaf":
                await _broadcast(session, websocket, msg)
                await _broadcast_all(session, {"type": "turn", "speaker": "deaf"})
                continue

            # Everything else: forward to other role(s)
            await _broadcast(session, websocket, msg)

    except WebSocketDisconnect:
        logger.info(f"[WS] disconnect session={sessionId} role={role}")
    except Exception as e:
        logger.error(f"[WS] error session={sessionId} role={role}: {e}")
    finally:
        session["users"].pop(role, None)
        if not session["users"] and not session["queue"]:
            sessions.pop(sessionId, None)
            logger.info(f"[WS] session {sessionId} cleaned up")


async def _broadcast(session: dict, sender_ws, msg: dict):
    """Send msg to all users in session except sender."""
    for ws in list(session["users"].values()):
        if ws is sender_ws:
            continue
        try:
            await ws.send_json(msg)
        except Exception:
            pass


async def _broadcast_all(session: dict, msg: dict):
    """Send msg to every user in session (including sender — for turn indicators etc.)."""
    for ws in list(session["users"].values()):
        try:
            await ws.send_json(msg)
        except Exception:
            pass


# ── SENTENCE → SIGNS ──────────────────────────────────────

# Phrase-level mappings (checked before word tokenization)
_PHRASE_MAP = {
    "how are you":  ["HOW ARE YOU"],
    "i'm fine":     ["I'M FINE"],
    "im fine":      ["I'M FINE"],
    "i love you":   ["I LOVE YOU"],
    "thank you":    ["THANK YOU"],
    "good morning": ["GOOD", "MORNING"],
    "good night":   ["GOOD", "NIGHT"],
    "good bye":     ["GOODBYE"],
}

# Word-level mappings
_WORD_MAP = {
    # ── Greetings ──────────────────────────────────────────
    "hi": "HELLO", "hello": "HELLO", "hey": "HELLO", "greetings": "HELLO", "howzit": "HELLO",
    "bye": "GOODBYE", "goodbye": "GOODBYE", "farewell": "GOODBYE",
    "how are you": "HOW ARE YOU", "howzit": "HOW ARE YOU",
    "i'm fine": "I'M FINE", "im fine": "I'M FINE",
    "i love you": "I LOVE YOU",
    "thanks": "THANK YOU", "thank": "THANK YOU", "thank you": "THANK YOU", "cheers": "THANK YOU",
    "please": "PLEASE", "pls": "PLEASE",
    "sorry": "SORRY", "apologies": "SORRY", "my bad": "SORRY", "excuse": "SORRY",

    # ── Confirmation / Negation ──────────────────────────────
    "yes": "YES", "ok": "YES", "okay": "YES", "yep": "YES", "yup": "YES",
    "correct": "YES", "right": "YES", "affirmative": "YES", "sure": "YES",
    "no": "NO", "nope": "NO", "nah": "NO",
    # Negation contractions → sign NO
    "not": "NO", "never": "NO", "nobody": "NO", "nothing": "NO", "none": "NO",
    "don't": "NO", "dont": "NO", "doesn't": "NO", "doesnt": "NO",
    "didn't": "NO", "didnt": "NO", "can't": "NO", "cant": "NO",
    "won't": "NO", "wont": "NO", "isn't": "NO", "isnt": "NO",
    "aren't": "NO", "arent": "NO", "wasn't": "NO", "wasnt": "NO",
    "weren't": "NO", "werent": "NO", "shouldn't": "NO", "shouldnt": "NO",
    "wouldn't": "NO", "wouldnt": "NO", "couldn't": "NO", "couldnt": "NO",

    # ── Instructions ────────────────────────────────────────
    "help": "HELP", "assist": "HELP", "assistance": "HELP", "helping": "HELP",
    "stop": "STOP", "halt": "STOP", "stopping": "STOP", "stopped": "STOP",
    "wait": "WAIT", "waiting": "WAIT", "hold on": "WAIT", "later": "WAIT",
    "repeat": "REPEAT", "again": "REPEAT", "say again": "REPEAT",
    "understand": "UNDERSTAND", "understood": "UNDERSTAND", "understanding": "UNDERSTAND",

    # ── Medical ─────────────────────────────────────────────
    "water": "WATER",
    "pain": "PAIN", "painful": "PAIN", "sore": "PAIN", "ache": "PAIN", "aching": "PAIN",
    "hurt": "HURT", "hurts": "HURT", "hurting": "HURT", "injured": "HURT",
    "emergency": "EMERGENCY",
    "doctor": "DOCTOR", "dr": "DOCTOR", "physician": "DOCTOR", "doc": "DOCTOR",
    "nurse": "NURSE", "nurses": "NURSE",
    "hospital": "HOSPITAL", "clinic": "HOSPITAL", "hospitals": "HOSPITAL",
    "sick": "SICK", "ill": "SICK", "unwell": "SICK", "nauseous": "SICK", "nausea": "SICK",
    "medicine": "MEDICINE", "medication": "MEDICINE", "pills": "MEDICINE",
    "tablet": "MEDICINE", "tablets": "MEDICINE", "drug": "MEDICINE", "drugs": "MEDICINE",
    "ambulance": "AMBULANCE",
    "fire": "FIRE", "burning": "FIRE", "flames": "FIRE",
    "dangerous": "DANGEROUS", "danger": "DANGEROUS", "hazard": "DANGEROUS",
    "careful": "CAREFUL", "caution": "CAREFUL", "watch out": "CAREFUL",
    "safe": "SAFE", "safety": "SAFE",

    # ── Emotions ────────────────────────────────────────────
    "happy": "HAPPY", "joyful": "HAPPY", "glad": "HAPPY", "joy": "HAPPY",
    "cheerful": "HAPPY", "pleased": "HAPPY", "delighted": "HAPPY",
    "sad": "SAD", "unhappy": "SAD", "upset": "SAD", "depressed": "SAD",
    "miserable": "SAD", "gloomy": "SAD", "heartbroken": "SAD",
    "angry": "ANGRY", "mad": "ANGRY", "furious": "ANGRY",
    "annoyed": "ANGRY", "rage": "ANGRY", "irritated": "ANGRY",
    "scared": "SCARED", "afraid": "SCARED", "frightened": "SCARED",
    "fear": "SCARED", "terrified": "SCARED", "panic": "SCARED",
    "love": "LOVE", "loving": "LOVE",
    "excited": "EXCITED", "exciting": "EXCITED", "thrilled": "EXCITED",
    "tired": "TIRED", "exhausted": "TIRED", "sleepy": "TIRED",
    "fatigue": "TIRED", "weary": "TIRED",
    "hungry": "HUNGRY", "starving": "HUNGRY", "famished": "HUNGRY",
    "thirsty": "THIRSTY", "thirst": "THIRSTY",
    "worried": "WORRIED", "anxious": "WORRIED", "nervous": "WORRIED",
    "stressed": "WORRIED", "stress": "WORRIED", "worry": "WORRIED",
    "proud": "PROUD", "pride": "PROUD",
    "confused": "CONFUSED", "confusing": "CONFUSED",
    "puzzled": "CONFUSED", "baffled": "CONFUSED",

    # ── Question words ───────────────────────────────────────
    "who": "WHO", "what": "WHAT", "where": "WHERE", "when": "WHEN",
    "why": "WHY", "how": "HOW", "which": "WHICH",

    # ── Pronouns ────────────────────────────────────────────
    "i": "I", "me": "I", "my": "I", "mine": "I", "myself": "I",
    "you": "YOU", "your": "YOU", "yours": "YOU",
    "we": "WE", "us": "WE", "our": "WE",
    "they": "THEY", "them": "THEY", "their": "THEY",
    "he": "THEY", "she": "THEY", "his": "THEY", "her": "THEY",  # approximate

    # ── Verbs (all common forms) ─────────────────────────────
    "come": "COME", "comes": "COME", "coming": "COME", "came": "COME",
    "bring": "COME", "brings": "COME", "brought": "COME",
    "go": "GO", "goes": "GO", "going": "GO", "went": "GO", "gone": "GO",
    "leave": "GO", "leaving": "GO", "left": "GO",
    "listen": "LISTEN", "listens": "LISTEN", "listening": "LISTEN", "listened": "LISTEN",
    "hear": "LISTEN", "hearing": "LISTEN", "heard": "LISTEN",
    "look": "LOOK", "looks": "LOOK", "looking": "LOOK", "looked": "LOOK",
    "see": "LOOK", "sees": "LOOK", "seeing": "LOOK", "saw": "LOOK", "seen": "LOOK",
    "watch": "LOOK", "watching": "LOOK", "watched": "LOOK",
    "find": "LOOK", "finding": "LOOK", "found": "LOOK",
    "show": "LOOK", "showing": "LOOK", "showed": "LOOK",
    "know": "KNOW", "knows": "KNOW", "knowing": "KNOW", "knew": "KNOW",
    "think": "KNOW", "thinks": "KNOW", "thinking": "KNOW", "thought": "KNOW",
    "believe": "KNOW", "believes": "KNOW", "believed": "KNOW",
    "understand": "UNDERSTAND", "understands": "UNDERSTAND",
    "want": "WANT", "wants": "WANT", "wanting": "WANT", "wanted": "WANT",
    "need": "WANT", "needs": "WANT", "needing": "WANT", "needed": "WANT",
    "require": "WANT", "requires": "WANT", "required": "WANT",
    "get": "WANT", "gets": "WANT",  # "get me water" → WANT WATER
    "take": "WANT", "takes": "WANT", "taking": "WANT", "took": "WANT",
    "give": "GIVE", "gives": "GIVE", "giving": "GIVE", "gave": "GIVE", "given": "GIVE",
    "eat": "EAT", "eats": "EAT", "eating": "EAT", "ate": "EAT", "eaten": "EAT",
    "drink": "DRINK", "drinks": "DRINK", "drinking": "DRINK",
    "drank": "DRINK", "drunk": "DRINK",
    "sleep": "SLEEP", "sleeps": "SLEEP", "sleeping": "SLEEP", "slept": "SLEEP",
    "rest": "SLEEP", "resting": "SLEEP",
    "sit": "SIT", "sits": "SIT", "sitting": "SIT", "sat": "SIT",
    "seat": "SIT", "seated": "SIT",
    "stand": "STAND", "stands": "STAND", "standing": "STAND", "stood": "STAND",
    "walk": "WALK", "walks": "WALK", "walking": "WALK", "walked": "WALK",
    "run": "RUN", "runs": "RUN", "running": "RUN", "ran": "RUN",
    "work": "WORK", "works": "WORK", "working": "WORK", "worked": "WORK",
    "job": "WORK", "jobs": "WORK", "labour": "WORK", "labor": "WORK",
    "wash": "WASH", "washes": "WASH", "washing": "WASH", "washed": "WASH",
    "clean": "WASH", "cleaning": "WASH", "cleaned": "WASH",
    "write": "WRITE", "writes": "WRITE", "writing": "WRITE",
    "wrote": "WRITE", "written": "WRITE",
    "read": "READ", "reads": "READ", "reading": "READ",
    "open": "OPEN", "opens": "OPEN", "opening": "OPEN", "opened": "OPEN",
    "close": "CLOSE", "closes": "CLOSE", "closing": "CLOSE",
    "closed": "CLOSE", "shut": "CLOSE",
    "tell": "TELL", "tells": "TELL", "telling": "TELL", "told": "TELL",
    "say": "TELL", "says": "TELL", "saying": "TELL", "said": "TELL",
    "speak": "TELL", "speaks": "TELL", "speaking": "TELL", "spoke": "TELL",
    "talk": "TELL", "talks": "TELL", "talking": "TELL", "talked": "TELL",
    "call": "TELL",  # "call the doctor" → TELL DOCTOR (close enough)
    "sign": "SIGN", "signs": "SIGN", "signing": "SIGN", "signed": "SIGN",
    "laugh": "LAUGH", "laughs": "LAUGH", "laughing": "LAUGH", "laughed": "LAUGH",
    "cry": "CRY", "cries": "CRY", "crying": "CRY", "cried": "CRY",
    "weep": "CRY", "weeping": "CRY", "wept": "CRY",
    "hug": "HUG", "hugs": "HUG", "hugging": "HUG", "hugged": "HUG",

    # ── Descriptions ────────────────────────────────────────
    "good": "GOOD", "great": "GOOD", "nice": "GOOD", "fine": "GOOD",
    "well": "GOOD", "wonderful": "GOOD", "excellent": "GOOD",
    "bad": "BAD", "terrible": "BAD", "awful": "BAD", "wrong": "BAD",
    "big": "BIG", "large": "BIG", "huge": "BIG", "giant": "BIG",
    "small": "SMALL", "little": "SMALL", "tiny": "SMALL",
    "hot": "HOT", "warm": "HOT", "boiling": "HOT",
    "cold": "COLD", "cool": "COLD", "freezing": "COLD", "chilly": "COLD",
    "quiet": "QUIET", "silent": "QUIET", "shh": "QUIET", "silence": "QUIET",
    "fast": "FAST", "quick": "FAST", "quickly": "FAST", "rapid": "FAST",
    "slow": "SLOW", "slowly": "SLOW",

    # ── People / family ─────────────────────────────────────
    "family": "FAMILY", "families": "FAMILY",
    "mom": "MOM", "mother": "MOM", "mum": "MOM", "mama": "MOM",
    "dad": "DAD", "father": "DAD", "papa": "DAD",
    "baby": "BABY", "infant": "BABY",
    "friend": "FRIEND", "friends": "FRIEND", "buddy": "FRIEND", "mate": "FRIEND",
    "child": "CHILD", "kid": "CHILD", "children": "CHILD", "kids": "CHILD",
    "person": "PERSON", "people": "PERSON", "man": "PERSON",
    "woman": "PERSON", "men": "PERSON", "women": "PERSON",
    "teacher": "TEACHER", "teachers": "TEACHER", "instructor": "TEACHER",

    # ── Places ──────────────────────────────────────────────
    "home": "HOME", "house": "HOME",
    "school": "SCHOOL", "class": "SCHOOL", "classroom": "SCHOOL",
    "church": "CHURCH",
    "police": "POLICE", "cop": "POLICE", "officer": "POLICE",

    # ── Money ───────────────────────────────────────────────
    "money": "MONEY", "cash": "MONEY", "rand": "MONEY",
    "pay": "MONEY", "paying": "MONEY", "paid": "MONEY",
    "cost": "EXPENSIVE", "expensive": "EXPENSIVE", "costly": "EXPENSIVE",
    "price": "EXPENSIVE",
    "free": "FREE", "no charge": "FREE",
    "share": "SHARE", "sharing": "SHARE", "shared": "SHARE",

    # ── Nature ──────────────────────────────────────────────
    "rain": "RAIN", "raining": "RAIN", "rainy": "RAIN",
    "sun": "SUN", "sunny": "SUN", "sunshine": "SUN",
    "wind": "WIND", "windy": "WIND",
    "tree": "TREE", "trees": "TREE",

    # ── Food ────────────────────────────────────────────────
    "food": "FOOD", "meal": "FOOD", "meals": "FOOD",
    "bread": "BREAD",
    "drink": "DRINK",

    # ── Transport ───────────────────────────────────────────
    "car": "CAR", "vehicle": "CAR", "drive": "CAR", "driving": "CAR",
    "taxi": "TAXI", "uber": "TAXI", "minibus": "TAXI",
    "bus": "BUS",

    # ── Rights ──────────────────────────────────────────────
    "rights": "RIGHTS", "right": "RIGHTS",
    "law": "LAW", "legal": "LAW", "legislation": "LAW",
    "equal": "EQUAL", "equality": "EQUAL", "fair": "EQUAL",

    # ── Time ────────────────────────────────────────────────
    "today": "TODAY", "now": "NOW", "currently": "NOW", "soon": "NOW",
    "morning": "MORNING", "afternoon": "MORNING",
    "evening": "NIGHT", "night": "NIGHT", "tonight": "NIGHT",
}

_FILLER = {
    # Articles / determiners
    "the","a","an","some","any","every","each","both","either",
    # Auxiliary verbs (carry no sign meaning on their own)
    "is","am","are","was","were","be","been","being",
    "have","has","had","do","does","did",
    "can","could","will","would","should","shall","must","may","might",
    # Prepositions / conjunctions
    "of","to","in","for","on","with","at","by","as","from",
    "about","between","through","before","after","during","into","onto",
    "up","down","out","off","over","under","around","toward",
    "and","but","or","so","if","then","because","since","although",
    "though","however","therefore","yet","nor",
    # Pronouns / determiners with no clear sign
    "it","its","itself","this","that","these","those",
    # Common adverbs / fillers
    "um","uh","ah","oh","hmm","like","just","really","very",
    "also","too","even","still","already","always","often","usually",
    "quite","almost","enough","only","other","same","another","such",
    # Subjective / modal words with no direct sign
    "feel","feels","felt","seem","seems","seemed",
    "become","became","becomes","getting","got",
    "next","last","first","second","third",
    "more","most","less","least","much","many","few","several",
    "new","old","long","short","different",
    "here","there","everywhere","somewhere","anywhere","nowhere",
}


def _stem(word: str) -> str:
    """Reduce an inflected word to an approximate base form for lookup."""
    if word in _WORD_MAP or word in _FILLER:
        return word
    for suffix, replacement in [
        ("ness", ""), ("ment", ""), ("tion", ""), ("sion", ""),
        ("ings", ""), ("ing", ""), ("edly", "e"), ("ied", "y"),
        ("ies", "y"), ("ier", "y"), ("iest", "y"),
        ("ers", ""), ("er", ""), ("est", ""), ("ly", ""),
        ("ed", ""), ("es", ""), ("s", ""),
    ]:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            base = word[: -len(suffix)] + replacement
            if base in _WORD_MAP:
                return base
    return word


def sentence_to_sign_names(text: str) -> list:
    """Convert an English sentence to an ordered list of SASL sign name strings."""
    if not text:
        return []

    lower = text.lower().strip()

    # Check full sentence against phrase map first
    for phrase, signs in _PHRASE_MAP.items():
        if phrase in lower:
            return signs

    words = re.sub(r"[^a-z0-9\s']", " ", lower).split()
    result = []
    i = 0
    while i < len(words):
        w = words[i]

        # Try 3-word phrase
        if i + 2 < len(words):
            three = w + " " + words[i + 1] + " " + words[i + 2]
            if three in _PHRASE_MAP:
                result.extend(_PHRASE_MAP[three])
                i += 3
                continue

        # Try 2-word phrase
        if i + 1 < len(words):
            two = w + " " + words[i + 1]
            if two in _PHRASE_MAP:
                result.extend(_PHRASE_MAP[two])
                i += 2
                continue
            if two in _WORD_MAP:
                result.append(_WORD_MAP[two])
                i += 2
                continue

        if w in _FILLER:
            i += 1
            continue

        if w in _WORD_MAP:
            result.append(_WORD_MAP[w])
        else:
            # Try stemmed form before fingerspelling
            stemmed = _stem(w)
            if stemmed != w and stemmed in _WORD_MAP:
                result.append(_WORD_MAP[stemmed])
            elif w not in _FILLER:
                # Fingerspell unknown word letter by letter
                for ch in w.upper():
                    if "A" <= ch <= "Z":
                        result.append(ch)
        i += 1

    return result