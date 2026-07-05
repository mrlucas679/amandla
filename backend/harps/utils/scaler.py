"""
harps.utils.scaler — per-feature normalisation fitted on TRAIN data.

Modes
-----
- "maxabs"   : x / max(|x|)           → values in [-1, 1]
- "standard" : (x - mean) / std
- "robust"   : (x - median) / IQR
- "none"     : passthrough

The scaler is always fit on training data only, then applied identically to
validation and test splits.
"""

from __future__ import annotations
import numpy as np
from typing import Optional, Tuple, Literal, Dict

ScalerMode = Literal["maxabs", "standard", "robust", "none"]


class FeatureScaler:
    """
    Unified per-feature scaler fit on TRAIN, applied to TRAIN/TEST/INFERENCE.

    Attributes
    ----------
    params_ : dict or None
        Fitted parameters (None until fit() is called).
    """

    def __init__(
        self,
        mode: ScalerMode = "maxabs",
        clip_range: Optional[Tuple[float, float]] = (-1.0, 1.0),
        eps: float = 1e-8,
    ):
        self.mode = mode
        self.clip_range = clip_range
        self.eps = float(eps)
        self.params_: Optional[Dict[str, np.ndarray]] = None

    def fit(self, X: np.ndarray) -> "FeatureScaler":
        """Compute scaling parameters from training data X (N, D)."""
        X = np.asarray(X)
        if X.ndim != 2:
            X = X.reshape(X.shape[0], -1)

        if self.mode == "none":
            self.params_ = {}
            return self

        if self.mode == "maxabs":
            maxabs = np.max(np.abs(X), axis=0)
            maxabs[maxabs < self.eps] = 1.0
            self.params_ = {"maxabs": maxabs.astype(np.float32)}

        elif self.mode == "standard":
            mean = np.mean(X, axis=0)
            std  = np.std(X, axis=0, ddof=0)
            std[std < self.eps] = 1.0
            self.params_ = {"mean": mean.astype(np.float32), "std": std.astype(np.float32)}

        elif self.mode == "robust":
            q25 = np.percentile(X, 25, axis=0)
            q50 = np.percentile(X, 50, axis=0)
            q75 = np.percentile(X, 75, axis=0)
            iqr = q75 - q25
            iqr[iqr < self.eps] = 1.0
            self.params_ = {"median": q50.astype(np.float32), "iqr": iqr.astype(np.float32)}

        else:
            raise ValueError(f"Unknown scaler mode: {self.mode!r}")

        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Apply fitted scaling to X (N, D)."""
        if self.params_ is None:
            raise RuntimeError("FeatureScaler not fitted. Call fit() first.")
        X = np.asarray(X)
        if X.ndim != 2:
            X = X.reshape(X.shape[0], -1)

        if self.mode == "none":
            Xs = X.astype(np.float32)
        elif self.mode == "maxabs":
            Xs = (X / self.params_["maxabs"]).astype(np.float32)
        elif self.mode == "standard":
            Xs = ((X - self.params_["mean"]) / self.params_["std"]).astype(np.float32)
        elif self.mode == "robust":
            Xs = ((X - self.params_["median"]) / self.params_["iqr"]).astype(np.float32)
        else:
            raise ValueError(f"Unknown scaler mode: {self.mode!r}")

        if self.clip_range is not None:
            lo, hi = self.clip_range
            Xs = np.clip(Xs, lo, hi)
        return Xs

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """Fit then transform in one call."""
        return self.fit(X).transform(X)

    def to_dict(self) -> dict:
        """Serialise to a JSON-safe dict."""
        return {
            "mode":       self.mode,
            "clip_range": self.clip_range,
            "eps":        self.eps,
            "params":     {k: v.tolist() for k, v in (self.params_ or {}).items()},
        }

    @classmethod
    def from_dict(cls, state: dict) -> "FeatureScaler":
        """Reconstruct from a dict previously returned by to_dict()."""
        obj = cls(mode=state["mode"], clip_range=state["clip_range"], eps=state["eps"])
        obj.params_ = {k: np.asarray(v, dtype=np.float32) for k, v in state.get("params", {}).items()}
        return obj