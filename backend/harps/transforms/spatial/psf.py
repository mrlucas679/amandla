"""
harps.transforms.spatial.psf — Spatial Path Signature Features (S-P-PSF / S-T-PSF).

Path signatures map a multidimensional path to a compact feature vector that
captures all iterated integrals of the path. Key property: they are invariant
to time reparametrisation (speed-invariant) — crucial for sign language where
the same sign can be performed quickly or slowly.

Feature sets
------------
SpatialPSF(include_pairs=True, n_sp=2)  → S-P-PSF feature set
SpatialPSF(include_triples=True, n_st=3) → S-T-PSF feature set

Requires iisignature. If not installed, SpatialPSF raises ImportError on
instantiation (not at module import time) so the rest of the code can load.
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


class SpatialPSF:
    """
    Spatial Path Signature Feature extractor.

    For each pair (and/or triple) of joints, concatenates their coordinate
    vectors frame by frame to form a path, then computes the iisignature
    path signature up to level ``n_sp`` (pairs) or ``n_st`` (triples).

    Input shape:  (T, J, C)
    Output shape: 1D float32 feature vector (length depends on J, C, levels)

    Args:
        n_sp:             Signature truncation level for pairs.
        n_st:             Signature truncation level for triples.
        include_pairs:    Compute pair signatures (S-P-PSF).
        include_triples:  Compute triple signatures (S-T-PSF).
        return_sequence:  If True return (T, feature) array; default False → 1D.
    """

    def __init__(
        self,
        n_sp: int = 2,
        n_st: int = 3,
        include_pairs: bool = True,
        include_triples: bool = True,
        return_sequence: bool = False,
    ):
        if not _HAS_IISIGNATURE:
            raise ImportError(
                "iisignature is required for SpatialPSF. "
                "Install: pip install iisignature  "
                "(or: pip install --no-binary :all: iisignature)"
            )
        self.n_sp            = int(n_sp)
        self.n_st            = int(n_st)
        self.include_pairs   = bool(include_pairs)
        self.include_triples = bool(include_triples)
        self.return_sequence = bool(return_sequence)

    def __call__(self, sample):
        """
        Compute spatial PSF features.

        Args:
            sample: (clip, y) where clip is (T, J, C) ndarray.

        Returns:
            (feature_vector, y) with feature_vector of shape (D,).
        """
        clip, y = sample
        T, J, C = clip.shape
        features = []

        if self.include_pairs:
            for i in range(J):
                for j in range(i + 1, J):
                    path = np.concatenate([clip[:, i, :], clip[:, j, :]], axis=1)  # (T, 2C)
                    sig  = _iis.sig(path.astype(np.float64), self.n_sp)
                    features.append(sig.astype(np.float32))

        if self.include_triples:
            for i in range(J):
                for j in range(i + 1, J):
                    for k in range(j + 1, J):
                        path = np.concatenate(
                            [clip[:, i, :], clip[:, j, :], clip[:, k, :]], axis=1
                        )  # (T, 3C)
                        sig = _iis.sig(path.astype(np.float64), self.n_st)
                        features.append(sig.astype(np.float32))

        if not features:
            return np.zeros(0, dtype=np.float32), y

        vec = np.concatenate(features).astype(np.float32)
        return vec, y

    def __repr__(self) -> str:
        return (f"SpatialPSF(n_sp={self.n_sp}, n_st={self.n_st}, "
                f"pairs={self.include_pairs}, triples={self.include_triples})")