"""
harps.transforms.spatial — spatial (per-frame + cross-frame) transforms.
"""
from .normalize import PersonCentricNormalize
from .augment   import RandomFlipLR, GaussianNoise
from .resampler import UniformFrameSample, LinearFrameResampler

# SpatialPSF requires iisignature; import only if available
try:
    from .psf import SpatialPSF
    _PSF_AVAILABLE = True
except ImportError:
    SpatialPSF = None  # type: ignore
    _PSF_AVAILABLE = False

__all__ = [
    "PersonCentricNormalize",
    "RandomFlipLR",
    "GaussianNoise",
    "UniformFrameSample",
    "LinearFrameResampler",
    "SpatialPSF",
]