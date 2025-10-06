"""Metrics computation (RMSE, percentiles, bootstrap CIs)."""
from __future__ import annotations

from typing import Dict, Any, Sequence
import numpy as np


def rmse(values: np.ndarray) -> float:
    return float(np.sqrt(np.mean(values**2)))


def summarize(values: np.ndarray, percentiles: Sequence[float] = (50, 90, 95, 99)) -> Dict[str, float]:
    res = {"mean": float(np.mean(values)), "std": float(np.std(values, ddof=1)), "rmse": rmse(values)}
    percs = np.percentile(values, percentiles)
    for p, v in zip(percentiles, percs):
        res[f"p{int(p)}"] = float(v)
    return res


def bootstrap_ci(values: np.ndarray, stat_fn, B: int = 500, alpha: float = 0.05, rng: np.random.Generator | None = None):
    rng = rng or np.random.default_rng()
    n = values.shape[0]
    stats = []
    for _ in range(B):
        idx = rng.integers(0, n, size=n)
        stats.append(stat_fn(values[idx]))
    lower = float(np.percentile(stats, 100 * alpha / 2))
    upper = float(np.percentile(stats, 100 * (1 - alpha / 2)))
    return lower, upper


__all__ = ["rmse", "summarize", "bootstrap_ci"]