"""Sensitivity analysis: One-at-a-Time (OAT) and optional Sobol (if SALib installed).

Current implementation: longitudinal RMSE proxy. Extension hooks: lateral / 2D by switching
`base_longitudinal_samples` to a vector composition including lateral GNSS / map / balise components.
"""
from __future__ import annotations

from typing import Dict, List, Tuple, Sequence, Any
import numpy as np
import math

try:
    import pandas as pd  # optional; only used when higher-level caller wants DataFrames
except Exception:  # pragma: no cover - fallback if pandas not available in minimal contexts
    pd = None  # type: ignore

from .config import Config
from .sim_sensors import (
    simulate_balise_errors,
    simulate_gnss_bias_noise,
    simulate_map_error,
    simulate_odometry_segment_error,
    simulate_imu_bias_position_error,
)
from .metrics import rmse


def base_longitudinal_samples(cfg: Config, n: int, rng: np.random.Generator) -> np.ndarray:
    bal = simulate_balise_errors(cfg, n, rng)
    map_err = simulate_map_error(cfg, n, rng)
    odo = simulate_odometry_segment_error(cfg, n, rng)
    imu = simulate_imu_bias_position_error(cfg, n, rng)
    gnss_open = simulate_gnss_bias_noise(cfg, n, rng, mode="open")
    # Simplified combined error (pre-fusion) as sum for sensitivity proxy
    return bal + map_err + odo + imu + gnss_open


def default_oat_params(cfg: Config) -> List[str]:
    """Return a curated list of numeric parameter paths for OAT sensitivity.

    Selection criteria:
    - Direct scale / spread parameters of major error sources.
    - Avoid pure means at 0 (no relative perturbation effect).
    - Include new lateral GNSS std parameters.
    """
    candidates = [
        "sensors.gnss.modes.open.noise.std",
        "sensors.gnss.modes.open.bias.std",
        "sensors.gnss.modes.open.noise_lat.std",
        "sensors.gnss.modes.open.bias_lat.std",
        "sensors.map.longitudinal.ref_error.std",
        "sensors.balise.latency_ms.std",
        "sensors.balise.multipath_tail_m.cap",
        "sensors.odometry.drift_per_km_m",
        "sensors.imu.accel_bias_mps2.std",
    ]
    # Filter any that do not exist (robustness if config changes)
    valid: List[str] = []
    for p in candidates:
        try:
            _ = _get_numeric(cfg.raw, p)
            valid.append(p)
        except KeyError:
            continue
    return valid


def _get_numeric(root: Dict, dotted: str):
    keys = dotted.split('.')
    cur = root
    for k in keys[:-1]:
        cur = cur[k]
    leaf = keys[-1]
    val = cur[leaf]
    if not isinstance(val, (int, float)):
        raise KeyError(f"Parameter {dotted} not numeric")
    return val


def oat_sensitivity(cfg: Config, param_paths: List[str], delta_pct: float, n: int, rng: np.random.Generator) -> List[Dict[str, float]]:
    """Perform OAT sensitivity.

    param_paths: list of dotted paths into cfg.raw dict (e.g., 'sensors.gnss.modes.open.noise.std').
    Returns list of dict entries with baseline_rmse, rmse_minus, rmse_plus, rel_change_plus, rel_change_minus.
    """
    baseline_samples = base_longitudinal_samples(cfg, n, rng)
    baseline_rmse = rmse(baseline_samples)

    results = []
    for p in param_paths:
        # Navigate to parent and key
        keys = p.split('.')
        parent = cfg.raw
        for k in keys[:-1]:
            if k not in parent:
                raise KeyError(f"Path segment '{k}' missing for parameter '{p}'")
            parent = parent[k]
        leaf = keys[-1]
        if leaf not in parent:
            raise KeyError(f"Leaf '{leaf}' not found for parameter '{p}'")
        orig = parent[leaf]
        if not isinstance(orig, (int, float)):
            # Skip non-numeric
            continue
        delta = orig * (delta_pct / 100.0)
        if delta == 0.0:
            # Fallback absolute perturbation: use 1% of baseline RMSE scaled? Use small epsilon relative to baseline_rmse
            delta = max(1e-6, 0.01 * baseline_rmse)
        # minus
        parent[leaf] = orig - delta
        samples_minus = base_longitudinal_samples(cfg, n, rng)
        rmse_minus = rmse(samples_minus)
        # plus
        parent[leaf] = orig + delta
        samples_plus = base_longitudinal_samples(cfg, n, rng)
        rmse_plus = rmse(samples_plus)
        # restore
        parent[leaf] = orig
        results.append({
            'param': p,
            'baseline_rmse': baseline_rmse,
            'rmse_minus': rmse_minus,
            'rmse_plus': rmse_plus,
            'rel_change_minus_pct': 100.0 * (rmse_minus - baseline_rmse) / baseline_rmse,
            'rel_change_plus_pct': 100.0 * (rmse_plus - baseline_rmse) / baseline_rmse,
            'abs_effect_pct': max(
                abs(100.0 * (rmse_minus - baseline_rmse) / baseline_rmse),
                abs(100.0 * (rmse_plus - baseline_rmse) / baseline_rmse),
            ),
        })
    # Sort descending by absolute effect
    results.sort(key=lambda d: d['abs_effect_pct'], reverse=True)
    return results

def _as_array_list(d: Dict[str, np.ndarray], order: Sequence[str]) -> np.ndarray:
    return np.column_stack([d[k] for k in order])


def compute_src(X: np.ndarray, y: np.ndarray, col_names: Sequence[str]) -> List[Dict[str, Any]]:
    """Compute Standardised Regression Coefficients (SRC).

    Uses ordinary least squares: y = X b + e. Standardised β_j = b_j * σ(X_j)/σ(y).
    Returns list sorted by absolute SRC descending.
    """
    # Center to improve conditioning
    Xc = X - X.mean(axis=0, keepdims=True)
    yc = y - y.mean()
    # Solve via least squares
    beta, *_ = np.linalg.lstsq(Xc, yc, rcond=None)
    y_std = y.std(ddof=1)
    src_vals = []
    for j, name in enumerate(col_names):
        x_std = X[:, j].std(ddof=1)
        if x_std == 0 or y_std == 0:
            src = 0.0
        else:
            src = float(beta[j] * x_std / y_std)
        src_vals.append({
            "param": name,
            "src": src,
            "abs_src": abs(src),
        })
    src_vals.sort(key=lambda r: r["abs_src"], reverse=True)
    return src_vals


def compute_prcc(X: np.ndarray, y: np.ndarray, col_names: Sequence[str]) -> List[Dict[str, Any]]:
    """Partial Rank Correlation Coefficients (PRCC) using residual method.

    Steps per variable i:
      1. Rank-transform all columns & y.
      2. Regress ranks(X_i) on ranks(X_{-i}) -> residual r_i.
      3. Regress ranks(y) on ranks(X_{-i}) -> residual r_y.
      4. PRCC_i = corr(r_i, r_y).
    """
    n, k = X.shape
    # Rank transform (average ranks)
    def rank(v: np.ndarray) -> np.ndarray:
        return np.argsort(np.argsort(v)) / (len(v) - 1)
    XR = np.column_stack([rank(X[:, j]) for j in range(k)])
    yR = rank(y)
    prcc_rows: List[Dict[str, Any]] = []
    for i, name in enumerate(col_names):
        idx_other = [j for j in range(k) if j != i]
        X_other = XR[:, idx_other]
        # Add intercept column
        Xo_aug = np.column_stack([np.ones(n), X_other])
        # Residual for Xi
        beta_x, *_ = np.linalg.lstsq(Xo_aug, XR[:, i], rcond=None)
        r_i = XR[:, i] - Xo_aug @ beta_x
        # Residual for y
        beta_y, *_ = np.linalg.lstsq(Xo_aug, yR, rcond=None)
        r_y = yR - Xo_aug @ beta_y
        denom = r_i.std(ddof=1) * r_y.std(ddof=1)
        if denom == 0:
            prcc_val = 0.0
        else:
            prcc_val = float(np.corrcoef(r_i, r_y)[0, 1])
        prcc_rows.append({
            "param": name,
            "prcc": prcc_val,
            "abs_prcc": abs(prcc_val),
        })
    prcc_rows.sort(key=lambda r: r["abs_prcc"], reverse=True)
    return prcc_rows


def quantile_conditioning(y: np.ndarray, X: Dict[str, np.ndarray], p: float = 95.0, low_q: float = 0.2, high_q: float = 0.8) -> List[Dict[str, Any]]:
    """ΔQ_p = Q_p(y | X_i high) - Q_p(y | X_i low) per variable.

    high = X_i >= quantile(X_i, high_q); low analog.
    """
    results: List[Dict[str, Any]] = []
    base_p = float(np.percentile(y, p))
    for name, vals in X.items():
        q_low = np.quantile(vals, low_q)
        q_high = np.quantile(vals, high_q)
        low_mask = vals <= q_low
        high_mask = vals >= q_high
        if low_mask.sum() < 20 or high_mask.sum() < 20:
            # Not enough samples -> skip
            continue
        q_low_p = float(np.percentile(y[low_mask], p))
        q_high_p = float(np.percentile(y[high_mask], p))
        results.append({
            "param": name,
            "baseline_q{:.0f}".format(p): base_p,
            "low_q{:.0f}".format(p): q_low_p,
            "high_q{:.0f}".format(p): q_high_p,
            "delta_q{:.0f}".format(p): q_high_p - q_low_p,
            "low_count": int(low_mask.sum()),
            "high_count": int(high_mask.sum()),
            "low_frac": float(low_mask.mean()),
            "high_frac": float(high_mask.mean()),
        })
    results.sort(key=lambda r: abs(r.get("delta_q{:.0f}".format(p), 0.0)), reverse=True)
    return results


def exceedance_sensitivity(y: np.ndarray, X: Dict[str, np.ndarray], threshold: float, low_q: float = 0.2, high_q: float = 0.8) -> List[Dict[str, Any]]:
    """ΔP(|y|>T) conditioning on X_i high vs low."""
    base = float((np.abs(y) > threshold).mean())
    rows: List[Dict[str, Any]] = []
    for name, vals in X.items():
        q_low = np.quantile(vals, low_q)
        q_high = np.quantile(vals, high_q)
        low_mask = vals <= q_low
        high_mask = vals >= q_high
        if low_mask.sum() < 20 or high_mask.sum() < 20:
            continue
        p_low = float((np.abs(y[low_mask]) > threshold).mean())
        p_high = float((np.abs(y[high_mask]) > threshold).mean())
        rows.append({
            "param": name,
            "threshold": threshold,
            "p_base": base,
            "p_low": p_low,
            "p_high": p_high,
            "delta_p": p_high - p_low,
            "delta_p_pct_points": 100.0 * (p_high - p_low),
            "low_count": int(low_mask.sum()),
            "high_count": int(high_mask.sum()),
        })
    rows.sort(key=lambda r: abs(r["delta_p"]), reverse=True)
    return rows


def lean_src_prcc_pipeline(component_samples: Dict[str, np.ndarray], fused_long: np.ndarray, fused_lat: np.ndarray | None = None, fused_2d: np.ndarray | None = None) -> Dict[str, List[Dict[str, Any]]]:
    """Compute SRC & PRCC for multiple derived targets.

    Targets implemented (keys in result dict):
      - rmse_long_proxy (uses raw fused_long)
      - rmse_2d_proxy (optional if fused_2d provided)
      - rmse_long_sq (fused_long**2) – proxy for contribution to RMSE^2
      - p95_long_indicator (I(|fused_long| > baseline p95)) – proxy for tail involvement
    """
    names = list(component_samples.keys())
    X = _as_array_list(component_samples, names)
    out: Dict[str, List[Dict[str, float]]] = {}
    # Base (fused longitudinal error)
    out['src_rmse_long_proxy'] = compute_src(X, fused_long, names)
    out['prcc_rmse_long_proxy'] = compute_prcc(X, fused_long, names)
    if fused_2d is not None:
        out['src_rmse_2d_proxy'] = compute_src(X, fused_2d, names)
        out['prcc_rmse_2d_proxy'] = compute_prcc(X, fused_2d, names)
    # Squared error target
    fused_sq = fused_long ** 2
    out['src_rmse_long_sq'] = compute_src(X, fused_sq, names)
    out['prcc_rmse_long_sq'] = compute_prcc(X, fused_sq, names)
    # Tail indicator at observed p95 baseline
    p95_base = np.percentile(np.abs(fused_long), 95)
    indicator = (np.abs(fused_long) > p95_base).astype(float)
    if indicator.mean() not in (0.0, 1.0):  # avoid degenerate
        out['src_p95_long_indicator'] = compute_src(X, indicator, names)
        out['prcc_p95_long_indicator'] = compute_prcc(X, indicator, names)
    return out


__all__ = [
    "oat_sensitivity",
    "default_oat_params",
    "compute_src",
    "compute_prcc",
    "quantile_conditioning",
    "exceedance_sensitivity",
    "lean_src_prcc_pipeline",
]
