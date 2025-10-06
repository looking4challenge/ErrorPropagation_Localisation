"""Sensitivity analysis: One-at-a-Time (OAT) and optional Sobol (if SALib installed).

Focus now: OAT ±delta_pct for selected scalar parameters influencing longitudinal error.
"""
from __future__ import annotations

from typing import Dict, List, Tuple
import numpy as np

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
        })
    return results


__all__ = ["oat_sensitivity"]
