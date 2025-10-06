from __future__ import annotations

import argparse
from pathlib import Path
import json
import numpy as np

from src.config import load_config, get_seed
from src.sim_sensors import (
    simulate_balise_errors,
    simulate_gnss_bias_noise,
    simulate_map_error,
    simulate_odometry_segment_error,
    simulate_imu_bias_position_error,
)
from src.metrics import summarize, bootstrap_ci, rmse
from src.fusion import fuse_pair


def main():
    ap = argparse.ArgumentParser(description="Monte Carlo localisation error proxy simulation")
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cfg = load_config(args.config)
    rng = np.random.default_rng(get_seed(cfg))
    n = int(cfg.sim["N_samples"])

    # Draw per-sensor longitudinal error approximations for a single representative epoch
    bal = simulate_balise_errors(cfg, n, rng)
    map_err = simulate_map_error(cfg, n, rng)
    odo = simulate_odometry_segment_error(cfg, n, rng)
    imu = simulate_imu_bias_position_error(cfg, n, rng)
    gnss_open = simulate_gnss_bias_noise(cfg, n, rng, mode="open")

    # Proxy: secure path (balise + odometry + map) aggregated as sum (assuming independence for now)
    secure = bal + odo + map_err
    # Variance estimates (sample) for weighting
    var_secure = np.var(secure, ddof=1)
    # Unsichere Pfad: gnss + imu
    unsafe = gnss_open + imu
    var_unsafe = np.var(unsafe, ddof=1)

    fused, var_fused = fuse_pair(secure, np.full(n, var_secure), unsafe, np.full(n, var_unsafe))

    metrics_secure = summarize(secure)
    metrics_unsafe = summarize(unsafe)
    metrics_fused = summarize(fused)

    # Bootstrap CI for RMSE fused
    rmse_ci = bootstrap_ci(fused, rmse, B=int(cfg.sim.get("B_bootstrap", 200)), alpha=0.05, rng=rng)
    metrics_fused["rmse_ci95_lower"], metrics_fused["rmse_ci95_upper"] = rmse_ci

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "metrics_secure.json").open("w") as f:
        json.dump(metrics_secure, f, indent=2)
    with (out_dir / "metrics_unsafe.json").open("w") as f:
        json.dump(metrics_unsafe, f, indent=2)
    with (out_dir / "metrics_fused.json").open("w") as f:
        json.dump(metrics_fused, f, indent=2)

    print("Saved metrics to", out_dir)


if __name__ == "__main__":
    main()