"""
Ollama Sign Recognition Service
Uses the local amandla model to recognize SASL signs from landmark data
"""
import os
import json
import logging
import asyncio

# Note: dotenv is loaded once by backend.main at startup — do NOT call load_dotenv() here

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "amandla")

_LANDMARK_NAMES = [
    "WRIST", "THUMB_CMC", "THUMB_MCP", "THUMB_IP", "THUMB_TIP",
    "INDEX_FINGER_MCP", "INDEX_FINGER_PIP", "INDEX_FINGER_DIP", "INDEX_FINGER_TIP",
    "MIDDLE_FINGER_MCP", "MIDDLE_FINGER_PIP", "MIDDLE_FINGER_DIP", "MIDDLE_FINGER_TIP",
    "RING_FINGER_MCP", "RING_FINGER_PIP", "RING_FINGER_DIP", "RING_FINGER_TIP",
    "PINKY_MCP", "PINKY_PIP", "PINKY_DIP", "PINKY_TIP",
]

# Landmark index constants — MediaPipe hand model (21 points).
_WRIST       = 0
_THUMB_TIP   = 4;  _THUMB_MCP   = 2
_INDEX_TIP   = 8;  _INDEX_MCP   = 5
_MIDDLE_TIP  = 12; _MIDDLE_MCP  = 9
_RING_TIP    = 16; _RING_MCP    = 13
_PINKY_TIP   = 20; _PINKY_MCP   = 17
_INDEX_PIP   = 6;  _MIDDLE_PIP  = 10
_RING_PIP    = 14; _PINKY_PIP   = 18


def _extract_features(landmarks: list) -> str:
    """Convert raw MediaPipe landmarks to a plain-English feature description.

    Raw x,y,z coordinates are meaningless to an LLM. This function computes
    geometric features — finger extension, thumb position, palm orientation,
    finger spread — and returns them as a readable string the model can
    classify against its list of known SASL signs.

    MediaPipe coordinate system:
        x: 0 (left) → 1 (right)
        y: 0 (top)  → 1 (bottom)  — NOTE: y increases downward
        z: depth (negative = toward camera)

    Args:
        landmarks: List of 21 dicts with 'x', 'y', 'z' keys (normalised 0–1).

    Returns:
        Plain-English feature string (e.g. "Index: extended. Middle: extended.
        Ring: curled. Pinky: curled. Thumb: abducted. Palm: facing camera.
        Fingers: spread.")
    """
    if len(landmarks) < 21:
        return "Insufficient landmark data."

    def pt(idx: int) -> dict:
        """Safe landmark accessor."""
        return landmarks[idx] if idx < len(landmarks) else {"x": 0.0, "y": 0.5, "z": 0.0}

    # ── Finger extension ───────────────────────────────────────────────────
    # A finger is extended when its tip is HIGHER (smaller y) than its MCP.
    # A small margin prevents borderline neutral positions from being called extended.
    def is_extended(tip_idx: int, mcp_idx: int, threshold: float = 0.04) -> bool:
        """Return True if the fingertip is above the MCP knuckle (extended)."""
        return (pt(mcp_idx)["y"] - pt(tip_idx)["y"]) > threshold

    index_ext  = is_extended(_INDEX_TIP,  _INDEX_MCP)
    middle_ext = is_extended(_MIDDLE_TIP, _MIDDLE_MCP)
    ring_ext   = is_extended(_RING_TIP,   _RING_MCP)
    pinky_ext  = is_extended(_PINKY_TIP,  _PINKY_MCP)

    # ── Thumb: abducted if tip is far left/right of index MCP ─────────────
    thumb_x_dist = abs(pt(_THUMB_TIP)["x"] - pt(_INDEX_MCP)["x"])
    thumb_abducted = thumb_x_dist > 0.08

    # ── Palm orientation: z-coordinate of wrist vs middle MCP ─────────────
    # Positive z diff → palm faces toward camera
    palm_z = pt(_WRIST)["z"] - pt(_MIDDLE_MCP)["z"]
    if palm_z > 0.02:
        palm_orientation = "facing camera"
    elif palm_z < -0.02:
        palm_orientation = "facing away"
    else:
        palm_orientation = "sideways"

    # ── Finger spread: distance between index and pinky tips ──────────────
    spread = abs(pt(_INDEX_TIP)["x"] - pt(_PINKY_TIP)["x"])
    fingers_spread = spread > 0.15

    # ── Compose readable feature string ───────────────────────────────────
    parts = [
        f"Index: {'extended' if index_ext else 'curled'}.",
        f"Middle: {'extended' if middle_ext else 'curled'}.",
        f"Ring: {'extended' if ring_ext else 'curled'}.",
        f"Pinky: {'extended' if pinky_ext else 'curled'}.",
        f"Thumb: {'abducted' if thumb_abducted else 'folded'}.",
        f"Palm: {palm_orientation}.",
        f"Fingers: {'spread' if fingers_spread else 'together'}.",
    ]
    return " ".join(parts)


async def recognize_sign(landmark_data: dict) -> dict:
    """
    Send landmark data to Ollama amandla model for sign recognition.

    Args:
        landmark_data: Dict with hand landmark positions from MediaPipe

    Returns:
        Dict with 'sign', 'confidence', and 'description'
    """
    try:
        # Build a geometric-feature prompt that the LLM can actually classify.
        # Raw x,y,z numbers are meaningless to a language model; computed features
        # (finger extension, palm orientation, spread) match what the Modelfile
        # system prompt teaches it to recognise.
        raw_landmarks = (
            landmark_data.get("landmarks", landmark_data)
            if isinstance(landmark_data, dict)
            else landmark_data
        )
        features = _extract_features(raw_landmarks)
        handedness = (
            landmark_data.get("handedness", "Right")
            if isinstance(landmark_data, dict)
            else "Right"
        )
        prompt = (
            f"Hand: {handedness}. "
            f"Features: {features}"
        )

        from backend.services.ollama_pool import get_client
        client = get_client()
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1
            },
            timeout=15.0,
        )

        if response.status_code != 200:
            logger.error(f"Ollama error: {response.status_code}")
            return {
                'sign': 'UNKNOWN',
                'confidence': 0.0,
                'description': 'Sign recognition failed'
            }

        data = response.json()
        response_text = data.get('response', '').strip()

        # Try to parse JSON response
        try:
            result = json.loads(response_text)
            logger.info(f"Sign recognized: {result.get('sign')} (conf={result.get('confidence')})")
            return result
        except json.JSONDecodeError:
            logger.warning(f"Ollama returned non-JSON: {response_text[:100]}")
            return {
                'sign': 'UNKNOWN',
                'confidence': 0.0,
                'description': 'Invalid response format'
            }

    except asyncio.TimeoutError:
        logger.warning("Ollama request timeout — trying NVIDIA NIM fallback")
        return await _recognize_via_nim(landmark_data)
    except Exception as e:
        logger.error(f"Sign recognition error: {e}")
        return await _recognize_via_nim(landmark_data)


async def _recognize_via_nim(landmark_data: dict) -> dict:
    """
    Fallback sign recognition using NVIDIA NIM (llama) when Ollama is unavailable.
    Only active when NVIDIA_ENABLED=true and NVIDIA_API_KEY is set.
    """
    try:
        from backend.services.nvidia_service import generate_with_nim, is_available
        if not is_available():
            return {'sign': 'UNKNOWN', 'confidence': 0.0, 'description': 'Ollama unavailable, NVIDIA disabled'}

        prompt = (
            "You are a South African Sign Language recognition engine. "
            "Identify the SASL sign from these MediaPipe hand landmarks. "
            f"Landmarks: {json.dumps(landmark_data)}. "
            'Reply ONLY with JSON: {"sign": "NAME", "confidence": 0.85, "description": "..."}'
        )
        raw = await generate_with_nim(prompt)
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].replace("json", "").strip()
        result = json.loads(raw)
        logger.info(f"[NIM] Sign recognised: {result.get('sign')} (conf={result.get('confidence')})")
        return result
    except Exception as e:
        logger.error(f"[NIM] Fallback recognition failed: {e}")
        return {'sign': 'UNKNOWN', 'confidence': 0.0, 'description': 'Sign recognition unavailable — please try again'}


async def health_check() -> bool:
    """Check if Ollama service is running and amandla model is available"""
    try:
        from backend.services.ollama_pool import get_client
        client = get_client()
        # Check if Ollama is running
        response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)

        if response.status_code != 200:
            logger.warning(f"Ollama health check failed: {response.status_code}")
            return False

        # Check if amandla model exists
        data = response.json()
        models = [m.get('name', '').split(':')[0] for m in data.get('models', [])]

        if OLLAMA_MODEL in models:
            logger.info(f"Ollama {OLLAMA_MODEL} model is available")
            return True
        else:
            logger.warning(f"Ollama model '{OLLAMA_MODEL}' not found. Available: {models}")
            return False

    except Exception as e:
        logger.error(f"Ollama health check error: {e}")
        return False

