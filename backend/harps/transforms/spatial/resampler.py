"""
harps.transforms.spatial.resampler — temporal resampling of skeleton clips.

Resampling to a fixed frame count is required before feeding into feature
extractors that expect a fixed-length input.
"""

from __future__ import annotations
import numpy as np


class UniformFrameSample:
    """
    Resample a clip to exactly ``m_frames`` frames using uniform index selection.

    Selects ``m_frames`` indices spaced by ``np.linspace(0, T-1, m_frames)``
    and gathers those frames. This is equivalent to slow-motion/fast-forward
    without interpolation.

    If T == m_frames, the clip is returned unchanged (no copy).
    If T < m_frames, indices wrap around (nearest-frame upsampling).

    Args:
        m_frames: Target number of frames after resampling.
    """

    def __init__(self, m_frames: int = 10):
        if m_frames < 1:
            raise ValueError(f"m_frames must be >= 1, got {m_frames}")
        self.m_frames = int(m_frames)

    def __call__(self, sample):
        """
        Resample clip to m_frames.

        Args:
            sample: (clip, y) tuple or dict {"X": clip, "y": y}.

        Returns:
            Same type as input with X having shape (m_frames, J, C).
        """
        if isinstance(sample, dict):
            clip, y = sample["X"], sample["y"]
        else:
            clip, y = sample

        T = clip.shape[0]
        if T == self.m_frames:
            return sample

        idx = np.round(np.linspace(0, T - 1, self.m_frames)).astype(int)
        out = clip[idx]

        if isinstance(sample, dict):
            return {**sample, "X": out}
        return out, y

    def __repr__(self) -> str:
        return f"UniformFrameSample(m_frames={self.m_frames})"


# Alias matching HARPS pipeline naming
LinearFrameResampler = UniformFrameSample