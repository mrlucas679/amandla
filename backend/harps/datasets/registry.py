"""
harps.datasets.registry — decorator-based dataset registration.

Builders register themselves with @register("name") so experiment code can
instantiate any dataset by name without hard-coding imports.

Usage::

    from harps.datasets.registry import register, make_dataset

    @register("jhmdb")
    def build_jhmdb(root, split, **kwargs):
        return JHMDB(root=root, subset=split, **kwargs)

    # Later:
    ds = make_dataset("jhmdb", root="/data/jhmdb", split="train")
"""

from typing import Callable, Dict, Any, Iterable, List

_DATASETS: Dict[str, Callable[..., Any]] = {}


def register(name: str, *, aliases: Iterable[str] = ()):
    """
    Class/function decorator that registers a dataset builder.

    Args:
        name:    Primary registration key.
        aliases: Optional extra names pointing to the same builder.

    Raises:
        KeyError: If name or any alias is already registered.
    """
    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        if name in _DATASETS:
            raise KeyError(f"Dataset name already registered: {name!r}")
        _DATASETS[name] = fn
        for alias in aliases:
            if alias in _DATASETS:
                raise KeyError(f"Dataset alias already registered: {alias!r}")
            _DATASETS[alias] = fn
        return fn
    return deco


def make_dataset(name: str, **kwargs) -> Any:
    """
    Instantiate a registered dataset by name.

    Args:
        name:    Registered dataset name (e.g. "jhmdb", "wlasl").
        **kwargs: Forwarded verbatim to the registered builder function.

    Returns:
        Dataset object satisfying the PoseDataset protocol.

    Raises:
        KeyError: If name is not registered.
    """
    try:
        builder = _DATASETS[name]
    except KeyError:
        available = ", ".join(sorted(_DATASETS))
        raise KeyError(f"Unknown dataset {name!r}. Available: [{available}]")
    return builder(**kwargs)


def list_datasets() -> List[str]:
    """Return all registered names (including aliases), sorted."""
    return sorted(_DATASETS)


def has_dataset(name: str) -> bool:
    """Return True if name is registered."""
    return name in _DATASETS