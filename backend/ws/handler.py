"""WebSocket handler for AMANDLA real-time communication.

Handles the main /ws/{sessionId}/{role} endpoint and dispatches
all incoming message types to their respective handlers.

WebSocket message types handled:
  text / speech_text — hearing user typed/spoke → SASL pipeline → deaf
  landmarks          — MediaPipe hand landmarks → Ollama sign recognition
  sasl_text          — deaf user typed SASL → English reconstruction → hearing
  assist_phrase      — assist-mode English phrase → forward to hearing
  sign               — deaf quick-sign button → buffer + broadcast
  emergency          — broadcast emergency alert to all session users
  speech_upload      — base64 audio → Whisper → SASL pipeline → deaf
  status_request     — AI service health check
  rights_analyze     — incident → rights analysis
  rights_letter      — details → formal complaint letter
"""

import asyncio
import base64
import json
import logging
import time as _time

from fastapi import WebSocket, WebSocketDisconnect

from backend.shared import (
    sessions,
    sign_buffers,
    sign_tasks,
    last_heavy_call,
    sanitise_text,
    check_rate_limit,
    verify_session_token,
    acquire_ws_connection,
    release_ws_connection,
    MAX_AUDIO_BYTES,
    MAX_CONCURRENT_SESSIONS,
)
from backend.ws.helpers import send_safe, broadcast, broadcast_all, get_role_ws

logger = logging.getLogger(__name__)

# Valid WebSocket roles
_VALID_ROLES = {"hearing", "deaf", "rights", "interpreter"}


async def websocket_endpoint(
    websocket: WebSocket,
    sessionId: str,
    role: str,
):
    """Main WebSocket endpoint for real-time communication.

    Token is passed via the Sec-WebSocket-Protocol header (not the URL query
    string) to prevent the secret from appearing in server access logs (ARCH-7).

    Args:
        websocket: The WebSocket connection.
        sessionId: The session identifier shared between hearing + deaf windows.
        role:      One of 'hearing', 'deaf', or 'rights'.
    """
    # ── Token extraction from WebSocket subprotocols (ARCH-7) ────────────
    # Client sends: new WebSocket(url, ['amandla-<TOKEN>'])
    # ASGI stores negotiated subprotocols in scope["subprotocols"] — this is
    # the canonical source in Starlette 0.20+. The raw Sec-WebSocket-Protocol
    # header is consumed by uvicorn and may not appear in websocket.headers.
    _token = ""
    _accepted_subprotocol = None

    # Primary: ASGI scope["subprotocols"]
    for _proto in websocket.scope.get("subprotocols", []):
        if _proto.startswith("amandla-"):
            _token = _proto[len("amandla-"):]
            _accepted_subprotocol = _proto
            break

    # Fallback: raw Sec-WebSocket-Protocol header (older uvicorn versions)
    if not _token:
        _protocol_header = websocket.headers.get("sec-websocket-protocol", "")
        for _part in _protocol_header.split(","):
            _part = _part.strip()
            if _part.startswith("amandla-"):
                _token = _part[len("amandla-"):]
                _accepted_subprotocol = _part
                break

    # ── Token validation ─────────────────────────────────────────────────
    if not verify_session_token(_token):
        await websocket.close(code=1008, reason="Invalid or missing session token")
        logger.warning("[WS] Rejected connection — bad token session=%s role=%s", sessionId, role)
        return

    # Validate role before accepting
    if role not in _VALID_ROLES:
        await websocket.close(code=1008, reason=f"Invalid role '{role}'")
        logger.warning("[WS] Rejected connection — invalid role='%s' session=%s", role, sessionId)
        return

    # ── Per-IP connection rate limit (FIX-5) ──────────────────────────
    _client_ip = websocket.client.host if websocket.client else "unknown"
    if not acquire_ws_connection(_client_ip):
        await websocket.close(code=1008, reason="Too many connections from this address")
        logger.warning(
            "[WS] Rejected connection — per-IP limit reached ip=%s session=%s",
            _client_ip, sessionId,
        )
        return

    # ── Concurrent session cap ─────────────────────────────────────────
    if sessionId not in sessions and len(sessions) >= MAX_CONCURRENT_SESSIONS:
        release_ws_connection(_client_ip)
        await websocket.close(code=1013, reason="Too many active sessions")
        logger.warning(
            "[WS] Rejected connection — concurrent session limit (%d) reached, session=%s",
            MAX_CONCURRENT_SESSIONS, sessionId,
        )
        return

    await websocket.accept(subprotocol=_accepted_subprotocol)
    logger.info("[WS] connect session=%s role=%s", sessionId, role)

    session = sessions.setdefault(sessionId, {"users": {}, "queue": []})

    # FEAT-8: hearing supports multiple simultaneous connections (multiple staff).
    # All other roles allow only one connection; a second replaces the stale one.
    if role == "hearing":
        existing = session["users"].get("hearing")
        if existing is None:
            session["users"]["hearing"] = websocket
        elif isinstance(existing, list):
            existing.append(websocket)
            logger.info("[WS] Added hearing connection #%d in session %s", len(existing), sessionId)
        else:
            # Upgrade single socket to list
            session["users"]["hearing"] = [existing, websocket]
            logger.info("[WS] Multiple hearing staff joined session %s", sessionId)
    else:
        if role in session["users"]:
            logger.warning("[WS] Role '%s' already taken in session %s — replacing stale connection", role, sessionId)
        session["users"][role] = websocket

    # ARCH-6: track session metadata (fire-and-forget, must not block connection)
    try:
        from backend.services.history_db import upsert_session
        await upsert_session(sessionId, role)
    except Exception:
        pass

    try:
        await websocket.send_json({"type": "status", "status": "connected", "session_id": sessionId})

        while True:
            data = await websocket.receive_text()
            logger.debug("[WS] recv session=%s role=%s len=%d", sessionId, role, len(data))

            try:
                msg = json.loads(data)
            except Exception:
                msg = {"type": "raw", "data": data}

            msg_type = msg.get("type")

            # ── INTERPRETER: read-only role — only status_request allowed ─
            # Interpreters observe all broadcasts but cannot inject messages.
            if role == "interpreter":
                if msg_type == "status_request":
                    await _handle_status_request(websocket, msg)
                # All other message types silently ignored for interpreter
                continue

            # ── HEARING TEXT → SASL SIGNS → DEAF ──────────────────────
            if msg_type in ("text", "speech_text") and role == "hearing":
                await _handle_text(websocket, session, sessionId, msg)
                continue

            # ── MEDIAPIPE LANDMARKS → SIGN RECOGNITION ────────────────
            if msg_type == "landmarks" and role == "deaf":
                await _handle_landmarks(websocket, session, sessionId, msg)
                continue

            # ── DEAF SASL TEXT → ENGLISH → HEARING ────────────────────
            if msg_type == "sasl_text" and role == "deaf":
                await _handle_sasl_text(session, sessionId, msg)
                continue

            # ── ASSIST-MODE PHRASE → HEARING ──────────────────────────
            if msg_type == "assist_phrase" and role == "deaf":
                await _handle_assist_phrase(session, sessionId, msg)
                continue

            # ── DEAF QUICK-SIGN BUTTON ────────────────────────────────
            if msg_type == "sign" and role == "deaf":
                await _handle_sign(websocket, session, sessionId, msg)
                continue

            # ── EMERGENCY ─────────────────────────────────────────────
            if msg_type == "emergency":
                logger.warning("[WS] EMERGENCY triggered session=%s by=%s", sessionId, role)
                await broadcast_all(session, msg)
                continue

            # ── SPEECH UPLOAD (base64 audio via WebSocket) ────────────
            if msg_type == "speech_upload":
                await _handle_speech_upload(websocket, session, sessionId, msg)
                continue

            # ── STATUS REQUEST ────────────────────────────────────────
            if msg_type == "status_request":
                await _handle_status_request(websocket, msg)
                continue

            # ── RIGHTS ANALYSIS ───────────────────────────────────────
            if msg_type == "rights_analyze":
                await _handle_rights_analyze(websocket, sessionId, msg)
                continue

            # ── RIGHTS LETTER ─────────────────────────────────────────
            if msg_type == "rights_letter":
                await _handle_rights_letter(websocket, sessionId, msg)
                continue

            # ── CONVERSATION HISTORY REQUEST ──────────────────────────
            if msg_type == "history_request":
                await _handle_history_request(websocket, sessionId, msg)
                continue

            # ── SPEECH ASSIST: correct garbled speech (hearing side only) ─
            if msg_type == "speech_correct" and role == "hearing":
                await _handle_speech_correct(websocket, sessionId, msg)
                continue

            # Everything else: forward to other role(s)
            await broadcast(session, websocket, msg)

    except WebSocketDisconnect:
        logger.info("[WS] disconnect session=%s role=%s", sessionId, role)
    except Exception as exc:
        logger.error("[WS] error session=%s role=%s: %s", sessionId, role, exc)
    finally:
        release_ws_connection(_client_ip)
        _cleanup_session(sessionId, role, session, websocket)


# ── MESSAGE HANDLERS ──────────────────────────────────────────────────────────

async def _handle_text(websocket, session, session_id, msg):
    """Handle text/speech_text from hearing user → SASL signs → deaf window."""
    from backend.services.sasl_pipeline import text_to_sasl_signs

    text = sanitise_text(msg.get("text", ""))
    language = msg.get("language")

    # Tell the deaf window that translation is in progress
    deaf_ws = get_role_ws(session, "deaf")
    if deaf_ws:
        await send_safe(deaf_ws, {"type": "translating", "session_id": session_id})

    sasl = await text_to_sasl_signs(text, language=language)
    out = {
        "type":             "signs",
        "signs":            sasl["signs"],
        "text":             sasl["text"],
        "original_english": sasl["original_english"],
        "language":         language,
        "source_language":  sasl.get("source_language"),
        "original_input":   sasl.get("original_input"),
        "session_id":       session_id,
        "non_manual_markers": sasl.get("non_manual_markers", []),
    }
    await broadcast(session, websocket, out)
    await broadcast_all(session, {"type": "turn", "speaker": "hearing"})

    # FEAT-3: Log to conversation history
    try:
        from backend.services.history_db import log_message
        await log_message(
            session_id=session_id,
            direction="hearing_to_deaf",
            original_text=text,
            sasl_gloss=sasl.get("text", ""),
            translated_text=" ".join(sasl.get("signs", [])),
            source="text",
        )
    except Exception as e:
        logger.warning("[History] Failed to log message: %s", e)
        # History failure must never break the main flow

    # Send SASL gloss acknowledgement back to the hearing user
    await send_safe(websocket, {
        "type":             "sasl_ack",
        "sasl_gloss":       sasl["text"],
        "original_english": text,
        "source_language":  sasl.get("source_language"),
        "original_input":   sasl.get("original_input"),
    })


async def _handle_landmarks(websocket, session, session_id, msg):
    """Handle MediaPipe hand landmarks → Ollama sign recognition.

    Debounces recognised signs into the shared sign buffer so the same
    reconstruction path is used whether the sign came from a quick-sign
    button or from the camera.
    """
    landmarks = msg.get("landmarks", [])
    handedness_raw = msg.get("handedness", "Right")
    if not landmarks:
        return

    # Normalise handedness to a list of strings (HARPS expects ["Left","Right"])
    if isinstance(handedness_raw, str):
        handedness_list = [handedness_raw]
    elif isinstance(handedness_raw, list):
        handedness_list = handedness_raw
    else:
        handedness_list = ["Right"]

    result = None
    method = "unknown"

    # ── Ollama LLM sign recognition (HARPS-1: synthetic ML model removed) ──
    # The HARPS model was trained on synthetic demo data (SIGN_00–SIGN_20)
    # and had ~0% real-world accuracy. Ollama provides better results until
    # real SASL training data is collected (future funded phase).
    try:
        from backend.services.ollama_service import recognize_sign
        result = await recognize_sign({
            "landmarks": landmarks,
            "handedness": handedness_raw,
        })
        method = result.get("method", "ollama") if result else "unknown"
    except Exception as ollama_exc:
        logger.warning("[WS] Landmark recognition error: %s", ollama_exc)
        return

    if result is None:
        return

    sign_name = result.get("sign", "UNKNOWN")
    confidence = result.get("confidence", 0.0)
    min_confidence = 0.5

    if sign_name != "UNKNOWN" and confidence >= min_confidence:
        from backend.services.sign_reconstruction import debounce_and_flush

        # Route into the debounce buffer (same path as quick-sign buttons)
        existing = sign_tasks.get(session_id)
        if existing and not existing.done():
            existing.cancel()
        sign_buffers.setdefault(session_id, []).append(sign_name)
        sign_tasks[session_id] = asyncio.create_task(
            debounce_and_flush(session_id, session)
        )

        # Echo back to deaf window for confirmation overlay
        try:
            await websocket.send_json({
                "type":       "sign",
                "text":       sign_name,
                "confidence": confidence,
                "sender":     "deaf",
                "source":     method,
            })
        except Exception:
            pass
        await broadcast_all(session, {"type": "turn", "speaker": "deaf"})


async def _handle_sasl_text(session, session_id, msg):
    """Handle deaf-typed SASL text → English reconstruction → hearing."""
    from backend.services.sign_reconstruction import (
        split_sasl_gloss, signs_to_english, simple_signs_to_english,
    )

    sasl_text = sanitise_text(msg.get("text", "")).strip()
    if not sasl_text:
        return

    hearing_ws = get_role_ws(session, "hearing")

    # Step 1: immediately tell hearing a message is coming
    if hearing_ws:
        await send_safe(hearing_ws, {
            "type":   "sasl_text",
            "text":   sasl_text,
            "sender": "deaf",
        })
    await broadcast_all(session, {"type": "turn", "speaker": "deaf"})

    # Step 2: translate — use longest-match splitter for multi-word signs (BUG-1 fix)
    signs = split_sasl_gloss(sasl_text)
    sasl_to_english_timeout_s = 6.0
    try:
        english = await asyncio.wait_for(signs_to_english(signs), timeout=sasl_to_english_timeout_s)
    except asyncio.TimeoutError:
        english = simple_signs_to_english(signs)
        logger.warning("[SASL→EN] Timeout — using rule-based: %r", signs)

    # Step 3: send translated English to hearing
    if english and hearing_ws:
        await send_safe(hearing_ws, {
            "type":          "deaf_speech",
            "text":          english,
            "signs":         signs,
            "sasl_original": sasl_text,
        })
        logger.info("[SASL→EN] '%s' → '%s'", sasl_text, english)

        # FEAT-3: Log to conversation history
        try:
            from backend.services.history_db import log_message
            await log_message(
                session_id=session_id,
                direction="deaf_to_hearing",
                original_text=sasl_text,
                sasl_gloss=" ".join(signs),
                translated_text=english,
                source="text",
            )
        except Exception as e:
            logger.warning("[History] Failed to log message: %s", e)
            # History failure must never break the main flow


async def _handle_assist_phrase(session, session_id, msg):
    """Handle assist-mode English phrase → forward directly to hearing.

    BUG-2 fix: Assist phrases are already natural English — no SASL reconstruction.

    Args:
        session:    The current session dict.
        session_id: The session identifier (needed for history logging).
        msg:        The incoming message dict with 'text' field.
    """
    phrase = sanitise_text(msg.get("text", "")).strip()
    if not phrase:
        return
    hearing_ws = get_role_ws(session, "hearing")
    await broadcast_all(session, {"type": "turn", "speaker": "deaf"})
    if hearing_ws:
        await send_safe(hearing_ws, {
            "type":   "deaf_speech",
            "text":   phrase,
            "source": "assist",
        })
        logger.info("[AssistPhrase] Forwarded to hearing: %r", phrase)

        # FEAT-3: Log assist-mode phrase to conversation history
        try:
            from backend.services.history_db import log_message
            await log_message(
                session_id=session_id,
                direction="deaf_to_hearing",
                original_text=phrase,
                sasl_gloss="",
                translated_text=phrase,
                source="assist",
            )
        except Exception as e:
            logger.warning("[History] Failed to log message: %s", e)
            # History failure must never break the main flow


async def _handle_sign(websocket, session, session_id, msg):
    """Handle deaf quick-sign button → buffer for English reconstruction + forward."""
    from backend.services.sign_reconstruction import debounce_and_flush

    sign_text = sanitise_text(msg.get("text", ""))
    # Buffer non-emergency signs for reconstruction
    if sign_text and sign_text != "EMERGENCY":
        existing = sign_tasks.get(session_id)
        if existing and not existing.done():
            existing.cancel()
        sign_buffers.setdefault(session_id, []).append(sign_text)
        sign_tasks[session_id] = asyncio.create_task(
            debounce_and_flush(session_id, session)
        )
    await broadcast(session, websocket, msg)
    await broadcast_all(session, {"type": "turn", "speaker": "deaf"})


async def _handle_speech_upload(websocket, session, session_id, msg):
    """Handle base64 audio upload via WebSocket → Whisper → SASL → deaf."""
    from backend.services.sasl_pipeline import text_to_sasl_signs

    request_id = msg.get("request_id")

    # Rate-limit: prevent flooding Whisper
    if not check_rate_limit(session_id, "speech_upload"):
        await send_safe(websocket, {
            "request_id": request_id,
            "error": "Too many requests — please wait a moment before trying again.",
        })
        return

    try:
        audio_b64 = msg.get("audio_b64", "")
        if not audio_b64:
            await send_safe(websocket, {
                "request_id": request_id,
                "error": "Missing required field: audio_b64",
            })
            return

        audio_bytes = base64.b64decode(audio_b64)
        if len(audio_bytes) > MAX_AUDIO_BYTES:
            await send_safe(websocket, {
                "request_id": request_id,
                "error": "Audio file too large (max 10 MB)",
            })
            return

        mime_type = msg.get("mime_type", "audio/webm")
        logger.info("[WS] speech_upload size=%d mime=%s", len(audio_bytes), mime_type)

        # Tell deaf window that translation is in progress
        deaf_ws = get_role_ws(session, "deaf")
        if deaf_ws:
            await send_safe(deaf_ws, {"type": "translating", "session_id": session_id})

        # Transcribe with Whisper
        from backend.services.whisper_service import transcribe_audio
        result = await transcribe_audio(audio_bytes, mime_type)
        text = result.get("text", "").strip()
        detected_language = result.get("language", "en")

        # If the user manually selected a language (e.g. one of the 5 SA languages
        # Whisper cannot auto-detect), use that override for the SASL pipeline.
        manual_language = msg.get("language")
        pipeline_language = manual_language if manual_language else detected_language

        # Convert to SASL signs (FEAT-5: pass language for pre-translation)
        sasl = await text_to_sasl_signs(text, language=pipeline_language)

        # Reply to the sender with transcription result (includes request_id)
        await send_safe(websocket, {
            "request_id":      request_id,
            "text":            text,
            "signs":           sasl["signs"],
            "sasl_gloss":      sasl["text"],
            "language":        detected_language,
            "confidence":      result.get("confidence", 0.0),
            "source_language": sasl.get("source_language"),
            "original_input":  sasl.get("original_input"),
        })

        # FEAT-3: Log speech upload to conversation history
        try:
            from backend.services.history_db import log_message
            await log_message(
                session_id=session_id,
                direction="hearing_to_deaf",
                original_text=text,
                sasl_gloss=sasl.get("text", ""),
                translated_text=" ".join(sasl.get("signs", [])),
                source="speech",
            )
        except Exception as e:
            logger.warning("[History] Failed to log message: %s", e)
            # History failure must never break the main flow

        # Also broadcast signs to deaf window (NO request_id)
        if sasl["signs"]:
            signs_msg = {
                "type":             "signs",
                "signs":            sasl["signs"],
                "text":             sasl["text"],
                "original_english": sasl.get("original_english", text),
                "language":         detected_language,
                "source_language":  sasl.get("source_language"),
                "original_input":   sasl.get("original_input"),
                "session_id":       session_id,
                "non_manual_markers": sasl.get("non_manual_markers", []),
            }
            await broadcast(session, websocket, signs_msg)
            await broadcast_all(session, {"type": "turn", "speaker": "hearing"})

    except Exception as speech_err:
        logger.error("[WS] speech_upload error: %s", speech_err)
        await send_safe(websocket, {
            "request_id": request_id,
            "error": "Speech processing failed. Try typing instead.",
        })


async def _handle_status_request(websocket, msg):
    """Handle status request → return AI service health."""
    from backend.routers.health import _check_ollama, _check_whisper

    request_id = msg.get("request_id")
    try:
        qwen_alive = await _check_ollama()
        whisper_ok = _check_whisper()
        await send_safe(websocket, {
            "request_id": request_id,
            "status":     "ok",
            "qwen":       "alive" if qwen_alive else "dead",
            "whisper":    "ready" if whisper_ok else "unavailable",
            "sessions":   len(sessions),
        })
    except Exception as status_err:
        logger.error("[WS] status_request error: %s", status_err)
        await send_safe(websocket, {
            "request_id": request_id,
            "error": "Status check failed",
        })


async def _handle_rights_analyze(websocket, session_id, msg):
    """Handle rights analysis request via WebSocket."""
    request_id = msg.get("request_id")

    if not check_rate_limit(session_id, "rights_analyze"):
        await send_safe(websocket, {
            "request_id": request_id,
            "error": "Too many requests — please wait a moment before trying again.",
        })
        return

    try:
        description = sanitise_text(msg.get("description", ""))
        if not description:
            await send_safe(websocket, {
                "request_id": request_id,
                "error": "Missing required field: description",
            })
            return

        # Whitelist incident_type to prevent prompt injection into Ollama (ARCH-8)
        # Values must match the <option value="..."> attributes in rights/index.html
        _VALID_INCIDENT_TYPES = {"workplace", "hospital", "school", "public", "housing", "other"}
        incident_type = sanitise_text(msg.get("incident_type", "workplace"))
        if incident_type not in _VALID_INCIDENT_TYPES:
            incident_type = "workplace"

        from backend.services.claude_service import analyse_incident
        result = await analyse_incident(description, incident_type)
        await send_safe(websocket, {
            "request_id": request_id,
            **result,
        })
    except Exception as rights_err:
        logger.error("[WS] rights_analyze error: %s", rights_err)
        await send_safe(websocket, {
            "request_id": request_id,
            "error": "Rights analysis failed. Please try again.",
        })


async def _handle_rights_letter(websocket, session_id, msg):
    """Handle rights letter generation request via WebSocket."""
    request_id = msg.get("request_id")

    if not check_rate_limit(session_id, "rights_letter"):
        await send_safe(websocket, {
            "request_id": request_id,
            "error": "Too many requests — please wait a moment before trying again.",
        })
        return

    try:
        description = sanitise_text(msg.get("description", ""))
        employer_name = sanitise_text(msg.get("employer_name", ""))
        incident_date = sanitise_text(msg.get("incident_date", ""))

        if not description or not employer_name or not incident_date:
            missing = []
            if not description:   missing.append("description")
            if not employer_name: missing.append("employer_name")
            if not incident_date: missing.append("incident_date")
            await send_safe(websocket, {
                "request_id": request_id,
                "error": f"Missing required fields: {', '.join(missing)}",
            })
            return

        user_name = sanitise_text(msg.get("user_name", "The Complainant"))
        analysis = msg.get("analysis")
        from backend.services.claude_service import generate_rights_letter
        result = await generate_rights_letter(
            incident_description=description,
            user_name=user_name,
            employer_name=employer_name,
            incident_date=incident_date,
            analysis=analysis or {},
        )
        await send_safe(websocket, {
            "request_id": request_id,
            **result,
        })
    except Exception as letter_err:
        logger.error("[WS] rights_letter error: %s", letter_err)
        await send_safe(websocket, {
            "request_id": request_id,
            "error": "Letter generation failed. Please try again.",
        })


async def _handle_history_request(websocket, session_id, msg):
    """Handle conversation history request via WebSocket.

    Returns the stored conversation history for the given session,
    or for a different session if session_id is provided in the message.

    Args:
        websocket:  The requesting WebSocket connection.
        session_id: The current session identifier (used as default).
        msg:        The incoming message dict with optional session_id override.
    """
    from backend.services.history_db import get_session_history, get_all_sessions

    request_id = msg.get("request_id")
    target_session = msg.get("session_id", session_id)
    limit = min(msg.get("limit", 100), 500)  # Cap at 500 to prevent abuse

    # Security: only allow reading another session when listing sessions.
    # A regular history fetch must always use the caller's own session_id.
    if not msg.get("list_sessions") and target_session != session_id:
        await send_safe(websocket, {
            "request_id": request_id,
            "type":       "history_response",
            "error":      "You can only view your own session history.",
        })
        return

    try:
        if msg.get("list_sessions"):
            # Return a list of all sessions with message counts
            session_list = await get_all_sessions()
            await send_safe(websocket, {
                "request_id": request_id,
                "type":       "history_response",
                "sessions":   session_list,
            })
        else:
            # Return messages for a specific session
            messages = await get_session_history(target_session, limit)
            await send_safe(websocket, {
                "request_id": request_id,
                "type":       "history_response",
                "session_id": target_session,
                "messages":   messages,
            })
    except Exception as hist_err:
        logger.error("[WS] history_request error: %s", hist_err)
        await send_safe(websocket, {
            "request_id": request_id,
            "error": "Failed to retrieve conversation history.",
        })


async def _handle_speech_correct(websocket, session_id, msg):
    """Correct garbled speech/text for hearing users with speech impediments.

    This handler is ONLY called for the hearing role and NEVER broadcasts
    to the deaf window. The corrected text is returned only to the sender.

    Uses Ollama to clean up incomplete or mis-articulated text so the hearing
    person can communicate clearly with other hearing people around them.

    Args:
        websocket:  The requesting WebSocket (hearing role).
        session_id: The current session identifier.
        msg:        Message with 'text' field containing the garbled input.
    """
    request_id = msg.get("request_id")
    raw_text = sanitise_text(msg.get("text", ""))

    if not raw_text:
        await send_safe(websocket, {
            "request_id": request_id,
            "type": "speech_corrected",
            "error": "No text to correct.",
        })
        return

    if not check_rate_limit(session_id, "speech_correct"):
        await send_safe(websocket, {
            "request_id": request_id,
            "type": "speech_corrected",
            "error": "Too many requests — please wait a moment.",
        })
        return

    _SPEECH_CORRECT_SYSTEM = (
        "You are a speech correction assistant helping someone with a speech impediment "
        "or articulation difficulty communicate clearly. "
        "The user's input may be incomplete, garbled, have missing words, or unusual phrasing. "
        "Correct it into clear, natural English that preserves the original meaning. "
        "Return ONLY the corrected sentence — no explanation, no quotation marks, no extra text."
    )

    try:
        import os
        _ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        _model = os.getenv("OLLAMA_MODEL", "amandla")

        from backend.services.ollama_pool import get_client
        client = get_client()
        response = await client.post(
            f"{_ollama_base}/api/generate",
            json={
                "model":       _model,
                "prompt":      f"Correct this speech: {raw_text}",
                "system":      _SPEECH_CORRECT_SYSTEM,
                "stream":      False,
                "temperature": 0.2,
            },
            timeout=10.0,
        )

        if response.status_code != 200:
            raise RuntimeError(f"Ollama HTTP {response.status_code}")

        corrected = response.json().get("response", "").strip()
        if not corrected:
            corrected = raw_text  # fall back to original if Ollama returns nothing

        logger.info("[Speech Assist] session=%s: '%s' → '%s'", session_id, raw_text[:60], corrected[:60])

        await send_safe(websocket, {
            "request_id": request_id,
            "type":       "speech_corrected",
            "original":   raw_text,
            "corrected":  corrected,
        })

    except Exception as exc:
        logger.warning("[Speech Assist] correction failed: %s — returning original", exc)
        # On any failure, return the original text so the user is not left empty-handed
        await send_safe(websocket, {
            "request_id": request_id,
            "type":       "speech_corrected",
            "original":   raw_text,
            "corrected":  raw_text,
            "fallback":   True,
        })


# ── SESSION CLEANUP ───────────────────────────────────────────────────────────

def _cleanup_session(session_id: str, role: str, session: dict, websocket=None) -> None:
    """Clean up session state when a WebSocket disconnects.

    Handles:
      - Removing the role from the session users
      - Cancelling pending sign-reconstruction tasks for deaf disconnects
      - Marking empty sessions for the reaper
      - Immediate cleanup of fully empty sessions

    Args:
        session_id: The WebSocket session identifier.
        role:       The role that disconnected ('hearing', 'deaf', 'rights').
        session:    The session dict.
    """
    try:
        # FEAT-8: hearing may have multiple sockets — remove only this one
        existing = session["users"].get(role)
        if isinstance(existing, list):
            if websocket is not None:
                try:
                    existing.remove(websocket)
                except ValueError:
                    pass
            if not existing:
                del session["users"][role]
        else:
            session["users"].pop(role, None)

        # If the deaf user disconnects, cancel pending sign-reconstruction task
        if role == "deaf":
            pending_task = sign_tasks.pop(session_id, None)
            if pending_task and not pending_task.done():
                pending_task.cancel()
            sign_buffers.pop(session_id, None)

        if not session["users"]:
            # Record when the session became empty so the reaper can expire it later
            session["_empty_since"] = _time.monotonic()

            # ARCH-6: mark session closed in the metadata table
            try:
                import asyncio as _asyncio
                from backend.services.history_db import close_session as _close_session
                _asyncio.ensure_future(_close_session(session_id))
            except Exception:
                pass

            # Clean up rate-limit tracking for this session
            last_heavy_call.pop(session_id, None)

            # Clean up sign tasks/buffers if not already done by the deaf block
            if role != "deaf":
                pending_task = sign_tasks.pop(session_id, None)
                if pending_task and not pending_task.done():
                    pending_task.cancel()
                sign_buffers.pop(session_id, None)

            # Remove session immediately if it has no queued messages
            if not session.get("queue"):
                sessions.pop(session_id, None)
                logger.info("[WS] session '%s' cleaned up immediately", session_id)
        else:
            logger.info(
                "[WS] role '%s' left session '%s' (%d still connected)",
                role, session_id, len(session["users"]),
            )
    except Exception as cleanup_err:
        logger.warning("[WS] cleanup error session=%s: %s", session_id, cleanup_err)

