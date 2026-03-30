"""
harps.train.mlp_trainer — MLPTrainer with extended epoch budget.

Thin wrapper over Trainer that uses TrainConfigMLP defaults
(300 epochs, same SGD+DropConnect+L1 protocol).
"""

from __future__ import annotations
from dataclasses import dataclass

import numpy as np
import torch.nn as nn

from .trainer import Trainer, TrainConfig


@dataclass
class TrainConfigMLP(TrainConfig):
    """Default config for two-layer MLP (longer training budget)."""
    epochs:         int   = 300
    lr0:            float = 0.005
    lr_decay:       float = 0.005
    momentum:       float = 0.7
    batch_size:     int   = 30
    drop_connect_p: float = 0.0
    l1_lambda:      float = 0.0
    l2_lambda:      float = 0.0


class MLPTrainer(Trainer):
    """
    Trainer subclass for MLPClassifier with 300-epoch default.

    Drop-in replacement for Trainer — only the default config differs.

    Args:
        model:     MLPClassifier or LinearNet instance.
        config:    TrainConfigMLP (defaults to 300 epochs).
        criterion: Loss function (default CrossEntropyLoss).
    """

    def __init__(
        self,
        model:     nn.Module,
        config:    TrainConfigMLP = None,
        criterion: nn.Module      = None,
    ):
        super().__init__(
            model     = model,
            config    = config or TrainConfigMLP(),
            criterion = criterion,
        )