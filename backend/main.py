"""AMANDLA backend — FastAPI server

Provides:
- GET  /health              — liveness check
- GET  /api/status          — AI service health (Ollama + Whisper)
- POST /speech              — audio upload → Whisper transcription → SASL signs
- POST /rights/analyze      — incident description → rights analysis (Ollama)
- POST /rights/letter       — full details → formal complaint letter (Ollama)
- POST /api/sasl/translate  — English text → SASL gloss + tokens
- GET  /api/sasl/health     — SASL transformer health
- WS   /ws/{sessionId}/{role} — main real-time communication channel

WebSocket message types handled (in addition to HTTP endpoints):
- speech_upload    — base64 audio → Whisper transcription → SASL signs
- status_request   — AI service health check (Ollama + Whisper)
- rights_analyze   — incident description → rights analysis
- rights_letter    — full details → formal complaint letter
- emergency        — broadcast emergency alert to all session users
"""
import sys
import os
import json
import base64
import asyncio
import logging
import logging.handlers

# Ensure project root is in sys.path regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env ONCE at startup — all modules can use os.getenv() after this
from dotenv import load_dotenv
load_dotenv()

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

# 5000 char limit for text messages via WebSocket (prevents abuse)
_MAX_TEXT_LENGTH = 5000

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

# ── Rate limiting middleware — prevents abuse of AI endpoints ────────────
try:
    from backend.middleware import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)
    logger.info("Rate limit middleware registered")
except Exception as _mw_err:
    logger.warning(f"Rate limit middleware not loaded: {_mw_err}")

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
      1. SASL transformer (Ollama) — proper SOV grammar, time-first, aspect markers
      2. classify_text_to_signs (Ollama → rule-based word map)

    All AI runs locally via Ollama — no cloud API keys needed.

    Args:
        text: English sentence from hearing user.

    Returns:
      { signs: [...], text: "<SASL gloss>", original_english: "<English>" }
    """
    global _sasl_transformer
    if not text:
        return {"signs": [], "text": "", "original_english": ""}

    # 1. Try SASL transformer (proper grammar ordering via Ollama)
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

        text = result.get("text", "").strip()
        sasl = await _text_to_sasl_signs(text)

        return {
            "text": text,                        # original English — for hearing window display
            "original_english": text,
            "sasl_gloss": sasl["text"],          # SASL grammar — for deaf window only
            "signs": sasl["signs"],
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
        analysis=req.analysis or {}
    )
    return result


# ── DEAF → HEARING SIGN RECONSTRUCTION ───────────────────
# Per-session buffers: accumulate signs from deaf user, then
# reconstruct to natural English and send to hearing with TTS.


_sign_buffers: Dict[str, list] = {}   # sessionId → [sign_names]
_sign_tasks:   Dict[str, Any]  = {}   # sessionId → asyncio.Task


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


async def _ollama_signs_to_english(signs: list) -> Optional[str]:
    """Use local Ollama model to reconstruct SASL signs → English."""
    try:
        import httpx
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
    """Reconstruct SASL sign sequence to natural English.

    Fallback chain: Ollama (local AI) → rule-based.
    No cloud API needed — everything runs locally.

    Args:
        signs: List of SASL sign name strings (e.g. ["WATER", "WANT", "I"]).

    Returns:
        Natural English sentence string (e.g. "I need water").
    """
    if not signs:
        return ""

    # 1. Ollama — local AI reconstruction
    try:
        ollama_result = await _ollama_signs_to_english(signs)
        if ollama_result:
            logger.info(f"[Signs2English] Ollama: {signs} → {ollama_result!r}")
            return ollama_result
    except Exception as e:
        logger.debug(f"[Signs2English] Ollama unavailable: {e}")

    # 2. Rule-based fallback (always works offline)
    result = _simple_signs_to_english(signs)
    logger.info(f"[Signs2English] Rule-based: {signs} → {result!r}")
    return result


async def _debounce_and_flush(session_id: str, session: dict):
    """Wait 1.5s after last sign, then reconstruct and send to hearing."""
    await asyncio.sleep(1.5)
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
                text     = msg.get("text", "")[:_MAX_TEXT_LENGTH]
                language = msg.get("language")   # Whisper-detected language code, e.g. "zu"
                sasl = await _text_to_sasl_signs(text)
                out = {
                    "type":             "signs",
                    "signs":            sasl["signs"],
                    "text":             sasl["text"],
                    "original_english": sasl["original_english"],
                    "language":         language,
                    "session_id":       sessionId
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

            # Deaf typed SASL text → reconstruct to English → send to hearing as deaf_speech
            if msg.get("type") == "sasl_text" and role == "deaf":
                sasl_text = msg.get("text", "")[:_MAX_TEXT_LENGTH].strip()
                if sasl_text:
                    hearing_ws = session["users"].get("hearing")

                    # Step 1: immediately tell hearing a message is coming (triggers indicator)
                    if hearing_ws:
                        await _send_safe(hearing_ws, {
                            "type":   "sasl_text",
                            "text":   sasl_text,
                            "sender": "deaf",
                        })
                    await _broadcast_all(session, {"type": "turn", "speaker": "deaf"})

                    # Step 2: translate (strip stray punctuation first)
                    signs = [w.strip('.,!?;:\'"') for w in sasl_text.upper().split()
                             if w.strip('.,!?;:\'"')]
                    try:
                        english = await asyncio.wait_for(_signs_to_english(signs), timeout=6.0)
                    except asyncio.TimeoutError:
                        english = _simple_signs_to_english(signs)
                        logger.warning(f"[SASL→EN] Timeout — using rule-based: {signs!r}")

                    # Step 3: send translated English to hearing
                    if english and hearing_ws:
                        await _send_safe(hearing_ws, {
                            "type":          "deaf_speech",
                            "text":          english,
                            "signs":         signs,
                            "sasl_original": sasl_text,
                        })
                        logger.info(f"[SASL→EN] '{sasl_text}' → '{english}'")
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
                    _sign_tasks[sessionId] = asyncio.create_task(
                        _debounce_and_flush(sessionId, session)
                    )
                await _broadcast(session, websocket, msg)
                await _broadcast_all(session, {"type": "turn", "speaker": "deaf"})
                continue

            # ── EMERGENCY — broadcast to ALL users in session ─────
            if msg.get("type") == "emergency":
                logger.warning(f"[WS] EMERGENCY triggered session={sessionId} by={role}")
                await _broadcast_all(session, msg)
                continue

            # ── SPEECH UPLOAD via WebSocket (base64 audio) ────────
            # Replaces direct fetch to POST /speech — keeps all
            # communication through the preload WS bridge.
            if msg.get("type") == "speech_upload":
                request_id = msg.get("request_id")
                try:
                    audio_b64 = msg.get("audio_b64", "")
                    if not audio_b64:
                        await _send_safe(websocket, {
                            "request_id": request_id,
                            "error": "Missing required field: audio_b64"
                        })
                        continue

                    # Decode base64 audio to raw bytes
                    audio_bytes = base64.b64decode(audio_b64)
                    if len(audio_bytes) > _MAX_AUDIO_BYTES:
                        await _send_safe(websocket, {
                            "request_id": request_id,
                            "error": "Audio file too large (max 10 MB)"
                        })
                        continue

                    mime_type = msg.get("mime_type", "audio/webm")
                    logger.info(f"[WS] speech_upload size={len(audio_bytes)} mime={mime_type}")

                    # Transcribe with Whisper
                    from backend.services.whisper_service import transcribe_audio
                    result = await transcribe_audio(audio_bytes, mime_type)
                    text = result.get("text", "").strip()

                    # Convert to SASL signs
                    sasl = await _text_to_sasl_signs(text)

                    # Reply to the sender with transcription result (includes request_id)
                    await _send_safe(websocket, {
                        "request_id":     request_id,
                        "text":           text,
                        "signs":          sasl["signs"],
                        "sasl_gloss":     sasl["text"],
                        "language":       result.get("language", "en"),
                        "confidence":     result.get("confidence", 0.0),
                    })

                    # Also broadcast signs to deaf window (NO request_id)
                    if sasl["signs"]:
                        signs_msg = {
                            "type":             "signs",
                            "signs":            sasl["signs"],
                            "text":             sasl["text"],
                            "original_english": text,
                            "language":         result.get("language"),
                            "session_id":       sessionId,
                        }
                        await _broadcast(session, websocket, signs_msg)
                        await _broadcast_all(session, {"type": "turn", "speaker": "hearing"})

                except Exception as speech_err:
                    logger.error(f"[WS] speech_upload error: {speech_err}")
                    await _send_safe(websocket, {
                        "request_id": request_id,
                        "error": "Speech processing failed. Try typing instead."
                    })
                continue

            # ── STATUS REQUEST via WebSocket ──────────────────────
            # Replaces direct fetch to GET /api/status
            if msg.get("type") == "status_request":
                request_id = msg.get("request_id")
                try:
                    qwen_alive = await _check_ollama()
                    whisper_ok = _check_whisper()
                    await _send_safe(websocket, {
                        "request_id": request_id,
                        "status":     "ok",
                        "qwen":       "alive" if qwen_alive else "dead",
                        "whisper":    "ready" if whisper_ok else "unavailable",
                        "sessions":   len(sessions),
                    })
                except Exception as status_err:
                    logger.error(f"[WS] status_request error: {status_err}")
                    await _send_safe(websocket, {
                        "request_id": request_id,
                        "error": "Status check failed"
                    })
                continue

            # ── RIGHTS ANALYSIS via WebSocket ─────────────────────
            # Replaces direct fetch to POST /rights/analyze
            if msg.get("type") == "rights_analyze":
                request_id = msg.get("request_id")
                try:
                    description = msg.get("description", "")
                    if not description:
                        await _send_safe(websocket, {
                            "request_id": request_id,
                            "error": "Missing required field: description"
                        })
                        continue

                    incident_type = msg.get("incident_type", "workplace")
                    from backend.services.claude_service import analyse_incident
                    result = await analyse_incident(description, incident_type)
                    await _send_safe(websocket, {
                        "request_id": request_id,
                        **result,
                    })
                except Exception as rights_err:
                    logger.error(f"[WS] rights_analyze error: {rights_err}")
                    await _send_safe(websocket, {
                        "request_id": request_id,
                        "error": "Rights analysis failed. Please try again."
                    })
                continue

            # ── RIGHTS LETTER via WebSocket ───────────────────────
            # Replaces direct fetch to POST /rights/letter
            if msg.get("type") == "rights_letter":
                request_id = msg.get("request_id")
                try:
                    description = msg.get("description", "")
                    employer_name = msg.get("employer_name", "")
                    incident_date = msg.get("incident_date", "")
                    if not description or not employer_name or not incident_date:
                        missing = []
                        if not description:   missing.append("description")
                        if not employer_name: missing.append("employer_name")
                        if not incident_date: missing.append("incident_date")
                        await _send_safe(websocket, {
                            "request_id": request_id,
                            "error": f"Missing required fields: {', '.join(missing)}"
                        })
                        continue

                    user_name = msg.get("user_name", "The Complainant")
                    analysis = msg.get("analysis")
                    from backend.services.claude_service import generate_rights_letter
                    result = await generate_rights_letter(
                        incident_description=description,
                        user_name=user_name,
                        employer_name=employer_name,
                        incident_date=incident_date,
                        analysis=analysis or {},
                    )
                    await _send_safe(websocket, {
                        "request_id": request_id,
                        **result,
                    })
                except Exception as letter_err:
                    logger.error(f"[WS] rights_letter error: {letter_err}")
                    await _send_safe(websocket, {
                        "request_id": request_id,
                        "error": "Letter generation failed. Please try again."
                    })
                continue

            # Everything else: forward to other role(s)
            await _broadcast(session, websocket, msg)

    except WebSocketDisconnect:
        logger.info(f"[WS] disconnect session={sessionId} role={role}")
    except Exception as e:
        logger.error(f"[WS] error session={sessionId} role={role}: {e}")
    finally:
        # Safe session cleanup — wrapped in try/except to avoid race conditions
        # when both windows disconnect simultaneously
        try:
            session["users"].pop(role, None)
            if not session["users"] and not session["queue"]:
                sessions.pop(sessionId, None)
                logger.info(f"[WS] session {sessionId} cleaned up")
        except Exception as cleanup_err:
            logger.warning(f"[WS] cleanup error session={sessionId}: {cleanup_err}")


async def _send_safe(ws, msg: dict):
    """Send a JSON message to a single WebSocket, swallowing errors."""
    try:
        await ws.send_json(msg)
    except Exception:
        pass


async def _broadcast(session: dict, sender_ws, msg: dict):
    """Send msg to all users in session except sender (parallel)."""
    targets = [ws for ws in session["users"].values() if ws is not sender_ws]
    if targets:
        await asyncio.gather(*(_send_safe(ws, msg) for ws in targets))


async def _broadcast_all(session: dict, msg: dict):
    """Send msg to every user in session including sender (parallel)."""
    targets = list(session["users"].values())
    if targets:
        await asyncio.gather(*(_send_safe(ws, msg) for ws in targets))


# ── SENTENCE → SIGNS ──────────────────────────────────────

# Import canonical maps from shared module (single source of truth)
from backend.services.sign_maps import sentence_to_sign_names
