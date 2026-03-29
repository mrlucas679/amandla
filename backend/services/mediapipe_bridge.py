"""
backend.services.mediapipe_bridge — convert MediaPipe landmark dicts to HARPS arrays.

MediaPipe hand landmarks are 21 points per hand, delivered by the frontend
as a flat list of {x, y, z} dicts. HARPS expects (T, J, C) numpy arrays.

Joint layout for HARPS "42_hands" mode:
  joints 0-20  — left hand  (MediaPipe hand 0 or explicitly "Left")
  joints 21-41 — right hand (MediaPipe hand 1 or explicitly "Right")

If only one hand is detected the missing hand is zeroed out.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import numpy as np

# Number of MediaPipe landmarks per hand
_MP_JOINTS = 21
# Total HARPS "42_hands" joints
_HARPS_JOINTS = 42
# Coordinates kept (x, y) — drop z for 2-D features unless caller requests 3-D
_DEFAULT_COORDS = 2


def landmarks_to_frame(
    landmarks: List[Dict[str, float]],
    handedness: Optional[List[str]] = None,
    n_coords: int = _DEFAULT_COORDS,
) -> np.ndarray:
    """
    Convert a single-frame MediaPipe landmark payload to a HARPS frame.

    Args:
        landmarks:  Flat list of landmark dicts [{x, y, z}, ...].
                    May contain 21 (one hand) or 42 (two hands) entries.
        handedness: Optional list of hand labels ("Left", "Right") aligned
                    with each group of 21 landmarks.
        n_coords:   Number of coordinates to keep per joint (2 or 3).

    Returns:
        frame: (42, n_coords) float32 array — left hand first, right second.
    """
    frame = np.zeros((_HARPS_JOINTS, n_coords), dtype=np.float32)

    n_lm = len(landmarks)
    if n_lm == 0:
        return frame

    # Split into up to two hands of 21 joints each
    groups: List[np.ndarray] = []
    for start in range(0, min(n_lm, _HARPS_JOINTS), _MP_JOINTS):
        chunk = landmarks[start : start + _MP_JOINTS]
        arr   = _lm_list_to_array(chunk, n_coords)
        groups.append(arr)

    if not groups:
        return frame

    if handedness is None or len(handedness) == 0:
        # Assign first group to left, second to right (if present)
        frame[:_MP_JOINTS] = groups[0]
        if len(groups) > 1:
            frame[_MP_JOINTS:] = groups[1]
    else:
        for idx, label in enumerate(handedness[:2]):
            if idx >= len(groups):
                break
            if label.lower() in ("left", "l"):
                frame[:_MP_JOINTS] = groups[idx]
            else:
                frame[_MP_JOINTS:] = groups[idx]

    return frame


def _lm_list_to_array(
    lm_list: List[Dict[str, float]], n_coords: int
) -> np.ndarray:
    """Convert a list of {x,y,z} dicts to (21, n_coords) array."""
    arr = np.zeros((_MP_JOINTS, n_coords), dtype=np.float32)
    keys = ["x", "y", "z"][:n_coords]
    for i, lm in enumerate(lm_list[:_MP_JOINTS]):
        for c, k in enumerate(keys):
            arr[i, c] = float(lm.get(k, 0.0))
    return arr


def normalize_frame(frame: np.ndarray) -> np.ndarray:
    """
    Person-centric normalise a single frame (J, C).

    Subtracts per-joint mean across joints, then divides by global max-abs.
    Mirrors PersonCentricNormalize but for a single frame.
    """
    out   = frame.copy()
    mean  = out.mean(axis=0, keepdims=True)
    out  -= mean
    scale = np.abs(out).max()
    if scale > 0:
        out /= scale
    return out