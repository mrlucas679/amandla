"""
backend.services.sign_buffer — accumulate landmark frames for HARPS inference.

MediaPipe emits one frame per message. HARPS needs a temporal sequence
(T frames) to compute path signature features. This buffer accumulates
frames and signals when a sufficient window is ready.
"""

from __future__ import annotations
from collections import deque
from typing import List, Optional
import numpy as np


# Default window length in frames
DEFAULT_WINDOW = 10
# Slide step: how many new frames trigger a fresh prediction
DEFAULT_STRIDE = 3


class SignSequenceBuffer:
    """
    Sliding-window frame accumulator for real-time sign recognition.

    Each call to ``push`` adds one frame of joint coordinates.
    When the buffer reaches ``window`` frames, ``ready`` returns True
    and ``get_sequence`` returns the buffered array.

    Args:
        window: Number of frames to accumulate before inference.
        stride: New frames needed before the next inference fires.
        n_joints: Expected joints per frame (default 42 for two hands).
        n_coords: Coordinates per joint (default 2: x,y or 3: x,y,z).
    """

    def __init__(
        self,
        window:   int = DEFAULT_WINDOW,
        stride:   int = DEFAULT_STRIDE,
        n_joints: int = 42,
        n_coords: int = 2,
    ):
        self.window   = window
        self.stride   = stride
        self.n_joints = n_joints
        self.n_coords = n_coords
        self._buf: deque = deque(maxlen=window)
        self._since_last: int = 0

    def push(self, frame: np.ndarray) -> None:
        """
        Add one frame to the buffer.

        Args:
            frame: (n_joints, n_coords) float32 array.
        """
        if frame.shape != (self.n_joints, self.n_coords):
            # Pad or truncate to expected shape
            frame = _reshape_frame(frame, self.n_joints, self.n_coords)
        self._buf.append(frame.astype(np.float32))
        self._since_last += 1

    @property
    def ready(self) -> bool:
        """True when the buffer has enough frames and stride is met."""
        return len(self._buf) >= self.window and self._since_last >= self.stride

    def get_sequence(self) -> np.ndarray:
        """
        Return the buffered sequence as (window, n_joints, n_coords) array.
        Resets the stride counter.
        """
        self._since_last = 0
        return np.stack(list(self._buf), axis=0)  # (T, J, C)

    def reset(self) -> None:
        """Clear all buffered frames."""
        self._buf.clear()
        self._since_last = 0

    def __len__(self) -> int:
        return len(self._buf)


def _reshape_frame(
    frame: np.ndarray, n_joints: int, n_coords: int
) -> np.ndarray:
    """Pad or crop frame to (n_joints, n_coords)."""
    out = np.zeros((n_joints, n_coords), dtype=np.float32)
    j   = min(frame.shape[0], n_joints)
    c   = min(frame.shape[1] if frame.ndim > 1 else 1, n_coords)
    if frame.ndim == 1:
        frame = frame.reshape(-1, 1)
    out[:j, :c] = frame[:j, :c]
    return out