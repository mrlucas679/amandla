"""
harps.utils.seed — random seed utilities for reproducibility.
"""

import random
import numpy as np


def set_seeds(seed: int = 123) -> None:
    """
    Set random seeds for Python, NumPy, and PyTorch (if installed).

    Args:
        seed: Integer seed value (default 123).
    """
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass