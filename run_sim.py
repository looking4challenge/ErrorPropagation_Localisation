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
    simulate_balise_errors_2d,
    simulate_gnss_bias_noise,
    simulate_map_error,
    simulate_map_error_2d,
    simulate_odometry_segment_error,
    simulate_imu_bias_position_error,
    combine_2d,
)
from src.metrics import summarize, bootstrap_ci, rmse
from src.fusion import fuse_pair
from src.plots import (
    plot_pdf,
    plot_cdf,
    plot_qq,
    plot_multi_pdf,
    plot_multi_cdf,
    COLORS,
)
from src.time_sim import simulate_time_series


def main():
    ap = argparse.ArgumentParser(description="Monte Carlo localisation error proxy simulation (Phase 4)")
    ap.add_argument("--config", required=True, help="Path to YAML config")
    ap.add_argument("--out", required=True, help="Output directory for metrics & samples")
    ap.add_argument("--figdir", default="figures", help="Directory for generated plots")
    ap.add_argument("--no-plots", action="store_true", help="Disable plot generation")
    ap.add_argument("--minimal-plots", action="store_true", help="Nur Kernplots (fused PDF/CDF + Pfadvergleich) erzeugen")
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

    # Draw per-sensor longitudinal (and lateral where defined) errors for a single representative epoch
    bal = simulate_balise_errors(cfg, n, rng)
    bal_long, bal_lat = simulate_balise_errors_2d(cfg, n, rng)
    map_err = simulate_map_error(cfg, n, rng)
    map_long, map_lat = simulate_map_error_2d(cfg, n, rng)
    odo = simulate_odometry_segment_error(cfg, n, rng)
    imu = simulate_imu_bias_position_error(cfg, n, rng)
    gnss_open = simulate_gnss_bias_noise(cfg, n, rng, mode="open")
    # Mode comparison (open/urban/tunnel) longitudinal only for now
    gnss_modes_samples = {}
    for mode_name in ["open", "urban", "tunnel"]:
        if mode_name in cfg.sensors["gnss"]["modes"]:
            gnss_modes_samples[f"gnss_{mode_name}"] = simulate_gnss_bias_noise(cfg, n, rng, mode=mode_name)

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

    # Lateral & 2D metrics (combine map + balise laterals; odometry/imu lateral neglected placeholder)
    lateral_secure = bal_lat + map_lat  # odometry lateral drift ~ negligible (assumption logged)
    # Assume unsafe path lateral dominated by GNSS (bias/noise) — reuse gnss_open as lateral proxy (first-order)
    lateral_unsafe = gnss_open  # simplification
    # 2D combine
    fused_2d = combine_2d(fused, (lateral_secure + lateral_unsafe) / 2.0)  # crude merge placeholder
    metrics_fused["rmse_2d"] = float(np.sqrt(np.mean(fused_2d**2)))
    metrics_fused["p95_2d"] = float(np.percentile(fused_2d, 95))

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
    # Add mode comparison metrics
    for mname, sample in gnss_modes_samples.items():
        json_map[mname] = summarize(sample)
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

    # Plots & Legendentabelle
    if not args.no_plots:
        fig_dir: Path = Path(args.figdir)  # explicit type for static analyzers
        fig_dir.mkdir(parents=True, exist_ok=True)

        # Kernplots immer
        plot_pdf(fused, fig_dir / "fused_pdf.png", title="Fusionierter Positionsfehler – PDF", color=COLORS.get("fused"))
        plot_cdf(fused, fig_dir / "fused_cdf.png", title="Fusionierter Positionsfehler – CDF", color=COLORS.get("fused"))
        plot_multi_pdf({"secure": secure, "unsafe": unsafe, "fused": fused}, fig_dir / "paths_pdf.png", title="Pfadvergleich Sicher / Unsicher / Fusion – PDF")
        plot_multi_cdf(
            {"secure": secure, "unsafe": unsafe, "fused": fused},
            fig_dir / "paths_cdf.png",
            title="Pfadvergleich Sicher / Unsicher / Fusion – CDF",
        )

        # GNSS mode comparison
        if len(gnss_modes_samples) > 1:
            plot_multi_pdf(gnss_modes_samples, fig_dir / "gnss_modes_pdf.png", title="GNSS Modi – PDF Vergleich")
            plot_multi_cdf(gnss_modes_samples, fig_dir / "gnss_modes_cdf.png", title="GNSS Modi – CDF Vergleich")

        if not args.minimal_plots:
            # Detailplots nur wenn nicht minimal
            plot_qq(fused, fig_dir / "fused_qq.png", title="Fusionierter Positionsfehler – QQ")
            plot_pdf(secure, fig_dir / "secure_pdf.png", title="Sicherer Pfad – PDF", color=COLORS.get("secure"))
            plot_pdf(unsafe, fig_dir / "unsafe_pdf.png", title="Unsicherer Pfad – PDF", color=COLORS.get("unsafe"))
            plot_pdf(bal, fig_dir / "balise_pdf.png", title="Balise Fehler – PDF", color=COLORS.get("balise"))
            plot_pdf(map_err, fig_dir / "map_pdf.png", title="Kartenfehler – PDF", color=COLORS.get("map"))
            plot_pdf(odo, fig_dir / "odometry_pdf.png", title="Odometrie Drift/Segmentfehler – PDF", color=COLORS.get("odometry"))
            plot_multi_pdf({"balise": bal, "map": map_err, "odometry": odo}, fig_dir / "core_components_pdf.png", title="Kernkomponenten Balise/Map/Odometrie – PDF Vergleich")
            plot_multi_cdf({"balise": bal, "map": map_err, "odometry": odo}, fig_dir / "core_components_cdf.png", title="Kernkomponenten Balise/Map/Odometrie – CDF Vergleich")

        # Legendentabelle (RMSE & P95) für alle bekannten Komponenten
        legend_rows = []
        for cname, metrics in json_map.items():
            # p95 Feld ist p95
            legend_rows.append({
                "component": cname,
                "rmse_m": metrics.get("rmse"),
                "p95_m": metrics.get("p95"),
                "color_hex": COLORS.get(cname, "#000000"),
            })
        df_legend = pd.DataFrame(legend_rows)
        df_legend.to_csv(out_dir / "legend_table.csv", index=False)

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
            plt.plot(ts_res.times, ts_res.rmse, label="RMSE [m]")
            plt.plot(ts_res.times, ts_res.p95, label="P95 [m]")
            plt.xlabel("Zeit t [s]"); plt.ylabel("Positionsfehler [m]")
            plt.title("Zeitverlauf Fusionspfad – RMSE & P95")
            plt.legend(); plt.tight_layout(); plt.savefig(fig_dir/"fused_time_metrics.png", dpi=150); plt.close()
            plt.figure(figsize=(6,3))
            plt.plot(ts_res.times, ts_res.var_secure, label="Var sicher [m²]")
            plt.plot(ts_res.times, ts_res.var_unsafe, label="Var unsicher [m²]")
            plt.xlabel("Zeit t [s]"); plt.ylabel("Varianz [m²]")
            plt.title("Komponenten-Varianzen über Zeit")
            plt.legend(); plt.tight_layout(); plt.savefig(fig_dir/"component_variances.png", dpi=150); plt.close()
            plt.figure(figsize=(6,3))
            plt.plot(ts_res.times, ts_res.share_oos, label="> Schwelle")
            plt.xlabel("Zeit t [s]"); plt.ylabel("Anteil [-]")
            plt.title("Out-of-Spec Anteil (|Fehler| > Schwelle)")
            plt.legend(); plt.tight_layout(); plt.savefig(fig_dir/"share_out_of_spec.png", dpi=150); plt.close()

    print(
        f"Saved metrics (JSON + CSV) to {out_dir}. Plots={'on' if not args.no_plots else 'off'} (minimal={args.minimal_plots}). "
        f"Raw samples={'saved' if args.save_samples else 'skipped'}. Time-series={'on' if args.time_series else 'off'}."
    )


if __name__ == "__main__":
    main()