"""
harps.datasets — adapters for skeleton/pose action recognition datasets.

Available adapters
------------------
JHMDB  : 2D joints from video, 15 joints, 21 action classes
MHAD   : 3D mocap, 43 joints, 11 action classes
WLASL  : OpenPose hand landmarks, 55 joints (configurable), 100–2000 sign classes

All adapters follow the PoseDataset protocol and return samples as::

    {"X": np.ndarray(T, J, C), "y": int, "meta": dict}

Use ``make_dataset("name", ...)`` to instantiate by name, or import directly.
"""

from .jhmdb    import JHMDB, build_jhmdb
from .mhad     import MHAD, build_mhad
from .wlasl    import WLASL, build_wlasl
from .cache    import FeatureCacheBuilder, load_scaled_npz, combine_from_cache
from .registry import make_dataset, register, list_datasets, has_dataset
from .base     import PoseDataset, Sample

__all__ = [
    "JHMDB", "build_jhmdb",
    "MHAD",  "build_mhad",
    "WLASL", "build_wlasl",
    "FeatureCacheBuilder", "load_scaled_npz", "combine_from_cache",
    "make_dataset", "register", "list_datasets", "has_dataset",
    "PoseDataset", "Sample",
]