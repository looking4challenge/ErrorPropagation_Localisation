#!/usr/bin/env python
"""Standalone script to quantify additive vs. joint P99 bias with bootstrap CI.

Usage:
  python additive_p99_bias.py --config config/model.yml --n 50000 --B 400 --out results/

Outputs:
  results/additive_p99_bias_eval.csv  (single-row summary)

Rationale:
  Provides transparent evidence of the conservatism (overbound) of the additive secure interval
  approximation: additive_p99 = Σ P99(component_i) vs. joint_p99 = P99(|Σ component_i|).
  Bias_pct = (additive_p99 / joint_p99 - 1)*100.
  Bootstrap over sample indices to derive CI for bias.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from src.config import load_config, get_seed
from src.sim_sensors import (
    simulate_balise_errors,
    simulate_map_error,
    simulate_odometry_segment_error,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--n", type=int, default=40000, help="MC samples for components")
    ap.add_argument("--B", type=int, default=400, help="Bootstrap replicates for bias CI")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--seed-offset", type=int, default=4242)
    args = ap.parse_args()

    cfg = load_config(args.config)
    rng = np.random.default_rng(get_seed(cfg) + args.seed_offset)
    n = int(args.n)

    bal = simulate_balise_errors(cfg, n, rng)
    map_err = simulate_map_error(cfg, n, rng)
    odo = simulate_odometry_segment_error(cfg, n, rng)
    secure = bal + map_err + odo
    p99_bal = float(np.percentile(np.abs(bal), 99))
    p99_map = float(np.percentile(np.abs(map_err), 99))
    p99_odo = float(np.percentile(np.abs(odo), 99))
    additive_p99 = p99_bal + p99_map + p99_odo
    joint_p99 = float(np.percentile(np.abs(secure), 99))
    bias_pct = 100.0 * (additive_p99 / joint_p99 - 1.0)

    # Bootstrap CI for bias
    B = int(args.B)
    n_idx = np.arange(n)
    boot_bias = []
    for _ in range(B):
        b = rng.integers(0, n, size=n)
        bal_b = bal[b]; map_b = map_err[b]; odo_b = odo[b]
        secure_b = bal_b + map_b + odo_b
        add_b = (
            np.percentile(np.abs(bal_b), 99)
            + np.percentile(np.abs(map_b), 99)
            + np.percentile(np.abs(odo_b), 99)
        )
        joint_b = np.percentile(np.abs(secure_b), 99)
        if joint_b == 0:
            continue
        boot_bias.append(100.0 * (add_b / joint_b - 1.0))
    if boot_bias:
        lower = float(np.percentile(boot_bias, 2.5))
        upper = float(np.percentile(boot_bias, 97.5))
    else:
        lower = float('nan'); upper = float('nan')

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {
            "n_samples": n,
            "additive_p99": additive_p99,
            "joint_p99": joint_p99,
            "bias_pct": bias_pct,
            "bias_ci95_lower": lower,
            "bias_ci95_upper": upper,
            "p99_balise": p99_bal,
            "p99_map": p99_map,
            "p99_odometry": p99_odo,
        }
    ]).to_csv(out_dir / "additive_p99_bias_eval.csv", index=False)
    print(f"Additive vs joint P99 bias: {bias_pct:.2f}% (95% CI [{lower:.2f}, {upper:.2f}]) written to additive_p99_bias_eval.csv")


if __name__ == "__main__":
    main()
