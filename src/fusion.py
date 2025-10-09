"""Fusion strategies.

Contains:
* Inverse-variance weighting (legacy surrogate)
* Rule-based 4-Regeln Schema (Clamping + Blend) – simplified for static MC epoch

The rule-based approach enforces a conservative safety interval derived from
secure path component P99 (additive) and clamps unsafe contributions while
allowing a smooth blend (alpha) if desired. For the current static Monte Carlo
epoch (no temporal state), the blend parameter is only a placeholder; the
interface is forward-compatible with time-series fusion where hysteresis over
several steps is applied.
"""
from __future__ import annotations

import numpy as np
from typing import Tuple


def fuse_pair(x_a: np.ndarray, var_a: np.ndarray, x_b: np.ndarray, var_b: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Inverse variance weighting (legacy baseline)."""
    var_a = np.clip(var_a, 1e-12, None)
    var_b = np.clip(var_b, 1e-12, None)
    w_a = var_b / (var_a + var_b)
    w_b = var_a / (var_a + var_b)
    x_f = w_a * x_a + w_b * x_b
    var_f = (var_a * var_b) / (var_a + var_b)
    return x_f, var_f


def rule_based_fusion(secure: np.ndarray, unsafe: np.ndarray, interval_width: float, blend_steps: int = 5) -> Tuple[np.ndarray, np.ndarray]:
    """Apply simplified 4-rule fusion (static epoch proxy).

    Rules (mapped to implementation):
      1. Primat des sicheren Pfads: Wenn |secure| <= interval_width ⇒ fused = secure.
      2. Sicherheitsintervallbegrenzung: Falls unsicherer Pfad genutzt wird, clamp(|unsafe|) ≤ interval_width.
      3. Sanfte Übergänge (Blend): Placeholder – static epoch returns direct selection; retained for API.
      4. Fail-safe Symmetrie: Output immer innerhalb [-interval_width, +interval_width].

    Returns fused values and proxy variance (empirical) for compatibility.
    """
    # Decide where secure path is within bounds (should generally be true by construction but keep explicit logic).
    use_secure = np.abs(secure) <= interval_width
    fused = np.empty_like(secure)
    # Where secure within bounds -> take it
    fused[use_secure] = secure[use_secure]
    # Else fallback to clamped unsafe
    unsafe_clamped = np.clip(unsafe, -interval_width, interval_width)
    fused[~use_secure] = unsafe_clamped[~use_secure]
    # Hard safety clamp (Rule 4)
    fused = np.clip(fused, -interval_width, interval_width)
    var_proxy = np.var(fused, ddof=1) * np.ones_like(fused)
    return fused, var_proxy

__all__ = ["fuse_pair", "rule_based_fusion"]