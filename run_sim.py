from __future__ import annotations

import argparse
from pathlib import Path
import json
import numpy as np
import pandas as pd
from datetime import datetime

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
from src.plots import plot_pdf, plot_cdf, plot_qq


def main():
    ap = argparse.ArgumentParser(description="Monte Carlo localisation error proxy simulation (Phase 4)")
    ap.add_argument("--config", required=True, help="Path to YAML config")
    ap.add_argument("--out", required=True, help="Output directory for metrics & samples")
    ap.add_argument("--figdir", default="figures", help="Directory for generated plots")
    ap.add_argument("--no-plots", action="store_true", help="Disable plot generation")
    ap.add_argument("--save-samples", action="store_true", help="Persist raw sample errors to CSV")
    args = ap.parse_args()

    cfg = load_config(args.config)
    rng = np.random.default_rng(get_seed(cfg))
    n = int(cfg.sim["N_samples"])

    # Timestamp for provenance
    ts = datetime.utcnow().isoformat() + "Z"

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

    metrics_bal = summarize(bal)
    metrics_map = summarize(map_err)
    metrics_odo = summarize(odo)
    metrics_imu = summarize(imu)
    metrics_gnss = summarize(gnss_open)
    metrics_secure = summarize(secure)
    metrics_unsafe = summarize(unsafe)
    metrics_fused = summarize(fused)

    # Bootstrap CI for RMSE fused
    rmse_ci = bootstrap_ci(fused, rmse, B=int(cfg.sim.get("B_bootstrap", 200)), alpha=0.05, rng=rng)
    metrics_fused["rmse_ci95_lower"], metrics_fused["rmse_ci95_upper"] = rmse_ci
    provenance = {"timestamp_utc": ts, "config": str(Path(args.config).resolve())}

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    # JSON per major aggregate component
    json_map = {
        "balise": metrics_bal,
        "map": metrics_map,
        "odometry": metrics_odo,
        "imu": metrics_imu,
        "gnss_open": metrics_gnss,
        "secure": metrics_secure,
        "unsafe": metrics_unsafe,
        "fused": metrics_fused,
    }
    for name, m in json_map.items():
        payload = {"component": name, "metrics": m, **provenance}
        with (out_dir / f"metrics_{name}.json").open("w") as f:
            json.dump(payload, f, indent=2)

    # Combined metrics CSV
    rows = []
    for name, m in json_map.items():
        r = {"component": name, **m}
        rows.append(r)
    df_metrics = pd.DataFrame(rows)
    df_metrics.to_csv(out_dir / "metrics_all.csv", index=False)

    # Optionally store raw samples
    if args.save_samples:
        df_samples = pd.DataFrame({
            "balise": bal,
            "map": map_err,
            "odometry": odo,
            "imu": imu,
            "gnss_open": gnss_open,
            "secure": secure,
            "unsafe": unsafe,
            "fused": fused,
        })
        df_samples.to_csv(out_dir / "samples.csv", index=False)

    # Plots
    if not args.no_plots:
        fig_dir = Path(args.figdir)
        fig_dir.mkdir(parents=True, exist_ok=True)
        plot_pdf(fused, fig_dir / "fused_pdf.png", title="Fused Error PDF")
        plot_cdf(fused, fig_dir / "fused_cdf.png", title="Fused Error CDF")
        plot_qq(fused, fig_dir / "fused_qq.png", title="Fused Error QQ")
        # Also secure/unsafe for comparison
        plot_pdf(secure, fig_dir / "secure_pdf.png", title="Secure Path PDF")
        plot_pdf(unsafe, fig_dir / "unsafe_pdf.png", title="Unsafe Path PDF")

    print(f"Saved metrics (JSON + CSV) to {out_dir}. Plots={'on' if not args.no_plots else 'off'}. Raw samples={'saved' if args.save_samples else 'skipped'}.")


if __name__ == "__main__":
    main()