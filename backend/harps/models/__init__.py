"""
harps.models — neural network classifiers for action/sign recognition.

Models
------
MLPClassifier : Two-layer identity-activation MLP (default architecture).
LinearNet     : Paper-authentic variant with explicit no-nonlinearity docs.
"""
from .mlp        import MLPClassifier
from .linear_net import LinearNet

__all__ = ["MLPClassifier", "LinearNet"]