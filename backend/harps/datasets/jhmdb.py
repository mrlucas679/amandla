"""
JHMDB dataset adapter (2D joints).

Expected directory structure::

    root/
      joint_positions/<action>/<clip>/joint_positions.mat
      splits/<action>_test_split1.txt
             <action>_test_split2.txt
             <action>_test_split3.txt

Each .mat clip is loaded as (T, J, 2) float32 via scipy.io.

Validation strategies
---------------------
- "official"              : use official train/test split files
- "official-kfold-train"  : k-fold CV inside the official train set
- "all-kfold"             : k-fold across all clips on disk

Reproducibility
---------------
All folds are deterministic given (seed, n_splits, fold_index) and sorted
item lists.
"""

from __future__ import annotations
import os
import json
from typing import List, Tuple, Literal, Optional

import numpy as np
import scipy.io as sio
from sklearn.model_selection import StratifiedShuffleSplit, StratifiedKFold

from .registry import register

Strategy = Literal["official", "official-kfold-train", "all-kfold"]


@register("jhmdb")
def build_jhmdb(
    root: str,
    split: Literal["train", "val", "test"],
    split_id: int = 1,
    strategy: Strategy = "official",
    make_val_from_train: bool = False,
    val_ratio: float = 0.0,
    seed: int = 0,
    n_splits: int = 5,
    fold_index: int = 0,
    indices: Optional[List[int]] = None,
    write_manifest: bool = False,
    manifest_dir: Optional[str] = None,
) -> "JHMDB":
    """Construct a JHMDB split. See JHMDB class for parameter docs."""
    return JHMDB(
        root=root, split_id=split_id, subset=split,
        strategy=strategy,
        make_val_from_train=make_val_from_train,
        val_ratio=val_ratio,
        seed=seed,
        n_splits=n_splits,
        fold_index=fold_index,
        indices=indices,
        write_manifest=write_manifest,
        manifest_dir=manifest_dir,
    )


class JHMDB:
    """
    Minimal adapter for JHMDB 2D skeleton joints.

    Each sample dict has shape ``{"X": (T, 15, 2), "y": int, "meta": dict}``.

    Class attributes
    ----------------
    joint_names : list of 15 joint name strings
    JOINT_COUNT : 15
    COORD_SIZE  : 2
    """

    joint_names: List[str] = [
        "head",       "neck",      "belly",
        "r_shoulder", "l_shoulder",
        "r_elbow",    "l_elbow",
        "r_wrist",    "l_wrist",
        "r_hip",      "l_hip",
        "r_knee",     "l_knee",
        "r_ankle",    "l_ankle",
    ]

    RIGHT_IDX   = [3, 5, 7,  9, 11, 13]
    LEFT_IDX    = [4, 6, 8, 10, 12, 14]
    JOINT_COUNT = 15
    COORD_SIZE  = 2

    def __init__(
        self,
        root: str,
        split_id: int = 1,
        subset: Literal["train", "val", "test"] = "train",
        strategy: Strategy = "official",
        make_val_from_train: bool = False,
        val_ratio: float = 0.0,
        seed: int = 0,
        n_splits: int = 5,
        fold_index: int = 0,
        indices: Optional[List[int]] = None,
        write_manifest: bool = False,
        manifest_dir: Optional[str] = None,
    ):
        if subset not in {"train", "val", "test"}:
            raise ValueError("subset must be 'train', 'val', or 'test'")

        self.root        = os.path.abspath(root)
        self.joints_path = os.path.join(self.root, "joint_positions")
        self.splits_path = os.path.join(self.root, "splits")

        for pth, label in [(self.joints_path, "joint_positions"), (self.splits_path, "splits")]:
            if not os.path.isdir(pth):
                raise FileNotFoundError(f"Missing {label} directory: {pth}")

        self.actions: List[str] = sorted(
            a for a in os.listdir(self.joints_path)
            if not a.startswith(".") and os.path.isdir(os.path.join(self.joints_path, a))
        )
        if not self.actions:
            raise RuntimeError("No action folders found under joint_positions/")

        self.action_to_label = {a: i for i, a in enumerate(self.actions)}
        self.class_names = self.actions

        official_train, official_test = self._official_partition(split_id)
        official_train = sorted(official_train, key=lambda p: (p[0], p[1]))
        official_test  = sorted(official_test,  key=lambda p: (p[0], p[1]))

        val_pairs: List[Tuple[str, str]] = []

        if strategy == "official":
            train_pairs, test_pairs = official_train, official_test
            if make_val_from_train and val_ratio > 0:
                train_pairs, val_pairs = self._stratified_val_from_train(train_pairs, val_ratio, seed)

        elif strategy == "official-kfold-train":
            y_arr = np.array([self.action_to_label[a] for a, _ in official_train], dtype=int)
            self._check_min_class(y_arr, n_splits, "official-kfold-train")
            skf   = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
            folds = list(skf.split(np.zeros(len(y_arr)), y_arr))
            tr_idx, va_idx = folds[fold_index]
            train_pairs = [official_train[i] for i in tr_idx]
            val_pairs   = [official_train[i] for i in va_idx]
            test_pairs  = official_test

        elif strategy == "all-kfold":
            all_pairs = sorted(self._all_pairs_on_disk(), key=lambda p: (p[0], p[1]))
            y_arr     = np.array([self.action_to_label[a] for a, _ in all_pairs], dtype=int)
            self._check_min_class(y_arr, n_splits, "all-kfold")
            skf   = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
            folds = list(skf.split(np.zeros(len(y_arr)), y_arr))
            tr_idx, te_idx = folds[fold_index]
            train_pairs = [all_pairs[i] for i in tr_idx]
            test_pairs  = [all_pairs[i] for i in te_idx]
            val_pairs   = []

        else:
            raise ValueError(f"Unknown strategy: {strategy!r}")

        pools = {"train": train_pairs, "val": val_pairs, "test": test_pairs}
        want  = pools[subset]

        self.samples: List[Tuple[str, str, int, str]] = []
        missing = []
        for a, clip in want:
            mat_file = os.path.join(self.joints_path, a, clip, "joint_positions.mat")
            if os.path.exists(mat_file):
                self.samples.append((a, clip, self.action_to_label[a], mat_file))
            else:
                missing.append((a, clip))
        if missing:
            raise FileNotFoundError(
                f"{len(missing)} clips listed but .mat files missing. First 5: {missing[:5]}"
            )

        if indices is not None:
            self.samples = [self.samples[i] for i in indices if 0 <= i < len(self.samples)]

        if write_manifest:
            md  = manifest_dir or os.path.join(self.root, "manifests")
            os.makedirs(md, exist_ok=True)
            out = os.path.join(md, f"jhmdb_{strategy}_split{split_id}_fold{fold_index}_{subset}.json")
            with open(out, "w") as f:
                json.dump({
                    "strategy": strategy, "split_id": split_id, "seed": seed,
                    "n_splits": n_splits, "fold_index": fold_index, "subset": subset,
                    "make_val_from_train": bool(make_val_from_train), "val_ratio": float(val_ratio),
                    "pairs": want,
                }, f, indent=2)

    # ── Dataset protocol ──────────────────────────────────────────────────────

    def __len__(self) -> int:
        """Return number of clips in this split."""
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict:
        """Load one clip and return HARPS sample dict."""
        a, clip_name, y, mat_file = self.samples[idx]
        data = sio.loadmat(mat_file)
        # pos_img shape from .mat is (2, J, T) → transpose to (T, J, 2)
        pos  = np.transpose(data["pos_img"].astype("float32"), (2, 1, 0))
        return {
            "X": pos,
            "y": int(y),
            "meta": {
                "dataset":   "jhmdb",
                "filename":  f"{a}/{clip_name}",
                "path":      mat_file,
                "action_id": int(y),
                "subject":   None,
                "trial":     None,
                "T":         int(pos.shape[0]),
                "fps":       None,
                "modality":  "2d_pose",
            },
        }

    # ── Augmentation helpers ──────────────────────────────────────────────────

    @classmethod
    def swap_pairs(cls) -> Tuple[List[int], List[int]]:
        """Right/left joint index pairs for horizontal flip augmentation."""
        return cls.RIGHT_IDX, cls.LEFT_IDX

    @classmethod
    def joint_count(cls) -> int:
        """Number of joints per frame (15)."""
        return cls.JOINT_COUNT

    @classmethod
    def coord_size(cls) -> int:
        """Coordinate dimensions per joint (2 for JHMDB)."""
        return cls.COORD_SIZE

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _read_split_file(self, action: str, split_id: int) -> Tuple[List[str], List[str]]:
        fn = f"{action}_test_split{split_id}.txt"
        p  = os.path.join(self.splits_path, fn)
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Split file not found: {p}")
        train, test = [], []
        with open(p) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) != 2:
                    continue
                clip, tag = parts
                clip = clip.replace(".avi", "")
                if tag == "1":
                    train.append(clip)
                elif tag == "2":
                    test.append(clip)
        return train, test

    def _official_partition(
        self, split_id: int
    ) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        train_pairs, test_pairs = [], []
        for a in self.actions:
            tr, te = self._read_split_file(a, split_id)
            train_pairs += [(a, c) for c in tr]
            test_pairs  += [(a, c) for c in te]
        overlap = set(train_pairs) & set(test_pairs)
        if overlap:
            raise AssertionError(f"Train/Test overlap in split {split_id}: {list(overlap)[:5]}")
        return train_pairs, test_pairs

    def _all_pairs_on_disk(self) -> List[Tuple[str, str]]:
        pairs = []
        for a in sorted(self.actions):
            a_dir = os.path.join(self.joints_path, a)
            for clip in sorted(os.listdir(a_dir)):
                if os.path.exists(os.path.join(a_dir, clip, "joint_positions.mat")):
                    pairs.append((a, clip))
        if not pairs:
            raise RuntimeError("No clips found under joint_positions/")
        return pairs

    def _stratified_val_from_train(
        self,
        train_pairs: List[Tuple[str, str]],
        val_ratio: float,
        seed: int,
    ) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        y     = np.array([self.action_to_label[a] for (a, _) in train_pairs], dtype=int)
        n     = len(train_pairs)
        if n == 0:
            return train_pairs, []
        sss   = StratifiedShuffleSplit(n_splits=1, test_size=float(val_ratio), random_state=seed)
        (tr_idx, va_idx), = sss.split(np.zeros(n), y)
        return [train_pairs[i] for i in tr_idx], [train_pairs[i] for i in va_idx]

    @staticmethod
    def _check_min_class(y: np.ndarray, n_splits: int, context: str) -> None:
        counts = np.bincount(y)
        if np.any(counts < n_splits):
            raise ValueError(
                f"{context}: class has fewer than n_splits={n_splits} samples. "
                f"Counts: {counts.tolist()}"
            )

    def class_distribution(self) -> dict:
        """Return a Counter of {label: count} for this split."""
        from collections import Counter
        return Counter([y for _, _, y, _ in self.samples])