"""Distribution samplers including truncated and mixture models.

Focus: Only implement what is immediately required by current config.
Extend incrementally as more distributions are needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Any
import numpy as np
from scipy import stats


class SamplerRegistry:
    def __init__(self):
        self._map: Dict[str, Callable[[Dict[str, Any], int, np.random.Generator], np.ndarray]] = {}

    def register(self, name: str):
        def deco(fn):
            self._map[name] = fn
            return fn
        return deco

    def get(self, name: str):
        if name not in self._map:
            raise KeyError(f"Distribution '{name}' not registered")
        return self._map[name]

    def sample(self, spec: Dict[str, Any], n: int, rng: np.random.Generator) -> np.ndarray:
        dist = spec.get("dist")
        if dist is None:
            raise ValueError("Distribution spec requires 'dist' key")
        return self.get(dist)(spec, n, rng)


registry = SamplerRegistry()


@registry.register("normal")
def _normal(spec, n, rng):
    return rng.normal(spec["mean"], spec["std"], size=n)


@registry.register("uniform")
def _uniform(spec, n, rng):
    return rng.uniform(spec["low"], spec["high"], size=n)


@registry.register("trunc_normal")
def _trunc_normal(spec, n, rng):
    a, b = (spec["lower"] - spec["mean"]) / spec["std"], (spec["upper"] - spec["mean"]) / spec["std"]
    return stats.truncnorm.rvs(a, b, loc=spec["mean"], scale=spec["std"], size=n, random_state=rng)


@registry.register("rayleigh")
def _rayleigh(spec, n, rng):
    return stats.rayleigh.rvs(scale=spec["sigma"], size=n, random_state=rng)


@registry.register("trunc_exp")
def _trunc_exp(spec, n, rng):
    lam = spec["lambda"]
    cap = spec["cap"]
    # Inverse CDF sampling of truncated exponential [0, cap]
    u = rng.uniform(0, 1, size=n)
    denom = 1 - np.exp(-lam * cap)
    return -np.log(1 - u * denom) / lam


def sample_mixture(base: np.ndarray, tail: np.ndarray, weight: float, rng: np.random.Generator) -> np.ndarray:
    if not (0 <= weight <= 1):
        raise ValueError("weight must be in [0,1]")
    mask = rng.uniform(0, 1, size=base.shape[0]) < weight
    out = base.copy()
    out[mask] = tail[mask]
    return out


__all__ = ["registry", "sample_mixture"]


# --- Correlation / Copula utilities ---
def sample_correlated_gaussian(rho: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    """Sample n d-dimensional standard normal vectors with correlation matrix rho.

    Uses Cholesky factorisation; adds small jitter if matrix not PD due to rounding.
    """
    if rho.shape[0] != rho.shape[1]:
        raise ValueError("rho must be square")
    d = rho.shape[0]
    # Ensure symmetry
    rho = (rho + rho.T) / 2.0
    # Jitter if needed
    for _ in range(3):
        try:
            L = np.linalg.cholesky(rho)
            break
        except np.linalg.LinAlgError:
            rho = rho + np.eye(d) * 1e-8
    else:
        # Fallback: eigenvalue projection to nearest PSD then jitter
        w, V = np.linalg.eigh(rho)
        w_clipped = np.clip(w, 1e-8, None)
        rho = (V @ np.diag(w_clipped) @ V.T)
        rho = rho / np.sqrt(np.outer(np.diag(rho), np.diag(rho)))  # re-normalize to corr
        L = np.linalg.cholesky(rho)
    z = rng.normal(size=(n, d))
    return z @ L.T  # (n,d)


def empirical_corr(x: np.ndarray) -> np.ndarray:
    return np.corrcoef(x, rowvar=False)


__all__.extend(["sample_correlated_gaussian", "empirical_corr"])