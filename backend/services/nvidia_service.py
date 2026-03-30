"""
NVIDIA NIM Service — fallback AI for AMANDLA.

Two capabilities:
  1. transcribe_with_parakeet(audio_bytes)
       Speech-to-text via NVIDIA Parakeet-CTC (1.1b).
       Called when Whisper fails or times out and NVIDIA_ENABLED=true.

  2. generate_with_nim(prompt, system)
       Text generation via NVIDIA NIM (meta/llama-3.1-8b-instruct).
       Called when Ollama/Qwen fails and NVIDIA_ENABLED=true.

Both require NVIDIA_API_KEY in .env.
"""
import os
import tempfile
import logging
import httpx

# Note: dotenv is loaded once by backend.main at startup — do NOT call load_dotenv() here

logger = logging.getLogger(__name__)

NVIDIA_API_KEY  = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_ENABLED  = os.getenv("NVIDIA_ENABLED", "false").lower() == "true"


def is_available() -> bool:
    """True when NVIDIA integration is enabled and an API key is present."""
    return NVIDIA_ENABLED and bool(NVIDIA_API_KEY)


async def transcribe_with_parakeet(audio_bytes: bytes) -> dict:
    """
    Fallback speech-to-text using NVIDIA Parakeet-CTC via NIM API.
    Only called when Whisper fails/times-out and NVIDIA_ENABLED=true.

    Returns dict with 'text', 'language', 'confidence', 'engine'.
    Raises on API error so the caller can handle the failure.
    """
    if not NVIDIA_API_KEY:
        raise ValueError("NVIDIA_API_KEY not set in .env")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            with open(tmp_path, "rb") as audio_file:
                resp = await client.post(
                    f"{NVIDIA_BASE_URL}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {NVIDIA_API_KEY}"},
                    files={"file": ("audio.wav", audio_file, "audio/wav")},
                    data={"model": "nvidia/parakeet-ctc-1.1b"}
                )
            resp.raise_for_status()
            result = resp.json()

        text = result.get("text", "")
        logger.info(f"[NVIDIA Parakeet] Transcribed: '{text[:60]}'")
        return {
            "text":       text,
            "language":   "en",
            "confidence": 0.90,
            "engine":     "nvidia-parakeet"
        }
    except Exception as e:
        logger.error(f"[NVIDIA Parakeet] Error: {e}")
        raise
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


async def generate_with_nim(prompt: str, system: str = "") -> str:
    """
    Fallback text generation via NVIDIA NIM (meta/llama-3.1-8b-instruct).
    Used when Ollama/Qwen is unavailable and NVIDIA_ENABLED=true.

    Returns the generated text string.
    Raises on API error so the caller can fall back further.
    """
    if not NVIDIA_API_KEY:
        raise ValueError("NVIDIA_API_KEY not set in .env")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{NVIDIA_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model":      "meta/llama-3.1-8b-instruct",
                "messages":   messages,
                "max_tokens": 1000
            }
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        logger.info(f"[NVIDIA NIM] Generated {len(text)} chars")
        return text