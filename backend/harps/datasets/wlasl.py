"""
WLASL dataset adapter — Word-Level American Sign Language (pose-based).

This adapter is the most relevant to AMANDLA because it uses OpenPose hand
and upper-body landmarks (55 joints) from video — the same kind of data
MediaPipe produces in the deaf window.

Directory layout::

    root/
      splits/
        all.json          (or wlasl100.json, wlasl300.json, wlasl1000.json, wlasl2000.json)
      pose_per_individual_videos/
        <video_id>/
          image_00001_keypoints.json
          image_00002_keypoints.json
          ...

Joint modes
-----------
WLASL supports 8 configurable joint subsets. For AMANDLA, "42_hands" (both
full hands) is the closest match to MediaPipe's 21-per-hand output.

Sample shape: {"X": (T, J_mode, C), "y": int, "meta": dict}
"""

from __future__ import annotations
from typing import List, Tuple, Optional, Dict, Any, Literal
import os
import json
import re
import numpy as np
from sklearn.model_selection import GroupShuffleSplit

from .registry import register

# ── Joint layout (55 upper-body + both hands) ────────────────────────────────

_BODY25_EXCLUDE = {9, 10, 11, 22, 23, 24, 12, 13, 14, 19, 20, 21}

_JOINT_NAMES_55 = (
    ["Nose", "Neck", "RShoulder", "RElbow", "RWrist",
     "LShoulder", "LElbow", "LWrist", "MidHip",
     "REye", "LEye", "REar", "LEar"] +
    [f"LHand_{i}" for i in range(21)] +
    [f"RHand_{i}" for i in range(21)]
)
_NAME_TO_IDX_55 = {n: i for i, n in enumerate(_JOINT_NAMES_55)}

_HANDS_IDX   = list(range(13, 55))   # both hands, 42 joints
_ARMS_FULL6  = [_NAME_TO_IDX_55[k] for k in
                ["RShoulder", "RElbow", "RWrist", "LShoulder", "LElbow", "LWrist"]]
_HAND_TIPS   = [4, 8, 12, 16, 20]
_HAND_MCP    = [2, 5, 9, 13, 17]

def _hands_indices_from(local_ids):
    return [13 + i for i in local_ids] + [34 + i for i in local_ids]

_HANDS_TIPS_10     = _hands_indices_from(_HAND_TIPS)
_HANDS_TIPS_MCP_20 = _hands_indices_from(_HAND_TIPS + _HAND_MCP)
_ARMSHANDS_IDX     = _ARMS_FULL6 + _HANDS_IDX

_JOINT_MODE_MAP = {
    "55_upperhands":          (list(range(55)),        "55u"),
    "42_hands":               (list(_HANDS_IDX),       "42h"),
    "48_armshands":           (list(_ARMSHANDS_IDX),   "48ah"),
    "10_hands_tips":          (list(_HANDS_TIPS_10),   "10tips"),
    "12_tips_wrists":         (list(_HANDS_TIPS_10) + [_NAME_TO_IDX_55["RWrist"],
                               _NAME_TO_IDX_55["LWrist"]], "12tipswr"),
    "14_tips_wrists_shoulders": (list(_HANDS_TIPS_10) + [
                               _NAME_TO_IDX_55["RWrist"], _NAME_TO_IDX_55["LWrist"],
                               _NAME_TO_IDX_55["RShoulder"], _NAME_TO_IDX_55["LShoulder"]], "14tipswrsh"),
    "16_arms_tips":           (list(_HANDS_TIPS_10) + list(_ARMS_FULL6), "16armtips"),
    "24_arms_tips_bases":     (list(_HANDS_TIPS_MCP_20) + list(_ARMS_FULL6), "24armtipsmcp"),
}

JointMode = Literal[
    "55_upperhands", "42_hands", "48_armshands",
    "10_hands_tips", "12_tips_wrists", "14_tips_wrists_shoulders",
    "16_arms_tips", "24_arms_tips_bases"
]

# ── Frame loading (strict: requires complete BODY_25 + both hands) ────────────

def _read_json(p: str) -> Any:
    with open(p) as f:
        return json.load(f)


def _uniform_downsample_indices(n_src: int, n_tgt: int) -> np.ndarray:
    """Pick n_tgt uniformly-spaced indices from [0, n_src-1]."""
    if n_src == n_tgt:
        return np.arange(n_src, dtype=int)
    if n_src < n_tgt:
        raise ValueError(f"Cannot downsample {n_src} → {n_tgt}")
    return np.linspace(0, n_src - 1, n_tgt).astype(int)


def _extract_frame_55(fr: dict, keep_conf: bool, normalize: str) -> np.ndarray:
    """
    Build one (55, C) frame from an OpenPose keypoints dict (STRICT).

    Raises ValueError if body, left hand, or right hand are incomplete.
    """
    def reshape3(lst):
        arr = np.asarray(lst, dtype=np.float32).reshape(-1, 3) if lst else np.zeros((0, 3), np.float32)
        return arr

    ppl   = fr.get("people", [])
    if not ppl:
        raise ValueError("No person detected in frame")
    pp    = ppl[0]
    body  = reshape3(pp.get("pose_keypoints_2d", []))
    lhand = reshape3(pp.get("hand_left_keypoints_2d", []))
    rhand = reshape3(pp.get("hand_right_keypoints_2d", []))

    if body.shape[0] != 25:
        raise ValueError(f"BODY_25 incomplete: got {body.shape[0]} joints")
    if lhand.shape[0] != 21:
        raise ValueError(f"Left hand incomplete: got {lhand.shape[0]} joints")
    if rhand.shape[0] != 21:
        raise ValueError(f"Right hand incomplete: got {rhand.shape[0]} joints")

    keep = [i for i in range(25) if i not in _BODY25_EXCLUDE]
    body = body[keep]                               # (13, 3)
    arr  = np.concatenate([body, lhand, rhand], 0)  # (55, 3)

    if normalize == "unit256":
        arr[:, :2] = 2.0 * (arr[:, :2] / 256.0 - 0.5)

    return arr[:, :2].astype(np.float32) if not keep_conf else arr.astype(np.float32)


Strategy = Literal["official", "official-kfold-train", "signer-kfold"]


@register("wlasl")
def build_wlasl(
    *,
    root: str,
    split: str,
    split_json: Optional[str] = None,
    subset_k: Optional[int] = 1000,
    target_len: Optional[int] = None,
    keep_confidence: bool = False,
    allow_missing: bool = False,
    pose_root: Optional[str] = None,
    strategy: Strategy = "official",
    n_splits: int = 5,
    fold_index: int = 0,
    val_ratio: float = 0.1,
    seed: int = 0,
    write_manifest: bool = False,
    manifest_dir: Optional[str] = None,
    joint_mode: JointMode = "55_upperhands",
    normalize: Literal["none", "unit256"] = "none",
    indices: Optional[List[int]] = None,
) -> "WLASL":
    """Construct a WLASL split. See WLASL class for full parameter docs."""
    if split_json is None:
        sj = "all.json" if subset_k is None else f"wlasl{subset_k}.json"
        split_json = os.path.join(root, "splits", sj)

    ds = WLASL(
        root=root, split=split, split_json=split_json,
        target_len=target_len, keep_confidence=keep_confidence,
        allow_missing=allow_missing,
        pose_root=pose_root or os.path.join(root, "pose_per_individual_videos"),
        strategy=strategy, n_splits=n_splits, fold_index=fold_index,
        val_ratio=val_ratio, seed=seed,
        write_manifest=write_manifest, manifest_dir=manifest_dir,
        joint_mode=joint_mode, normalize=normalize,
    )

    if indices is not None:
        class _Subset:
            def __init__(self, base, idxs):
                self.base = base; self.idxs = list(idxs)
                self.class_names = base.class_names
                self.joint_names = base.joint_names
                self.swap_pairs  = base.swap_pairs
            def __len__(self): return len(self.idxs)
            def __getitem__(self, i): return self.base[self.idxs[i]]
            def joint_count(self): return self.base.joint_count()
            def coord_size(self):  return self.base.coord_size()
        return _Subset(ds, indices)

    return ds


class WLASL:
    """
    STRICT pose adapter for WLASL isolated gloss classification.

    Each sample: {"X": (T, J_mode, C), "y": int, "meta": dict}
    """

    def __init__(
        self,
        *,
        root: str,
        split: str,
        split_json: str,
        target_len: Optional[int] = None,
        keep_confidence: bool = False,
        allow_missing: bool = False,
        pose_root: str,
        strategy: Strategy = "official",
        n_splits: int = 5,
        fold_index: int = 0,
        val_ratio: float = 0.1,
        seed: int = 0,
        write_manifest: bool = False,
        manifest_dir: Optional[str] = None,
        joint_mode: JointMode = "55_upperhands",
        normalize: Literal["none", "unit256"] = "none",
    ):
        self.root       = os.path.abspath(root)
        self.split      = str(split).lower()
        assert self.split in {"train", "val", "test"}
        self.keep_conf  = bool(keep_confidence)
        self.target_len = None if target_len is None else int(target_len)
        self.pose_root  = os.path.abspath(pose_root)
        self.split_json = os.path.abspath(split_json)
        self.joint_mode = joint_mode
        self.normalize  = normalize
        self.strategy   = strategy
        self.seed       = seed
        self.allow_missing = allow_missing

        content = _read_json(self.split_json)
        glosses, table = [], []
        for entry in content:
            gloss = entry.get("gloss")
            if not isinstance(gloss, str):
                continue
            glosses.append(gloss)
            for inst in entry.get("instances", []):
                vid = str(inst.get("video_id", "")).strip()
                if not vid:
                    continue
                table.append({
                    "video_id":    vid,
                    "gloss":       gloss,
                    "split":       str(inst.get("split", "")).lower(),
                    "frame_start": int(inst.get("frame_start", 1)),
                    "frame_end":   int(inst.get("frame_end", 1)),
                    "signer_id":   inst.get("signer_id"),
                    "variation_id": inst.get("variation_id"),
                })

        self.class_names   = sorted(set(glosses))
        self._gloss_to_idx = {g: i for i, g in enumerate(self.class_names)}
        jm_info            = _JOINT_MODE_MAP.get(joint_mode)
        if jm_info is None:
            raise ValueError(f"Unknown joint_mode: {joint_mode!r}")
        self._sel_idx, _   = jm_info[0], jm_info[1]
        self._joint_names  = [_JOINT_NAMES_55[i] for i in self._sel_idx]

        # Build splits
        if strategy == "official":
            splits = {"train": [], "val": [], "test": []}
            for row in table:
                if row["split"] in splits:
                    splits[row["split"]].append(row)

        elif strategy == "official-kfold-train":
            official_train = sorted([r for r in table if r["split"] == "train"],
                                    key=lambda r: (r["gloss"], r["video_id"]))
            official_test  = sorted([r for r in table if r["split"] == "test"],
                                    key=lambda r: (r["gloss"], r["video_id"]))
            train_cv = [r for r in official_train if r["signer_id"] is not None]
            X   = np.arange(len(train_cv))
            y   = np.array([self._gloss_to_idx[r["gloss"]] for r in train_cv], dtype=int)
            grp = np.array([r["signer_id"] for r in train_cv])
            try:
                from sklearn.model_selection import StratifiedGroupKFold
                sgkf  = StratifiedGroupKFold(n_splits=max(2, n_splits), shuffle=True, random_state=seed)
                folds = list(sgkf.split(X, y, grp))
            except Exception:
                from sklearn.model_selection import StratifiedKFold
                skf   = StratifiedKFold(n_splits=max(2, n_splits), shuffle=True, random_state=seed)
                folds = list(skf.split(X, y))
            tr_idx, va_idx = folds[fold_index]
            splits = {
                "train": [train_cv[i] for i in tr_idx],
                "val":   [train_cv[i] for i in va_idx],
                "test":  official_test,
            }

        elif strategy == "signer-kfold":
            pool  = [r for r in table if r["signer_id"] is not None]
            X     = np.arange(len(pool))
            y     = np.array([self._gloss_to_idx[r["gloss"]] for r in pool], dtype=int)
            grp   = np.array([r["signer_id"] for r in pool])
            try:
                from sklearn.model_selection import StratifiedGroupKFold
                sgkf  = StratifiedGroupKFold(n_splits=max(2, n_splits), shuffle=True, random_state=seed)
                folds = list(sgkf.split(X, y, grp))
            except Exception:
                from sklearn.model_selection import StratifiedKFold
                skf   = StratifiedKFold(n_splits=max(2, n_splits), shuffle=True, random_state=seed)
                folds = list(skf.split(X, y))
            tr_idx, te_idx = folds[fold_index]
            tr_rows = [pool[i] for i in tr_idx]
            te_rows = [pool[i] for i in te_idx]
            if val_ratio > 0:
                gss   = GroupShuffleSplit(n_splits=1, test_size=val_ratio, random_state=seed)
                idx   = np.arange(len(tr_rows))
                ytr   = np.array([self._gloss_to_idx[r["gloss"]] for r in tr_rows], dtype=int)
                grp_t = np.array([r["signer_id"] for r in tr_rows])
                try:
                    tr_i, va_i = next(gss.split(idx.reshape(-1, 1), ytr, grp_t))
                except Exception:
                    from sklearn.model_selection import StratifiedShuffleSplit
                    sss   = StratifiedShuffleSplit(n_splits=1, test_size=val_ratio, random_state=seed)
                    (tr_i, va_i), = sss.split(idx, ytr)
                va_rows = [tr_rows[i] for i in va_i]
                tr_rows = [tr_rows[i] for i in tr_i]
            else:
                va_rows = []
            splits = {"train": tr_rows, "val": va_rows, "test": te_rows}

        else:
            raise ValueError(f"Unknown WLASL strategy: {strategy!r}")

        # Filter out clips with no frames in range (when allow_missing=False)
        self._dropped: Dict[str, List] = {"train": [], "val": [], "test": []}
        if not allow_missing:
            for k in list(splits.keys()):
                kept, gone = [], []
                for r in splits[k]:
                    folder = os.path.join(self.pose_root, r["video_id"])
                    has_frames = any(
                        os.path.exists(os.path.join(folder, f"image_{i:05d}_keypoints.json"))
                        for i in range(int(r["frame_start"]), int(r["frame_end"]) + 1)
                    ) if os.path.isdir(folder) else False
                    (kept if has_frames else gone).append(r)
                splits[k] = kept
                self._dropped[k] = gone

        self.items = splits[self.split]

        m = re.search(r"wlasl(\d+)\.json$", os.path.basename(self.split_json))
        self.subset_k: Optional[int] = int(m.group(1)) if m else None

    # ── Dataset protocol ─────────────────────────────────────────────────────

    @property
    def joint_names(self) -> List[str]:
        """Names of joints for this joint_mode."""
        return list(self._joint_names)

    def joint_count(self) -> int:
        """Number of joints selected by joint_mode."""
        return len(self._joint_names)

    def coord_size(self) -> int:
        """Coordinate dimensions: 2 (xy) or 3 (xy + confidence)."""
        return 3 if self.keep_conf else 2

    def swap_pairs(self) -> List[Tuple[int, int]]:
        """Joint pairs to swap for left-right flip augmentation."""
        sel_pos = {idx: pos for pos, idx in enumerate(self._sel_idx)}

        def map_name(name):
            base = _NAME_TO_IDX_55.get(name)
            return sel_pos.get(base) if base is not None else None

        pairs = []
        for a, b in [("RShoulder", "LShoulder"), ("RElbow", "LElbow"),
                     ("RWrist", "LWrist"), ("REye", "LEye"), ("REar", "LEar")]:
            ia, ib = map_name(a), map_name(b)
            if ia is not None and ib is not None:
                pairs.append((ia, ib))
        for k in range(21):
            ia = sel_pos.get(_NAME_TO_IDX_55.get(f"RHand_{k}"))
            ib = sel_pos.get(_NAME_TO_IDX_55.get(f"LHand_{k}"))
            if ia is not None and ib is not None:
                pairs.append((ia, ib))
        return pairs

    def __len__(self) -> int:
        """Number of clips in this split."""
        return len(self.items)

    def __getitem__(self, i: int) -> dict:
        """Load one clip and return HARPS sample dict."""
        r = self.items[i]
        X = self._load_clip(r["video_id"], r["frame_start"], r["frame_end"])
        y = int(self._gloss_to_idx[r["gloss"]])
        return {
            "X": X.astype(np.float32),
            "y": y,
            "meta": {
                "video_id":    r["video_id"],
                "gloss":       r["gloss"],
                "class_id":    y,
                "frame_start": r["frame_start"],
                "frame_end":   r["frame_end"],
                "signer_id":   r["signer_id"],
                "split":       self.split,
                "joint_mode":  self.joint_mode,
            },
        }

    def _load_clip(self, vid: str, frame_start: int, frame_end: int) -> np.ndarray:
        """Load, select joint subset, and optionally resample one video clip."""
        folder = os.path.join(self.pose_root, vid)
        if not os.path.isdir(folder):
            raise FileNotFoundError(f"Pose folder missing: {folder}")

        def fname(k):
            return os.path.join(folder, f"image_{k:05d}_keypoints.json")

        in_range = [fname(k) for k in range(int(frame_start), int(frame_end) + 1)
                    if os.path.exists(fname(k))]
        if not in_range:
            raise FileNotFoundError(f"No frames in [{frame_start},{frame_end}] for {vid}")

        if self.target_len is None:
            chosen = in_range
        else:
            if len(in_range) < self.target_len:
                raise ValueError(f"Clip too short: {len(in_range)} < {self.target_len} for {vid}")
            chosen = [in_range[j] for j in _uniform_downsample_indices(len(in_range), self.target_len)]

        frames = [_extract_frame_55(_read_json(p), self.keep_conf, self.normalize) for p in chosen]
        X55    = np.stack(frames, axis=0)  # (T, 55, C)

        X = X55[:, self._sel_idx, :] if len(self._sel_idx) != 55 else X55
        if not np.all(np.isfinite(X)):
            raise ValueError(f"Non-finite values in clip {vid}")
        return X