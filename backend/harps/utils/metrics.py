"""
harps.utils.metrics — accuracy, F1-score, confusion matrix, Excel export.
"""

import os
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix


def compute_metrics(y_true, y_pred) -> dict:
    """
    Compute classification metrics.

    Args:
        y_true: Ground-truth integer labels.
        y_pred: Predicted integer labels.

    Returns:
        dict with keys: accuracy, f1_weighted, confusion_matrix
    """
    return {
        "accuracy":         float(accuracy_score(y_true, y_pred)),
        "f1_weighted":      float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred),
    }


def export_metrics_excel(path: str, results: dict, cms: dict, class_names: list) -> None:
    """
    Write experiment results to an Excel workbook.

    One sheet "Metrics" with summary rows, plus one "CM_<name>" sheet per
    confusion matrix.

    Args:
        path:        Destination .xlsx path (directory is created as needed).
        results:     Dict mapping feature_set name → dict of scalar metrics.
        cms:         Dict mapping feature_set name → confusion matrix ndarray.
        class_names: Ordered list of class label strings.
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        rows = [{"feature_set": k, **v} for k, v in results.items()]
        pd.DataFrame(rows).to_excel(writer, sheet_name="Metrics", index=False)
        for name, cm in cms.items():
            if cm is None:
                continue
            pd.DataFrame(
                cm, index=class_names, columns=class_names
            ).to_excel(writer, sheet_name=f"CM_{name[:25]}")