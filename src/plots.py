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


def add_plot_explanation(explanation: str, fontsize: int = 8, color: str = "#444444"):
    """Platziert eine erklärende Beschreibung zentriert zwischen Titel und Plot-Fläche.

    Umsetzung: Nutzung von axes-koordinaten (ax.transAxes). Position y≈0.92 (unterhalb des Titels, oberhalb Datenbereich).
    Fallback: Falls keine aktive Axes vorhanden → keine Aktion.
    """
    ax = plt.gca()
    # Reserviere etwas Platz oben
    fig = ax.figure
    if fig is not None:
        try:
            fig.subplots_adjust(top=0.80)
        except Exception:
            pass
    ax.text(0.5, 0.92, explanation, ha='center', va='top', transform=ax.transAxes,
            fontsize=fontsize, color=color, wrap=True)


def plot_pdf(
    values: np.ndarray,
    out: Path,
    title: str = "PDF",
    x_label: str = "Positionsfehler [m]",
    y_label: str = "Wahrscheinlichkeitsdichte [1/m]",
    color: str | None = None,
    explanation: str | None = None,
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
    explanation : str | None
        Optionale laienverständliche Erklärung des Plots
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
    plt.grid(alpha=0.25, linestyle=":")
    plt.legend()
    
    # Standarderklärung falls keine spezifische angegeben
    if explanation is None:
        explanation = "Wahrscheinlichkeitsverteilung der Positionsfehler. Histogram zeigt gemessene Häufigkeiten, gestrichelte Linie die beste Normalverteilungs-Näherung."
    
    if explanation:
        add_plot_explanation(explanation)
    
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()


def plot_cdf(
    values: np.ndarray,
    out: Path,
    title: str = "CDF",
    x_label: str = "Positionsfehler [m]",
    y_label: str = "Kumulative Verteilung F(x) [-]",
    color: str | None = None,
    explanation: str | None = None,
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
    plt.grid(alpha=0.25, linestyle=":")
    
    # Standarderklärung falls keine spezifische angegeben
    if explanation is None:
        explanation = "Kumulative Verteilung: Zeigt für jeden Fehlerwert x die Wahrscheinlichkeit, dass der tatsächliche Fehler ≤ x ist. Beispiel: Bei y=0.95 kann man das 95%-Perzentil ablesen."
    
    if explanation:
        add_plot_explanation(explanation)
    
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()


def plot_qq(
    values: np.ndarray,
    out: Path,
    title: str = "QQ Plot",
    axis_label: str = "Positionsfehler [m]",
    explanation: str | None = None,
):
    """QQ-Plot (Normal) mit metrischen Achsenbeschriftungen."""
    ensure_dir(out.parent)
    plt.figure(figsize=(4, 3))
    stats.probplot(values, dist="norm", plot=plt)
    plt.title(title)
    # probplot erzeugt Achsen ohne Einheiten → nachträglich setzen
    plt.xlabel(f"Theoretische Quantile {axis_label}")
    plt.ylabel(f"Empirische Quantile {axis_label}")
    # Hilfslinien & Grid (konform mit anderen Plots)
    plt.axline((0, 0), slope=1, color="#444", linewidth=0.8, linestyle=":")
    plt.grid(alpha=0.25, linestyle=":")
    
    # Standarderklärung falls keine spezifische angegeben
    if explanation is None:
        explanation = "Quantil-Quantil-Plot: Vergleicht die gemessenen Werte mit einer Normalverteilung. Punkte nahe der Diagonale bedeuten gute Normalverteilungs-Näherung. Abweichungen zeigen Verteilungsunterschiede."
    
    if explanation:
        add_plot_explanation(explanation)
    
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches='tight')
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
    explanation: str | None = None,
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
    explanation : str | None
        Optionale laienverständliche Erklärung des Plots
    """
    ensure_dir(out.parent)
    plt.figure(figsize=(6, 3.2))
    # Erkennung identischer / nahezu identischer Verteilungen (vereinfacht):
    names = list(components.keys())
    arrays = [np.asarray(components[n]) for n in names]
    identical_groups: list[list[int]] = []
    visited: set[int] = set()
    for i, base in enumerate(arrays):
        if i in visited:
            continue
        group = [i]
        base_sorted = np.sort(base)
        for j in range(i+1, len(arrays)):
            if j in visited:
                continue
            a = arrays[j]
            if a.shape != base.shape:
                continue
            a_sorted = np.sort(a)
            # Schnelle Ähnlichkeitsheuristik: max abs diff + Varianzverhältnis + KS-Statistik
            max_diff = float(np.max(np.abs(base_sorted - a_sorted)))
            var_base = float(np.var(base_sorted)) + 1e-15
            var_a = float(np.var(a_sorted)) + 1e-15
            var_ratio = max(var_base/var_a, var_a/var_base)
            if max_diff < 1e-6 and var_ratio < 1.0005:
                group.append(j)
        for g in group:
            visited.add(g)
        identical_groups.append(group)

    line_styles_cycle = ["-", "--", ":", "-."]
    style_map: dict[int, str] = {}
    for grp in identical_groups:
        for k, idx in enumerate(grp):
            style_map[idx] = line_styles_cycle[k % len(line_styles_cycle)]

    for idx, name in enumerate(names):
        vals = arrays[idx]
        c = COLORS.get(name, None)
        hist, edges = np.histogram(vals, bins=max_bins, density=True)
        centers = 0.5 * (edges[:-1] + edges[1:])
        label = name
        if show_stats:
            rmse = np.sqrt(np.mean(vals**2))
            p95 = np.percentile(vals, 95)
            label = f"{name} (RMSE={rmse:.3f} m, P95={p95:.3f} m)"
        if any(idx in grp and len(grp) > 1 for grp in identical_groups):
            label += " [identisch]"
        ls = style_map.get(idx, "-")
        plt.plot(centers, hist, label=label, color=c, linewidth=1.4, linestyle=ls)
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.legend(fontsize=8)
    plt.grid(alpha=0.25, linestyle=":")
    
    # Standarderklärung falls keine spezifische angegeben
    if explanation is None:
        explanation = "Vergleich der Fehlerverteilungen verschiedener Komponenten. Jede Linie zeigt die Wahrscheinlichkeitsdichte einer Komponente. Breitere Kurven bedeuten größere Streuung."
    
    if explanation:
        add_plot_explanation(explanation)
    
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()


def plot_multi_cdf(
    components: Mapping[str, np.ndarray],
    out: Path,
    title: str,
    x_label: str = "Positionsfehler [m]",
    y_label: str = "F(x) [-]",
    explanation: str | None = None,
):
    """Überlagerte empirische CDFs."""
    ensure_dir(out.parent)
    plt.figure(figsize=(6, 3.2))
    names = list(components.keys())
    arrays = [np.asarray(components[n]) for n in names]
    identical_groups: list[list[int]] = []
    visited: set[int] = set()
    for i, base in enumerate(arrays):
        if i in visited:
            continue
        group = [i]
        base_sorted = np.sort(base)
        for j in range(i+1, len(arrays)):
            if j in visited:
                continue
            a = arrays[j]
            if a.shape != base.shape:
                continue
            a_sorted = np.sort(a)
            max_diff = float(np.max(np.abs(base_sorted - a_sorted)))
            var_base = float(np.var(base_sorted)) + 1e-15
            var_a = float(np.var(a_sorted)) + 1e-15
            var_ratio = max(var_base/var_a, var_a/var_base)
            if max_diff < 1e-6 and var_ratio < 1.0005:
                group.append(j)
        for g in group:
            visited.add(g)
        identical_groups.append(group)
    line_styles_cycle = ["-", "--", ":", "-."]
    style_map: dict[int, str] = {}
    for grp in identical_groups:
        for k, idx in enumerate(grp):
            style_map[idx] = line_styles_cycle[k % len(line_styles_cycle)]
    for idx, name in enumerate(names):
        vals = arrays[idx]
        xs = np.sort(vals)
        ys = np.linspace(0, 1, len(xs))
        c = COLORS.get(name, None)
        label = name
        if any(idx in grp and len(grp) > 1 for grp in identical_groups):
            label += " [identisch]"
        ls = style_map.get(idx, "-")
        plt.plot(xs, ys, label=label, color=c, linewidth=1.4, linestyle=ls)
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.legend(fontsize=8)
    plt.grid(alpha=0.25, linestyle=":")
    
    # Standarderklärung falls keine spezifische angegeben
    if explanation is None:
        explanation = "Vergleich der kumulativen Verteilungen verschiedener Komponenten. Steilere Kurven bedeuten präzisere Messungen, flachere größere Unsicherheit."
    
    if explanation:
        add_plot_explanation(explanation)
    
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()


__all__ = [
    "COLORS",
    "add_plot_explanation",
    "plot_pdf",
    "plot_cdf",
    "plot_qq",
    "plot_multi_pdf",
    "plot_multi_cdf",
]
