"""Plot helpers (PDF, CDF, QQ) - kept lightweight to avoid over-coupling.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats


def ensure_dir(d: str | Path):
    Path(d).mkdir(parents=True, exist_ok=True)


def plot_pdf(values: np.ndarray, out: Path, title: str = "PDF"):
    ensure_dir(out.parent)
    plt.figure(figsize=(4,3))
    plt.hist(values, bins=60, density=True, alpha=0.6, label="Samples")
    mu = np.mean(values); sigma = np.std(values)
    xs = np.linspace(mu - 4*sigma, mu + 4*sigma, 300)
    plt.plot(xs, 1/(sigma*np.sqrt(2*np.pi))*np.exp(-0.5*((xs-mu)/sigma)**2), 'r--', label="Normal approx")
    plt.title(title)
    plt.legend(); plt.tight_layout(); plt.savefig(out, dpi=150); plt.close()


def plot_cdf(values: np.ndarray, out: Path, title: str = "CDF"):
    ensure_dir(out.parent)
    plt.figure(figsize=(4,3))
    xs = np.sort(values)
    ys = np.linspace(0,1,len(xs))
    plt.plot(xs, ys, label="Empirical")
    plt.title(title); plt.xlabel("Error"); plt.ylabel("F(x)")
    plt.tight_layout(); plt.savefig(out, dpi=150); plt.close()


def plot_qq(values: np.ndarray, out: Path, title: str = "QQ Plot"):
    ensure_dir(out.parent)
    plt.figure(figsize=(4,3))
    stats.probplot(values, dist="norm", plot=plt)
    plt.title(title)
    plt.tight_layout(); plt.savefig(out, dpi=150); plt.close()


__all__ = ["plot_pdf", "plot_cdf", "plot_qq"]
