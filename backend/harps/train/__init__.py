"""
harps.train — training utilities for HARPS classifiers.
"""
from .trainer      import Trainer, TrainConfig
from .mlp_trainer  import MLPTrainer, TrainConfigMLP
from .checkpoint   import save_checkpoint, load_checkpoint
from .monitoring   import ConvergenceTracker, ConvergenceLog, fullbatch_grad_norm
from ._spike_logger import SpikeLogger, SpikeEvent

__all__ = [
    "Trainer", "TrainConfig",
    "MLPTrainer", "TrainConfigMLP",
    "save_checkpoint", "load_checkpoint",
    "ConvergenceTracker", "ConvergenceLog", "fullbatch_grad_norm",
    "SpikeLogger", "SpikeEvent",
]