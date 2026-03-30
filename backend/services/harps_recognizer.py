"""
backend.services.harps_recognizer — HARPS-based sign recogniser.

Drop-in replacement for ollama_service.recognize_sign().

Architecture:
  MediaPipe landmarks (one frame)
    → SignSequenceBuffer (accumulate T frames)
      → TemporalJointPSF feature extraction  (or SJ fallback)
        → FeatureScaler (pre-fitted, loaded from checkpoint)
          → MLPClassifier.predict_proba()
            → top-1 class → sign name string

The model is loaded lazily on first call so the backend starts up even
when the checkpoint doesn't exist yet (training hasn't been run).
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Paths — resolved relative to this file
# ------------------------------------------------------------------
_HERE        = Path(__file__).parent
_CKPT_DIR    = _HERE.parent / "harps_model"
_CKPT_PATH   = _CKPT_DIR / "model.pth"
_META_PATH   = _CKPT_DIR / "meta.json"
_SCALER_PATH = _CKPT_DIR / "scaler.json"

# How many frames to buffer before running inference (overridable via .env)
_WINDOW      = int(os.environ.get("HARPS_WINDOW", "10"))
_STRIDE      = int(os.environ.get("HARPS_STRIDE", "3"))
# Feature set used during training
_FEATURE_SET = os.environ.get("HARPS_FEATURE_SET", "SJ")


class HARPSSignRecognizer:
    """
    Stateful single-session sign recogniser backed by HARPS.

    One instance per WebSocket session (created by the WS handler).

    Args:
        window:      Frame buffer window size.
        stride:      Frames between predictions.
        feature_set: "SJ" (no iisignature) or "TJ"/"T_TUPLE" etc.
    """

    def __init__(
        self,
        window:      int = _WINDOW,
        stride:      int = _STRIDE,
        feature_set: str = _FEATURE_SET,
    ):
        from .sign_buffer import SignSequenceBuffer
        self.feature_set = feature_set
        self._buf        = SignSequenceBuffer(window=window, stride=stride)
        self._model      = None   # lazy-loaded
        self._scaler     = None
        self._class_names: List[str] = []
        self._m_frames   = 10    # updated from meta.json on load
        self._loaded     = False

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------
    def _ensure_loaded(self) -> bool:
        """Load model + scaler from disk. Returns False if not available."""
        if self._loaded:
            return True
        if not _CKPT_PATH.exists():
            logger.warning("HARPS checkpoint not found at %s — falling back to Ollama", _CKPT_PATH)
            return False
        try:
            import torch
            from backend.harps.train.checkpoint import load_checkpoint
            from backend.harps.models           import MLPClassifier
            from backend.harps.utils.scaler     import FeatureScaler

            # Load metadata
            meta = {}
            if _META_PATH.exists():
                with _META_PATH.open() as f:
                    meta = json.load(f)

            self._class_names = meta.get("class_names", [])
            self._m_frames    = meta.get("m_frames", 10)
            self.feature_set  = meta.get("feature_set", self.feature_set)
            input_dim         = meta.get("input_dim", 0)
            hidden_dim        = meta.get("hidden_dim", 64)
            num_classes       = meta.get("num_classes", len(self._class_names))

            model = MLPClassifier(
                input_dim   = input_dim,
                hidden_dim  = hidden_dim,
                num_classes = num_classes,
            )
            load_checkpoint(str(_CKPT_PATH), model=model)
            model.eval()
            self._model = model

            if _SCALER_PATH.exists():
                with _SCALER_PATH.open() as f:
                    scaler_dict   = json.load(f)
                self._scaler = FeatureScaler.from_dict(scaler_dict)

            self._loaded = True
            logger.info("HARPS model loaded: %d classes, input_dim=%d", num_classes, input_dim)
            return True
        except Exception as exc:
            logger.error("HARPS model load failed: %s", exc, exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------
    def _extract_features(self, sequence: np.ndarray) -> np.ndarray:
        """
        (T, J, C) → (1, D) feature array.

        Uses TemporalJointPSF if iisignature available, else SJ (flatten).
        """
        # Resample to the number of frames used during training
        T = sequence.shape[0]
        if T != self._m_frames:
            idx      = np.linspace(0, T - 1, self._m_frames).round().astype(int)
            sequence = sequence[idx]

        try:
            if self.feature_set == "SJ":
                raise ImportError("SJ forced")

            from backend.harps.transforms.temporal.psf import TemporalJointPSF
            tj = TemporalJointPSF(n_tj=5)
            out = tj({"X": sequence, "y": 0})
            feats = out["X"].reshape(1, -1)
        except ImportError:
            # SJ fallback — flatten
            feats = sequence.reshape(1, -1)

        if self._scaler is not None:
            feats = self._scaler.transform(feats)
        return feats

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def push_frame(
        self,
        landmarks:  List[Dict[str, float]],
        handedness: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Ingest one MediaPipe landmark frame and return a prediction if ready.

        Args:
            landmarks:  List of {x,y,z} dicts from MediaPipe.
            handedness: Optional list of "Left"/"Right" labels.

        Returns:
            dict with keys sign, confidence, method="harps" or None if not
            enough frames yet.
        """
        from .mediapipe_bridge import landmarks_to_frame, normalize_frame

        frame = landmarks_to_frame(landmarks, handedness, n_coords=2)
        frame = normalize_frame(frame)
        self._buf.push(frame)

        if not self._buf.ready:
            return None

        if not self._ensure_loaded():
            return None  # model not available

        sequence = self._buf.get_sequence()  # (T, 42, 2)
        try:
            feats  = self._extract_features(sequence)
            import torch
            with torch.no_grad():
                X_t    = torch.as_tensor(feats, dtype=torch.float32)
                probs  = torch.softmax(self._model(X_t), dim=1).squeeze(0).numpy()
            top_idx    = int(probs.argmax())
            confidence = float(probs[top_idx])

            sign_name  = (
                self._class_names[top_idx]
                if top_idx < len(self._class_names)
                else str(top_idx)
            )
            return {
                "sign":        sign_name,
                "confidence":  round(confidence, 4),
                "method":      "harps",
                "top_k":       _top_k(probs, self._class_names, k=3),
            }
        except Exception as exc:
            logger.error("HARPS inference error: %s", exc, exc_info=True)
            return None

    def reset(self) -> None:
        """Clear frame buffer (call on session end or long silence)."""
        self._buf.reset()


def _top_k(probs: np.ndarray, class_names: List[str], k: int = 3) -> List[dict]:
    idx = np.argsort(probs)[::-1][:k]
    return [
        {"sign": class_names[i] if i < len(class_names) else str(i),
         "confidence": round(float(probs[i]), 4)}
        for i in idx
    ]


# ------------------------------------------------------------------
# Async drop-in for ollama_service.recognize_sign
# ------------------------------------------------------------------
async def recognize_sign_harps(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Async wrapper compatible with ollama_service.recognize_sign() signature.

    The recogniser is stateless from the caller's perspective — the buffer
    is owned by the recogniser singleton stored per session in the WS handler.

    This function is provided for one-shot backward compatibility only.
    Use HARPSSignRecognizer directly for proper frame buffering.
    """
    recognizer = HARPSSignRecognizer()
    landmarks  = payload.get("landmarks", [])
    handedness = payload.get("handedness", [])
    result     = recognizer.push_frame(landmarks, handedness)
    if result is None:
        return {"sign": "PROCESSING", "confidence": 0.0, "method": "harps"}
    return result