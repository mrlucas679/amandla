"""
harps.transforms.spatial.normalize — PersonCentricNormalize.

Normalises skeleton poses so they are invariant to:
  - signer position in the frame (centering)
  - signer size / distance from camera (global max-abs scaling)

Algorithm (verified against test_normalize_person_centric.py)
-------------------------------------------------------------
1. For each time frame t:
       X[t] -= X[t].mean(axis=joint_axis)   # centre joints around person
2. Globally:
       X /= max(|X|)                         # scale to max absolute value = 1
"""

from __future__ import annotations
import numpy as np


class PersonCentricNormalize:
    """
    Per-frame joint centering followed by global max-abs scaling.

    Input:  (T, J, C) ndarray  — or dict {"X": ..., "y": ...}
    Output: (T, J, C) float32  — centred and scaled

    The original input array is never modified (a copy is made).

    Args:
        joint_axis: Axis along which joints are indexed (default 1 for (T,J,C)).
        coord_axis: Axis along which coordinates are indexed (default 2).
    """

    def __init__(self, joint_axis: int = 1, coord_axis: int = 2):
        self.joint_axis = joint_axis
        self.coord_axis = coord_axis

    def __call__(self, sample):
        """
        Normalise one clip.

        Args:
            sample: (clip, y) tuple or dict {"X": clip, "y": y}.

        Returns:
            Same type as input with X replaced by normalised array.
        """
        if isinstance(sample, dict):
            clip, y = sample["X"], sample["y"]
        else:
            clip, y = sample

        X = np.array(clip, dtype=np.float32, copy=True)

        # Step 1: centre each frame by subtracting mean over joints
        mean = X.mean(axis=self.joint_axis, keepdims=True)  # (T, 1, C)
        X -= mean

        # Step 2: global max-abs scaling
        scale = np.max(np.abs(X))
        if scale > 1e-8:
            X /= scale

        if isinstance(sample, dict):
            return {**sample, "X": X}
        return X, y

    def __repr__(self) -> str:
        return f"PersonCentricNormalize(joint_axis={self.joint_axis}, coord_axis={self.coord_axis})"
