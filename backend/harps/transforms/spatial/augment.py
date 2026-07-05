"""
harps.transforms.spatial.augment — data augmentation for skeleton poses.

RandomFlipLR : horizontal mirror flip (negate x, swap L/R joints)
GaussianNoise: additive Gaussian noise for training robustness
"""

from __future__ import annotations
from typing import Optional, Tuple, List
import numpy as np


class RandomFlipLR:
    """
    Horizontal (left-right) flip of skeleton pose data.

    Steps:
      1. Negate the x coordinate (coord index ``x_index`` on ``coord_axis``).
      2. Swap symmetric joint pairs (right ↔ left) on ``joint_axis``.

    The input array is never modified in-place (a copy is made).

    Args:
        p:           Probability of applying the flip (0 = never, 1 = always).
        swap_pairs:  (right_indices, left_indices) or None.
        joint_axis:  Axis that indexes joints (default 1 for (T,J,C)).
        coord_axis:  Axis that indexes coordinates (default 2 for (T,J,C)).
        x_index:     Index of the horizontal coordinate within coord_axis (default 0).
        coord_size:  Expected number of coordinates (validation only).
        joint_count: Expected number of joints (validation only).
    """

    def __init__(
        self,
        p: float = 0.5,
        swap_pairs: Optional[Tuple[List[int], List[int]]] = None,
        joint_axis: int = 1,
        coord_axis: int = 2,
        x_index: int = 0,
        coord_size: Optional[int] = None,
        joint_count: Optional[int] = None,
    ):
        self.p           = float(p)
        self.swap_pairs  = swap_pairs
        self.joint_axis  = joint_axis
        self.coord_axis  = coord_axis
        self.x_index     = x_index
        self.coord_size  = coord_size
        self.joint_count = joint_count

    def __call__(self, sample):
        """
        Apply the flip with probability p.

        Args:
            sample: (clip, y) tuple where clip is ndarray ≥ 3D.

        Returns:
            (flipped_clip, y) or unchanged (clip, y) if flip not applied.
        """
        clip, y = sample

        if clip.ndim < 3:
            raise ValueError(f"Expected ndim >= 3, got {clip.ndim}")

        C = clip.shape[self.coord_axis]
        J = clip.shape[self.joint_axis]

        if self.coord_size is not None and C != self.coord_size:
            raise ValueError(f"Expected coord_size={self.coord_size}, got {C}")
        if self.joint_count is not None and J != self.joint_count:
            raise ValueError(f"Expected joint_count={self.joint_count}, got {J}")
        if self.x_index >= C:
            raise ValueError(f"x_index={self.x_index} out of range for C={C}")

        if np.random.random() >= self.p:
            return clip, y

        out = clip.copy()

        # Negate x coordinate
        sl             = [slice(None)] * out.ndim
        sl[self.coord_axis] = self.x_index
        out[tuple(sl)] = -out[tuple(sl)]

        # Swap L/R joint pairs
        if self.swap_pairs is not None:
            right_idx, left_idx = self.swap_pairs
            sl_r = [slice(None)] * out.ndim
            sl_l = [slice(None)] * out.ndim
            sl_r[self.joint_axis] = right_idx
            sl_l[self.joint_axis] = left_idx
            tmp              = out[tuple(sl_r)].copy()
            out[tuple(sl_r)] = out[tuple(sl_l)]
            out[tuple(sl_l)] = tmp

        return out, y

    def __repr__(self) -> str:
        return (f"RandomFlipLR(p={self.p}, swap_pairs={'set' if self.swap_pairs else None}, "
                f"joint_axis={self.joint_axis}, coord_axis={self.coord_axis})")


class GaussianNoise:
    """
    Add zero-mean Gaussian noise to all joint coordinates.

    Applied only to (T, J, C) float arrays. Useful for training-time
    regularisation — set std=0 to disable without removing from pipeline.

    Args:
        std: Standard deviation of the noise (in normalised coordinate units).
    """

    def __init__(self, std: float = 0.01):
        self.std = float(std)

    def __call__(self, sample):
        """
        Add noise to clip coordinates.

        Args:
            sample: (clip, y) tuple.

        Returns:
            (noisy_clip, y).
        """
        clip, y = sample
        if self.std <= 0.0:
            return sample
        noise = np.random.randn(*clip.shape).astype(np.float32) * self.std
        return clip.astype(np.float32) + noise, y

    def __repr__(self) -> str:
        return f"GaussianNoise(std={self.std})"