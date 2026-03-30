"""
harps.experiments.ablation — chunked, resumable ablation runner.

Runs a grid of (feature_set × fold) experiments with checkpointing so
partial runs can be resumed after interruption.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import numpy as np

from ..models      import MLPClassifier
from ..train       import MLPTrainer, TrainConfigMLP, save_checkpoint
from ..utils       import FeatureScaler, compute_metrics, log_result
from .pipelines    import Pipelines, PipelineConfig, make_feature_dict


@dataclass
class AblationConfig:
    """Configuration for the ablation study."""
    feature_sets:   List[str]  = field(default_factory=lambda: ["SJ", "TJ", "FULL"])
    hidden_dim:     int        = 64
    train_config:   TrainConfigMLP = field(default_factory=TrainConfigMLP)
    scaler_mode:    str        = "maxabs"   # maxabs | standard | robust
    n_folds:        int        = 5
    output_dir:     str        = "outputs/ablation"
    resume:         bool       = True       # skip already-completed (fold, feature_set) pairs
    seed:           int        = 42


def _state_path(output_dir: str) -> Path:
    return Path(output_dir) / "_state.json"


def _load_state(output_dir: str) -> dict:
    p = _state_path(output_dir)
    if p.exists():
        with p.open() as f:
            return json.load(f)
    return {"completed": []}


def _save_state(output_dir: str, state: dict) -> None:
    p = _state_path(output_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        json.dump(state, f, indent=2)


def run_ablation(
    samples_by_fold: List[Dict[str, list]],
    cfg: AblationConfig = None,
) -> List[dict]:
    """
    Run ablation across feature sets and folds.

    Args:
        samples_by_fold: List of fold dicts, each with keys:
                         "train": list of samples, "test": list of samples.
        cfg:             AblationConfig.

    Returns:
        List of result dicts (one per completed (fold, feature_set) pair).
    """
    cfg    = cfg or AblationConfig()
    outdir = Path(cfg.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    state  = _load_state(cfg.output_dir) if cfg.resume else {"completed": []}
    pipe   = Pipelines(PipelineConfig())
    results: List[dict] = []

    for fold_idx, fold_data in enumerate(samples_by_fold):
        train_samples = fold_data["train"]
        test_samples  = fold_data["test"]

        feature_dict_train = make_feature_dict(pipe, train_samples, cfg.feature_sets)
        feature_dict_test  = make_feature_dict(pipe, test_samples,  cfg.feature_sets)

        for fs_name in cfg.feature_sets:
            run_key = f"fold{fold_idx}_{fs_name}"
            if cfg.resume and run_key in state["completed"]:
                continue  # already done

            if feature_dict_train.get(fs_name) is None:
                # PSF unavailable
                results.append({"fold": fold_idx, "feature_set": fs_name, "skipped": True})
                continue

            X_tr, y_tr = feature_dict_train[fs_name]
            X_te, y_te = feature_dict_test[fs_name]

            # Scale
            scaler = FeatureScaler(mode=cfg.scaler_mode)
            X_tr   = scaler.fit_transform(X_tr)
            X_te   = scaler.transform(X_te)

            # Build model
            input_dim   = X_tr.shape[1]
            num_classes = int(y_tr.max()) + 1
            model = MLPClassifier(
                input_dim   = input_dim,
                hidden_dim  = cfg.hidden_dim,
                num_classes = num_classes,
            )

            train_cfg         = TrainConfigMLP(**vars(cfg.train_config))
            train_cfg.seed    = cfg.seed + fold_idx
            trainer           = MLPTrainer(model, train_cfg)

            ckpt_path = str(outdir / f"ckpt_fold{fold_idx}_{fs_name}.pth")
            fit_result = trainer.fit(X_tr, y_tr, X_te, y_te, checkpoint_path=ckpt_path)

            y_pred  = trainer.predict(X_te)
            metrics = compute_metrics(y_te, y_pred)

            row = {
                "fold":        fold_idx,
                "feature_set": fs_name,
                "train_acc":   fit_result["train_acc"],
                "val_acc":     fit_result.get("val_acc", None),
                "accuracy":    metrics["accuracy"],
                "f1_weighted": metrics["f1_weighted"],
                "spike_count": fit_result["spike_count"],
            }
            results.append(row)

            log_result(
                str(outdir / "results.csv"),
                fold=fold_idx, feature_set=fs_name,
                train_acc=row["train_acc"], val_acc=row["val_acc"],
                accuracy=row["accuracy"], f1_weighted=row["f1_weighted"],
            )

            # Save tracker diagnostics
            diag_dir = outdir / f"diag_fold{fold_idx}_{fs_name}"
            diag_dir.mkdir(parents=True, exist_ok=True)
            trainer.tracker.save_iter_csv(str(diag_dir / "iterations.csv"))
            fig = trainer.tracker.plot_4panel(lambda_note=f"{fs_name} fold{fold_idx}")
            fig.savefig(str(diag_dir / "convergence.png"), dpi=100)
            import matplotlib.pyplot as plt
            plt.close(fig)

            state["completed"].append(run_key)
            _save_state(cfg.output_dir, state)

    return results