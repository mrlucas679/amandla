"""
harps.train._spike_logger — detect and log loss spikes during training.

A "spike" is any iteration where the loss increases by more than
``threshold`` × the running mean loss.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import csv
from pathlib import Path


@dataclass
class SpikeEvent:
    iteration: int
    loss_before: float
    loss_after:  float
    ratio:       float


class SpikeLogger:
    """
    Detect loss spikes and optionally revert them.

    Args:
        threshold: Ratio above which a step is a spike
                   (loss_new / loss_old > threshold).
        window:    Rolling window size for computing mean loss.
    """

    def __init__(self, threshold: float = 2.0, window: int = 20):
        self.threshold = threshold
        self.window    = window
        self._history: List[float] = []
        self.spikes:   List[SpikeEvent] = []

    def check(self, iteration: int, loss: float) -> bool:
        """
        Record ``loss`` and return True if it is a spike.

        Args:
            iteration: Current training iteration index.
            loss:      Current loss value.

        Returns:
            True if this step is classified as a spike.
        """
        is_spike = False
        if self._history:
            window_slice = self._history[-self.window:]
            mean_prev    = sum(window_slice) / len(window_slice)
            if mean_prev > 0 and (loss / mean_prev) > self.threshold:
                last = self._history[-1]
                self.spikes.append(SpikeEvent(
                    iteration    = iteration,
                    loss_before  = last,
                    loss_after   = loss,
                    ratio        = loss / mean_prev,
                ))
                is_spike = True
        self._history.append(loss)
        return is_spike

    def save_csv(self, path: str) -> None:
        """Write all spike events to a CSV file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["iteration", "loss_before", "loss_after", "ratio"])
            for ev in self.spikes:
                w.writerow([ev.iteration, ev.loss_before, ev.loss_after, f"{ev.ratio:.4f}"])

    def summary(self) -> str:
        return f"SpikeLogger: {len(self.spikes)} spikes detected (threshold={self.threshold})"
