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


def expected_shortfall_conditioning(y: np.ndarray, X: Dict[str, np.ndarray], p: float = 95.0, low_q: float = 0.2, high_q: float = 0.8, min_tail: int = 15) -> List[Dict[str, Any]]:
    """ES_p (Expected Shortfall) conditioning on X_i high vs low subsets.

    ES_p defined here for absolute errors as mean(|y| | |y| > Q_p(|y|)). Baseline threshold is global.
    For each parameter high/low subset reuse same threshold to ensure comparability.
    Returns rows with delta_es = ES_high - ES_low.
    """
    abs_y = np.abs(y)
    threshold = np.percentile(abs_y, p)
    base_tail = abs_y[abs_y > threshold]
    if base_tail.size == 0:
        return []
    es_base = float(base_tail.mean())
    rows: List[Dict[str, Any]] = []
    for name, vals in X.items():
        q_low = np.quantile(vals, low_q)
        q_high = np.quantile(vals, high_q)
        low_mask = vals <= q_low
        high_mask = vals >= q_high
        if low_mask.sum() < 30 or high_mask.sum() < 30:  # need enough conditioning samples
            continue
        tail_low = np.abs(y[low_mask]) > threshold
        tail_high = np.abs(y[high_mask]) > threshold
        if tail_low.sum() < min_tail or tail_high.sum() < min_tail:
            continue
        es_low = float(np.abs(y[low_mask])[tail_low].mean())
        es_high = float(np.abs(y[high_mask])[tail_high].mean())
        rows.append({
            "param": name,
            f"threshold_q{int(p)}": float(threshold),
            f"es_base_q{int(p)}": es_base,
            f"es_low_q{int(p)}": es_low,
            f"es_high_q{int(p)}": es_high,
            f"delta_es_q{int(p)}": es_high - es_low,
            "low_count": int(low_mask.sum()),
            "high_count": int(high_mask.sum()),
            "tail_low_count": int(tail_low.sum()),
            "tail_high_count": int(tail_high.sum()),
        })
    rows.sort(key=lambda r: abs(r.get(f"delta_es_q{int(p)}", 0.0)), reverse=True)
    return rows


def _set_param(cfg: Config, path: str, value: float):
    keys = path.split('.')
    cur = cfg.raw
    for k in keys[:-1]:
        cur = cur[k]
    cur[keys[-1]] = float(value)


def _get_param(cfg: Config, path: str) -> float:
    keys = path.split('.')
    cur = cfg.raw
    for k in keys[:-1]:
        cur = cur[k]
    v = cur[keys[-1]]
    if not isinstance(v, (int, float)):
        raise ValueError(f"Parameter {path} not numeric")
    return float(v)


def _sample_fused_errors(cfg: Config, n: int, rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate fused longitudinal, lateral and 2D errors (same logic as run_sim)."""
    # Re-import locally to avoid circular deps if extended later
    from .sim_sensors import (
        simulate_balise_errors, simulate_balise_errors_2d, simulate_map_error_2d,
        simulate_map_error, simulate_odometry_segment_error, simulate_imu_bias_position_error,
        simulate_gnss_bias_noise_2d, combine_2d
    )
    from .fusion import fuse_pair
    bal_long, bal_lat = simulate_balise_errors_2d(cfg, n, rng)
    map_long, map_lat = simulate_map_error_2d(cfg, n, rng)
    odo = simulate_odometry_segment_error(cfg, n, rng)
    imu = simulate_imu_bias_position_error(cfg, n, rng)
    gnss_long, gnss_lat = simulate_gnss_bias_noise_2d(cfg, n, rng, mode="open")
    secure_long = simulate_balise_errors(cfg, n, rng) + simulate_odometry_segment_error(cfg, n, rng) + simulate_map_error(cfg, n, rng)
    unsafe_long = gnss_long + imu
    var_secure_long = np.var(secure_long, ddof=1)
    var_unsafe_long = np.var(unsafe_long, ddof=1)
    from .fusion import fuse_pair as fuse_pair_long
    fused_long, _ = fuse_pair_long(secure_long, np.full(n, var_secure_long), unsafe_long, np.full(n, var_unsafe_long))
    # Lateral fuse (secure: bal_lat + map_lat, unsafe: gnss_lat)
    lat_secure = bal_lat + map_lat
    lat_unsafe = gnss_lat
    var_secure_lat = np.var(lat_secure, ddof=1)
    var_unsafe_lat = np.var(lat_unsafe, ddof=1)
    fused_lat, _ = fuse_pair(lat_secure, np.full(n, var_secure_lat), lat_unsafe, np.full(n, var_unsafe_lat))
    fused_2d = combine_2d(fused_long, fused_lat)
    return fused_long, fused_lat, fused_2d


def sobol_sensitivity(cfg: Config, param_paths: Sequence[str], n_base: int, mc_n: int, rng: np.random.Generator, metrics: Sequence[str] | None = None, delta_pct: float = 10.0) -> Dict[str, Any]:
    """Compute Sobol first-order & total indices for selected metrics.

    Approach: Treat each parameter as Uniform[L, U] with L=val*(1-delta_pct/100), U=val*(1+delta_pct/100). If val==0 use ±delta_abs where
    delta_abs = (delta_pct/100)*fallback_scale (fallback_scale = 1.0 or 1e-3 if small).
    metrics: subset of {"rmse_long", "rmse_2d", "p95_long"}.
    Returns dict mapping metric name -> DataFrame-like dict with columns: param, S1, S1_conf, ST, ST_conf.
    """
    try:
        # Prefer new sobol sampler (deprecates saltelli in SALib >=1.5)
        try:  # nested to allow fallback
            from SALib.sample import sobol as _sobol_sampler_mod  # type: ignore
            sample_fn = _sobol_sampler_mod.sample  # module has sample()
        except Exception:
            from SALib.sample import saltelli  # type: ignore
            sample_fn = lambda problem, n_base, calc_second_order=False: saltelli.sample(problem, n_base, calc_second_order=calc_second_order)
        from SALib.analyze import sobol  # analysis interface unchanged
    except Exception as e:  # pragma: no cover - SALib import failure path
        raise RuntimeError("SALib not available for Sobol analysis") from e
    if metrics is None:
        metrics = ["rmse_long", "rmse_2d", "p95_long"]
    # Build problem definition
    bounds = []
    base_vals = []
    for p in param_paths:
        v = _get_param(cfg, p)
        if v == 0.0:
            scale = 1.0
            lower = - (delta_pct/100.0) * scale
            upper = + (delta_pct/100.0) * scale
        else:
            lower = v * (1 - delta_pct/100.0)
            upper = v * (1 + delta_pct/100.0)
        if lower == upper:
            lower -= 1e-6
            upper += 1e-6
        bounds.append([lower, upper])
        base_vals.append(v)
    problem = {
        'num_vars': len(param_paths),
        'names': list(param_paths),
        'bounds': bounds,
    }
    # Generate samples
    sobol_samples = sample_fn(problem, n_base, calc_second_order=False)
    k = problem['num_vars']
    n_eval = sobol_samples.shape[0]
    # Storage for metric values
    metric_vals: Dict[str, List[float]] = {m: [] for m in metrics}
    # Evaluate model per sample
    for row in sobol_samples:
        # set parameters
        for j, p in enumerate(param_paths):
            _set_param(cfg, p, row[j])
        # generate MC sample for metrics
        fused_long, fused_lat, fused_2d = _sample_fused_errors(cfg, mc_n, rng)
        if 'rmse_long' in metric_vals:
            metric_vals['rmse_long'].append(rmse(fused_long))
        if 'rmse_2d' in metric_vals:
            metric_vals['rmse_2d'].append(rmse(fused_2d))
        if 'p95_long' in metric_vals:
            metric_vals['p95_long'].append(float(np.percentile(np.abs(fused_long), 95)))
    # Restore original parameters
    for p, v in zip(param_paths, base_vals):
        _set_param(cfg, p, v)
    # Analyze
    results: Dict[str, Any] = {}
    for mname, vals in metric_vals.items():
        Y = np.array(vals, dtype=float)
        if Y.ndim != 1 or Y.size != n_eval:
            raise RuntimeError(f"Unexpected shape for metric {mname} values")
        S = sobol.analyze(problem, Y, calc_second_order=False, print_to_console=False)
        rows = []
        for p, s1, s1c, st, stc in zip(param_paths, S['S1'], S['S1_conf'], S['ST'], S['ST_conf']):
            rows.append({
                'param': p,
                'S1': float(s1),
                'S1_conf': float(s1c),
                'ST': float(st),
                'ST_conf': float(stc),
            })
        # Sort by total order
        rows.sort(key=lambda r: (float('nan') if math.isnan(r['ST']) else -r['ST']))
        results[mname] = rows
    return results


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
    "expected_shortfall_conditioning",
    "sobol_sensitivity",
    "lean_src_prcc_pipeline",
]
