"""
harps.transforms.compose — chain transforms that operate on (clip, y) pairs.

Each transform in the chain receives and returns a sample. Samples may be:
  - dict:  {"X": ndarray, "y": int, ...}
  - tuple: (X, y) or (X, y, meta)
  - list:  [X, y] or [X, y, meta]

The Compose class normalises between these formats so individual transforms
only need to handle (clip, y) tuples internally.
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple


def _split_sample(sample: Any) -> Tuple[Any, Any, Any, str]:
    """Unpack sample into (clip, y, extras, kind)."""
    if isinstance(sample, dict):
        if "X" not in sample or "y" not in sample:
            raise KeyError("Dict samples must have 'X' and 'y' keys.")
        extras = {k: v for k, v in sample.items() if k not in ("X", "y")}
        return sample["X"], sample["y"], extras, "dict"

    if isinstance(sample, tuple):
        if len(sample) < 2:
            raise ValueError("Tuple samples must have at least (X, y).")
        extras = list(sample[2:]) if len(sample) > 2 else []
        return sample[0], sample[1], extras, "tuple"

    if isinstance(sample, list):
        if len(sample) < 2:
            raise ValueError("List samples must have at least [X, y].")
        extras = sample[2:] if len(sample) > 2 else []
        return sample[0], sample[1], list(extras), "list"

    raise TypeError(f"Unsupported sample type for Compose: {type(sample)}")


def _ensure_pair(sample: Any, op: Any) -> Tuple[Any, Any]:
    """Extract (clip, y) from an intermediate transform result."""
    if isinstance(sample, dict) and "X" in sample and "y" in sample:
        return sample["X"], sample["y"]
    if isinstance(sample, (tuple, list)) and len(sample) >= 2:
        return sample[0], sample[1]
    raise TypeError(f"{op} must return a sample with (X, y); got {type(sample)}.")


def _merge_sample(clip: Any, y: Any, extras: Any, kind: str) -> Any:
    """Reassemble the caller's preferred sample format after transforms."""
    if kind == "dict":
        out: Dict[str, Any] = {"X": clip, "y": y}
        if isinstance(extras, dict):
            out.update(extras)
        return out
    if kind == "list":
        rows: List[Any] = [clip, y]
        if isinstance(extras, list):
            rows.extend(extras)
        return rows
    if kind == "tuple":
        tail = extras if isinstance(extras, list) else []
        return tuple([clip, y, *tail]) if tail else (clip, y)
    return clip, y


class Compose:
    """
    Chain an ordered sequence of transforms.

    Each transform must accept and return a sample (dict, tuple, or list)
    containing at least (X, y). Extra keys/fields are preserved.

    Args:
        ops: Iterable of callable transforms.

    Example::

        pipe = Compose([
            PersonCentricNormalize(),
            UniformFrameSample(m_frames=10),
            TemporalJointPSF(n_tj=5),
        ])
        feat, y = pipe((clip, label))
    """

    def __init__(self, ops):
        self.ops = list(ops)

    def __call__(self, sample: Any) -> Any:
        """Apply all transforms in sequence."""
        clip, y, extras, kind = _split_sample(sample)
        payload = (clip, y)

        for op in self.ops:
            result = op(payload)
            clip, y = _ensure_pair(result, op)
            payload = (clip, y)

        return _merge_sample(clip, y, extras, kind)

    def __repr__(self) -> str:
        ops_str = "\n  ".join(repr(op) for op in self.ops)
        return f"Compose([\n  {ops_str}\n])"