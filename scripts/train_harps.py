"""
scripts/train_harps.py — Train the HARPS sign recognition model.

Usage
-----
  # Train on WLASL dataset (requires downloaded data):
  python scripts/train_harps.py --dataset wlasl --data_root data/wlasl

  # Quick demo with synthetic data (no dataset required):
  python scripts/train_harps.py --demo

  # Custom options:
  python scripts/train_harps.py --demo --hidden_dim 128 --epochs 200 --feature_set SJ

The trained model is saved to backend/harps_model/ and loaded automatically
by the AMANDLA backend (HARPSSignRecognizer) on next startup.
"""

import argparse
import json
import os
import sys
import numpy as np
from pathlib import Path

# Ensure project root in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "backend" / "harps_model"


def parse_args():
    p = argparse.ArgumentParser(description="Train HARPS sign recogniser")
    p.add_argument("--demo",        action="store_true",
                   help="Train on synthetic data (no real dataset needed)")
    p.add_argument("--dataset",     default="wlasl",
                   help="Dataset name: wlasl | jhmdb | mhad")
    p.add_argument("--data_root",   default="data/wlasl",
                   help="Root directory of the dataset")
    p.add_argument("--joint_mode",  default="42_hands",
                   help="WLASL joint mode (42_hands, 10_hands_tips, ...)")
    p.add_argument("--hidden_dim",  type=int, default=64)
    p.add_argument("--epochs",      type=int, default=300)
    p.add_argument("--feature_set", default="SJ",
                   choices=["SJ", "TJ", "T_TUPLE", "FULL"],
                   help="Feature set. SJ=flatten (fast), TJ requires iisignature")
    p.add_argument("--scaler",      default="maxabs",
                   choices=["maxabs", "standard", "robust"])
    p.add_argument("--seed",        type=int, default=42)
    p.add_argument("--device",      default="cpu")
    return p.parse_args()


# Core SASL signs used in the AMANDLA app (matches signs_library.js and quick-sign categories)
SASL_DEMO_SIGNS = [
    "HELLO", "GOODBYE", "THANK YOU", "PLEASE", "SORRY",
    "YES", "NO", "HELP", "STOP", "WAIT",
    "DOCTOR", "NURSE", "HOSPITAL", "SICK", "PAIN",
    "HURT", "MEDICINE", "AMBULANCE", "EMERGENCY", "WATER",
    "HAPPY", "SAD", "ANGRY", "SCARED", "TIRED",
    "HUNGRY", "THIRSTY", "UNDERSTAND", "REPEAT", "COME",
    "GO", "RIGHTS", "LAW", "EQUAL", "LOVE",
    "GOOD", "BAD", "I", "YOU", "HOW ARE YOU",
    "I'M FINE",
]


def make_demo_data(n_classes=None, n_per_class=50, T=10, J=42, C=2, seed=42):
    """
    Generate synthetic sign-like data using real SASL sign names.

    Each class has a unique mean trajectory so the model can learn something
    meaningful for demonstration purposes. Uses real SASL class names so the
    output is human-readable when the model is deployed.

    Note: This synthetic data cannot recognise real hand poses — it is for
    framework validation only. Replace with real recordings for production.
    """
    class_names = SASL_DEMO_SIGNS
    if n_classes is not None:
        class_names = class_names[:n_classes]
    rng = np.random.default_rng(seed)
    samples = []
    for cls, _ in enumerate(class_names):
        # Class-specific direction bias
        bias = rng.standard_normal((J, C)) * 0.5
        for _ in range(n_per_class):
            noise = rng.standard_normal((T, J, C)).astype(np.float32) * 0.3
            # Temporal trend: joints drift in class-specific direction
            trend = np.linspace(0, 1, T)[:, None, None] * bias[None]
            clip  = (noise + trend.astype(np.float32))
            samples.append({"X": clip, "y": cls})
    rng.shuffle(samples)
    return samples, class_names


def extract_features(samples, feature_set, M_FRAMES=10):
    """Extract features from samples list → (X, y) arrays."""
    from backend.harps.experiments.pipelines import Pipelines, PipelineConfig
    pipe = Pipelines(PipelineConfig(M_FRAMES=M_FRAMES))

    dispatch = {
        "SJ":     pipe.pipeline_SJ,
        "TJ":     pipe.pipeline_TJ,
        "T_TUPLE": pipe.pipeline_T_TUPLE,
        "FULL":   pipe.pipeline_FULL,
    }
    fn = dispatch.get(feature_set, pipe.pipeline_SJ)
    try:
        return fn(samples)
    except ImportError:
        print(f"  iisignature not available for {feature_set}, falling back to SJ")
        return pipe.pipeline_SJ(samples)


def main():
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"HARPS Training")
    print(f"  feature_set : {args.feature_set}")
    print(f"  hidden_dim  : {args.hidden_dim}")
    print(f"  epochs      : {args.epochs}")
    print(f"  scaler      : {args.scaler}")
    print(f"  output dir  : {OUTPUT_DIR}")
    print()

    # ── 1. Load / generate data ──────────────────────────────────────────────
    if args.demo:
        n_demo = len(SASL_DEMO_SIGNS)
        print(f"Generating synthetic demo data ({n_demo} SASL classes × 50 samples)...")
        samples, class_names = make_demo_data(n_per_class=50, seed=args.seed)
    else:
        print(f"Loading {args.dataset} from {args.data_root} ...")
        from backend.harps.datasets import registry
        ds = registry.make_dataset(
            args.dataset,
            root        = args.data_root,
            joint_mode  = args.joint_mode,
            strategy    = "official",
        )
        all_data = ds.load_all()
        samples     = all_data["train"] + all_data.get("test", [])
        class_names = ds.class_names

    print(f"  {len(samples)} samples, {len(class_names)} classes")

    # ── 2. Extract features ──────────────────────────────────────────────────
    print(f"Extracting {args.feature_set} features...")
    X, y = extract_features(samples, args.feature_set)
    print(f"  X shape: {X.shape},  y shape: {y.shape}")

    # Train/val split (80/20 stratified by class)
    rng      = np.random.default_rng(args.seed)
    n        = len(y)
    idx      = rng.permutation(n)
    split    = int(0.8 * n)
    tr_idx   = idx[:split]
    val_idx  = idx[split:]
    X_tr, y_tr = X[tr_idx], y[tr_idx]
    X_val, y_val = X[val_idx], y[val_idx]

    # ── 3. Scale ─────────────────────────────────────────────────────────────
    from backend.harps.utils import FeatureScaler
    scaler = FeatureScaler(mode=args.scaler)
    X_tr   = scaler.fit_transform(X_tr)
    X_val  = scaler.transform(X_val)

    # ── 4. Train ─────────────────────────────────────────────────────────────
    from backend.harps.models import MLPClassifier
    from backend.harps.train  import MLPTrainer, TrainConfigMLP

    num_classes = int(y.max()) + 1
    input_dim   = X_tr.shape[1]
    model = MLPClassifier(
        input_dim   = input_dim,
        hidden_dim  = args.hidden_dim,
        num_classes = num_classes,
    )
    cfg = TrainConfigMLP(
        epochs  = args.epochs,
        seed    = args.seed,
        device  = args.device,
    )
    trainer = MLPTrainer(model, cfg)

    print(f"Training MLPClassifier ({input_dim} -> {args.hidden_dim} -> {num_classes})...")
    result = trainer.fit(
        X_tr, y_tr, X_val, y_val,
        checkpoint_path=str(OUTPUT_DIR / "model.pth"),
    )
    print(f"  train_acc : {result['train_acc']:.4f}")
    print(f"  val_acc   : {result.get('val_acc', 'N/A')}")
    print(f"  spikes    : {result['spike_count']}")

    # ── 5. Evaluate ──────────────────────────────────────────────────────────
    from backend.harps.utils import compute_metrics
    y_pred  = trainer.predict(X_val)
    metrics = compute_metrics(y_val, y_pred)
    print(f"  accuracy  : {metrics['accuracy']:.4f}")
    print(f"  f1_weighted: {metrics['f1_weighted']:.4f}")

    # ── 6. Save metadata + scaler ─────────────────────────────────────────────
    meta = {
        "class_names": class_names,
        "input_dim":   input_dim,
        "hidden_dim":  args.hidden_dim,
        "num_classes": num_classes,
        "feature_set": args.feature_set,
        "m_frames":    10,
        "scaler_mode": args.scaler,
        "train_acc":   result["train_acc"],
        "val_acc":     result.get("val_acc"),
        "accuracy":    metrics["accuracy"],
        "f1_weighted": metrics["f1_weighted"],
    }
    with (OUTPUT_DIR / "meta.json").open("w") as f:
        json.dump(meta, f, indent=2)

    with (OUTPUT_DIR / "scaler.json").open("w") as f:
        json.dump(scaler.to_dict(), f, indent=2)

    # Save convergence plot
    try:
        fig = trainer.tracker.plot_4panel(lambda_note=f"{args.feature_set}")
        fig.savefig(str(OUTPUT_DIR / "convergence.png"), dpi=100)
        import matplotlib.pyplot as plt
        plt.close(fig)
        print(f"  convergence plot saved")
    except Exception:
        pass

    print()
    print(f"Model saved to {OUTPUT_DIR}/")
    print("Restart the AMANDLA backend to load the new model.")


if __name__ == "__main__":
    main()