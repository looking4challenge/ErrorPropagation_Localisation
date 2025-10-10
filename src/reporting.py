"""Utility functions to generate Markdown tables for metrics & sensitivity results.

Creates standalone markdown snippets so the main report can include them via copy/paste
or future automated inclusion (pattern replacement of anchors).
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import math
from typing import Sequence, Optional


def _round(v, digits=3):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return ""  # empty cell for missing
    if isinstance(v, (int,)):
        return str(v)
    return f"{v:.{digits}g}" if abs(v) < 1e-2 or abs(v) >= 1e3 else f"{v:.{digits}f}".rstrip('0').rstrip('.')


def metrics_table(metrics_csv: Path, out_md: Path, include_lateral_2d: bool = True) -> None:
    df = pd.read_csv(metrics_csv)
    # Order of components – keep original but ensure fused last for emphasis
    order = [c for c in [
        "balise", "map", "odometry", "imu", "gnss_open", "gnss_urban", "gnss_tunnel",
        "secure", "unsafe", "fused"
    ] if c in set(df.component)]
    df = df.set_index("component").loc[order].reset_index()
    cols = ["component", "mean", "std", "rmse", "p50", "p90", "p95", "p99"]
    if include_lateral_2d and {"rmse_lateral", "p95_lateral", "rmse_2d", "p95_2d"}.issubset(df.columns):
        cols += ["rmse_lateral", "p95_lateral", "rmse_2d", "p95_2d"]
    subset = df[cols]
    # Build markdown
    header = "| " + " | ".join([c.replace('_', ' ') for c in subset.columns]) + " |"
    sep = "|" + "---|" * len(subset.columns)
    rows = []
    for _, r in subset.iterrows():
        rows.append("| " + " | ".join(_round(r[c]) for c in subset.columns) + " |")
    md = ["<!-- AUTO-GENERATED: metrics_table -->", header, sep, *rows, ""]
    # Relative improvements secure→fused if present (robust against missing / NaN)
    if {"secure", "fused"}.issubset(set(df.component)):
        try:
            idx_df = df.set_index('component')
            def _safe_float(x):
                try:
                    return float(x)
                except Exception:
                    return float('nan')
            rmse_secure = _safe_float(idx_df.loc['secure', 'rmse'])
            rmse_fused = _safe_float(idx_df.loc['fused', 'rmse'])
            p95_secure = _safe_float(idx_df.loc['secure', 'p95'])
            p95_fused = _safe_float(idx_df.loc['fused', 'p95'])
            if rmse_secure > 0 and p95_secure > 0 and not any(math.isnan(x) for x in [rmse_fused, p95_fused]):
                red_rmse = 100.0 * (1 - rmse_fused / rmse_secure)
                red_p95 = 100.0 * (1 - p95_fused / p95_secure)
                md.append(f"*Relativer Gewinn Fused vs Secure:* RMSE −{red_rmse:.1f}% ; P95 −{red_p95:.1f}%.")
        except Exception:
            pass
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md), encoding="utf-8")


def oat_table(oat_csv: Path, out_md: Path, top_n: int = 10):
    if not oat_csv.exists():
        return
    df = pd.read_csv(oat_csv)
    df = df.sort_values("abs_effect_pct", ascending=False).head(top_n)
    cols = ["param", "baseline_rmse", "rmse_minus", "rmse_plus", "rel_change_minus_pct", "rel_change_plus_pct", "abs_effect_pct"]
    header = "| " + " | ".join([c.replace('_', ' ') for c in cols]) + " |"
    sep = "|" + "---|" * len(cols)
    rows = ["| " + " | ".join(_round(r[c]) for c in cols) + " |" for _, r in df.iterrows()]
    out_md.write_text("\n".join(["<!-- AUTO-GENERATED: oat_table -->", header, sep, *rows, ""]), encoding="utf-8")


def sobol_table(sobol_consolidated_csv: Path, out_md: Path, top_n: int = 12):
    if not sobol_consolidated_csv.exists():
        return
    df = pd.read_csv(sobol_consolidated_csv)
    df = df.sort_values("mean_ST", ascending=False).head(top_n)
    cols = ["param", "mean_ST", "mean_S1", "share_mean_ST", "metrics_covered"]
    header = "| " + " | ".join([c.replace('_', ' ') for c in cols]) + " |"
    sep = "|" + "---|" * len(cols)
    rows = ["| " + " | ".join(_round(r[c]) for c in cols) + " |" for _, r in df.iterrows()]
    out_md.write_text("\n".join(["<!-- AUTO-GENERATED: sobol_table -->", header, sep, *rows, ""]), encoding="utf-8")


def quantile_table(q_csv: Path, out_md: Path):
    if not q_csv.exists():
        return
    df = pd.read_csv(q_csv)
    # Expect columns param, baseline_q95, low_q95, high_q95, delta_q95
    if "delta_q95" not in df.columns:
        # fallback to generic naming search
        delta_col = [c for c in df.columns if c.startswith("delta_q")] or []
        if delta_col:
            df.rename(columns={delta_col[0]: "delta_q95"}, inplace=True)
    df = df.sort_values("delta_q95", ascending=False)
    cols = [c for c in ["param", "baseline_q95", "low_q95", "high_q95", "delta_q95"] if c in df.columns]
    header = "| " + " | ".join([c.replace('_', ' ') for c in cols]) + " |"
    sep = "|" + "---|" * len(cols)
    rows = ["| " + " | ".join(_round(r[c]) for c in cols) + " |" for _, r in df.iterrows()]
    out_md.write_text("\n".join(["<!-- AUTO-GENERATED: quantile_table -->", header, sep, *rows, ""]), encoding="utf-8")


def bias_p99_table(bias_csv: Path, out_md: Path, top_n: int = 10):
    if not bias_csv.exists():
        return
    df = pd.read_csv(bias_csv)
    # expecting delta_bias_pct_max_abs
    if "delta_bias_pct_max_abs" not in df.columns:
        return
    df = df.sort_values("delta_bias_pct_max_abs", ascending=False).head(top_n)
    cols = ["param", "additive_bias_pct_baseline", "delta_bias_pct_max_abs"]
    subset_cols = [c for c in cols if c in df.columns]
    header = "| " + " | ".join([c.replace('_', ' ') for c in subset_cols]) + " |"
    sep = "|" + "---|" * len(subset_cols)
    rows = ["| " + " | ".join(_round(r.get(c)) for c in subset_cols) + " |" for _, r in df.iterrows()]
    out_md.write_text("\n".join(["<!-- AUTO-GENERATED: p99_bias_table -->", header, sep, *rows, ""]), encoding="utf-8")


def generate_all(result_dir: Path, report_dir: Path) -> None:
    metrics_table(result_dir / "metrics_all.csv", report_dir / "metrics_table.md")
    oat_table(result_dir / "sensitivity_oat.csv", report_dir / "sensitivity_oat_table.md")
    sobol_table(result_dir / "sensitivity_sobol_consolidated.csv", report_dir / "sensitivity_sobol_table.md")
    quantile_table(result_dir / "sensitivity_quantile_p95.csv", report_dir / "sensitivity_quantile_table.md")
    bias_p99_table(result_dir / "sensitivity_additive_p99_bias.csv", report_dir / "sensitivity_p99_bias_table.md")


__all__ = [
    "metrics_table",
    "oat_table",
    "sobol_table",
    "quantile_table",
    "bias_p99_table",
    "generate_all",
]
