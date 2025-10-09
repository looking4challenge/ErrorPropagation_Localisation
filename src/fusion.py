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


def rule_based_fusion(secure: np.ndarray, unsafe: np.ndarray, interval_width: float, blend_steps: int = 5,
            prefer: str = "unsafe") -> Tuple[np.ndarray, np.ndarray]:
  """Apply rule-based fusion (static epoch proxy) with preference strategy.

  Updated Semantik (2025-10-09): Präzisionspfad (unsafe = GNSS+IMU) wird genutzt,
  solange er innerhalb der sicheren Intervallhalbbreite liegt. Andernfalls Fallback
  auf sicheren Pfad. Beide Pfade werden final auf die Intervallgrenzen geclamped.

  Regeln (aktualisiert):
    1. If prefer=='unsafe' and |unsafe| <= interval_width ⇒ fused = clamp(unsafe).
     (Bei prefer!='unsafe' wird legacy Verhalten beibehalten.)
    2. Else fused = clamp(secure).
    3. Blend placeholder (blend_steps) noch nicht zeitdynamisch genutzt.
    4. Sicherheitsgarantie: |fused| ≤ interval_width stets gewährleistet.

  Returns
  -------
  fused : ndarray
    Gewählter Pfad pro Sample.
  var_proxy : ndarray
    Einheitliches Varianz-Proxy (empirisch) für Kompatibilität.
  """
  fused = np.empty_like(secure)
  if prefer == "unsafe":
    unsafe_in = np.abs(unsafe) <= interval_width
    # Use unsafe where inside interval
    fused[unsafe_in] = np.clip(unsafe[unsafe_in], -interval_width, interval_width)
    # Fallback to secure otherwise (clamped for symmetry)
    fused[~unsafe_in] = np.clip(secure[~unsafe_in], -interval_width, interval_width)
  else:
    # Legacy behaviour (secure-first)
    secure_in = np.abs(secure) <= interval_width
    fused[secure_in] = np.clip(secure[secure_in], -interval_width, interval_width)
    fused[~secure_in] = np.clip(unsafe[~secure_in], -interval_width, interval_width)
  # Hard clamp (safety guard, idempotent)
  fused = np.clip(fused, -interval_width, interval_width)
  var_proxy = np.var(fused, ddof=1) * np.ones_like(fused)
  return fused, var_proxy

__all__ = ["fuse_pair", "rule_based_fusion"]