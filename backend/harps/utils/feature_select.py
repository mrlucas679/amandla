"""
harps.utils.feature_select — feature importance computation and masking.

Uses the first linear layer's weights to score input features, then builds
boolean masks for pruning (top-k or threshold-based).
"""

import json
import numpy as np


class FeatureSelector:
    """
    Compute per-input feature importances from a trained model and build masks.

    Importance for feature i is defined as the sum of absolute weights in the
    first hidden layer that connect to that feature:

        importance[i] = sum_j |W_fc1[j, i]|

    This works for both LinearNet and MLPClassifier as both expose fc1.

    Args:
        model:      A PyTorch nn.Module with an ``fc1`` linear layer.
        model_type: "linear" or "mlp" (informational only, not used in computation).
    """

    def __init__(self, model, model_type: str = "linear"):
        self.model = model
        self.model_type = model_type

    def compute_importance(self, mode: str = "l1") -> np.ndarray:
        """
        Compute importance scores for all input features.

        Args:
            mode: "l1" (sum of absolute row weights per input column).

        Returns:
            importance: ndarray of shape (input_dim,).
        """
        try:
            import torch  # noqa: F401
        except ImportError:
            raise ImportError("PyTorch is required for FeatureSelector.compute_importance()")

        if not hasattr(self.model, "fc1"):
            raise ValueError("Model does not have an fc1 layer.")

        import torch
        with torch.no_grad():
            W = self.model.fc1.weight.detach().cpu().numpy()  # (hidden, input_dim)

        if mode == "l1":
            return np.abs(W).sum(axis=0)  # (input_dim,)
        raise ValueError(f"Unsupported importance mode: {mode!r}")

    @staticmethod
    def build_mask_threshold(importance: np.ndarray, threshold: float = 1e-6) -> np.ndarray:
        """
        Boolean mask: True for features whose importance exceeds threshold.

        Args:
            importance: Array of importance scores.
            threshold:  Minimum importance to keep.

        Returns:
            mask: Boolean ndarray of shape (input_dim,).
        """
        imax = float(np.max(importance))
        imin = float(np.min(importance))
        print(f"Importance range: [{imin:.6g}, {imax:.6g}]  threshold={threshold}")
        return (importance > float(threshold)).astype(bool)

    @staticmethod
    def build_mask_topk(importance: np.ndarray, k: int) -> np.ndarray:
        """
        Boolean mask: True for the top-k most important features.

        Args:
            importance: Array of importance scores.
            k:          Number of features to keep.

        Returns:
            mask: Boolean ndarray of shape (input_dim,).
        """
        if k is None or k <= 0:
            raise ValueError("k must be a positive integer.")
        k = min(k, importance.size)
        idx = np.argsort(-importance)[:k]
        mask = np.zeros_like(importance, dtype=bool)
        mask[idx] = True
        kth_val = float(np.sort(importance)[-k]) if k > 0 else None
        print(f"Top-{k} threshold: {kth_val:.6g}  "
              f"range [{float(np.min(importance)):.6g}, {float(np.max(importance)):.6g}]")
        return mask

    @staticmethod
    def apply_mask(X: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Select feature columns where mask is True."""
        return X[:, mask]

    @staticmethod
    def save_mask(mask: np.ndarray, path: str) -> None:
        """Persist a boolean mask as JSON for reuse."""
        with open(path, "w") as f:
            json.dump({"mask": mask.astype(int).tolist()}, f)

    @staticmethod
    def load_mask(path: str) -> np.ndarray:
        """Load a boolean mask previously saved with save_mask."""
        with open(path, "r") as f:
            data = json.load(f)
        return np.array(data["mask"], dtype=bool)