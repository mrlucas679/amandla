"""
harps.transforms — composable feature extraction pipeline.

All transforms follow the (clip, y) → (output, y) protocol and can be
chained with Compose.

Core
----
Compose               : Chain transforms sequentially.

Spatial
-------
PersonCentricNormalize : Centre joints per frame; scale to max-abs=1.
RandomFlipLR           : Horizontal flip (x-negate + L/R joint swap).
GaussianNoise          : Additive Gaussian noise for augmentation.
UniformFrameSample     : Resample clip to fixed number of frames.
LinearFrameResampler   : Alias for UniformFrameSample.
SpatialPSF             : Spatial path-signature features (requires iisignature).

Temporal (require iisignature)
------------------------------
TemporalJointPSF   : T-J-PSF — per-joint temporal trajectory signatures.
TemporalSpatialPSF : T-S-PSF — temporal evolution of spatial aggregates.
TemporalTuplePSF   : T-TUPLE-PSF — bone-vector temporal signatures (newest).
"""

from .compose import Compose
from .spatial import (
    PersonCentricNormalize,
    RandomFlipLR,
    GaussianNoise,
    UniformFrameSample,
    LinearFrameResampler,
    SpatialPSF,
)
from .temporal import TemporalJointPSF, TemporalSpatialPSF, TemporalTuplePSF

__all__ = [
    "Compose",
    "PersonCentricNormalize",
    "RandomFlipLR",
    "GaussianNoise",
    "UniformFrameSample",
    "LinearFrameResampler",
    "SpatialPSF",
    "TemporalJointPSF",
    "TemporalSpatialPSF",
    "TemporalTuplePSF",
]