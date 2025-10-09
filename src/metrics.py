"""Metrics & statistical diagnostics (RMSE, quantiles, bootstrap CIs, convergence traces).

Additions:
 - quantile_convergence_trace: incremental estimation of selected quantiles (P95/P99) incl. RSE.
 - es_convergence_trace: Expected Shortfall (ES_p) convergence via light bootstrap per batch.
 - rmse_convergence_trace: RMSE convergence with delta-method SE approximation.
 - quantile_density_estimate: kernel density at quantile for RSE formula.
"""
from __future__ import annotations

from typing import Dict, Any, Sequence, List, Iterable
import numpy as np
from math import sqrt

# ---------------------------------------------------------------------------
# Basic metrics
# ---------------------------------------------------------------------------


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

# ---------------------------------------------------------------------------
# Convergence utilities
# ---------------------------------------------------------------------------

def _bandwidth_silverman(values: np.ndarray) -> float:
    """Silverman's rule-of-thumb bandwidth (1.06 * min(sd, IQR/1.34) * n^{-1/5})."""
    n = len(values)
    if n < 2:
        return 1.0
    std = np.std(values, ddof=1)
    iqr = np.subtract(*np.percentile(values, [75, 25]))
    scale = min(std, iqr / 1.34) if (iqr > 0 and std > 0) else max(std, 1e-9)
    return 1.06 * scale * (n ** (-1 / 5)) if scale > 0 else 1.0


def quantile_density_estimate(values: np.ndarray, q: float) -> float:
    """Estimate density f(x_q) at empirical quantile x_q via Gaussian kernel about point.

    This is a lightweight approximation adequate for RSE estimates; not for production KDE use.
    """
    x_q = np.quantile(values, q)
    h = _bandwidth_silverman(values)
    if h <= 0:
        return 1.0
    z = (values - x_q) / h
    # Gaussian kernel
    k = np.exp(-0.5 * z**2) / sqrt(2 * np.pi)
    fhat = np.mean(k) / h
    return float(max(fhat, 1e-12))  # guard


def quantile_rse(values: np.ndarray, q: float) -> float:
    """Relative standard error (RSE = SE/estimate) of sample quantile using asymptotic formula.

    Var(Q_p) ≈ p(1-p) / ( n * f(Q_p)^2 ) with density estimated via simple KDE.
    Returns RSE (dimensionless)."""
    p = q
    n = len(values)
    if n <= 1:
        return float('nan')
    f_q = quantile_density_estimate(values, p)
    var_est = p * (1 - p) / (n * (f_q ** 2))
    q_val = np.quantile(values, p)
    if q_val == 0:
        return float('inf')
    rse = sqrt(max(var_est, 0.0)) / abs(q_val)
    return float(rse)


def rmse_rse(values: np.ndarray) -> float:
    """Approximate RSE for RMSE via delta method.

    Let m2 = mean(X^2). RMSE = sqrt(m2). Var(m2)=Var(X^2)/n. Var(RMSE)≈Var(m2)/(4 m2).
    """
    n = len(values)
    if n <= 1:
        return float('nan')
    sq = values**2
    m2 = np.mean(sq)
    var_sq = np.var(sq, ddof=1)
    if m2 <= 0:
        return float('inf')
    var_rmse = var_sq / (n * 4 * m2)
    se = sqrt(max(var_rmse, 0.0))
    return float(se / sqrt(m2))


def quantile_convergence_trace(values: np.ndarray, quantiles: Sequence[float] = (0.95, 0.99), batch_size: int = 5000) -> List[Dict[str, Any]]:
    """Generate convergence trace for selected quantiles using cumulative batches.

    Parameters
    ----------
    values : array of samples (absolute error recommended for tail metrics)
    quantiles : list of probabilities (0<p<1)
    batch_size : size of incremental batch; last batch may be smaller.
    """
    n_total = len(values)
    traces: List[Dict[str, Any]] = []
    if n_total == 0:
        return traces
    # Permute to avoid artefacts if upstream ordering non-random
    perm = np.random.default_rng(12345).permutation(n_total)
    vals = values[perm]
    for end in range(batch_size, n_total + batch_size, batch_size):
        end_idx = min(end, n_total)
        sub = vals[:end_idx]
        row: Dict[str, Any] = {"cumulative_n": end_idx}
        for q in quantiles:
            qv = float(np.quantile(sub, q))
            row[f"q{int(q*100)}"] = qv
            row[f"q{int(q*100)}_rse"] = quantile_rse(sub, q)
        traces.append(row)
        if end_idx == n_total:
            break
    return traces


def rmse_convergence_trace(values: np.ndarray, batch_size: int = 5000) -> List[Dict[str, Any]]:
    """Convergence trace for RMSE with delta-method RSE."""
    n_total = len(values)
    if n_total == 0:
        return []
    perm = np.random.default_rng(2222).permutation(n_total)
    vals = values[perm]
    rows: List[Dict[str, Any]] = []
    for end in range(batch_size, n_total + batch_size, batch_size):
        end_idx = min(end, n_total)
        sub = vals[:end_idx]
        r = rmse(sub)
        rows.append({"cumulative_n": end_idx, "rmse": r, "rmse_rse": rmse_rse(sub)})
        if end_idx == n_total:
            break
    return rows


def es_convergence_trace(values: np.ndarray, p: float = 0.95, batch_size: int = 5000, B_boot: int = 200, rng: np.random.Generator | None = None) -> List[Dict[str, Any]]:
    """Convergence trace for Expected Shortfall ES_p(|X|) using light bootstrap for SE.

    ES_p = mean(|X| | |X| > Q_p(|X|)). Bootstraps within each cumulative subset with B_boot replicates.
    Returns rows with cumulative_n, es_p, es_se, es_rse.
    """
    rng = rng or np.random.default_rng()
    abs_vals = np.abs(values)
    n_total = len(abs_vals)
    perm = rng.permutation(n_total)
    v = abs_vals[perm]
    rows: List[Dict[str, Any]] = []
    for end in range(batch_size, n_total + batch_size, batch_size):
        end_idx = min(end, n_total)
        sub = v[:end_idx]
        q = np.quantile(sub, p)
        tail = sub[sub > q]
        if tail.size == 0:
            es = float('nan'); rse = float('nan'); se = float('nan')
        else:
            es = float(tail.mean())
            # Bootstrap tail mean
            if B_boot > 0:
                stats = []
                t_n = tail.size
                for _ in range(B_boot):
                    idx = rng.integers(0, t_n, size=t_n)
                    stats.append(float(tail[idx].mean()))
                se = float(np.std(stats, ddof=1))
                rse = se / es if es != 0 else float('inf')
            else:
                se = float('nan'); rse = float('nan')
        rows.append({"cumulative_n": end_idx, f"es{int(p*100)}": es, f"es{int(p*100)}_se": se, f"es{int(p*100)}_rse": rse})
        if end_idx == n_total:
            break
    return rows


__all__ = [
    "rmse",
    "summarize",
    "bootstrap_ci",
    # convergence
    "quantile_convergence_trace",
    "rmse_convergence_trace",
    "es_convergence_trace",
]