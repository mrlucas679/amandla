"""
harps.train.checkpoint — save and load PyTorch training checkpoints.

All checkpoint writes in HARPS go through these functions. Never call
torch.save/load directly in experiment code.
"""

import os
import torch


def save_checkpoint(
    path: str,
    epoch: int,
    model,
    optimizer=None,
    scheduler=None,
    extra: dict = None,
) -> None:
    """
    Save a training checkpoint to disk.

    Args:
        path:      Destination file path (.pth). Parent dirs are created.
        epoch:     Current epoch number (for resume tracking).
        model:     PyTorch nn.Module whose state_dict is saved.
        optimizer: Optional optimizer whose state is saved.
        scheduler: Optional LR scheduler whose state is saved.
        extra:     Optional dict of additional values to store (e.g.
                   {"class_names": [...], "input_dim": 840, "feature_set": "T-J-PSF"}).
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    payload = {"epoch": epoch, "model_state_dict": model.state_dict()}
    if optimizer is not None:
        payload["optimizer_state_dict"] = optimizer.state_dict()
    if scheduler is not None:
        payload["scheduler_state_dict"] = scheduler.state_dict()
    if extra:
        payload.update(extra)
    torch.save(payload, path)


def load_checkpoint(
    path: str,
    model=None,
    optimizer=None,
    scheduler=None,
) -> dict:
    """
    Load a checkpoint and restore model / optimizer / scheduler state.

    Args:
        path:      Path to the .pth checkpoint file.
        model:     If provided, loads model_state_dict into it.
        optimizer: If provided, loads optimizer_state_dict if present.
        scheduler: If provided, loads scheduler_state_dict if present.

    Returns:
        The raw checkpoint dict (contains "epoch" and any extra fields).
    """
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    if model is not None:
        model.load_state_dict(ckpt["model_state_dict"])
    if optimizer is not None and "optimizer_state_dict" in ckpt:
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
    if scheduler is not None and "scheduler_state_dict" in ckpt:
        scheduler.load_state_dict(ckpt["scheduler_state_dict"])
    return ckpt