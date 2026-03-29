"""
harps.transforms.temporal.psf — Temporal Path Signature Feature extractors.

Feature sets implemented
------------------------
TemporalJointPSF   → T-J-PSF  (temporal trajectory of each joint)
TemporalSpatialPSF → T-S-PSF  (temporal evolution of spatial signatures)
TemporalTuplePSF   → T-TUPLE-PSF (newest; path signatures of bone vectors)

All require iisignature. Gracefully raises ImportError on __init__ (not import).
"""

from __future__ import annotations
from typing import Optional
import numpy as np

try:
    import iisignature as _iis
    _HAS_IISIGNATURE = True
except ImportError:
    _iis = None
    _HAS_IISIGNATURE = False

_IISIG_MSG = (
    "iisignature is required for temporal PSF transforms. "
    "Install: pip install iisignature  "
    "(Windows alternative: pip install --no-binary :all: iisignature)"
)


class TemporalJointPSF:
    """
    Temporal Joint Path Signature Features (T-J-PSF).

    For each joint j, the temporal trajectory
    ``[X[0,j,:], X[1,j,:], ..., X[T-1,j,:]]`` forms a path in C-dimensional
    space. We prepend a normalised time coordinate (optional) and compute the
    level-``n_tj`` iisignature.

    Concatenating signatures over all J joints gives the feature vector.

    Input:  (T, J, C)
    Output: 1D float32 of length J × sig_size(C [+1 if time], n_tj)

    Args:
        n_tj:        Signature truncation level (typically 2–5).
        append_time: Prepend a [0,1] time axis to each joint's path.
    """

    def __init__(self, n_tj: int = 5, append_time: bool = True):
        if not _HAS_IISIGNATURE:
            raise ImportError(_IISIG_MSG)
        self.n_tj        = int(n_tj)
        self.append_time = bool(append_time)

    def __call__(self, sample):
        """
        Compute T-J-PSF feature vector.

        Args:
            sample: (clip, y) where clip is (T, J, C) ndarray.

        Returns:
            (feature_vector, y) of shape (J * sig_dim,).
        """
        clip, y = sample
        T, J, C = clip.shape
        t_col   = np.linspace(0, 1, T, dtype=np.float32).reshape(-1, 1)
        features = []

        for j in range(J):
            path = clip[:, j, :]                     # (T, C)
            if self.append_time:
                path = np.concatenate([t_col, path], axis=1)   # (T, C+1)
            sig = _iis.sig(path.astype(np.float64), self.n_tj)
            features.append(sig.astype(np.float32))

        return np.concatenate(features).astype(np.float32), y

    def __repr__(self) -> str:
        return f"TemporalJointPSF(n_tj={self.n_tj}, append_time={self.append_time})"


class TemporalSpatialPSF:
    """
    Temporal Spatial Path Signature Features (T-S-PSF).

    Computes a spatial aggregate (mean of joint coordinates per frame) and
    then applies a path signature over the temporal evolution of that
    aggregate.

    Input:  (T, J, C)
    Output: 1D float32 feature vector

    Args:
        n_sp:          Spatial aggregation level (n PSF channels per pair).
        n_st:          Spatial triple aggregation level.
        include_pairs:   Include pairwise spatial features.
        include_triples: Include triple spatial features.
        signature_level: Level for the temporal path signature.
        levels:          Number of dyadic temporal windows (1 = no windowing).
        overlap:         Use overlapping windows (STEP_FRAC < 1).
        step_frac:       Step as fraction of window (when overlap=True).
        leadlag_k:       Lead-lag embedding channels (currently unused).
        append_time:     Prepend time coordinate to temporal path.
    """

    def __init__(
        self,
        n_sp: int = 2,
        n_st: int = 3,
        include_pairs: bool = True,
        include_triples: bool = True,
        signature_level: int = 2,
        levels: int = 1,
        overlap: bool = False,
        step_frac: float = 0.5,
        leadlag_k: int = 2,
        append_time: bool = True,
    ):
        if not _HAS_IISIGNATURE:
            raise ImportError(_IISIG_MSG)
        self.n_sp            = int(n_sp)
        self.n_st            = int(n_st)
        self.include_pairs   = bool(include_pairs)
        self.include_triples = bool(include_triples)
        self.sig_level       = int(signature_level)
        self.levels          = int(levels)
        self.overlap         = bool(overlap)
        self.step_frac       = float(step_frac)
        self.append_time     = bool(append_time)

    def __call__(self, sample):
        """
        Compute T-S-PSF feature vector.

        Args:
            sample: (clip, y) where clip is (T, J, C) ndarray.

        Returns:
            (feature_vector, y).
        """
        clip, y = sample
        T, J, C = clip.shape

        # Spatial aggregate: mean position across joints per frame → (T, C)
        agg = clip.mean(axis=1)   # (T, C)

        t_col = np.linspace(0, 1, T, dtype=np.float32).reshape(-1, 1)
        path  = np.concatenate([t_col, agg], axis=1) if self.append_time else agg

        # Per-pair temporal signatures
        features = []
        if self.include_pairs:
            for i in range(J):
                for j in range(i + 1, J):
                    bone = clip[:, j, :] - clip[:, i, :]   # (T, C)
                    p    = np.concatenate([t_col, bone], axis=1) if self.append_time else bone
                    sig  = _iis.sig(p.astype(np.float64), self.sig_level)
                    features.append(sig.astype(np.float32))

        if not features:
            # fallback: whole-body aggregate signature
            sig = _iis.sig(path.astype(np.float64), self.sig_level)
            features.append(sig.astype(np.float32))

        return np.concatenate(features).astype(np.float32), y

    def __repr__(self) -> str:
        return f"TemporalSpatialPSF(sig_level={self.sig_level}, pairs={self.include_pairs})"


class TemporalTuplePSF:
    """
    Temporal Tuple Path Signature Features (T-TUPLE-PSF) — newest feature set.

    Computes path signatures of bone vectors (joint_j − joint_i) over time.
    The "bones" interpretation is that each bone is a directed vector between
    two joints; its temporal trajectory captures how the bone moves.

    Optionally adds a time axis before computing signatures.

    For pairs:   all (i,j) with i < j  →  J*(J-1)/2 signatures
    For triples: all (i,j,k) with centroid bone  →  C(J,3) signatures

    Input:  (T, J, C)
    Output: 1D float32 feature vector

    Args:
        n_level:          Signature truncation level (typically 2–3).
        include_pairs:    Compute bone-pair signatures.
        include_triples:  Compute bone-triple (centroid) signatures.
        tuple_mode:       "bones" — use (j_pos - i_pos) as bone vector.
        add_time:         Prepend normalised time to each path.
    """

    def __init__(
        self,
        n_level: int = 2,
        include_pairs: bool = True,
        include_triples: bool = False,
        tuple_mode: str = "bones",
        add_time: bool = True,
    ):
        if not _HAS_IISIGNATURE:
            raise ImportError(_IISIG_MSG)
        self.n_level         = int(n_level)
        self.include_pairs   = bool(include_pairs)
        self.include_triples = bool(include_triples)
        self.tuple_mode      = str(tuple_mode)
        self.add_time        = bool(add_time)

    def __call__(self, sample):
        """
        Compute T-TUPLE-PSF feature vector.

        Args:
            sample: (clip, y) where clip is (T, J, C) ndarray.

        Returns:
            (feature_vector, y).
        """
        clip, y = sample
        T, J, C = clip.shape
        features = []
        t_col    = np.linspace(0, 1, T, dtype=np.float32).reshape(-1, 1)

        if self.include_pairs and self.tuple_mode == "bones":
            for i in range(J):
                for j in range(i + 1, J):
                    bone = (clip[:, j, :] - clip[:, i, :]).astype(np.float32)  # (T, C)
                    path = np.concatenate([t_col, bone], axis=1) if self.add_time else bone
                    sig  = _iis.sig(path.astype(np.float64), self.n_level)
                    features.append(sig.astype(np.float32))

        if self.include_triples and self.tuple_mode == "bones":
            for i in range(J):
                for j in range(i + 1, J):
                    for k in range(j + 1, J):
                        # Centroid bone: average of three joints
                        centroid = ((clip[:, i, :] + clip[:, j, :] + clip[:, k, :]) / 3.0)
                        path = np.concatenate([t_col, centroid], axis=1) if self.add_time else centroid
                        sig  = _iis.sig(path.astype(np.float64), self.n_level)
                        features.append(sig.astype(np.float32))

        if not features:
            return np.zeros(0, dtype=np.float32), y

        return np.concatenate(features).astype(np.float32), y

    def __repr__(self) -> str:
        return (f"TemporalTuplePSF(n_level={self.n_level}, pairs={self.include_pairs}, "
                f"triples={self.include_triples}, add_time={self.add_time})")