"""
harps.datasets.base — protocol and type definitions shared by all adapters.

Every dataset adapter must satisfy the PoseDataset protocol so transforms and
the FeatureCacheBuilder can operate without knowing which dataset is in use.

Sample contract
---------------
Each __getitem__ call returns a dict::

    {
        "X":    np.ndarray of shape (T, J, C),   # time × joints × coords
        "y":    int,                              # integer class label
        "meta": dict,                             # arbitrary metadata
    }
"""

from typing import Protocol, Dict, Any, List, Tuple, Optional
import numpy as np

# Canonical sample type used throughout HARPS
Sample = Dict[str, Any]  # {"X": np.ndarray(T,J,C), "y": int, "meta": dict}


class PoseDataset(Protocol):
    """
    Structural protocol for skeleton / pose datasets.

    Any class that implements __len__, __getitem__, class_names, and swap_pairs
    satisfies this protocol without explicit inheritance.
    """

    class_names: List[str]
    joint_names: Optional[List[str]]
    fps: Optional[float]

    def __len__(self) -> int:
        """Return total number of samples."""
        ...

    def __getitem__(self, idx: int) -> Sample:
        """Return one sample dict {"X": ndarray(T,J,C), "y": int, "meta": dict}."""
        ...

    def swap_pairs(self) -> Optional[List[Tuple[int, int]]]:
        """Return list of (right_idx, left_idx) joint pairs for horizontal flip."""
        ...