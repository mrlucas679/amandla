"""
harps.train.monitoring — convergence tracking and gradient diagnostics.

ConvergenceTracker records per-iteration statistics and produces:
  - 4-panel convergence figure (objective, diff, max-grad, weight/bias bars)
  - Per-layer gradient heatmaps
  - Top-K |grad| CSV
  - Iterations CSV
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable, List, Tuple, Optional
from pathlib import Path
import csv

import torch
import numpy as np
import matplotlib
matplotlib.use("Agg")   # non-interactive backend safe for headless server
import matplotlib.pyplot as plt


@dataclass
class ConvergenceLog:
    """Accumulated per-iteration convergence statistics."""
    iter_ix:            List[int]   = field(default_factory=list)
    obj_penalised:      List[float] = field(default_factory=list)
    obj_penalised_diff: List[float] = field(default_factory=list)
    max_abs_grad:       List[float] = field(default_factory=list)
    mean_grad_weights:  List[float] = field(default_factory=list)
    mean_grad_biases:   List[float] = field(default_factory=list)


def _l1_l2_penalty(params: Iterable, l1: float, l2: float) -> torch.Tensor:
    """Compute L1 + L2 penalty term for logging (not for optimization)."""
    device = next(p for p in params if p.requires_grad).device
    total  = torch.tensor(0.0, device=device)
    for p in params:
        if not p.requires_grad:
            continue
        if l1:
            total = total + l1 * p.abs().sum()
        if l2:
            total = total + 0.5 * l2 * (p * p).sum()
    return total


def fullbatch_grad_norm(
    model,
    X_np: np.ndarray,
    y_np: np.ndarray,
    criterion,
    l1: float = 0.0,
    l2: float = 0.0,
    batch_size: int = 4096,
    device=None,
) -> Tuple[float, float]:
    """
    Compute the exact full-batch gradient norm ‖∇L‖₂.

    Args:
        model:      PyTorch model.
        X_np:       Input features (N, D) float32 array.
        y_np:       Labels (N,) int array.
        criterion:  Loss function (CrossEntropyLoss etc.).
        l1, l2:     Regularisation lambdas.
        batch_size: Mini-batch size for accumulation (memory limit).
        device:     Torch device (auto-detects from model params if None).

    Returns:
        (grad_norm, mean_objective)
    """
    if device is None:
        device = next(model.parameters()).device

    torch.set_grad_enabled(True)
    model.train()
    model.zero_grad(set_to_none=True)

    N = int(X_np.shape[0])
    total_obj = 0.0

    for i in range(0, N, batch_size):
        xb = torch.as_tensor(X_np[i:i + batch_size], dtype=torch.float32, device=device)
        yb = torch.as_tensor(y_np[i:i + batch_size], dtype=torch.long, device=device)
        logits    = model(xb)
        reduction = getattr(criterion, "reduction", "mean")
        if reduction == "mean":
            loss_b = criterion(logits, yb) * (xb.shape[0] / N)
        elif reduction == "sum":
            loss_b = criterion(logits, yb) / N
        else:
            loss_b = criterion(logits, yb).sum() / N
        loss_b.backward()
        total_obj += float(loss_b.detach().cpu())

    if l1 or l2:
        pen_terms = []
        for p in model.parameters():
            if not p.requires_grad:
                continue
            if l1:
                pen_terms.append(l1 * p.abs().sum())
            if l2:
                pen_terms.append(0.5 * l2 * (p * p).sum())
        if pen_terms:
            pen = torch.stack(pen_terms).sum()
            total_obj += float(pen.detach().cpu())
            pen.backward()

    grads  = [p.grad.reshape(-1) for p in model.parameters() if p.grad is not None]
    g_norm = torch.cat(grads).norm().item() if grads else 0.0
    return g_norm, total_obj


class ConvergenceTracker:
    """
    Per-iteration convergence recorder.

    Call ``step()`` after ``loss.backward()`` and before ``optimizer.step()``.
    The tracker accumulates across chunks so convergence plots span the full
    training run.

    Args:
        l1_lambda:      L1 regularisation lambda (for penalty display only).
        l2_lambda:      L2 / weight-decay lambda.
        grad_threshold: Reference line drawn on gradient plots.
    """

    def __init__(
        self,
        l1_lambda: float = 0.0,
        l2_lambda: float = 0.0,
        grad_threshold: float = 1e-3,
    ):
        self.l1_lambda      = l1_lambda
        self.l2_lambda      = l2_lambda
        self.grad_threshold = grad_threshold
        self.log            = ConvergenceLog()
        self._last_obj: Optional[float] = None
        self.last_grads: dict = {}

    @torch.no_grad()
    def step(
        self,
        model: torch.nn.Module,
        data_loss: torch.Tensor,
        iteration: int,
        extra_penalty: Optional[torch.Tensor] = None,
    ) -> None:
        """
        Record one training step's statistics.

        Args:
            model:         Model whose parameters' gradients are recorded.
            data_loss:     Data loss tensor (after backward).
            iteration:     Global step index.
            extra_penalty: Optional additional penalty tensor for logging.
        """
        penalty = _l1_l2_penalty(model.parameters(), self.l1_lambda, self.l2_lambda)
        if extra_penalty is not None:
            penalty = penalty + extra_penalty.detach()
        obj = (data_loss.detach() + penalty.detach()).item()

        self.log.obj_penalised.append(obj)
        diff = 0.0 if self._last_obj is None else obj - self._last_obj
        self.log.obj_penalised_diff.append(diff)
        self._last_obj = obj

        grads = [p.grad.detach().abs().max().item()
                 for p in model.parameters() if p.grad is not None]
        self.log.max_abs_grad.append(max(grads) if grads else 0.0)

        w_grads, b_grads = [], []
        for name, p in model.named_parameters():
            if p.grad is None:
                continue
            g = p.grad.detach().abs().reshape(-1)
            if "bias" in name:
                b_grads.append(g)
            else:
                w_grads.append(g)
        self.log.mean_grad_weights.append(
            torch.cat(w_grads).mean().item() if w_grads else 0.0
        )
        self.log.mean_grad_biases.append(
            torch.cat(b_grads).mean().item() if b_grads else 0.0
        )
        self.log.iter_ix.append(iteration)

        self.last_grads = {
            name: p.grad.detach().float().cpu().clone()
            for name, p in model.named_parameters()
            if p.grad is not None
        }

    def save_iter_csv(self, path: str) -> None:
        """Write per-iteration log to CSV."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["iter", "obj_penalised", "obj_penalised_diff",
                         "max_abs_grad", "mean_grad_weights", "mean_grad_biases"])
            for row in zip(
                self.log.iter_ix, self.log.obj_penalised,
                self.log.obj_penalised_diff, self.log.max_abs_grad,
                self.log.mean_grad_weights, self.log.mean_grad_biases
            ):
                w.writerow(list(row))

    def plot_4panel(
        self, lambda_note: Optional[str] = None, figsize=(11, 9)
    ) -> plt.Figure:
        """Generate 4-panel convergence figure."""
        it  = np.asarray(self.log.iter_ix, dtype=float)
        fig, axs = plt.subplots(2, 2, figsize=figsize)

        axs[0, 0].plot(it, self.log.obj_penalised, lw=0.7)
        axs[0, 0].set_title("Penalised objective")
        axs[0, 0].set_xlabel("Iteration"); axs[0, 0].set_ylabel("obj")
        if lambda_note:
            axs[0, 0].text(0.02, 0.85, lambda_note, transform=axs[0, 0].transAxes)

        axs[0, 1].plot(it, self.log.obj_penalised_diff, lw=0.5)
        axs[0, 1].axhline(0.0, ls="--", lw=0.6, color="grey")
        axs[0, 1].set_title("Objective (differenced)")
        axs[0, 1].set_xlabel("Iteration"); axs[0, 1].set_ylabel("diff")

        axs[1, 0].plot(it, self.log.max_abs_grad, lw=0.7, label="max |grad|")
        axs[1, 0].axhline(self.grad_threshold, ls="--", lw=0.8, color="grey",
                          label=f"threshold={self.grad_threshold}")
        axs[1, 0].set_title("Maximum abs gradient")
        axs[1, 0].set_xlabel("Iteration"); axs[1, 0].set_ylabel("max |grad|")
        axs[1, 0].legend(fontsize=8)

        last_w = self.log.mean_grad_weights[-1] if self.log.mean_grad_weights else 0.0
        last_b = self.log.mean_grad_biases[-1] if self.log.mean_grad_biases else 0.0
        axs[1, 1].bar([0, 1], [last_w, last_b], tick_label=["weights", "biases"])
        axs[1, 1].axhline(self.grad_threshold, ls="--", lw=0.8, color="grey")
        axs[1, 1].set_title("Parameter gradients (last step)")
        axs[1, 1].set_ylabel("mean |grad|")

        plt.tight_layout()
        return fig

    def plot_layer_grad_heatmap(
        self, layer: str, which: str = "weight", cmap: str = "viridis"
    ) -> Optional[plt.Figure]:
        """
        Plot |grad| heatmap for one layer parameter.

        Args:
            layer: Layer name prefix (e.g. "fc1").
            which: "weight" or "bias".
            cmap:  Matplotlib colormap name.

        Returns:
            Matplotlib Figure or None if gradients not available.
        """
        key = f"{layer}.{which}"
        g   = self.last_grads.get(key)
        if g is None:
            return None

        G   = g.abs().cpu().numpy()
        fig = plt.figure(figsize=(8, 4))
        ax  = fig.add_subplot(1, 1, 1)
        if G.ndim == 2:
            im = ax.imshow(G, aspect="auto", cmap=cmap)
            ax.set_title(f"{key} |grad|")
            ax.set_xlabel("in features"); ax.set_ylabel("out units")
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        else:
            ax.plot(G, marker="o", lw=1)
            ax.set_title(f"{key} |grad|")
            ax.set_xlabel("unit index"); ax.set_ylabel("|grad|")
        fig.tight_layout()
        return fig

    def topk_param_grads(self, k: int = 20) -> list:
        """Return top-K |grad| entries across all parameters at last step."""
        items = []
        for name, g in self.last_grads.items():
            flat = g.abs().view(-1)
            if flat.numel() == 0:
                continue
            vals, idx = torch.topk(flat, min(k, flat.numel()))
            shape = tuple(g.shape)
            for v, i in zip(vals.tolist(), idx.tolist()):
                items.append((name, np.unravel_index(int(i), shape), float(v)))
        items.sort(key=lambda x: x[2], reverse=True)
        return items[:k]

    def save_topk_param_grads_csv(self, path: str, k: int = 20) -> None:
        """Write top-K |grad| CSV."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        rows = self.topk_param_grads(k=k)
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["parameter", "index", "abs_grad"])
            for name, idx, val in rows:
                w.writerow([name, str(tuple(int(i) for i in idx)), f"{val:.8g}"])