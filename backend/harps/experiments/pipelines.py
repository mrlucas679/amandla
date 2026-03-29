"""
harps.experiments.pipelines — feature extraction pipelines.

Each pipeline takes a list of samples {"X": (T,J,C), "y": int, ...} and
returns stacked feature arrays (N, D) + labels (N,).

Feature sets from HARPS paper:
  SJ          — Spatial joints baseline (flatten)
  SP_ST       — Spatial Pairs + Spatial Triples PSF fusion
  TJ          — Temporal Joint PSF
  TS          — Temporal Spatial PSF
  T_TUPLE     — Temporal Tuple PSF (bone vectors)
  FULL        — All PSF features fused
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
import numpy as np

from ..transforms import (
    Compose,
    PersonCentricNormalize,
    UniformFrameSample,
)

# PSF transforms are optional (require iisignature)
try:
    from ..transforms import (
        SpatialPSF,
        TemporalJointPSF,
        TemporalSpatialPSF,
        TemporalTuplePSF,
    )
    _HAS_PSF = True
except (ImportError, TypeError):
    SpatialPSF = TemporalJointPSF = TemporalSpatialPSF = TemporalTuplePSF = None
    _HAS_PSF = False


@dataclass
class PipelineConfig:
    """Feature extraction hyper-parameters."""
    M_FRAMES:   int = 10   # number of frames after resampling
    N_SP:       int = 2    # PSF level for spatial pairs
    N_ST:       int = 3    # PSF level for spatial triples
    N_TJ:       int = 5    # PSF level for temporal joints
    N_TS:       int = 2    # PSF level for temporal spatial
    N_TUPLE:    int = 2    # PSF level for temporal tuple (bone)


def _extract_features(samples: list, transform) -> Tuple[np.ndarray, np.ndarray]:
    """Apply transform to each sample and stack X, y arrays."""
    Xs, ys = [], []
    for s in samples:
        out = transform(s)
        if isinstance(out, dict):
            Xs.append(out["X"].reshape(1, -1) if out["X"].ndim > 1 else out["X"].reshape(1, -1))
            ys.append(out["y"])
        else:
            clip, y = out
            Xs.append(clip.reshape(1, -1))
            ys.append(y)
    return np.vstack(Xs), np.array(ys)


class Pipelines:
    """
    Collection of named feature pipelines.

    Args:
        cfg: PipelineConfig with dimensionality hyper-parameters.
    """

    def __init__(self, cfg: PipelineConfig = None):
        self.cfg = cfg or PipelineConfig()

    def _base_transforms(self):
        return [
            PersonCentricNormalize(),
            UniformFrameSample(m_frames=self.cfg.M_FRAMES),
        ]

    def pipeline_SJ(self, samples: list) -> Tuple[np.ndarray, np.ndarray]:
        """Spatial Joints baseline — flatten normalised frames."""
        def transform(s):
            clip = s["X"]
            # PersonCentric normalize
            mean = clip.mean(axis=1, keepdims=True)
            clip = clip - mean
            scale = np.abs(clip).max()
            if scale > 0:
                clip = clip / scale
            # Uniform resample
            T = clip.shape[0]
            if T != self.cfg.M_FRAMES:
                idx   = np.linspace(0, T - 1, self.cfg.M_FRAMES).round().astype(int)
                clip  = clip[idx]
            feats = clip.reshape(-1)
            return {"X": feats, "y": s["y"]}

        return _extract_features(samples, transform)

    def pipeline_SP_ST(self, samples: list) -> Tuple[np.ndarray, np.ndarray]:
        """Spatial Pairs + Spatial Triples PSF fusion."""
        if not _HAS_PSF or SpatialPSF is None:
            raise ImportError("iisignature required for spatial PSF pipelines")

        sp_transform = SpatialPSF(n_level=self.cfg.N_SP, mode="pairs")
        st_transform = SpatialPSF(n_level=self.cfg.N_ST, mode="triples")

        def transform(s):
            clip = s["X"]
            mean = clip.mean(axis=1, keepdims=True)
            clip = (clip - mean) / max(np.abs(clip - mean).max(), 1e-7)
            T = clip.shape[0]
            if T != self.cfg.M_FRAMES:
                idx  = np.linspace(0, T - 1, self.cfg.M_FRAMES).round().astype(int)
                clip = clip[idx]
            sp = sp_transform({"X": clip, "y": s["y"]})["X"]
            st = st_transform({"X": clip, "y": s["y"]})["X"]
            return {"X": np.concatenate([sp, st]), "y": s["y"]}

        return _extract_features(samples, transform)

    def pipeline_TJ(self, samples: list) -> Tuple[np.ndarray, np.ndarray]:
        """Temporal Joint PSF — path signatures of joint trajectories."""
        if not _HAS_PSF or TemporalJointPSF is None:
            raise ImportError("iisignature required for temporal PSF pipelines")

        tj_transform = TemporalJointPSF(n_tj=self.cfg.N_TJ)

        def transform(s):
            clip = s["X"]
            mean = clip.mean(axis=1, keepdims=True)
            clip = (clip - mean) / max(np.abs(clip - mean).max(), 1e-7)
            T = clip.shape[0]
            if T != self.cfg.M_FRAMES:
                idx  = np.linspace(0, T - 1, self.cfg.M_FRAMES).round().astype(int)
                clip = clip[idx]
            return tj_transform({"X": clip, "y": s["y"]})

        return _extract_features(samples, transform)

    def pipeline_TS(self, samples: list) -> Tuple[np.ndarray, np.ndarray]:
        """Temporal Spatial PSF — bone vector temporal signatures."""
        if not _HAS_PSF or TemporalSpatialPSF is None:
            raise ImportError("iisignature required for temporal PSF pipelines")

        ts_transform = TemporalSpatialPSF(n_ts=self.cfg.N_TS)

        def transform(s):
            clip = s["X"]
            mean = clip.mean(axis=1, keepdims=True)
            clip = (clip - mean) / max(np.abs(clip - mean).max(), 1e-7)
            T = clip.shape[0]
            if T != self.cfg.M_FRAMES:
                idx  = np.linspace(0, T - 1, self.cfg.M_FRAMES).round().astype(int)
                clip = clip[idx]
            return ts_transform({"X": clip, "y": s["y"]})

        return _extract_features(samples, transform)

    def pipeline_T_TUPLE(self, samples: list) -> Tuple[np.ndarray, np.ndarray]:
        """Temporal Tuple PSF — bone vectors with time prepend."""
        if not _HAS_PSF or TemporalTuplePSF is None:
            raise ImportError("iisignature required for T-TUPLE pipeline")

        tt_transform = TemporalTuplePSF(
            n_level    = self.cfg.N_TUPLE,
            tuple_mode = "bones",
            add_time   = True,
        )

        def transform(s):
            clip = s["X"]
            mean = clip.mean(axis=1, keepdims=True)
            clip = (clip - mean) / max(np.abs(clip - mean).max(), 1e-7)
            T = clip.shape[0]
            if T != self.cfg.M_FRAMES:
                idx  = np.linspace(0, T - 1, self.cfg.M_FRAMES).round().astype(int)
                clip = clip[idx]
            return tt_transform({"X": clip, "y": s["y"]})

        return _extract_features(samples, transform)

    def pipeline_FULL(self, samples: list) -> Tuple[np.ndarray, np.ndarray]:
        """Full feature fusion: SJ + SP + ST + TJ + TS + T-TUPLE."""
        if not _HAS_PSF:
            # Fallback: SJ only
            return self.pipeline_SJ(samples)

        sj_X, ys   = self.pipeline_SJ(samples)
        try:
            sp_X, _    = self.pipeline_SP_ST(samples)
            tj_X, _    = self.pipeline_TJ(samples)
            ts_X, _    = self.pipeline_TS(samples)
            tt_X, _    = self.pipeline_T_TUPLE(samples)
            return np.hstack([sj_X, sp_X, tj_X, ts_X, tt_X]), ys
        except Exception:
            return sj_X, ys


def make_feature_dict(
    pipelines_obj: Pipelines,
    samples: list,
    feature_sets: Optional[List[str]] = None,
) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """
    Run multiple pipelines and return a dict of {name: (X, y)}.

    Args:
        pipelines_obj: Pipelines instance.
        samples:       List of {"X": (T,J,C), "y": int, ...} samples.
        feature_sets:  Names to compute. Defaults to ["SJ", "TJ", "FULL"].

    Returns:
        dict mapping feature set name to (X_array, y_array).
    """
    if feature_sets is None:
        feature_sets = ["SJ", "TJ", "FULL"]

    _dispatch = {
        "SJ":     pipelines_obj.pipeline_SJ,
        "SP_ST":  pipelines_obj.pipeline_SP_ST,
        "TJ":     pipelines_obj.pipeline_TJ,
        "TS":     pipelines_obj.pipeline_TS,
        "T_TUPLE": pipelines_obj.pipeline_T_TUPLE,
        "FULL":   pipelines_obj.pipeline_FULL,
    }

    result = {}
    for name in feature_sets:
        fn = _dispatch.get(name)
        if fn is None:
            raise ValueError(f"Unknown feature set: {name!r}. Choose from {list(_dispatch)}")
        try:
            result[name] = fn(samples)
        except ImportError as e:
            result[name] = None  # iisignature unavailable
    return result