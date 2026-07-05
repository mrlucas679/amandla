"""
harps.datasets.cache — FeatureCacheBuilder and npz helpers.

The FeatureCacheBuilder handles the full offline preprocessing pipeline:
  1. Load raw clips from a dataset adapter
  2. Apply a PRE transform (normalize, resample, etc.)
  3. Apply feature head transforms (PSF, flatten, etc.)
  4. Scale features using a FeatureScaler fitted on train
  5. Save everything as .npz files for fast reuse

All .npz reads/writes go through this module. Never use ad-hoc np.savez/load
elsewhere in the codebase.
"""

from __future__ import annotations
import os
import json
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Callable, Any

import numpy as np
from tqdm import tqdm

from .registry import make_dataset
from ..utils.scaler import FeatureScaler
from ..utils.pca import FeaturePCA


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _unpack_sample(s: Any) -> Tuple[np.ndarray, int, dict]:
    """Accept dict {"X":…,"y":…,"meta":…} or tuple (X, y) or (X, y, meta)."""
    if isinstance(s, dict):
        return s["X"], int(s["y"]), dict(s.get("meta", {}))
    if isinstance(s, (tuple, list)):
        if len(s) >= 3:
            return s[0], int(s[1]), dict(s[2])
        return s[0], int(s[1]), {}
    raise TypeError(f"Unsupported sample type: {type(s)}")


class SplitData:
    """Lightweight container holding .npz paths for each split."""

    def __init__(self, paths: Dict[str, str]):
        self.paths = paths


class FeatureCacheBuilder:
    """
    Offline feature caching pipeline for sign language datasets.

    Usage::

        builder = FeatureCacheBuilder(cache_root="cache/jhmdb/sj")
        ds_map, class_names = builder.load_splits(
            "jhmdb", ["train", "test"],
            common_kwargs={"root": "/data/jhmdb", "split_id": 1})

        for sk in ["train", "test"]:
            builder.preprocess(ds_map[sk], sk, PRE_factory, cfg)

        builder.features_from_preprocessed(head_sj, "SJ", "train")
        builder.features_from_preprocessed(head_sj, "SJ", "test")
        builder.scale_from_train("SJ", ["train", "test"])
    """

    def __init__(self, cache_root: str):
        self.cache_root = cache_root
        _ensure_dir(cache_root)

    # ── Dataset loading ──────────────────────────────────────────────────────

    def load_splits(
        self,
        dataset_name: str,
        splits: Sequence[str],
        common_kwargs: Dict,
        split_kwargs: Optional[Dict[str, Dict]] = None,
    ) -> Tuple[Dict, Optional[List[str]]]:
        """
        Build one dataset object per split name.

        Returns:
            (ds_map, class_names) where ds_map is {split_name: dataset}.
        """
        split_kwargs = split_kwargs or {}
        ds_map: Dict[str, Any] = {}
        for sk in splits:
            kw = {**common_kwargs, **split_kwargs.get(sk, {})}
            try:
                ds_map[sk] = make_dataset(dataset_name, split=sk, **kw)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to build {dataset_name!r} for split={sk!r}: {e}"
                ) from e
        class_names = getattr(ds_map[splits[0]], "class_names", None)
        return ds_map, class_names

    # ── Preprocessing ────────────────────────────────────────────────────────

    def preprocess(
        self,
        dataset,
        split_key: str,
        PRE_factory: Callable,
        cfg,
        deterministic_aug: bool = True,
        seed_base: int = 2025,
    ) -> str:
        """
        Apply PRE transform to every clip and save as .npz.

        Skips clips that have wrong shape, non-finite values, or raise
        exceptions (STRICT: dataset is expected to handle its own errors).

        Args:
            dataset:          Dataset object satisfying PoseDataset protocol.
            split_key:        "train", "val", or "test".
            PRE_factory:      Callable(cfg) → transform callable.
            cfg:              Config object passed to PRE_factory.
            deterministic_aug: Seed augmentation per sample for reproducibility.
            seed_base:        Base seed for per-sample augmentation.

        Returns:
            Path to the written .npz file.
        """
        out_path = os.path.join(self.cache_root, f"preproc_{split_key}.npz")
        if os.path.exists(out_path):
            return out_path

        PRE = PRE_factory(cfg)

        expected_joints = None
        expected_coords = None
        for attr in ("joint_count", "JOINT_COUNT"):
            v = getattr(dataset, attr, None)
            if v is not None:
                expected_joints = int(v() if callable(v) else v)
                break
        for attr in ("coord_size", "COORD_SIZE"):
            v = getattr(dataset, attr, None)
            if v is not None:
                expected_coords = int(v() if callable(v) else v)
                break

        X_list: List[np.ndarray] = []
        y_list: List[int] = []
        sk_total = sk_shape = sk_nonfinite = sk_other = 0

        for i in tqdm(range(len(dataset)), desc=f"preproc {split_key}"):
            if deterministic_aug and split_key == "train":
                np.random.seed(seed_base + i)
            try:
                s       = dataset[i]
                X_raw, y_raw, meta = _unpack_sample(s)
                X       = np.asarray(X_raw, dtype=np.float32)

                if X.ndim != 3:
                    sk_total += 1; sk_shape += 1; continue

                T, J, C = X.shape
                if expected_joints is not None and J != expected_joints:
                    sk_total += 1; sk_shape += 1; continue
                if expected_coords is not None and C != expected_coords:
                    sk_total += 1; sk_shape += 1; continue
                if not np.all(np.isfinite(X)):
                    sk_total += 1; sk_nonfinite += 1; continue

                # Apply PRE transform
                if isinstance(s, dict):
                    repacked = {**s, "X": X, "y": int(y_raw)}
                else:
                    repacked = (X, int(y_raw))
                res = PRE(repacked)

                if isinstance(res, dict):
                    X_pp, y_pp = res["X"], int(res["y"])
                elif isinstance(res, (tuple, list)):
                    X_pp, y_pp = res[0], int(res[1])
                else:
                    sk_total += 1; sk_other += 1; continue

                X_pp = np.asarray(X_pp, dtype=np.float32)
                if X_pp.ndim != 3 or not np.all(np.isfinite(X_pp)):
                    sk_total += 1; sk_shape += 1; continue

                X_list.append(X_pp)
                y_list.append(y_pp)

            except Exception as e:
                print(f"[preproc {split_key}] SKIP idx={i}: {e}")
                sk_total += 1; sk_other += 1

        print(f"[preproc {split_key}] kept={len(X_list)} skipped={sk_total}")

        X_obj = np.empty(len(X_list), dtype=object)
        for j, arr in enumerate(X_list):
            X_obj[j] = arr
        y_arr = np.array(y_list, dtype=np.int64)
        np.savez(out_path, X=X_obj, y=y_arr, allow_pickle=True)
        return out_path

    # ── Feature extraction ───────────────────────────────────────────────────

    def features_from_preprocessed(
        self, head_callable: Callable, feature_name: str, split_tag: str
    ) -> str:
        """
        Apply a feature head to preprocessed clips and save raw features.

        Args:
            head_callable: Callable((X, y)) → (feature_vector, y).
            feature_name:  Name tag (e.g. "SJ", "T-J-PSF").
            split_tag:     "train", "val", or "test".

        Returns:
            Path to the raw feature .npz.
        """
        out_path = os.path.join(self.cache_root, f"{feature_name}_{split_tag}_raw.npz")
        if os.path.exists(out_path):
            return out_path

        pre_path = os.path.join(self.cache_root, f"preproc_{split_tag}.npz")
        pack = np.load(pre_path, allow_pickle=True)
        X_obj, y = pack["X"], pack["y"]

        feats: List[np.ndarray] = []
        for i in tqdm(range(len(X_obj)), desc=f"{feature_name} {split_tag}"):
            res = head_callable((X_obj[i], int(y[i])))
            fv  = res[0] if isinstance(res, (tuple, list)) else res
            feats.append(np.asarray(fv).reshape(-1).astype(np.float32))

        # Pad to common width and stack
        maxlen = max(f.shape[0] for f in feats) if feats else 0
        X_out  = np.zeros((len(feats), maxlen), dtype=np.float32)
        for i, f in enumerate(feats):
            X_out[i, :f.shape[0]] = f

        np.savez(out_path, X=X_out, y=y)
        return out_path

    # ── Scaling ──────────────────────────────────────────────────────────────

    def scale_from_train(
        self,
        feature_name: str,
        splits: Sequence[str],
        *,
        mode: str = "maxabs",
        clip_range: Optional[Tuple[float, float]] = (-1.0, 1.0),
        eps: float = 1e-8,
        pca_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Fit a FeatureScaler on train raw features, apply to all splits.

        Optionally applies PCA after scaling when pca_params is provided.
        """
        train_raw = os.path.join(self.cache_root, f"{feature_name}_train_raw.npz")
        if not os.path.exists(train_raw):
            raise FileNotFoundError(f"Training raw cache not found: {train_raw}")

        tr   = np.load(train_raw, allow_pickle=True)
        Xtr  = np.asarray(tr["X"], dtype=np.float32)
        ytr  = tr["y"]

        scaler = FeatureScaler(mode=mode, clip_range=clip_range, eps=eps)
        scaler.fit(Xtr)

        scaler_path = os.path.join(self.cache_root, f"{feature_name}_scaler.json")
        with open(scaler_path, "w") as f:
            json.dump(scaler.to_dict(), f)

        Xtr_s = scaler.transform(Xtr)

        pca_obj = None
        if pca_params:
            try:
                n_comp = pca_params.get("n_components")
                whiten = bool(pca_params.get("whiten", False))
                p_eps  = float(pca_params.get("eps", 1e-8))
                pca_obj = FeaturePCA(n_components=n_comp, whiten=whiten, eps=p_eps)
                Xtr_s   = pca_obj.fit_transform(Xtr_s)
                print(f"[PCA] {feature_name}: {Xtr.shape[1]} → {Xtr_s.shape[1]}")
            except Exception as e:
                print(f"[PCA] {feature_name}: failed ({e}), skipping")
                pca_obj = None

        np.savez(os.path.join(self.cache_root, f"{feature_name}_train.npz"), X=Xtr_s, y=ytr)

        for k in splits:
            if k == "train":
                continue
            raw = os.path.join(self.cache_root, f"{feature_name}_{k}_raw.npz")
            if not os.path.exists(raw):
                continue
            P  = np.load(raw, allow_pickle=True)
            Xk = np.asarray(P["X"], dtype=np.float32)
            Xk = scaler.transform(Xk)
            if pca_obj is not None:
                try:
                    Xk = pca_obj.transform(Xk).astype(np.float32)
                except Exception:
                    pass
            np.savez(os.path.join(self.cache_root, f"{feature_name}_{k}.npz"), X=Xk, y=P["y"])


# ── Convenience helpers ───────────────────────────────────────────────────────

def load_scaled_npz(name: str, split_key: str, cache_root: str) -> np.lib.npyio.NpzFile:
    """Load a scaled feature .npz produced by FeatureCacheBuilder."""
    return np.load(os.path.join(cache_root, f"{name}_{split_key}.npz"), allow_pickle=True)


def combine_from_cache(
    names: Iterable[str], cache_root: str, split_key: str
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Horizontally concatenate multiple feature sets for a given split.

    All feature sets must have the same label array (verified by assertion).

    Returns:
        (X, y) where X is (N, sum_of_dims).
    """
    packs = [load_scaled_npz(n, split_key, cache_root) for n in names]
    y     = packs[0]["y"]
    for P in packs[1:]:
        assert np.all(P["y"] == y), "Label mismatch between feature caches"
    return np.hstack([P["X"] for P in packs]), y