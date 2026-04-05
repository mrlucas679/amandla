"""AMANDLA backend — FastAPI server

Provides:
- GET  /health              — liveness check
- GET  /api/status          — AI service health (Ollama + Whisper)
- POST /speech              — audio upload → Whisper transcription → SASL signs
- POST /rights/analyze      — incident description → rights analysis (Gemini)
- POST /rights/letter       — full details → formal complaint letter (Gemini)
- POST /api/sasl/translate  — English text → SASL gloss + tokens
- GET  /api/sasl/health     — SASL transformer health
- WS   /ws/{sessionId}/{role} — main real-time communication channel
"""
import sys
import os
import json
import re
import logging
import logging.handlers

# Ensure project root is in sys.path regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional

# ── Logging: console + rotating file ────────────────────────────────────────
_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(_log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            os.path.join(_log_dir, "amandla.log"),
            maxBytes=5 * 1024 * 1024,  # 5 MB per file
            backupCount=3,
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger(__name__)

# 10 MB upload cap for audio files
_MAX_AUDIO_BYTES = 10 * 1024 * 1024

app = FastAPI(title="AMANDLA Backend")

# ── SASL transformer routes ────────────────────────────────────────
try:
    from sasl_transformer.routes import router as sasl_router
    app.include_router(sasl_router, prefix="/api/sasl")
    logger.info("SASL transformer routes registered at /api/sasl/*")
except Exception as _e:
    logger.error(f"SASL transformer routes not loaded: {_e}", exc_info=True)

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


# ── SASL PIPELINE ─────────────────────────────────────────

# Module-level SASL transformer singleton (lazy init on first use)
_sasl_transformer = None


async def _text_to_sasl_signs(text: str) -> dict:
    """
    Convert English text → SASL-ordered sign names + gloss text.

    Fallback chain:
      1. SASL transformer (Gemini) — proper SOV grammar, time-first, aspect markers
      2. classify_text_to_signs (Ollama → Gemini → rule-based word map)

    Returns:
      { signs: [...], text: "<SASL gloss>", original_english: "<English>" }
    """
    global _sasl_transformer
    if not text:
        return {"signs": [], "text": "", "original_english": ""}

    # 1. Try SASL transformer (proper grammar ordering via Gemini)
    try:
        from sasl_transformer.transformer import SASLTransformer
        from sasl_transformer.models import TranslationRequest
        if _sasl_transformer is None:
            _sasl_transformer = SASLTransformer()
        transformer = _sasl_transformer
        response = await transformer.translate(TranslationRequest(english_text=text))
        sign_names = [tok.gloss for tok in response.tokens]
        if sign_names:
            logger.info(f"[SASL] '{text[:50]}' → '{response.gloss_text}'")
            return {
                "signs": sign_names,
                "text": response.gloss_text,
                "original_english": text,
                "non_manual_markers": list(response.non_manual_markers) if response.non_manual_markers else [],
                "sign_coverage": getattr(response, "sign_coverage", 1.0),
                "fingerspelled": list(getattr(response, "fingerspelled_words", [])),
            }
    except Exception as e:
        logger.warning(f"[SASL] Transformer failed, falling back: {e}")

    # 2. Fallback: raw sign name list (no grammar reordering)
    from backend.services.ollama_client import classify_text_to_signs
    sign_names = await classify_text_to_signs(text)
    return {
        "signs": sign_names,
        "text": " ".join(sign_names),
        "original_english": text,
        "non_manual_markers": [],
    }


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
    if len(content) > _MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file too large (max 10 MB)")
    logger.info(f"[Speech] Received {audio.filename} size={len(content)} mime={mime_type}")

    try:
        from backend.services.whisper_service import transcribe_audio
        result = await transcribe_audio(content, mime_type)

        if result.get("error") and not result.get("text"):
            logger.warning(f"[Speech] Transcription returned error: {result['error']}")

        text     = result.get("text", "").strip()
        detected = result.get("language", "en")

        # Reject transcriptions detected as non-English — they are Whisper hallucinations
        # caused by background noise or very short audio clips.
        if detected and detected != "en" and not result.get("engine") == "parakeet":
            logger.warning(f"[Speech] Non-English detected ({detected}) — discarding transcription: {text[:60]!r}")
            return {
                "text": "",
                "original_english": "",
                "sasl_gloss": "",
                "signs": [],
                "language": detected,
                "confidence": 0.0,
                "error": f"Speech detected as '{detected}' — please speak English clearly."
            }

        sasl = await _text_to_sasl_signs(text)

        return {
            "text": text,                        # original English — for hearing window display
            "original_english": text,
            "sasl_gloss": sasl["text"],          # SASL grammar — for deaf window only
            "signs": sasl["signs"],
            "language": detected,
            "confidence": result.get("confidence", 0.0),
            "sign_coverage": sasl.get("sign_coverage", 1.0),
            "fingerspelled_words": sasl.get("fingerspelled", []),
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


# ── DEAF → HEARING SIGN RECONSTRUCTION ───────────────────
# Per-session buffers: accumulate signs from deaf user, then
# reconstruct to natural English and send to hearing with TTS.

import asyncio as _asyncio

_sign_buffers:    Dict[str, list] = {}   # sessionId → [sign_names]
_sign_tasks:      Dict[str, Any]  = {}   # sessionId → asyncio.Task
_harps_recognizers: Dict[str, Any] = {}  # sessionId → HARPSSignRecognizer


def _simple_signs_to_english(signs: list) -> str:
    """Rule-based SASL sign sequence → natural English sentence (no network).

    For single known signs, returns a complete proper sentence.
    For sequences, builds the best English it can from a word map.
    """
    # Single-sign → complete natural English sentence
    _sentence_map = {
        "HELP":      "I need help.",
        "WATER":     "I need water.",
        "DOCTOR":    "I need a doctor.",
        "NURSE":     "I need a nurse.",
        "HOSPITAL":  "I need to go to the hospital.",
        "SICK":      "I am not feeling well.",
        "PAIN":      "I am in pain.",
        "HURT":      "I am hurt.",
        "MEDICINE":  "I need medicine.",
        "AMBULANCE": "Please call an ambulance.",
        "EMERGENCY": "This is an emergency.",
        "HAPPY":     "I am happy.",
        "SAD":       "I am sad.",
        "ANGRY":     "I am angry.",
        "SCARED":    "I am scared.",
        "TIRED":     "I am tired.",
        "HUNGRY":    "I am hungry.",
        "THIRSTY":   "I am thirsty.",
        "WORRIED":   "I am worried.",
        "CONFUSED":  "I am confused.",
        "STOP":      "Please stop.",
        "WAIT":      "Please wait.",
        "REPEAT":    "Please repeat that.",
        "UNDERSTAND":"I understand.",
        "YES":       "Yes.",
        "NO":        "No.",
        "PLEASE":    "Please.",
        "THANK YOU": "Thank you.",
        "SORRY":     "I am sorry.",
        "HELLO":     "Hello.",
        "GOODBYE":   "Goodbye.",
        "HOME":      "I want to go home.",
        "GO":        "I need to go.",
        "COME":      "Please come here.",
        "RIGHTS":    "I know my rights.",
        "LAW":       "This is against the law.",
        "EQUAL":     "I deserve equal treatment.",
        "GOOD":      "I am doing well.",
        "BAD":       "Things are not good.",
    }

    # Single sign — use the full-sentence map
    if len(signs) == 1:
        key = signs[0].upper()
        if key in _sentence_map:
            return _sentence_map[key]

    # Multi-sign — word-level map + basic SVO reconstruction
    _word_map = {
        "I": "I", "YOU": "you", "WE": "we", "THEY": "they",
        "WANT": "need", "HELP": "help", "WATER": "water",
        "DOCTOR": "a doctor", "NURSE": "a nurse", "HOSPITAL": "the hospital",
        "SICK": "sick", "PAIN": "in pain", "HURT": "hurt",
        "MEDICINE": "medicine", "AMBULANCE": "an ambulance",
        "EMERGENCY": "an emergency", "HAPPY": "happy", "SAD": "sad",
        "ANGRY": "angry", "SCARED": "scared", "TIRED": "tired",
        "HUNGRY": "hungry", "THIRSTY": "thirsty", "WORRIED": "worried",
        "CONFUSED": "confused", "GOOD": "good", "BAD": "bad",
        "YES": "yes", "NO": "no", "PLEASE": "please",
        "THANK YOU": "thank you", "SORRY": "sorry",
        "STOP": "stop", "WAIT": "wait", "COME": "come", "GO": "go",
        "HOME": "home", "SCHOOL": "school", "WORK": "work",
    }
    words = [_word_map.get(s.upper(), s.lower()) for s in signs]
    sentence = " ".join(words)
    return sentence[0].upper() + sentence[1:] + ("." if not sentence.endswith(".") else "") if sentence else ""


async def _ollama_signs_to_english(signs: list) -> str:
    """Use local Ollama model to reconstruct SASL signs → English."""
    try:
        import httpx
        from dotenv import load_dotenv
        load_dotenv()
        base  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "amandla")
        sign_str = " ".join(signs)
        prompt = (
            f"Convert these SASL sign names to a single natural English sentence.\n"
            f"Signs: {sign_str}\n"
            f"Rules: reorder to English SVO, add pronouns/articles/helpers, keep it short.\n"
            f"Reply with ONLY the English sentence.\n"
            f"Example: SICK DOCTOR → 'I am sick and need a doctor'"
        )
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(
                f"{base}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False, "temperature": 0.2}
            )
            if r.status_code == 200:
                text = r.json().get("response", "").strip().split("\n")[0].strip()
                if text and len(text) < 250:
                    return text
    except Exception as e:
        logger.debug(f"[Signs2English] Ollama failed: {e}")
    return None


async def _signs_to_english(signs: list) -> str:
    """Reconstruct SASL sign sequence to natural English. Gemini → rule-based."""
    if not signs:
        return ""

    # 1. Gemini — best grammar reconstruction (has SASL grammar understanding)
    try:
        from backend.services.gemini_service import signs_to_english as gemini_s2e
        result = await gemini_s2e(signs)
        if result:
            logger.info(f"[Signs2English] Gemini: {signs} → {result!r}")
            return result
    except Exception as e:
        logger.debug(f"[Signs2English] Gemini unavailable: {e}")

    # 2. Rule-based fallback (Ollama skipped — unreliable for reverse SASL→English task)
    result = _simple_signs_to_english(signs)
    logger.info(f"[Signs2English] Rule-based: {signs} → {result!r}")
    return result


async def _debounce_and_flush(session_id: str, session: dict):
    """Wait 1.5s after last sign, then reconstruct and send to hearing."""
    await _asyncio.sleep(1.5)
    signs = _sign_buffers.pop(session_id, [])
    _sign_tasks.pop(session_id, None)
    if not signs:
        return
    english = await _signs_to_english(signs)
    if not english:
        return
    hearing_ws = session["users"].get("hearing")
    if hearing_ws:
        await _send_safe(hearing_ws, {
            "type":   "deaf_speech",
            "text":   english,
            "signs":  signs,
        })
        logger.info(f"[Signs2English] Sent to hearing: {english!r}")


# ── WEBSOCKET ─────────────────────────────────────────────

@app.websocket("/ws/{sessionId}/{role}")
async def websocket_endpoint(websocket: WebSocket, sessionId: str, role: str):
    await websocket.accept()
    logger.info(f"[WS] connect session={sessionId} role={role}")

    session = sessions.setdefault(sessionId, {"users": {}, "queue": []})
    if role in session["users"]:
        logger.warning(f"[WS] Role '{role}' already taken in session {sessionId} — replacing stale connection")
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

            # Hearing user sends text → convert to SASL signs → broadcast to deaf
            if msg.get("type") in ("text", "speech_text") and role == "hearing":
                text     = msg.get("text", "")
                language = msg.get("language")   # Whisper-detected language code, e.g. "zu"
                sasl = await _text_to_sasl_signs(text)
                out = {
                    "type":               "signs",
                    "signs":              sasl["signs"],
                    "text":               sasl["text"],
                    "original_english":   sasl["original_english"],
                    "language":           language,
                    "session_id":         sessionId,
                    "non_manual_markers": sasl.get("non_manual_markers", []),
                    "sign_coverage":      sasl.get("sign_coverage", 1.0),
                    "fingerspelled_words": sasl.get("fingerspelled", []),
                }
                await _broadcast(session, websocket, out)
                # Also echo turn indicator to both sides
                await _broadcast_all(session, {"type": "turn", "speaker": "hearing"})
                continue

            # Deaf window sent MediaPipe landmarks → HARPS recogniser (Ollama fallback)
            if msg.get("type") == "landmarks" and role == "deaf":
                landmarks  = msg.get("landmarks", [])
                handedness = msg.get("handedness", [])
                hand_count = msg.get("hand_count", 1)
                if isinstance(handedness, str):
                    handedness = [handedness]
                # Log every landmark frame so we can diagnose hand count issues
                logger.info(f"[Landmarks] hand_count={hand_count} landmarks={len(landmarks)} handedness={handedness}")
                if landmarks:
                    try:
                        # Lazy-create a per-session HARPS recognizer
                        if sessionId not in _harps_recognizers:
                            from backend.services.harps_recognizer import HARPSSignRecognizer
                            _harps_recognizers[sessionId] = HARPSSignRecognizer()
                        harps_rec = _harps_recognizers[sessionId]
                        result = harps_rec.push_frame(landmarks, handedness)

                        # Filter HARPS demo-trained placeholder labels → let Ollama handle
                        if result is not None and re.match(r"^SIGN_\d+$", result.get("sign", "")):
                            result = None

                        # HARPS not ready or produced demo labels → try Ollama as one-shot fallback
                        if result is None:
                            try:
                                from backend.services.ollama_service import recognize_sign
                                # Ollama handles one hand (21 pts). Pick the right hand if present,
                                # otherwise fall back to the first detected hand.
                                ollama_lm = landmarks
                                ollama_hand = handedness[0] if handedness else "Right"
                                if len(landmarks) > 21:
                                    # Two hands sent — find right hand group
                                    for hi, hl in enumerate(handedness):
                                        if hl.lower() == "right":
                                            ollama_lm   = landmarks[hi * 21 : hi * 21 + 21]
                                            ollama_hand = "Right"
                                            break
                                    else:
                                        ollama_lm   = landmarks[:21]
                                        ollama_hand = handedness[0]
                                result = await recognize_sign({
                                    "landmarks": ollama_lm,
                                    "handedness": ollama_hand
                                })
                                if result:
                                    result["method"] = "ollama"
                            except Exception:
                                result = None

                        if result:
                            sign_name  = result.get("sign", "UNKNOWN")
                            confidence = result.get("confidence", 0.0)
                            method     = result.get("method", "unknown")
                            min_conf   = 0.5 if method == "harps" else 0.5
                            if sign_name not in ("UNKNOWN", "PROCESSING") and confidence >= min_conf:
                                sign_out = {
                                    "type":       "sign",
                                    "text":       sign_name,
                                    "confidence": confidence,
                                    "sender":     "deaf",
                                    "source":     "mediapipe",
                                    "method":     method,
                                }
                                await _broadcast(session, websocket, sign_out)
                                try:
                                    await websocket.send_json(sign_out)
                                except Exception:
                                    pass
                                await _broadcast_all(session, {"type": "turn", "speaker": "deaf"})
                                # Buffer mediapipe-detected sign for English reconstruction —
                                # same pipeline as quick-sign buttons (deaf_speech → hearing TTS)
                                existing = _sign_tasks.get(sessionId)
                                if existing and not existing.done():
                                    existing.cancel()
                                _sign_buffers.setdefault(sessionId, []).append(sign_name)
                                _sign_tasks[sessionId] = _asyncio.create_task(
                                    _debounce_and_flush(sessionId, session)
                                )
                    except Exception as e:
                        logger.warning(f"[WS] Landmark recognition error: {e}")
                continue

            # Deaf quick-sign button → buffer for English reconstruction + forward raw sign
            if msg.get("type") == "sign" and role == "deaf":
                sign_text = msg.get("text", "")
                # Buffer non-emergency signs for reconstruction
                if sign_text and sign_text != "EMERGENCY":
                    existing = _sign_tasks.get(sessionId)
                    if existing and not existing.done():
                        existing.cancel()
                    _sign_buffers.setdefault(sessionId, []).append(sign_text)
                    _sign_tasks[sessionId] = _asyncio.create_task(
                        _debounce_and_flush(sessionId, session)
                    )
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
            _harps_recognizers.pop(sessionId, None)
            logger.info(f"[WS] session {sessionId} cleaned up")


async def _send_safe(ws, msg: dict):
    """Send a JSON message to a single WebSocket, swallowing errors."""
    try:
        await ws.send_json(msg)
    except Exception:
        pass


async def _broadcast(session: dict, sender_ws, msg: dict):
    """Send msg to all users in session except sender (parallel)."""
    import asyncio
    targets = [ws for ws in session["users"].values() if ws is not sender_ws]
    if targets:
        await asyncio.gather(*(_send_safe(ws, msg) for ws in targets))


async def _broadcast_all(session: dict, msg: dict):
    """Send msg to every user in session including sender (parallel)."""
    import asyncio
    targets = list(session["users"].values())
    if targets:
        await asyncio.gather(*(_send_safe(ws, msg) for ws in targets))


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