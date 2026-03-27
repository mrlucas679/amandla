"""
Whisper Speech-to-Text Service
Primary: faster-whisper (local, no API key needed).
Fallback: NVIDIA Parakeet via NIM API (activates when NVIDIA_ENABLED=true and Whisper times out).
Model is lazy-loaded on first use to avoid hanging startup.
"""
import os
import time
import tempfile
import asyncio
import subprocess
import logging

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE     = os.getenv("WHISPER_DEVICE", "cpu")
NVIDIA_ENABLED     = os.getenv("NVIDIA_ENABLED", "false").lower() == "true"
NVIDIA_API_KEY     = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL    = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

WHISPER_TIMEOUT_S  = 120.0  # CPU transcription of short clips can take 30–60 s on 'small' model

# Lazy-loaded — None until first use
_model = None


def get_model():
    """Return the Whisper model, loading it on first call."""
    global _model
    if _model is not None:
        return _model
    try:
        from faster_whisper import WhisperModel
        logger.info(f"[Whisper] Loading model '{WHISPER_MODEL_SIZE}' on '{WHISPER_DEVICE}'…")
        _model = WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type="int8")
        logger.info("[Whisper] Model ready")
    except Exception as e:
        logger.warning(f"[Whisper] Could not load model: {e}")
        _model = None
    return _model


def convert_audio_to_wav(audio_bytes: bytes, mime_type: str = "audio/webm") -> bytes:
    """
    Convert any audio format (webm, ogg, mp4, wav) to 16 kHz mono wav for Whisper.
    Strips codec suffix from mime_type (e.g. 'audio/webm;codecs=opus' → 'audio/webm').
    """
    ext_map = {
        "audio/webm":  ".webm",
        "audio/ogg":   ".ogg",
        "audio/mp4":   ".mp4",
        "audio/mpeg":  ".mp3",
        "audio/wav":   ".wav",
        "audio/x-wav": ".wav",
    }
    base_mime = mime_type.split(";")[0].strip().lower()
    ext = ext_map.get(base_mime, ".webm")

    if ext == ".wav":
        return audio_bytes

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as inp:
        inp.write(audio_bytes)
        inp_path = inp.name

    out_path = inp_path[:-len(ext)] + ".wav"

    try:
        ffmpeg_exe = _get_ffmpeg()
        result = subprocess.run(
            [ffmpeg_exe, "-y", "-i", inp_path, "-ar", "16000", "-ac", "1", "-f", "wav", out_path],
            capture_output=True, timeout=20
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")
        with open(out_path, "rb") as f:
            return f.read()
    finally:
        for p in (inp_path, out_path):
            try:
                os.unlink(p)
            except Exception:
                pass


def _get_ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


async def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/webm") -> dict:
    """
    Full pipeline: convert audio → wav → Whisper transcription.
    Falls back to NVIDIA Parakeet if Whisper times out or fails and NVIDIA_ENABLED=true.
    Returns dict with 'text', 'language', 'confidence', 'duration_ms'.
    """
    start = time.time()
    loop = asyncio.get_running_loop()

    try:
        # Load model in executor so it never blocks the event loop
        model = await loop.run_in_executor(None, get_model)

        if model is None and not NVIDIA_ENABLED:
            return {
                "text": "",
                "language": "en",
                "confidence": 0.0,
                "error": "Whisper model not loaded and NVIDIA fallback disabled"
            }

        # Convert audio format in executor (may call ffmpeg)
        wav_bytes = await loop.run_in_executor(
            None, lambda: convert_audio_to_wav(audio_bytes, mime_type)
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
            tmp_path = tmp.name

        try:
            if model is None:
                raise RuntimeError("Whisper model unavailable")

            # Run transcription in executor with timeout.
            # IMPORTANT: consume the segment generator inside the executor —
            # faster-whisper returns a lazy generator; iterating it outside the
            # executor would block the event loop.
            def _run_transcription():
                segs_gen, inf = model.transcribe(tmp_path, beam_size=5)
                segs = list(segs_gen)   # force full computation here in the thread
                return segs, inf

            try:
                segments, info = await asyncio.wait_for(
                    loop.run_in_executor(None, _run_transcription),
                    timeout=WHISPER_TIMEOUT_S
                )
            except asyncio.TimeoutError:
                logger.warning(f"[Whisper] Transcription timed out after {WHISPER_TIMEOUT_S}s")
                raise TimeoutError("Whisper timeout")

            text = " ".join(seg.text.strip() for seg in segments)
            elapsed = time.time() - start
            logger.info(f"[Whisper] Transcribed in {elapsed:.2f}s: '{text[:60]}'")
            return {
                "text": text,
                "language": info.language,
                "confidence": 0.85,
                "duration_ms": int(elapsed * 1000),
                "engine": "whisper"
            }
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    except Exception as whisper_err:
        # ── NVIDIA PARAKEET FALLBACK ──────────────────────────
        if NVIDIA_ENABLED and NVIDIA_API_KEY:
            logger.info(f"[Whisper] Falling back to Parakeet — reason: {whisper_err}")
            try:
                return await _transcribe_parakeet(audio_bytes, mime_type)
            except Exception as parakeet_err:
                logger.error(f"[Parakeet] Fallback failed: {parakeet_err}")
                return {
                    "text": "",
                    "language": "en",
                    "confidence": 0.0,
                    "error": f"Whisper: {whisper_err} | Parakeet: {parakeet_err}"
                }
        else:
            logger.error(f"[Whisper] Transcription failed (no fallback): {whisper_err}")
            return {
                "text": "",
                "language": "en",
                "confidence": 0.0,
                "error": str(whisper_err)
            }


async def _transcribe_parakeet(audio_bytes: bytes, mime_type: str) -> dict:
    """
    Transcribe audio using NVIDIA Parakeet via NIM API (OpenAI-compatible).
    Only called when NVIDIA_ENABLED=true and Whisper fails/times out.
    """
    import httpx

    start = time.time()

    # Convert to wav for upload
    try:
        wav_bytes = convert_audio_to_wav(audio_bytes, mime_type)
    except Exception:
        wav_bytes = audio_bytes

    # Write temp file for upload
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            with open(tmp_path, "rb") as f:
                resp = await client.post(
                    f"{NVIDIA_BASE_URL}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {NVIDIA_API_KEY}"},
                    files={"file": ("audio.wav", f, "audio/wav")},
                    data={"model": "nvidia/parakeet-ctc-0.6b-asr"}
                )
            resp.raise_for_status()
            data = resp.json()

        text = data.get("text", "")
        elapsed = time.time() - start
        logger.info(f"[Parakeet] Transcribed in {elapsed:.2f}s: '{text[:60]}'")
        return {
            "text": text,
            "language": "en",
            "confidence": 0.90,
            "duration_ms": int(elapsed * 1000),
            "engine": "parakeet"
        }
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass