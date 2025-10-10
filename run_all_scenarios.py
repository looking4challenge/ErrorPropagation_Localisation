from __future__ import annotations
"""
Batch Runner für alle definierten Szenario-YAMLs (ohne sehr rechenaufwändige Sobol-Analyse).
Erzeugt je Szenario eigene Ergebnis- und Figure-Unterordner.

Enthaltene Analysen:
- Basis Monte Carlo (N=10000)
- Secure Interval Export + Komponenten-Kovarianz
- Time-Series (+adaptive Intervalle, Fusionsstatistiken, Intervall-Bounds)
- Konvergenz-Traces (RMSE/P95/P99/ES95)
- OAT (longitudinal) & OAT 2D
- Additive vs Joint P99 Bias Sensitivität
- SRC & PRCC
- Quantil-Conditioning (p=95)
- Exceedance Sensitivität (T = p95 fused fallback) 
- ES95 Conditioning

Ausgeschlossen (bewusst):
- Sobol (zu rechenintensiv für Standardlauf)
- Optionale Sobol-Refinements

Optionales Abschalten einzelner Feature-Gruppen über Umgebungsvariablen ("0" oder leer):
  DISABLE_TIME_SERIES
  DISABLE_SENSITIVITY   (deaktiviert OAT / OAT2D / P99Bias / SRC/PRCC / Quantil / Exceedance / ES95)
  DISABLE_CONVERGENCE
  DISABLE_INTERVAL_EXPORT

Beispiel PowerShell:
  python run_all_scenarios.py
"""
import os
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).parent
CONFIG_DIR = ROOT / "config"
RUN_SIM = ROOT / "run_sim.py"

SCENARIOS = [
    "scenario_regular.yml",
    "scenario_bad_weather.yml",
    "scenario_no_gnss.yml",
    "scenario_odo_5cm.yml",
]

def env_disabled(name: str) -> bool:
    val = os.environ.get(name, "").strip().lower()
    return val in {"0","false","no","off"}

DIS_TIME = env_disabled("DISABLE_TIME_SERIES")
DIS_SENS = env_disabled("DISABLE_SENSITIVITY")
DIS_CONV = env_disabled("DISABLE_CONVERGENCE")
DIS_INTERVAL = env_disabled("DISABLE_INTERVAL_EXPORT")

BASE_FLAGS = [
    "--export-secure-interval",
    "--export-covariance",
]
if not DIS_TIME:
    BASE_FLAGS += ["--time-series","--fusion-stats","--export-interval-bounds"]
if not DIS_CONV:
    BASE_FLAGS += ["--convergence"]
if not DIS_INTERVAL:
    pass  # already included export-secure-interval & interval bounds above

SENS_FLAGS = [] if DIS_SENS else [
    "--oat",
    "--oat-2d",
    "--p99-bias-sens",
    "--src-prcc",
    "--quantile-conditioning",
    "--exceedance",
    "--es95",
]

# Keine Sobol Flags anhängen (bewusst)

def run():
    python_exe = sys.executable
    for scen in SCENARIOS:
        cfg_path = CONFIG_DIR / scen
        if not cfg_path.exists():
            print(f"[WARN] Szenario fehlt: {cfg_path}")
            continue
        scen_tag = scen.replace("scenario_", "").replace(".yml", "")
        out_dir = ROOT / "results" / scen_tag
        fig_dir = ROOT / "figures" / scen_tag
        out_dir.mkdir(parents=True, exist_ok=True)
        fig_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            python_exe, str(RUN_SIM),
            "--config", str(cfg_path),
            "--out", str(out_dir),
            "--figdir", str(fig_dir),
            "--override-n", "10000",
            # Plot-Erklärungen sind schon in Plotfunktionen integriert
        ] + BASE_FLAGS + SENS_FLAGS
        print("\n=== RUN SCENARIO:", scen_tag, "===")
        print("CMD:", " ".join(cmd))
        # Subprozess ausführen
        res = subprocess.run(cmd, capture_output=True, text=True)
        print(res.stdout)
        if res.returncode != 0:
            print(res.stderr)
            print(f"[ERROR] Szenario {scen_tag} fehlgeschlagen (RC={res.returncode})")
        else:
            print(f"[OK] Szenario {scen_tag} abgeschlossen. Ergebnisse: {out_dir}")

if __name__ == "__main__":
    run()
