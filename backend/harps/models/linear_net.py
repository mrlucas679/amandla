"""
harps.models.linear_net — paper-authentic linear classifier.

Identical architecture to MLPClassifier but with explicit documentation
that this is the "paper-authentic" linear variant: no activations, no
dropout, DropConnect applied externally by the Trainer.
"""

import torch
import torch.nn as nn


class LinearNet(nn.Module):
    """
    Paper-authentic two-layer linear classifier (no non-linearities).

    x → Linear(input_dim, hidden_dim) → Linear(hidden_dim, num_classes)

    DropConnect is applied in the Trainer on fc1.weight, not here.

    Args:
        input_dim:   Input feature dimensionality.
        hidden_dim:  Hidden layer width (default 64).
        num_classes: Output class count (default 21 for JHMDB).
    """

    def __init__(self, input_dim: int, hidden_dim: int = 64, num_classes: int = 21):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim, bias=True)
        self.fc2 = nn.Linear(hidden_dim, num_classes, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass with no non-linearity.

        Args:
            x: (batch_size, input_dim) float tensor.

        Returns:
            logits: (batch_size, num_classes) float tensor.
        """
        h = self.fc1(x)    # no activation
        return self.fc2(h)