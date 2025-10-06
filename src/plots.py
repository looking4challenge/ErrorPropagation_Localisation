"""Plot helpers (PDF, CDF, QQ) - kept lightweight to avoid over-coupling.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence, Dict, Mapping
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats

# Zentrales konsistentes Farbschema (ColorBrewer / qualitative + leichte Anpassungen)
COLORS: Dict[str, str] = {
    "balise": "#1b9e77",      # grünlich
    "map": "#7570b3",         # violett
    "odometry": "#d95f02",    # orange
    "imu": "#e7298a",         # magenta
    "gnss_open": "#66a61e",   # grün
    "secure": "#1f78b4",      # blau
    "unsafe": "#e31a1c",      # rot
    "fused": "#6a3d9a",       # dunkles violett
}


def ensure_dir(d: str | Path):
    Path(d).mkdir(parents=True, exist_ok=True)


def plot_pdf(
    values: np.ndarray,
    out: Path,
    title: str = "PDF",
    x_label: str = "Positionsfehler [m]",
    y_label: str = "Wahrscheinlichkeitsdichte [1/m]",
    color: str | None = None,
):
    """Plot empirische PDF inkl. Normalapprox. Einheiten explizit.

    Parameters
    ----------
    values : np.ndarray
        Stichprobe (Positionsfehler, metrisch)
    out : Path
        Zieldatei (PNG)
    title : str
        Plot-Titel
    x_label : str
        X-Achsenbeschriftung mit Einheit
    y_label : str
        Y-Achsenbeschriftung mit Einheit (Dichte ⇒ 1/m)
    """
    ensure_dir(out.parent)
    plt.figure(figsize=(4, 3))
    plt.hist(values, bins=60, density=True, alpha=0.55, label="Stichprobe", color=color)
    mu = np.mean(values)
    sigma = np.std(values)
    if sigma > 0:
        xs = np.linspace(mu - 4 * sigma, mu + 4 * sigma, 300)
        plt.plot(
            xs,
            1 / (sigma * np.sqrt(2 * np.pi)) * np.exp(-0.5 * ((xs - mu) / sigma) ** 2),
            color if color else "r",
            linestyle="--",
            label="Normalapprox.",
        )
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


def plot_cdf(
    values: np.ndarray,
    out: Path,
    title: str = "CDF",
    x_label: str = "Positionsfehler [m]",
    y_label: str = "Kumulative Verteilung F(x) [-]",
    color: str | None = None,
):
    """Plot empirische CDF mit Einheiten."""
    ensure_dir(out.parent)
    plt.figure(figsize=(4, 3))
    xs = np.sort(values)
    ys = np.linspace(0, 1, len(xs))
    plt.plot(xs, ys, label="Empirisch", color=color)
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


def plot_qq(
    values: np.ndarray,
    out: Path,
    title: str = "QQ Plot",
    axis_label: str = "Positionsfehler [m]",
):
    """QQ-Plot (Normal) mit metrischen Achsenbeschriftungen."""
    ensure_dir(out.parent)
    plt.figure(figsize=(4, 3))
    stats.probplot(values, dist="norm", plot=plt)
    plt.title(title)
    # probplot erzeugt Achsen ohne Einheiten → nachträglich setzen
    plt.xlabel(f"Theoretische Quantile {axis_label}")
    plt.ylabel(f"Empirische Quantile {axis_label}")
    # Hilfslinien
    plt.axline((0, 0), slope=1, color="#444", linewidth=0.8, linestyle=":")
    plt.grid(alpha=0.25, linestyle=":")
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


def plot_multi_pdf(
    components: Mapping[str, np.ndarray],
    out: Path,
    title: str,
    x_label: str = "Positionsfehler [m]",
    y_label: str = "Dichte [1/m]",
    max_bins: int = 70,
    show_stats: bool = True,
    kde: bool = False,
):
    """Überlagerte PDFs mehrerer Komponenten (normalisierte Histogramme).

    Parameters
    ----------
    components : Mapping[str, ndarray]
        name -> Stichprobe
    show_stats : bool
        Falls True, RMSE & P95 in Legende ergänzen
    kde : bool
        Optional simple Gaussian KDE (scipy) – nicht default (Performance)
    """
    ensure_dir(out.parent)
    plt.figure(figsize=(6, 3.2))
    for name, vals in components.items():
        c = COLORS.get(name, None)
        # Histogram als Linie (step) für bessere Vergleichbarkeit
        hist, edges = np.histogram(vals, bins=max_bins, density=True)
        centers = 0.5 * (edges[:-1] + edges[1:])
        label = name
        if show_stats:
            rmse = np.sqrt(np.mean(vals**2))
            p95 = np.percentile(vals, 95)
            label = f"{name} (RMSE={rmse:.3f} m, P95={p95:.3f} m)"
        plt.plot(centers, hist, label=label, color=c, linewidth=1.4)
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.legend(fontsize=8)
    plt.grid(alpha=0.25, linestyle=":")
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


def plot_multi_cdf(
    components: Mapping[str, np.ndarray],
    out: Path,
    title: str,
    x_label: str = "Positionsfehler [m]",
    y_label: str = "F(x) [-]",
):
    """Überlagerte empirische CDFs."""
    ensure_dir(out.parent)
    plt.figure(figsize=(6, 3.2))
    for name, vals in components.items():
        xs = np.sort(vals)
        ys = np.linspace(0, 1, len(xs))
        c = COLORS.get(name, None)
        plt.plot(xs, ys, label=name, color=c, linewidth=1.4)
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.legend(fontsize=8)
    plt.grid(alpha=0.25, linestyle=":")
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


__all__ = [
    "COLORS",
    "plot_pdf",
    "plot_cdf",
    "plot_qq",
    "plot_multi_pdf",
    "plot_multi_cdf",
]
