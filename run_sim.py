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
    simulate_gnss_bias_noise_2d,
    simulate_map_error,
    simulate_map_error_2d,
    simulate_odometry_segment_error,
    simulate_imu_bias_position_error,
    combine_2d,
)
from src.metrics import (
    summarize,
    bootstrap_ci,
    rmse,
    quantile_convergence_trace,
    rmse_convergence_trace,
    es_convergence_trace,
)
from src.fusion import fuse_pair, rule_based_fusion
from src.plots import (
    plot_pdf,
    plot_cdf,
    plot_qq,
    plot_multi_pdf,
    plot_multi_cdf,
    COLORS,
)
from src.time_sim import simulate_time_series
from src.sensitivity import (
    oat_sensitivity,
    oat_sensitivity_2d,
    additive_p99_bias_sensitivity,
    default_oat_params,
    lean_src_prcc_pipeline,
    quantile_conditioning,
    exceedance_sensitivity,
    expected_shortfall_conditioning,
    sobol_sensitivity,
)


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
    ap.add_argument("--fusion-mode", choices=["var_weight","rule_based"], default=None, help="Override fusion mode (default: config driven)")
    ap.add_argument("--export-secure-interval", action="store_true", help="Export secure interval metrics CSV (width, additive vs joint P99, bias %)")
    ap.add_argument("--export-covariance", action="store_true", help="Export empirische Kovarianz/Korrelation der secure Komponenten (validiert additive Annahme)")
    # Adaptive interval / stateful fusion extensions
    ap.add_argument("--interval-update-cadence-s", type=float, default=1.0, help="Adaptive Intervall-Aktualisierungscadence in s")
    ap.add_argument("--no-adaptive-interval", action="store_true", help="Deaktiviert adaptive Intervallberechnung (Fallback global additive P99)")
    ap.add_argument("--fusion-stats", action="store_true", help="Exportiert Fusionsmodusanteile & Switch Rate (fusion_mode_stats.csv, fusion_switch_rate.csv)")
    ap.add_argument("--export-interval-bounds", action="store_true", help="Exportiert finale Intervallgrenzen je Sample (secure_interval_bounds.csv)")
    ap.add_argument("--convergence", action="store_true", help="Export Konvergenz-Traces (RMSE, P95, P99, ES95)")
    ap.add_argument("--perf", action="store_true", help="Messe Runtime adaptiver stateful Fusion vs. Legacy (nur Kurzlauf)")
    ap.add_argument("--stress", nargs="*", default=None, help="Stress scenario flags: balise_tail, odo_residual, heavy_map")
    ap.add_argument("--early-detect-validate", action="store_true", help="Validate Early-Detection impact (ΔP95) and log result")
    ap.add_argument("--override-n", type=int, default=None, help="Override N_samples (dev/performance)")
    ap.add_argument("--oat", action="store_true", help="Run OAT sensitivity (longitudinal RMSE proxy)")
    ap.add_argument("--oat-params", nargs="*", default=None, help="Explicit dotted param paths for OAT (overrides default list)")
    ap.add_argument("--oat-2d", action="store_true", help="Run extended OAT sensitivity (long/lat/2D metrics)")
    ap.add_argument("--oat-2d-params", nargs="*", default=None, help="Explicit param paths for OAT 2D (fallback: OAT defaults)")
    ap.add_argument("--p99-bias-sens", action="store_true", help="Parameter impact on additive vs joint P99 bias (secure path)")
    # Lean Erweiterung Flags
    ap.add_argument("--src-prcc", action="store_true", help="Compute SRC & PRCC rankings (lean)")
    ap.add_argument("--quantile-p", type=float, default=95.0, help="Quantile level for conditioning ΔQp (default 95)")
    ap.add_argument("--quantile-conditioning", action="store_true", help="Enable quantile conditioning ΔQp sensitivity")
    ap.add_argument("--exceedance-threshold", type=float, default=None, help="Threshold T for exceedance ΔP(|e|>T) (default: use p95 of fused if not set)")
    ap.add_argument("--exceedance", action="store_true", help="Enable exceedance sensitivity ΔP(|e|>T)")
    # Sobol & ES95 Erweiterung
    ap.add_argument("--sobol", action="store_true", help="Run Sobol First/Total order indices (default: rmse_long, rmse_2d, p95_long, p95_2d)")
    ap.add_argument("--sobol-base", type=int, default=750, help="Base sample size for Saltelli (total eval ~ (2k+2)*N)")
    ap.add_argument("--sobol-auto-base", action="store_true", help="Automatische Heuristik für n_base abhängig von Parameteranzahl k")
    ap.add_argument("--sobol-params", nargs="*", default=None, help="Explicit parameter paths for Sobol (fallback: OAT default list)")
    ap.add_argument("--sobol-delta-pct", type=float, default=10.0, help="Relative variation window ±pct for Sobol bounds")
    ap.add_argument("--sobol-mc-n", type=int, default=800, help="Inner MC sample per Sobol evaluation (fused error resampling)")
    ap.add_argument("--sobol-metrics", nargs="*", default=None, help="Subset of metrics for Sobol (choices: rmse_long rmse_2d p95_long p95_2d)")
    ap.add_argument("--es95", action="store_true", help="Compute ES95 conditioning sensitivity (High-Low ΔES)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    rng = np.random.default_rng(get_seed(cfg))
    n = int(cfg.sim["N_samples"]) if args.override_n is None else int(args.override_n)

    # Timestamp for provenance
    ts = datetime.now(UTC).isoformat()

    # Draw per-sensor longitudinal (and lateral where defined) errors for a single representative epoch
    # Apply stress flag modifications (temporary, revert in memory only)
    stress_flags = set(args.stress or [])
    if stress_flags:
        if "balise_tail" in stress_flags:
            # Increase multipath tail weight conservatively
            orig_weight = cfg.sensors["balise"]["multipath_tail_m"]["weight"]
            cfg.sensors["balise"]["multipath_tail_m"]["weight"] = min(0.50, orig_weight * 2.0)
        if "odo_residual" in stress_flags:
            o = cfg.sensors["odometry"]["residual_circumference_m"]
            span = max(abs(o["low"]), abs(o["high"]))
            # widen by 2x (bounded)
            o["low"], o["high"] = -min(span * 2.0, 0.10), min(span * 2.0, 0.10)
        if "heavy_map" in stress_flags and "interpolation" in cfg.sensors["map"]["longitudinal"]:
            cfg.sensors["map"]["longitudinal"]["interpolation"]["weight"] = min(0.6, cfg.sensors["map"]["longitudinal"]["interpolation"]["weight"] * 1.5)

    bal = simulate_balise_errors(cfg, n, rng)
    bal_long, bal_lat = simulate_balise_errors_2d(cfg, n, rng)
    map_err = simulate_map_error(cfg, n, rng)
    map_long, map_lat = simulate_map_error_2d(cfg, n, rng)
    odo = simulate_odometry_segment_error(cfg, n, rng)
    imu = simulate_imu_bias_position_error(cfg, n, rng)
    # Separate longitudinal & lateral GNSS errors (open mode) for realistic lateral unsafe path
    gnss_open_long, gnss_open_lat = simulate_gnss_bias_noise_2d(cfg, n, rng, mode="open")
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
    unsafe = gnss_open_long + imu
    var_unsafe = np.var(unsafe, ddof=1)

    # Secure interval (additive P99 of components) for rule-based fusion & reporting
    # Components comprising secure longitudinal path
    secure_components = {"balise": bal, "odometry": odo, "map": map_err}
    p99_components = {k: float(np.percentile(np.abs(v), 99)) for k, v in secure_components.items()}
    additive_p99 = float(sum(p99_components.values()))
    # Joint P99 via empirical distribution of secure path
    joint_p99 = float(np.percentile(np.abs(secure), 99))
    additive_bias_pct = 100.0 * (additive_p99 / joint_p99 - 1.0) if joint_p99 > 0 else float('nan')
    cfg_fusion = cfg.sensors.get("fusion", {})
    fusion_mode_cfg = "rule_based" if cfg_fusion.get("rule_based", False) else "var_weight"
    fusion_mode = args.fusion_mode or fusion_mode_cfg
    if fusion_mode == "rule_based":
        fused, var_fused = rule_based_fusion(secure, unsafe, interval_width=additive_p99, blend_steps=int(cfg_fusion.get("blend_steps", 5)))
    else:
        fused, var_fused = fuse_pair(secure, np.full(n, var_secure), unsafe, np.full(n, var_unsafe))

    metrics_bal = summarize(bal)
    metrics_map = summarize(map_err)
    metrics_odo = summarize(odo)
    metrics_imu = summarize(imu)
    metrics_gnss = summarize(gnss_open_long)
    metrics_secure = summarize(secure)
    metrics_unsafe = summarize(unsafe)
    metrics_fused = summarize(fused)
    # Extend with interval metadata (keep numeric fields numeric; add separate meta fields for strings)
    metrics_fused["secure_interval_p99_additive"] = additive_p99
    metrics_fused["secure_interval_p99_joint"] = joint_p99
    metrics_fused["secure_interval_additive_bias_pct"] = additive_bias_pct
    fusion_meta = {"fusion_mode": fusion_mode}

    # Lateral & 2D metrics (refined):
    # Secure lateral path: balise_lat + map_lat (odometry lateral drift negligible; documented)
    lateral_secure = bal_lat + map_lat
    # Unsafe lateral path: GNSS lateral (imu lateral neglected)
    lateral_unsafe = gnss_open_lat
    # Fuse lateral separately via variance inverse weighting
    var_secure_lat = np.var(lateral_secure, ddof=1)
    var_unsafe_lat = np.var(lateral_unsafe, ddof=1)
    fused_lat, var_fused_lat = fuse_pair(lateral_secure, np.full(n, var_secure_lat), lateral_unsafe, np.full(n, var_unsafe_lat))
    # 2D radial error based on fused longitudinal & fused lateral
    fused_2d = combine_2d(fused, fused_lat)
    # Add lateral & 2D metrics
    metrics_fused["rmse_lateral"] = float(np.sqrt(np.mean(fused_lat**2)))
    metrics_fused["p95_lateral"] = float(np.percentile(fused_lat, 95))
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
        "fused": {**metrics_fused, **fusion_meta},
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
            "gnss_open": gnss_open_long,
            "secure": secure,
            "unsafe": unsafe,
            "fused": fused,
            "lateral_secure": lateral_secure,
            "lateral_unsafe": lateral_unsafe,
            "fused_lat": fused_lat,
            "fused_2d": fused_2d,
            "secure_interval_additive_p99": np.full(n, additive_p99),
        })
        df_samples.to_csv(out_dir / "samples.csv", index=False)

    # Export secure interval metrics summary if requested
    if args.export_secure_interval:
        si_rows = [{
            "additive_p99": additive_p99,
            "joint_p99": joint_p99,
            "bias_pct": additive_bias_pct,
            **{f"p99_{k}": v for k, v in p99_components.items()},
            "fusion_mode": fusion_mode,
            "n_samples": n,
        }]
        pd.DataFrame(si_rows).to_csv(out_dir / "secure_interval_metrics.csv", index=False)

    # Export empirical covariance/correlation of secure components
    if getattr(args, "export_covariance", False):
        comp_names = list(secure_components.keys())
        comp_mat = np.column_stack([secure_components[c] for c in comp_names])
        cov = np.cov(comp_mat, rowvar=False, ddof=1)
        corr = np.corrcoef(comp_mat, rowvar=False)
        rows_cov = []
        for i, ci in enumerate(comp_names):
            for j, cj in enumerate(comp_names):
                rows_cov.append({
                    "comp_i": ci,
                    "comp_j": cj,
                    "cov": float(cov[i, j]),
                    "corr": float(corr[i, j]),
                })
        pd.DataFrame(rows_cov).to_csv(out_dir / "covariance_components_secure.csv", index=False)

    # Convergence traces (quantiles, RMSE, ES95) for fused path
    if getattr(args, "convergence", False):
        abs_fused = np.abs(fused)
        # Heuristic batch size: aim for ~10 batches (min 1000)
        batch_size = max(1000, int(n / 10))
        q_trace = quantile_convergence_trace(abs_fused, quantiles=(0.95, 0.99), batch_size=batch_size)
        rmse_trace = rmse_convergence_trace(fused, batch_size=batch_size)
        es_trace = es_convergence_trace(fused, p=0.95, batch_size=batch_size, B_boot=120)
        if q_trace:
            pd.DataFrame(q_trace).to_csv(out_dir / "convergence_quantiles.csv", index=False)
        if rmse_trace:
            pd.DataFrame(rmse_trace).to_csv(out_dir / "convergence_rmse.csv", index=False)
        if es_trace:
            pd.DataFrame(es_trace).to_csv(out_dir / "convergence_es95.csv", index=False)

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
        import time
        t0 = time.perf_counter()
        ts_res = simulate_time_series(
            cfg, rng,
            threshold_oos=args.oos_threshold,
            with_lateral=True,
            adaptive_interval=not args.no_adaptive_interval,
            interval_update_cadence_s=float(args.interval_update_cadence_s),
            export_interval_bounds=args.export_interval_bounds,
            blend_steps=cfg.sensors.get("fusion", {}).get("blend_steps", 5),
        )
        t1 = time.perf_counter()
        data_map = {
            "t_s": ts_res.times,
            "rmse_long": ts_res.rmse,
            "p95_long": ts_res.p95,
            "var_secure_long": ts_res.var_secure,
            "var_unsafe_long": ts_res.var_unsafe,
            "share_out_of_spec_long": ts_res.share_oos,
        }
        # Optional lateral / 2D
        if ts_res.rmse_lat is not None:
            data_map["rmse_lat"] = ts_res.rmse_lat
        if ts_res.p95_lat is not None:
            data_map["p95_lat"] = ts_res.p95_lat
        if ts_res.rmse_2d is not None:
            data_map["rmse_2d"] = ts_res.rmse_2d
        if ts_res.p95_2d is not None:
            data_map["p95_2d"] = ts_res.p95_2d
        ts_df = pd.DataFrame(data_map)
        ts_df.to_csv(out_dir / "time_series_metrics.csv", index=False)
        # Fusion mode shares & switch rate
        if args.fusion_stats and ts_res.mode_share is not None:
            stats_df = pd.DataFrame({
                "t_s": ts_res.times[:len(ts_res.mode_share['midpoint'])],
                "share_midpoint": ts_res.mode_share["midpoint"],
                "share_unsafe": ts_res.mode_share["unsafe"],
                "share_unsafe_clamped": ts_res.mode_share["unsafe_clamped"],
            })
            stats_df.to_csv(out_dir / "fusion_mode_stats.csv", index=False)
            if ts_res.switch_rate is not None:
                pd.DataFrame({"t_s": ts_res.times[:len(ts_res.switch_rate)], "switch_rate": ts_res.switch_rate}).to_csv(out_dir / "fusion_switch_rate.csv", index=False)
            # Derived average mode residence time (approx) = dt / switch_rate where switch_rate>0 else NaN
            if ts_res.switch_rate is not None and len(ts_res.switch_rate) > 0:
                import numpy as _np
                dt_local = float(cfg.sim.get("dt_s", 0.1))
                residence = dt_local / ts_res.switch_rate
                # Replace inf/NaN (zero switch rate) with NaN explicitly
                bad = ~_np.isfinite(residence)
                if bad.any():
                    residence[bad] = _np.nan
                pd.DataFrame({"t_s": ts_res.times[:len(residence)], "residence_time_est_s": residence}).to_csv(out_dir / "fusion_mode_residence_est.csv", index=False)
        if args.export_interval_bounds and ts_res.interval_lower is not None and ts_res.interval_upper is not None:
            pd.DataFrame({
                "interval_lower": ts_res.interval_lower,
                "interval_upper": ts_res.interval_upper,
            }).to_csv(out_dir / "secure_interval_bounds.csv", index=False)
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
            if ts_res.rmse_lat is not None:
                plt.figure(figsize=(6,3))
                plt.plot(ts_res.times, ts_res.rmse_lat, label="RMSE_lat [m]")
                if ts_res.rmse_2d is not None:
                    plt.plot(ts_res.times, ts_res.rmse_2d, label="RMSE_2D [m]")
                plt.xlabel("Zeit t [s]"); plt.ylabel("Fehler [m]")
                plt.title("Zeitverlauf Lateral & 2D RMSE")
                plt.legend(); plt.tight_layout(); plt.savefig(fig_dir/"fused_time_lat_2d.png", dpi=150); plt.close()
            # Secure interval growth plot
            if (
                ts_res.si_times is not None and ts_res.si_additive_p99 is not None
                and ts_res.si_joint_p99 is not None and ts_res.si_bias_pct is not None
            ):
                df_si = pd.DataFrame({
                    "t_s": ts_res.si_times,
                    "p99_additive": ts_res.si_additive_p99,
                    "p99_joint": ts_res.si_joint_p99,
                    "bias_pct": ts_res.si_bias_pct,
                })
                df_si.to_csv(out_dir / "secure_interval_growth.csv", index=False)
                plt.figure(figsize=(6.2,3.2))
                plt.plot(ts_res.si_times, ts_res.si_additive_p99, label="Additiv P99 [m]", color="#1b9e77")
                plt.plot(ts_res.si_times, ts_res.si_joint_p99, label="Joint P99 [m]", color="#d95f02")
                plt.xlabel("Zeit t [s]"); plt.ylabel("Intervallhalbbreite [m]")
                plt.title("Secure Intervall Wachstum (P99)")
                plt.legend(); plt.grid(alpha=0.25, linestyle=":")
                plt.tight_layout(); plt.savefig(fig_dir/"secure_interval_growth.png", dpi=150); plt.close()
                plt.figure(figsize=(6.2,3.2))
                plt.plot(ts_res.si_times, ts_res.si_bias_pct, label="Bias [%]", color="#7570b3")
                plt.xlabel("Zeit t [s]"); plt.ylabel("Additiv Bias [%]")
                plt.title("Additive vs. Joint P99 Bias Verlauf")
                plt.legend(); plt.grid(alpha=0.25, linestyle=":")
                plt.tight_layout(); plt.savefig(fig_dir/"secure_interval_bias.png", dpi=150); plt.close()
            # Fusion mode shares stacked area
            if args.fusion_stats and ts_res.mode_share is not None:
                plt.figure(figsize=(6.4,3.2))
                T = ts_res.times[:len(ts_res.mode_share['midpoint'])]
                plt.stackplot(T,
                               ts_res.mode_share['midpoint'],
                               ts_res.mode_share['unsafe'],
                               ts_res.mode_share['unsafe_clamped'],
                               labels=["midpoint","unsafe","unsafe_clamped"],
                               colors=["#8da0cb","#66c2a5","#fc8d62"], alpha=0.9)
                plt.xlabel("Zeit t [s]"); plt.ylabel("Anteil [-]")
                plt.title("Fusionsmodusanteile über Zeit")
                plt.legend(loc='upper right', fontsize=8)
                plt.tight_layout(); plt.savefig(fig_dir/"fusion_mode_share.png", dpi=150); plt.close()
            # Interval bounds plot longitudinal (sample subset median bounds)
            if ts_res.interval_lower is not None and ts_res.interval_upper is not None:
                # Show fused vs median lower/upper & midpoint
                # For performance we only store last interval snapshot; create synthetic representation
                plt.figure(figsize=(6.4,3.2))
                # Reconstruct midpoint
                midpoint = 0.5*(ts_res.interval_lower + ts_res.interval_upper)
                # Plot histogram-like lines (since time dimension lost, treat as distribution snapshot)
                import numpy as np
                # Sort for envelope visualisation
                ord_idx = np.argsort(midpoint)
                plt.plot(midpoint[ord_idx], label="midpoint (sorted)", color="#1b9e77")
                plt.plot(ts_res.interval_lower[ord_idx], label="lower", color="#d95f02", linestyle=":")
                plt.plot(ts_res.interval_upper[ord_idx], label="upper", color="#7570b3", linestyle=":")
                plt.ylabel("Fehlerraum [m]")
                plt.xlabel("Sample (sortiert nach midpoint)")
                plt.title("Asymmetrische Intervallgrenzen Snapshot")
                plt.legend(fontsize=8)
                plt.tight_layout(); plt.savefig(fig_dir/"fused_time_interval_bounds.png", dpi=150); plt.close()
        # Optional performance benchmark vs. legacy
        if args.perf:
            # Short legacy run (disable rule based & adaptive)
            cfg_legacy = load_config(args.config)
            # Force disable rule-based
            if "fusion" in cfg_legacy.sensors and cfg_legacy.sensors["fusion"].get("rule_based", False):
                cfg_legacy.sensors["fusion"]["rule_based"] = False
            rng_legacy = np.random.default_rng(get_seed(cfg_legacy) + 2222)
            import time as _time
            tL0 = _time.perf_counter()
            simulate_time_series(
                cfg_legacy, rng_legacy,
                threshold_oos=args.oos_threshold,
                with_lateral=False,
                adaptive_interval=False,
                interval_update_cadence_s=float(args.interval_update_cadence_s),
                export_interval_bounds=False,
                blend_steps=cfg_legacy.sensors.get("fusion", {}).get("blend_steps", 5),
            )
            tL1 = _time.perf_counter()
            pd.DataFrame([{
                "runtime_adaptive_s": t1 - t0,
                "runtime_legacy_s": tL1 - tL0,
                "overhead_pct": 100.0 * ((t1 - t0)/(tL1 - tL0) - 1.0) if (tL1 - tL0) > 0 else float('nan'),
                "n_samples": int(cfg.sim.get("N_samples", 0)),
                "horizon_s": float(cfg.sim.get("time_horizon_s", 0.0)),
                "dt_s": float(cfg.sim.get("dt_s", 0.0)),
            }]).to_csv(out_dir / "performance_fusion_runtime.csv", index=False)

    # OAT Sensitivity
    if args.oat:
        param_list = args.oat_params if args.oat_params else default_oat_params(cfg)
        delta_pct = float(cfg.sim.get("delta_pct", 10))
        oat_rng = np.random.default_rng(get_seed(cfg) + 999)
        oat_results = oat_sensitivity(cfg, param_list, delta_pct, min(3000, n), oat_rng)
        df_oat = pd.DataFrame(oat_results)
        df_oat.to_csv(out_dir / "sensitivity_oat.csv", index=False)
        if not args.no_plots:
            # Horizontal bar plot of abs_effect_pct
            import matplotlib.pyplot as plt
            plt.figure(figsize=(7, max(2, 0.4 * len(oat_results))))
            ylabels = [str(r['param']) for r in oat_results]
            effects = [float(r['abs_effect_pct']) for r in oat_results]
            y_pos = np.arange(len(oat_results))
            plt.barh(y_pos, effects, color="#4c72b0")
            plt.yticks(y_pos, ylabels)
            plt.xlabel("|ΔRMSE| max(±) [%]")
            plt.title(f"OAT Sensitivität (±{delta_pct:.1f}% Perturbation)")
            plt.tight_layout(); plt.savefig(Path(args.figdir)/"oat_bar.png", dpi=150); plt.close()

    # Extended OAT 2D Sensitivity
    if getattr(args, 'oat_2d', False):
        param_list_2d = args.oat_2d_params if args.oat_2d_params else (args.oat_params if args.oat_params else default_oat_params(cfg))
        delta_pct = float(cfg.sim.get("delta_pct", 10))
        rng_oat2d = np.random.default_rng(get_seed(cfg) + 1777)
        results_2d = oat_sensitivity_2d(cfg, param_list_2d, delta_pct, min(2500, n), rng_oat2d)
        pd.DataFrame(results_2d).to_csv(out_dir / "sensitivity_oat_2d.csv", index=False)
        if not args.no_plots and results_2d:
            import matplotlib.pyplot as plt
            plt.figure(figsize=(7.2, max(2.4, 0.45 * len(results_2d))))
            params = [r['param'] for r in results_2d]
            overall = [r['abs_effect_overall_pct'] for r in results_2d]
            y = np.arange(len(params))
            plt.barh(y, overall, color="#32648e")
            plt.yticks(y, params)
            plt.xlabel("Max |Δ| über Metriken [%]")
            plt.title(f"OAT 2D Sensitivität (±{delta_pct:.1f}%) – Gesamt")
            plt.grid(alpha=0.25, linestyle=":")
            plt.tight_layout(); plt.savefig(Path(args.figdir)/"oat_2d_overall_bar.png", dpi=150); plt.close()
            # Per-Metrik Vergleich (gruppenweise Balken): nur falls Effekte vorhanden
            metric_keys = [
                ("rmse_long", "abs_effect_rmse_long_pct"),
                ("rmse_lat", "abs_effect_rmse_lat_pct"),
                ("rmse_2d", "abs_effect_rmse_2d_pct"),
                ("p95_lat", "abs_effect_p95_lat_pct"),
                ("p95_2d", "abs_effect_p95_2d_pct"),
            ]
            # Build matrix param x metric
            effects_mat = []
            for r in results_2d:
                row = []
                for _, key in metric_keys:
                    row.append(r.get(key, np.nan))
                effects_mat.append(row)
            effects_arr = np.array(effects_mat, dtype=float)
            if not np.all(np.isnan(effects_arr)):
                plt.figure(figsize=(8.2, max(2.6, 0.50 * len(results_2d))))
                n_params = len(results_2d)
                n_metrics = len(metric_keys)
                y = np.arange(n_params)
                bar_h = 0.12 if n_metrics > 4 else 0.16
                # Center bars around y
                offsets = np.linspace(-(n_metrics-1)/2.0*bar_h*1.2, (n_metrics-1)/2.0*bar_h*1.2, n_metrics)
                palette = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e"]
                for mi, (label, _) in enumerate(metric_keys):
                    vals = effects_arr[:, mi]
                    if np.all(np.isnan(vals)):
                        continue
                    plt.barh(y + offsets[mi], vals, height=bar_h, label=label, color=palette[mi % len(palette)])
                plt.yticks(y, params)
                plt.xlabel("|Δ| [%]")
                plt.title("OAT 2D – Aufgeschlüsselte Effekte je Metrik")
                plt.grid(alpha=0.25, linestyle=":")
                plt.legend(fontsize=8, ncol=2)
                plt.tight_layout(); plt.savefig(Path(args.figdir)/"oat_2d_per_metric.png", dpi=150); plt.close()

    # Additive vs Joint P99 Bias Sensitivity
    if getattr(args, 'p99_bias_sens', False):
        param_list_bias = args.oat_params if args.oat_params else default_oat_params(cfg)
        delta_pct = float(cfg.sim.get("delta_pct", 10))
        rng_bias = np.random.default_rng(get_seed(cfg) + 5151)
        bias_rows = additive_p99_bias_sensitivity(cfg, param_list_bias, delta_pct, min(4000, n), rng_bias)
        pd.DataFrame(bias_rows).to_csv(out_dir / "sensitivity_additive_p99_bias.csv", index=False)
        if not args.no_plots and bias_rows:
            import matplotlib.pyplot as plt
            plt.figure(figsize=(7.0, max(2.4, 0.45 * len(bias_rows))))
            params = [r['param'] for r in bias_rows]
            delta_bias = [r['delta_bias_pct_max_abs'] for r in bias_rows]
            y = np.arange(len(params))
            plt.barh(y, delta_bias, color="#8c564b")
            plt.yticks(y, params)
            plt.xlabel("Max |Δ Bias| [%-Pkt]")
            plt.title(f"Additive vs Joint P99 Bias Sensitivität (±{delta_pct:.1f}%)")
            plt.grid(alpha=0.25, linestyle=":")
            plt.tight_layout(); plt.savefig(Path(args.figdir)/"sensitivity_additive_p99_bias.png", dpi=150); plt.close()

    # Lean Erweiterung: SRC + PRCC + Quantil & Exceedance Analysen
    if args.src_prcc or args.quantile_conditioning or args.exceedance:
        # Komponenten-Samples zusammenstellen (Basis gleiche wie secure/unsafe decomposition)
        component_map = {
            "balise": bal,
            "map": map_err,
            "odometry": odo,
            "imu": imu,
            "gnss_open": gnss_open_long,
        }
        if args.src_prcc:
            pipe_res = lean_src_prcc_pipeline(component_map, fused, fused_lat, fused_2d)
            # Write each list to CSV
            for key, rows in pipe_res.items():
                pd.DataFrame(rows).to_csv(out_dir / f"sensitivity_{key}.csv", index=False)
            if not args.no_plots and 'src_rmse_long_proxy' in pipe_res and 'prcc_rmse_long_proxy' in pipe_res:
                import matplotlib.pyplot as plt
                # Extract top n (all) for rmse_long_proxy
                src_rows = pipe_res['src_rmse_long_proxy']
                prcc_rows = pipe_res['prcc_rmse_long_proxy']
                # Align ordering by abs_src
                order = [r['param'] for r in src_rows]
                src_vals = [r['src'] for r in src_rows]
                prcc_map = {r['param']: r['prcc'] for r in prcc_rows}
                prcc_vals = [prcc_map[p] for p in order]
                y = np.arange(len(order))
                plt.figure(figsize=(7, max(2.5, 0.45 * len(order))))
                plt.barh(y + 0.2, src_vals, height=0.4, label='SRC (RMSE_long)', color='#4c72b0')
                plt.barh(y - 0.2, prcc_vals, height=0.4, label='PRCC (RMSE_long)', color='#dd8452')
                plt.yticks(y, order)
                plt.axvline(0, color='#444', linewidth=0.8)
                plt.xlabel('Koeffizient [-]')
                plt.title('Sensitivität SRC vs. PRCC – RMSE_long')
                plt.legend()
                plt.grid(alpha=0.25, linestyle=':')
                plt.tight_layout(); plt.savefig(Path(args.figdir)/'sensitivity_src_prcc_rmse_long.png', dpi=150); plt.close()
                # Scatter Vergleich
                plt.figure(figsize=(4.2,4))
                plt.scatter(src_vals, prcc_vals, c=np.arange(len(order)), cmap='viridis', s=60, edgecolors='k')
                for i,p in enumerate(order):
                    plt.text(src_vals[i], prcc_vals[i], p, fontsize=8, ha='left', va='bottom')
                plt.xlabel('SRC')
                plt.ylabel('PRCC')
                lim = max(1.0, max(max(map(abs, src_vals)), max(map(abs, prcc_vals))) * 1.05)
                plt.xlim(-lim, lim); plt.ylim(-lim, lim)
                plt.axhline(0, color='#666', linewidth=0.7, linestyle=':')
                plt.axvline(0, color='#666', linewidth=0.7, linestyle=':')
                plt.title('SRC vs. PRCC Streudiagramm')
                plt.grid(alpha=0.25, linestyle=':')
                plt.tight_layout(); plt.savefig(Path(args.figdir)/'sensitivity_src_vs_prcc_scatter.png', dpi=150); plt.close()
        if args.quantile_conditioning:
            qres = quantile_conditioning(fused, component_map, p=args.quantile_p)
            pd.DataFrame(qres).to_csv(out_dir / f"sensitivity_quantile_p{int(args.quantile_p)}.csv", index=False)
            if not args.no_plots and qres:
                import matplotlib.pyplot as plt
                ordered = sorted(qres, key=lambda r: abs(r.get(f'delta_q{int(args.quantile_p)}', 0.0)), reverse=True)
                params = [r['param'] for r in ordered]
                deltas = [r[f'delta_q{int(args.quantile_p)}'] for r in ordered]
                y = np.arange(len(params))
                plt.figure(figsize=(6.5, max(2.5, 0.45 * len(params))))
                plt.barh(y, deltas, color='#6a3d9a')
                plt.yticks(y, params)
                plt.xlabel(f"ΔQ{int(args.quantile_p)} [m]")
                plt.title(f"Quantil-Sensitivität ΔQ{int(args.quantile_p)} (High−Low)")
                plt.grid(alpha=0.25, linestyle=':')
                plt.tight_layout(); plt.savefig(Path(args.figdir)/f'sensitivity_delta_q{int(args.quantile_p)}.png', dpi=150); plt.close()
        if args.exceedance:
            thr = args.exceedance_threshold
            if thr is None:
                thr = float(np.percentile(np.abs(fused), 95))  # fallback p95 fused
            eres = exceedance_sensitivity(fused, component_map, threshold=thr)
            pd.DataFrame(eres).to_csv(out_dir / f"sensitivity_exceedance_T{thr:.3f}.csv", index=False)
            if not args.no_plots and eres:
                import matplotlib.pyplot as plt
                params = [r['param'] for r in eres]
                deltas = [r['delta_p_pct_points'] for r in eres]
                y = np.arange(len(params))
                plt.figure(figsize=(6.5, max(2.5, 0.45 * len(params))))
                plt.barh(y, deltas, color='#e31a1c')
                plt.yticks(y, params)
                plt.xlabel('ΔP(|e|>T) [%-Pkt]')
                plt.title(f'Exceedance Sensitivität ΔP(|e|>{thr:.3f} m)')
                plt.grid(alpha=0.25, linestyle=':')
                plt.tight_layout(); plt.savefig(Path(args.figdir)/f'sensitivity_exceedance_T{thr:.3f}_bar.png', dpi=150); plt.close()

    # ES95 Expected Shortfall Conditioning (nach Basis-Metriken & Komponenten Samples)
    if args.es95:
        component_map_es = {
            "balise": bal,
            "map": map_err,
            "odometry": odo,
            "imu": imu,
            "gnss_open": gnss_open_long,
        }
        es_rows = expected_shortfall_conditioning(fused, component_map_es, p=95.0)
        if es_rows:
            pd.DataFrame(es_rows).to_csv(out_dir / "sensitivity_es95.csv", index=False)
            if not args.no_plots:
                import matplotlib.pyplot as plt
                params = [r['param'] for r in es_rows]
                deltas = [r['delta_es_q95'] for r in es_rows]
                y = np.arange(len(params))
                plt.figure(figsize=(6.5, max(2.5, 0.45 * len(params))))
                plt.barh(y, deltas, color='#1b9e77')
                plt.yticks(y, params)
                plt.xlabel('ΔES95 [m]')
                plt.title('ES95 Sensitivität (High−Low)')
                plt.grid(alpha=0.25, linestyle=':')
                plt.tight_layout(); plt.savefig(Path(args.figdir)/'sensitivity_es95_bar.png', dpi=150); plt.close()

    # Sobol Analyse (am Ende – teurer Schritt)
    if args.sobol:
        sobol_params = args.sobol_params if args.sobol_params else default_oat_params(cfg)
        # Auto-Heuristik: Ziel ~ 1-2% typische ST Konf-Std für Top-Parameter bei moderatem k
        if args.sobol_auto_base:
            k = len(sobol_params)
            # Staffelung: kleiner k => höhere Basis, großer k => gedeckelt für Runtime
            if k <= 6:
                n_base = 1200
            elif k <= 10:
                n_base = 900
            elif k <= 16:
                n_base = 750
            else:
                n_base = 600
        else:
            n_base = int(args.sobol_base)
        try:
            sobol_metrics = ["rmse_long", "rmse_2d", "p95_long", "p95_2d"] if (args.sobol_metrics is None or len(args.sobol_metrics) == 0) else args.sobol_metrics
            sobol_res = sobol_sensitivity(
                cfg,
                sobol_params,
                n_base=n_base,
                mc_n=int(args.sobol_mc_n),
                rng=np.random.default_rng(get_seed(cfg) + 12345),
                metrics=sobol_metrics,
                delta_pct=float(args.sobol_delta_pct),
            )
            for mname, rows in sobol_res.items():
                pd.DataFrame(rows).to_csv(out_dir / f"sensitivity_sobol_{mname}.csv", index=False)
            # Konsolidiertes Ranking: Mittelwert Rang(ST) + Sekundärkriterium Rang(S1)
            rank_rows = []
            # Sammle alle Parameter
            all_params = sorted({r['param'] for rows in sobol_res.values() for r in rows})
            # Baue Lookup pro Metric
            metric_lookup = {m: {r['param']: r for r in rows} for m, rows in sobol_res.items()}
            for p in all_params:
                st_vals = []
                s1_vals = []
                coverage = 0
                for m, rows in sobol_res.items():
                    rmap = metric_lookup[m]
                    if p in rmap:
                        coverage += 1
                        st_vals.append(rmap[p]['ST'])
                        s1_vals.append(rmap[p]['S1'])
                if coverage == 0:
                    continue
                mean_st = float(np.nanmean(st_vals)) if st_vals else float('nan')
                mean_s1 = float(np.nanmean(s1_vals)) if s1_vals else float('nan')
                rank_rows.append({
                    'param': p,
                    'mean_ST': mean_st,
                    'mean_S1': mean_s1,
                    'metrics_covered': coverage,
                    'k_params': len(sobol_params),
                    'n_base_used': n_base,
                })
            if rank_rows:
                # Ranking nach mean_ST absteigend
                rank_rows.sort(key=lambda d: (float('-inf') if np.isnan(d['mean_ST']) else -d['mean_ST']))
                total_mean_st = sum(r['mean_ST'] for r in rank_rows if not np.isnan(r['mean_ST']))
                for r in rank_rows:
                    r['share_mean_ST'] = (r['mean_ST'] / total_mean_st) if (total_mean_st > 0 and not np.isnan(r['mean_ST'])) else float('nan')
                pd.DataFrame(rank_rows).to_csv(out_dir / "sensitivity_sobol_consolidated.csv", index=False)
                # Optionale Refinement Runde
                if getattr(args, 'sobol_refine_top_n', 0) > 0:
                    top_n = max(1, min(args.sobol_refine_top_n, len(rank_rows)))
                    refined_params = [r['param'] for r in rank_rows[:top_n]]
                    base_ref = int(args.sobol_refine_base) if getattr(args, 'sobol_refine_base', None) is not None else int(max(50, n_base * getattr(args,'sobol_refine_scale',2.0)))
                    try:
                        sobol_res_ref = sobol_sensitivity(
                            cfg,
                            refined_params,
                            n_base=base_ref,
                            mc_n=int(args.sobol_mc_n),
                            rng=np.random.default_rng(get_seed(cfg) + 54321),
                            metrics=sobol_metrics,
                            delta_pct=float(args.sobol_delta_pct),
                        )
                        for mname, rows in sobol_res_ref.items():
                            pd.DataFrame(rows).to_csv(out_dir / f"sensitivity_sobol_refined_{mname}.csv", index=False)
                        ref_rank_rows = []
                        all_params_ref = sorted({r['param'] for rows in sobol_res_ref.values() for r in rows})
                        ref_lookup = {m: {r['param']: r for r in rows} for m, rows in sobol_res_ref.items()}
                        for p in all_params_ref:
                            st_vals = [ref_lookup[m][p]['ST'] for m in sobol_res_ref if p in ref_lookup[m]]
                            s1_vals = [ref_lookup[m][p]['S1'] for m in sobol_res_ref if p in ref_lookup[m]]
                            mean_st = float(np.nanmean(st_vals)) if st_vals else float('nan')
                            mean_s1 = float(np.nanmean(s1_vals)) if s1_vals else float('nan')
                            ref_rank_rows.append({'param': p, 'mean_ST': mean_st, 'mean_S1': mean_s1, 'metrics_covered': len(sobol_res_ref), 'n_base_used': base_ref, 'refinement': True})
                        if ref_rank_rows:
                            total_mean_st_ref = sum(r['mean_ST'] for r in ref_rank_rows if not np.isnan(r['mean_ST']))
                            for r in ref_rank_rows:
                                r['share_mean_ST'] = (r['mean_ST'] / total_mean_st_ref) if (total_mean_st_ref > 0 and not np.isnan(r['mean_ST'])) else float('nan')
                            ref_rank_rows.sort(key=lambda d: (float('-inf') if np.isnan(d['mean_ST']) else -d['mean_ST']))
                            pd.DataFrame(ref_rank_rows).to_csv(out_dir / "sensitivity_sobol_consolidated_refined.csv", index=False)
                            if not args.no_plots:
                                import matplotlib.pyplot as plt
                                plt.figure(figsize=(6, max(2.0, 0.5 * len(ref_rank_rows))))
                                y = np.arange(len(ref_rank_rows))
                                plt.barh(y, [r['mean_ST'] for r in ref_rank_rows], color='#08519c')
                                plt.yticks(y, [r['param'] for r in ref_rank_rows])
                                plt.xlabel('mean_ST (refined)')
                                plt.title('Sobol Refined Top-N')
                                plt.grid(alpha=0.25, linestyle=':')
                                plt.tight_layout(); plt.savefig(Path(args.figdir)/'sensitivity_sobol_refined_meanST.png', dpi=150); plt.close()
                    except Exception as e_ref:
                        print(f"Sobol Refinement Fehler (ignoriert): {e_ref}")
            if not args.no_plots:
                import matplotlib.pyplot as plt
                for mname, rows in sobol_res.items():
                    plt.figure(figsize=(6.5, max(2.5, 0.45 * len(rows))))
                    params = [r['param'] for r in rows]
                    ST = [r['ST'] for r in rows]
                    S1 = [r['S1'] for r in rows]
                    y = np.arange(len(params))
                    plt.barh(y+0.18, ST, height=0.36, label='ST', color='#2b8cbe')
                    plt.barh(y-0.18, S1, height=0.36, label='S1', color='#a6bddb')
                    plt.yticks(y, params)
                    plt.xlabel('Index [-]')
                    plt.title(f'Sobol Indizes – {mname}')
                    plt.legend(); plt.grid(alpha=0.25, linestyle=':')
                    plt.tight_layout(); plt.savefig(Path(args.figdir)/f'sensitivity_sobol_{mname}.png', dpi=150); plt.close()
        except RuntimeError as e:
            print(f"Sobol Analyse übersprungen: {e}")

    # Early detection impact validation (difference in P95 if toggled hypothetically)
    if args.early_detect_validate and cfg.sensors.get("balise", {}).get("early_detection", {}).get("enabled", False) is False:
        # Simulate hypothetical early detection by reducing latency mean by c1*v (bounded)
        bal_cfg = cfg.sensors["balise"]
        early = bal_cfg.get("early_detection", {})
        c1 = early.get("c1_ms_per_mps", 0.5)
        cap_ms = early.get("cap_ms", 4.0)
        # Approx average speed from morphology
        v_avg = np.mean(cfg.raw.get("morphology", {}).get("speed_range_kmh", [0, 45])) / 3.6
        delta_t_ms = min(c1 * v_avg, cap_ms)
        # Approx effect: subtract v * delta_t from balise latency term only
        v_proxy = np.full(n, v_avg)
        bal_improved = bal - v_proxy * (delta_t_ms / 1000.0)
        secure_improved = bal_improved + odo + map_err
        joint_p99_improved = float(np.percentile(np.abs(secure_improved), 99))
        p95_before = metrics_fused.get("p95")
        p95_after = float(np.percentile(np.abs((secure_improved + unsafe)/2.0), 95))  # rough recompute fused proxy
        delta_p95 = p95_after - p95_before if p95_before is not None else float('nan')
        with (out_dir / "early_detection_eval.json").open("w") as f:
            json.dump({"p95_baseline": p95_before, "p95_hypo": p95_after, "delta_p95": delta_p95, "joint_p99_secure_baseline": joint_p99, "joint_p99_secure_hypo": joint_p99_improved}, f, indent=2)

    print(
        f"Saved metrics (JSON + CSV) to {out_dir}. Plots={'on' if not args.no_plots else 'off'} (minimal={args.minimal_plots}). "
        f"Raw samples={'saved' if args.save_samples else 'skipped'}. Time-series={'on' if args.time_series else 'off'}. "
        f"OAT={'on' if args.oat else 'off'}. OAT2D={'on' if getattr(args,'oat_2d',False) else 'off'}. P99BiasSens={'on' if getattr(args,'p99_bias_sens',False) else 'off'}. SRC/PRCC={'on' if args.src_prcc else 'off'}. Quantile={'on' if args.quantile_conditioning else 'off'}. Exceedance={'on' if args.exceedance else 'off'}. Sobol={'on' if args.sobol else 'off'}. ES95={'on' if args.es95 else 'off'}. FusionMode={fusion_mode}. Stress={','.join(stress_flags) if stress_flags else 'none'}."
    )


if __name__ == "__main__":
    main()