from __future__ import annotations

import argparse
from pathlib import Path
import json
import numpy as np
import pandas as pd
from datetime import datetime, UTC

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
from src.time_sim import simulate_time_series


def main():
    ap = argparse.ArgumentParser(description="Monte Carlo localisation error proxy simulation (Phase 4)")
    ap.add_argument("--config", required=True, help="Path to YAML config")
    ap.add_argument("--out", required=True, help="Output directory for metrics & samples")
    ap.add_argument("--figdir", default="figures", help="Directory for generated plots")
    ap.add_argument("--no-plots", action="store_true", help="Disable plot generation")
    ap.add_argument("--save-samples", action="store_true", help="Persist raw sample errors to CSV")
    ap.add_argument("--time-series", action="store_true", help="Run time-series simulation (RMSE(t), P95(t), Var paths)")
    ap.add_argument("--oos-threshold", type=float, default=0.2, help="Out-of-spec threshold for share_oos metric (m)")
    ap.add_argument("--override-n", type=int, default=None, help="Override N_samples (dev/performance)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    rng = np.random.default_rng(get_seed(cfg))
    n = int(cfg.sim["N_samples"]) if args.override_n is None else int(args.override_n)

    # Timestamp for provenance
    ts = datetime.now(UTC).isoformat()

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

    # Optional time-series run
    if args.time_series:
        ts_res = simulate_time_series(cfg, rng, threshold_oos=args.oos_threshold)
        ts_df = pd.DataFrame({
            "t_s": ts_res.times,
            "rmse": ts_res.rmse,
            "p95": ts_res.p95,
            "var_secure": ts_res.var_secure,
            "var_unsafe": ts_res.var_unsafe,
            "share_out_of_spec": ts_res.share_oos,
        })
        ts_df.to_csv(out_dir / "time_series_metrics.csv", index=False)
        if not args.no_plots:
            # Simple time plots
            import matplotlib.pyplot as plt
            fig_dir = Path(args.figdir)
            plt.figure(figsize=(6,3))
            plt.plot(ts_res.times, ts_res.rmse, label="RMSE")
            plt.plot(ts_res.times, ts_res.p95, label="P95")
            plt.xlabel("t [s]"); plt.ylabel("Error [m]"); plt.title("Fused Error Time Metrics"); plt.legend(); plt.tight_layout(); plt.savefig(fig_dir/"fused_time_metrics.png", dpi=150); plt.close()
            plt.figure(figsize=(6,3))
            plt.plot(ts_res.times, ts_res.var_secure, label="Var secure")
            plt.plot(ts_res.times, ts_res.var_unsafe, label="Var unsafe")
            plt.xlabel("t [s]"); plt.ylabel("Var [m^2]"); plt.title("Component Variances"); plt.legend(); plt.tight_layout(); plt.savefig(fig_dir/"component_variances.png", dpi=150); plt.close()
            plt.figure(figsize=(6,3))
            plt.plot(ts_res.times, ts_res.share_oos, label="> threshold")
            plt.xlabel("t [s]"); plt.ylabel("Share"); plt.title("Out-of-Spec Share"); plt.legend(); plt.tight_layout(); plt.savefig(fig_dir/"share_out_of_spec.png", dpi=150); plt.close()

    print(f"Saved metrics (JSON + CSV) to {out_dir}. Plots={'on' if not args.no_plots else 'off'}. Raw samples={'saved' if args.save_samples else 'skipped'}. Time-series={'on' if args.time_series else 'off'}.")


if __name__ == "__main__":
    main()