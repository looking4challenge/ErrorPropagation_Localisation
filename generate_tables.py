"""CLI helper to auto-generate Markdown tables for metrics & sensitivities.

Usage (PowerShell):
  python generate_tables.py --results results --report report
"""
from __future__ import annotations

import argparse
from pathlib import Path
from src.reporting import generate_all


def main():
    ap = argparse.ArgumentParser(description="Generate Markdown tables from simulation results")
    ap.add_argument("--results", default="results", help="Directory containing metrics_all.csv & sensitivity CSVs")
    ap.add_argument("--report", default="report", help="Output directory for markdown table snippets")
    args = ap.parse_args()
    res_dir = Path(args.results)
    rep_dir = Path(args.report)
    if not res_dir.exists():
        raise SystemExit(f"Results directory not found: {res_dir}")
    rep_dir.mkdir(parents=True, exist_ok=True)
    generate_all(res_dir, rep_dir)
    print(f"Generated tables in {rep_dir}")


if __name__ == "__main__":
    main()
