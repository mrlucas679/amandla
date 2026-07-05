"""
harps.transforms.temporal — temporal feature extraction transforms.
"""
try:
    from .psf import TemporalJointPSF, TemporalSpatialPSF, TemporalTuplePSF
    _PSF_AVAILABLE = True
except ImportError:
    TemporalJointPSF    = None  # type: ignore
    TemporalSpatialPSF  = None  # type: ignore
    TemporalTuplePSF    = None  # type: ignore
    _PSF_AVAILABLE = False

__all__ = ["TemporalJointPSF", "TemporalSpatialPSF", "TemporalTuplePSF"]