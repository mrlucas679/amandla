"""
harps.utils.cache — helpers for .npz caching of intermediate features.

All dataset preprocessing and feature extraction results are stored as .npz
files so they survive restarts and can be reused across experiment runs.
"""

import os
import numpy as np


def ensure_dir(path: str) -> None:
    """Create directory (and parents) if it does not already exist."""
    os.makedirs(path, exist_ok=True)


def save_npz(path: str, **arrays) -> None:
    """
    Save arrays to a .npz file, creating parent directories as needed.

    Args:
        path:    Destination file path (will be created or overwritten).
        **arrays: Named numpy arrays to store.
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    np.savez(path, **arrays)


def load_npz(path: str) -> np.lib.npyio.NpzFile:
    """
    Load a .npz file previously saved with save_npz.

    Args:
        path: Path to the .npz file.

    Returns:
        NpzFile object whose keys map to numpy arrays.
    """
    return np.load(path, allow_pickle=True)