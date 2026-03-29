"""
harps.train.trainer — full training loop for HARPS LinearNet / MLPClassifier.

Implements the exact training protocol from the HARPS paper:
  - SGD with momentum + exponential LR decay
  - DropConnect on fc1.weight
  - L1 + L2 regularisation
  - SpikeLogger for spike detection
  - ConvergenceTracker for gradient diagnostics
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import math

import torch
import torch.nn as nn
import numpy as np

from .monitoring   import ConvergenceTracker
from ._spike_logger import SpikeLogger
from .checkpoint   import save_checkpoint


@dataclass
class TrainConfig:
    """Hyper-parameters for the HARPS paper training protocol."""
    batch_size:     int   = 30
    epochs:         int   = 50
    lr0:            float = 0.005    # initial learning rate
    lr_decay:       float = 0.005    # exponential decay coefficient
    momentum:       float = 0.7
    l1_lambda:      float = 0.0
    l2_lambda:      float = 0.0      # weight-decay equivalent
    drop_connect_p: float = 0.0      # DropConnect probability on fc1.weight
    grad_threshold: float = 1e-3     # reference line on convergence plots
    spike_threshold: float = 2.0
    spike_window:    int   = 20
    seed:            int   = 42
    device:          str   = "cpu"


class Trainer:
    """
    Train a LinearNet or MLPClassifier using the HARPS protocol.

    Args:
        model:     PyTorch model (LinearNet or MLPClassifier).
        config:    TrainConfig hyper-parameters.
        criterion: Loss function (default CrossEntropyLoss).
    """

    def __init__(
        self,
        model:     nn.Module,
        config:    TrainConfig = None,
        criterion: nn.Module   = None,
    ):
        self.config    = config or TrainConfig()
        self.device    = torch.device(self.config.device)
        self.model     = model.to(self.device)
        self.criterion = criterion or nn.CrossEntropyLoss()

        # Reproducibility
        torch.manual_seed(self.config.seed)
        np.random.seed(self.config.seed)

        self.optimizer = torch.optim.SGD(
            self.model.parameters(),
            lr       = self.config.lr0,
            momentum = self.config.momentum,
            weight_decay = self.config.l2_lambda,
        )

        self.tracker = ConvergenceTracker(
            l1_lambda      = self.config.l1_lambda,
            l2_lambda      = self.config.l2_lambda,
            grad_threshold = self.config.grad_threshold,
        )
        self.spike_logger = SpikeLogger(
            threshold = self.config.spike_threshold,
            window    = self.config.spike_window,
        )

        self._global_step = 0

    def _lr_at_epoch(self, epoch: int) -> float:
        """Exponential LR decay: lr = lr0 * exp(-decay * epoch)."""
        return self.config.lr0 * math.exp(-self.config.lr_decay * epoch)

    def _apply_drop_connect(self, module: nn.Module) -> Optional[torch.Tensor]:
        """
        Apply DropConnect to fc1.weight in-place during forward.

        Returns the original weight tensor so it can be restored after
        the forward + backward pass.
        """
        if self.config.drop_connect_p <= 0.0:
            return None
        fc1 = getattr(module, "fc1", None)
        if fc1 is None:
            return None
        original = fc1.weight.data.clone()
        mask = torch.bernoulli(
            torch.ones_like(fc1.weight.data) * (1.0 - self.config.drop_connect_p)
        )
        fc1.weight.data = fc1.weight.data * mask / max(1e-7, 1.0 - self.config.drop_connect_p)
        return original

    def _restore_drop_connect(self, module: nn.Module, original: Optional[torch.Tensor]) -> None:
        if original is None:
            return
        fc1 = getattr(module, "fc1", None)
        if fc1 is not None:
            fc1.weight.data = original

    def _l1_penalty(self) -> torch.Tensor:
        if self.config.l1_lambda == 0.0:
            return torch.tensor(0.0, device=self.device)
        total = torch.tensor(0.0, device=self.device)
        for p in self.model.parameters():
            if p.requires_grad:
                total = total + p.abs().sum()
        return self.config.l1_lambda * total

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val:   Optional[np.ndarray] = None,
        y_val:   Optional[np.ndarray] = None,
        checkpoint_path: Optional[str] = None,
    ) -> dict:
        """
        Train the model.

        Args:
            X_train:          (N, D) float32 feature array.
            y_train:          (N,) int label array.
            X_val:            Optional validation features.
            y_val:            Optional validation labels.
            checkpoint_path:  If set, save best checkpoint here.

        Returns:
            dict with keys: train_acc, val_acc (if val provided),
            n_epochs, n_steps, spike_count.
        """
        X_t = torch.as_tensor(X_train, dtype=torch.float32, device=self.device)
        y_t = torch.as_tensor(y_train, dtype=torch.long,    device=self.device)
        N   = X_t.shape[0]

        best_val_acc = -1.0
        history: List[dict] = []

        for epoch in range(self.config.epochs):
            # Update learning rate
            for pg in self.optimizer.param_groups:
                pg["lr"] = self._lr_at_epoch(epoch)

            self.model.train()
            perm = torch.randperm(N, device=self.device)
            epoch_loss = 0.0
            n_batches  = 0

            for i in range(0, N, self.config.batch_size):
                idx = perm[i:i + self.config.batch_size]
                xb, yb = X_t[idx], y_t[idx]

                self.optimizer.zero_grad()

                # DropConnect
                saved_w = self._apply_drop_connect(self.model)

                logits = self.model(xb)
                loss   = self.criterion(logits, yb)

                # L1 penalty
                l1_pen = self._l1_penalty()
                total_loss = loss + l1_pen
                total_loss.backward()

                # Restore weights before optimizer step
                self._restore_drop_connect(self.model, saved_w)

                self.tracker.step(self.model, total_loss, self._global_step)
                self.spike_logger.check(self._global_step, float(total_loss.detach().cpu()))

                self.optimizer.step()
                epoch_loss += float(total_loss.detach().cpu())
                n_batches  += 1
                self._global_step += 1

            avg_loss = epoch_loss / max(1, n_batches)

            # Eval
            train_acc = self._accuracy(X_t, y_t)
            val_acc   = None
            if X_val is not None and y_val is not None:
                X_v = torch.as_tensor(X_val, dtype=torch.float32, device=self.device)
                y_v = torch.as_tensor(y_val, dtype=torch.long,    device=self.device)
                val_acc = self._accuracy(X_v, y_v)

                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    if checkpoint_path:
                        save_checkpoint(
                            checkpoint_path, epoch, self.model, self.optimizer,
                            extra={"val_acc": val_acc, "train_acc": train_acc}
                        )

            history.append({
                "epoch":      epoch,
                "loss":       avg_loss,
                "train_acc":  train_acc,
                "val_acc":    val_acc,
            })

        final_train_acc = self._accuracy(X_t, y_t)
        result = {
            "train_acc":   final_train_acc,
            "n_epochs":    self.config.epochs,
            "n_steps":     self._global_step,
            "spike_count": len(self.spike_logger.spikes),
            "history":     history,
        }
        if X_val is not None:
            result["val_acc"] = best_val_acc
        return result

    @torch.no_grad()
    def _accuracy(self, X: torch.Tensor, y: torch.Tensor) -> float:
        self.model.eval()
        preds  = self.model(X).argmax(dim=1)
        return float((preds == y).float().mean().item())

    @torch.no_grad()
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return predicted class indices for X."""
        self.model.eval()
        X_t = torch.as_tensor(X, dtype=torch.float32, device=self.device)
        return self.model(X_t).argmax(dim=1).cpu().numpy()

    @torch.no_grad()
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return softmax probabilities for X."""
        self.model.eval()
        X_t    = torch.as_tensor(X, dtype=torch.float32, device=self.device)
        logits = self.model(X_t)
        return torch.softmax(logits, dim=1).cpu().numpy()