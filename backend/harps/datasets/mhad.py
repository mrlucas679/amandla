"""
MHAD dataset adapter — Berkeley Multimodal Human Action Dataset.

Expected directory layout::

    root/
      Mocap/
        moc_s##_a##_r##.txt   (motion-capture text files, 43 joints × 3 coords)

Each file has rows of whitespace-separated floats; one row per time step.
T-pose calibration files (a00) are skipped automatically.

Sample shape: {"X": (T, 43, 3), "y": int, "meta": dict}
"""

from __future__ import annotations
import os
import re
from typing import List, Tuple, Literal, Optional, Dict

import numpy as np
from sklearn.model_selection import StratifiedKFold, StratifiedShuffleSplit

from .registry import register

# Official subject groups for cross-subject split
_TRAIN_SUBJECTS = {1, 2, 3, 4, 5}
_TEST_SUBJECTS  = {6, 7}

# Left/right joint pair indices (for RandomFlipLR)
_MIRROR_PAIRS = [
    (1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12),
    (13, 14), (15, 16), (17, 18), (19, 20), (21, 22),
    (23, 24), (25, 26), (27, 28), (29, 30), (31, 32),
    (33, 34),
]
RIGHT_IDX = [p[0] for p in _MIRROR_PAIRS]
LEFT_IDX  = [p[1] for p in _MIRROR_PAIRS]


def _parse_filename(fname: str) -> Optional[Dict]:
    """Extract (subject, action, repetition) from moc_s##_a##_r##.txt."""
    m = re.match(r"moc_s(\d+)_a(\d+)_r(\d+)\.txt$", fname)
    if m is None:
        return None
    s, a, r = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if a == 0:
        return None  # T-pose calibration
    return {"subject": s, "action": a, "repetition": r}


def _load_clip(path: str) -> np.ndarray:
    """Load a MHAD .txt file as (T, 43, 3) float32."""
    data = np.loadtxt(path, dtype=np.float32)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    T = data.shape[0]
    return data.reshape(T, 43, 3)


@register("mhad")
def build_mhad(
    root: str,
    split: Literal["train", "val", "test"],
    strategy: Literal["subject", "kfold", "random"] = "subject",
    seed: int = 0,
    n_splits: int = 5,
    fold_index: int = 0,
    val_ratio: float = 0.1,
    indices: Optional[List[int]] = None,
) -> "MHAD":
    """Construct a MHAD split. See MHAD class for parameter docs."""
    return MHAD(
        root=root, split=split, strategy=strategy,
        seed=seed, n_splits=n_splits, fold_index=fold_index,
        val_ratio=val_ratio, indices=indices,
    )


class MHAD:
    """
    Adapter for Berkeley MHAD motion-capture data.

    Attributes
    ----------
    class_names : list of action label strings
    JOINT_COUNT : 43
    COORD_SIZE  : 3
    """

    JOINT_COUNT = 43
    COORD_SIZE  = 3

    def __init__(
        self,
        root: str,
        split: Literal["train", "val", "test"] = "train",
        strategy: Literal["subject", "kfold", "random"] = "subject",
        seed: int = 0,
        n_splits: int = 5,
        fold_index: int = 0,
        val_ratio: float = 0.1,
        indices: Optional[List[int]] = None,
    ):
        self.root = os.path.abspath(root)
        mocap_dir = os.path.join(self.root, "Mocap")
        if not os.path.isdir(mocap_dir):
            raise FileNotFoundError(f"Expected Mocap/ directory at: {mocap_dir}")

        # Discover all clips
        all_items = []
        for fname in sorted(os.listdir(mocap_dir)):
            meta = _parse_filename(fname)
            if meta is None:
                continue
            path = os.path.join(mocap_dir, fname)
            all_items.append({**meta, "path": path})

        if not all_items:
            raise RuntimeError(f"No valid .txt clips found in {mocap_dir}")

        # Build class names from unique action indices
        actions = sorted({it["action"] for it in all_items})
        self.class_names = [f"action_{a:02d}" for a in actions]
        self._action_to_label = {a: i for i, a in enumerate(actions)}

        # Assign labels
        for it in all_items:
            it["label"] = self._action_to_label[it["action"]]

        # Build splits
        if strategy == "subject":
            train_items = [it for it in all_items if it["subject"] in _TRAIN_SUBJECTS]
            test_items  = [it for it in all_items if it["subject"] in _TEST_SUBJECTS]
            if val_ratio > 0 and split != "test":
                y   = np.array([it["label"] for it in train_items], dtype=int)
                sss = StratifiedShuffleSplit(n_splits=1, test_size=val_ratio, random_state=seed)
                (tr_idx, va_idx), = sss.split(np.zeros(len(y)), y)
                val_items   = [train_items[i] for i in va_idx]
                train_items = [train_items[i] for i in tr_idx]
            else:
                val_items = []
            pools = {"train": train_items, "val": val_items, "test": test_items}

        elif strategy == "kfold":
            all_items_s = sorted(all_items, key=lambda x: (x["subject"], x["action"], x["repetition"]))
            y   = np.array([it["label"] for it in all_items_s], dtype=int)
            skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
            folds = list(skf.split(np.zeros(len(y)), y))
            tr_idx, te_idx = folds[fold_index]
            train_items = [all_items_s[i] for i in tr_idx]
            test_items  = [all_items_s[i] for i in te_idx]
            pools = {"train": train_items, "val": [], "test": test_items}

        else:  # random
            all_items_s = sorted(all_items, key=lambda x: (x["subject"], x["action"], x["repetition"]))
            y    = np.array([it["label"] for it in all_items_s], dtype=int)
            sss  = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
            (tr_idx, te_idx), = sss.split(np.zeros(len(y)), y)
            train_items = [all_items_s[i] for i in tr_idx]
            test_items  = [all_items_s[i] for i in te_idx]
            pools = {"train": train_items, "val": [], "test": test_items}

        self._items = pools[split]
        if indices is not None:
            self._items = [self._items[i] for i in indices if 0 <= i < len(self._items)]

    def __len__(self) -> int:
        """Return number of clips in this split."""
        return len(self._items)

    def __getitem__(self, idx: int) -> dict:
        """Load one MHAD clip and return HARPS sample dict."""
        it = self._items[idx]
        X  = _load_clip(it["path"])
        return {
            "X": X,
            "y": int(it["label"]),
            "meta": {
                "dataset":    "mhad",
                "path":       it["path"],
                "subject":    it["subject"],
                "action":     it["action"],
                "repetition": it["repetition"],
                "T":          int(X.shape[0]),
                "fps":        None,
                "modality":   "3d_mocap",
            },
        }

    @classmethod
    def swap_pairs(cls) -> Tuple[List[int], List[int]]:
        """Right/left joint pairs for horizontal flip."""
        return RIGHT_IDX, LEFT_IDX

    @classmethod
    def joint_count(cls) -> int:
        """Number of joints per frame (43)."""
        return cls.JOINT_COUNT

    @classmethod
    def coord_size(cls) -> int:
        """Coordinate dimensions per joint (3 for MHAD)."""
        return cls.COORD_SIZE