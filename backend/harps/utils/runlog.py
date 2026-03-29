"""
harps.utils.runlog — append-only CSV run logger for experiment tracking.

Every time an experiment configuration is evaluated, call log_result() to
append one row. Headers are written automatically on first use.
"""

import csv
import os


def log_result(csv_path: str, **fields) -> None:
    """
    Append one row of keyword-argument fields to a CSV log file.

    Creates the file and writes column headers on first call. Subsequent
    calls append rows in sorted-key order.

    Args:
        csv_path: Path to the CSV log file (directories created as needed).
        **fields: Arbitrary keyword arguments forming one row of data.

    Example::

        log_result("results/sasl.csv",
                   feature_set="T-J-PSF", split=1, top1_acc=0.87, seed=42)
    """
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)) or ".", exist_ok=True)
    exists = os.path.isfile(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sorted(fields.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(fields)