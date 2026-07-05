"""
harps.utils.pca — lightweight NumPy PCA mirroring sklearn API.

Avoids sklearn dependency for inference-time dimensionality reduction.
"""

from __future__ import annotations
import numpy as np
from typing import Optional, Dict, Any


class FeaturePCA:
    """
    Lightweight PCA transformer (NumPy-only, no sklearn required).

    Component selection
    -------------------
    - int n_components  : keep exactly that many components
    - float 0 < n < 1  : keep enough components to explain that fraction of variance
    - None             : keep all components

    Attributes (after fit)
    ----------------------
    mean_                    : (D,) mean subtracted before projection
    components_              : (k, D) top-k eigenvectors (rows)
    explained_variance_      : (k,) variance explained by each component
    explained_variance_ratio_: (k,) fraction of total variance per component
    """

    def __init__(
        self,
        n_components: Optional[int | float] = None,
        whiten: bool = False,
        eps: float = 1e-8,
    ):
        self.n_components = n_components
        self.whiten = whiten
        self.eps = float(eps)
        self.mean_: Optional[np.ndarray] = None
        self.components_: Optional[np.ndarray] = None
        self.explained_variance_: Optional[np.ndarray] = None
        self.explained_variance_ratio_: Optional[np.ndarray] = None

    def fit(self, X: np.ndarray) -> "FeaturePCA":
        """Fit PCA on data X (N, D)."""
        X = np.asarray(X, dtype=np.float64)
        N, D = X.shape
        self.mean_ = X.mean(axis=0)
        Xc = X - self.mean_

        # Economy-mode SVD
        U, S, Vt = np.linalg.svd(Xc, full_matrices=False)  # Vt: (min(N,D), D)
        ev = (S ** 2) / max(N - 1, 1)
        total_var = float(ev.sum()) or 1.0

        # Decide number of components
        k = Vt.shape[0]
        if self.n_components is None:
            pass
        elif isinstance(self.n_components, float) and 0.0 < self.n_components < 1.0:
            cumev = np.cumsum(ev) / total_var
            k = int(np.searchsorted(cumev, self.n_components) + 1)
            k = min(k, Vt.shape[0])
        else:
            k = min(int(self.n_components), Vt.shape[0])

        self.components_ = Vt[:k].astype(np.float32)
        self.explained_variance_ = ev[:k].astype(np.float32)
        self.explained_variance_ratio_ = (ev[:k] / total_var).astype(np.float32)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Project X onto fitted components."""
        if self.components_ is None:
            raise RuntimeError("FeaturePCA not fitted. Call fit() first.")
        X = np.asarray(X, dtype=np.float64)
        Xc = X - self.mean_
        Z = Xc @ self.components_.T.astype(np.float64)
        if self.whiten:
            scale = np.sqrt(self.explained_variance_.astype(np.float64)) + self.eps
            Z /= scale
        return Z.astype(np.float32)

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """Fit then transform in one call."""
        return self.fit(X).transform(X)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise fitted state to a JSON-safe dict."""
        return {
            "n_components":             self.n_components,
            "whiten":                   self.whiten,
            "eps":                      self.eps,
            "mean":                     self.mean_.tolist() if self.mean_ is not None else None,
            "components":               self.components_.tolist() if self.components_ is not None else None,
            "explained_variance":       self.explained_variance_.tolist() if self.explained_variance_ is not None else None,
            "explained_variance_ratio": self.explained_variance_ratio_.tolist() if self.explained_variance_ratio_ is not None else None,
        }

    @classmethod
    def from_dict(cls, state: Dict[str, Any]) -> "FeaturePCA":
        """Reconstruct from dict produced by to_dict()."""
        obj = cls(n_components=state["n_components"], whiten=state["whiten"], eps=state["eps"])
        if state.get("mean") is not None:
            obj.mean_ = np.asarray(state["mean"], dtype=np.float64)
        if state.get("components") is not None:
            obj.components_ = np.asarray(state["components"], dtype=np.float32)
        if state.get("explained_variance") is not None:
            obj.explained_variance_ = np.asarray(state["explained_variance"], dtype=np.float32)
        if state.get("explained_variance_ratio") is not None:
            obj.explained_variance_ratio_ = np.asarray(state["explained_variance_ratio"], dtype=np.float32)
        return obj