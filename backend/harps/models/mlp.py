"""
harps.models.mlp — two-layer MLP classifier for action/sign recognition.

Architecture: Linear(input_dim → hidden_dim) → Linear(hidden_dim → num_classes)
No non-linearity between layers (identity activation, per HARPS paper).
DropConnect is applied by the Trainer during training, not here.
"""

import torch
import torch.nn as nn


class MLPClassifier(nn.Module):
    """
    Two-layer linear network for PSF feature classification.

    The first layer projects input features to a hidden representation;
    the second layer produces class logits. No activation is applied
    between layers (identity / linear classifier) — this matches the
    HARPS paper's design where the PSF features provide rich nonlinear
    structure and the network acts as a linear head.

    Args:
        input_dim:   Dimensionality of the input feature vector.
        hidden_dim:  Number of hidden units (default 64).
        num_classes: Number of output classes.
    """

    def __init__(self, input_dim: int, hidden_dim: int = 64, num_classes: int = 21):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.out = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Tensor of shape (batch_size, input_dim).

        Returns:
            logits: Tensor of shape (batch_size, num_classes).
        """
        h = self.fc1(x)       # identity activation (no ReLU)
        return self.out(h)