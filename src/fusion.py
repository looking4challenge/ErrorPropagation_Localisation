"""Fusion strategies & adaptive secure interval utilities.

Contains:
* Inverse-variance weighting (legacy surrogate)
* Static epoch rule-based fusion (backwards compatibility)
* Stateful rule-based fusion for time series (adaptive intervals, smoothing)
* Adaptive (potentially asymmetrische) Intervallgrenzen Berechnung

Design Notes (2025-10-09):
---------------------------------
The *secure interval* defines safety bounds [lower_i, upper_i] per sample i.
Initial implementation keeps symmetry (lower=-upper) but code pathway allows
future asymmetry (different lower/upper) driven by speed-dependent error
topologies. Midpoint is defined as 0.5*(lower+upper) (not necessarily 0 if
asymmetry emerges). The *unsafe path* (GNSS+IMU surrogate) is used if:
  (a) available (no outage) AND (b) raw unsafe error lies within bounds.
Otherwise the fusion falls back to either clamped secure path (if available
but outside) or midpoint (if outage) while always enforcing clamping.

Smoothing: Mode transitions are linearly blended over `blend_steps` to avoid
abrupt jumps (C: decision). Exponential smoothing variant is intentionally not
activated (documented in decisions.log).
"""
from __future__ import annotations

import numpy as np
from typing import Tuple, Dict, Any
from dataclasses import dataclass

import math


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


# --- Adaptive / Stateful Fusion Extensions ----------------------------------------------------

@dataclass
class RuleFusionState:
  """Holds per-sample state for time-series rule-based fusion.

  Attributes
  ----------
  fused : np.ndarray
    Last fused value per sample.
  mode : np.ndarray[int]
    Encoded mode (0=midpoint, 1=unsafe, 2=unsafe_clamped).
  blend_left : np.ndarray[int]
    Remaining blend steps (0 => no active blend) for samples undergoing transition.
  """
  fused: np.ndarray
  mode: np.ndarray
  blend_left: np.ndarray


MODE_MIDPOINT = 0
MODE_UNSAFE = 1
MODE_UNSAFE_CLAMPED = 2
MODE_NAMES = {
  MODE_MIDPOINT: "midpoint",
  MODE_UNSAFE: "unsafe",
  MODE_UNSAFE_CLAMPED: "unsafe_clamped",
}


def compute_secure_interval_bounds(
  secure: np.ndarray,
  speeds: np.ndarray,
  method: str = "adaptive",
  quantile_low_pct: float = 1.0,
  quantile_high_pct: float = 99.0,
  speed_bin_width: float = 5.0,
  min_bin_fraction: float = 0.05,
  rng: np.random.Generator | None = None,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
  """Compute (lower, upper) bounds per sample for secure interval.

  Current implementation:
    * method='adaptive': speed-binned expanding snapshot quantiles.
    * Fallback (if unstable): global symmetric absolute quantile (high_pct) => lower=-q, upper=+q.

  Returns
  -------
  lower, upper : np.ndarray
    Bounds arrays (same shape as secure).
  meta : dict
    Diagnostic meta info: {"used_bins", "fallback", "global_q"}.
  """
  n = secure.shape[0]
  if method != "adaptive":
    q = float(np.percentile(np.abs(secure), quantile_high_pct))
    return -np.full(n, q), np.full(n, q), {"fallback": True, "global_q": q, "used_bins": 0, "n_bins": 0, "fallback_escalated": False}

  # Speed bins
  vmax = max(1e-9, float(np.max(speeds)))
  n_bins = max(1, int(math.ceil(vmax / speed_bin_width)))
  edges = np.linspace(0.0, n_bins * speed_bin_width, n_bins + 1)
  inds = np.clip(np.digitize(speeds, edges) - 1, 0, n_bins - 1)

  # Global fallback prepared (also initialises arrays to safe values for empty bins)
  q_global = float(np.percentile(np.abs(secure), quantile_high_pct))
  lower = -np.full(n, q_global)
  upper = np.full(n, q_global)
  lower_global = -q_global
  upper_global = q_global

  fallback = False
  used_bins = 0
  min_bin_size = int(math.ceil(min_bin_fraction * n))

  for b in range(n_bins):
    mask = inds == b
    if not np.any(mask):  # already global fallback values set
      continue
    if mask.sum() < min_bin_size:
      # keep global fallback for this bin
      fallback = True
      continue
    seg = secure[mask]
    q_low = float(np.percentile(seg, quantile_low_pct))
    q_high = float(np.percentile(seg, quantile_high_pct))
    if q_low > q_high:  # numeric safeguard
      q_low, q_high = -abs(q_high), abs(q_high)
    lower[mask] = q_low
    upper[mask] = q_high
    used_bins += 1

  # Escalate to full global fallback if too many bins unstable (>20% fallback bins)
  fallback_bins = n_bins - used_bins
  fallback_escalated = False
  if n_bins > 0 and (fallback_bins / n_bins) > 0.20:
    lower[:] = lower_global
    upper[:] = upper_global
    fallback = True
    fallback_escalated = True

  meta = {
    "fallback": fallback,
    "global_q": q_global,
    "used_bins": used_bins,
    "n_bins": n_bins,
    "fallback_escalated": fallback_escalated,
    "fallback_bins": fallback_bins,
  }
  return lower, upper, meta


def rule_based_fusion_step(
  secure: np.ndarray,
  unsafe: np.ndarray,
  lower: np.ndarray,
  upper: np.ndarray,
  outage: np.ndarray,
  state: RuleFusionState,
  blend_steps: int = 5,
  outage_fallback: str = "midpoint",
) -> Tuple[np.ndarray, RuleFusionState, Dict[str, Any]]:
  """One time-step update for rule-based fusion (stateful).

  Parameters
  ----------
  secure, unsafe : arrays (n,)
  lower, upper : arrays (n,) interval bounds (may be asymmetric)
  outage : bool array (n,) True where unsafe path unavailable
  state : RuleFusionState
  blend_steps : int >=1 number of steps for linear smoothing of transitions

  Returns
  -------
  fused : np.ndarray
  new_state : RuleFusionState
  meta : dict with counts per mode & switches
  """
  n = secure.shape[0]
  assert unsafe.shape[0] == n
  fused_prev = state.fused
  mode_prev = state.mode
  blend_left = state.blend_left

  # Determine target modes
  unsafe_in_bounds = (~outage) & (unsafe >= lower) & (unsafe <= upper)
  # Mode selection
  mode = np.empty(n, dtype=int)
  # Unsafe accepted
  mode[unsafe_in_bounds] = MODE_UNSAFE
  # Outage handling selectable
  if outage_fallback == "secure":
    # treat outage samples like unsafe_clamped (secure path but possibly clamped)
    mode[outage] = MODE_UNSAFE_CLAMPED
  else:  # default midpoint
    mode[outage] = MODE_MIDPOINT
  # Remaining (available but out-of-bounds) -> unsafe_clamped (secure clamped)
  mask_remaining = ~(unsafe_in_bounds | outage)
  mode[mask_remaining] = MODE_UNSAFE_CLAMPED

  # Midpoint values
  midpoint = 0.5 * (lower + upper)
  target = np.empty(n)
  target[mode == MODE_UNSAFE] = np.clip(unsafe[mode == MODE_UNSAFE], lower[mode == MODE_UNSAFE], upper[mode == MODE_UNSAFE])
  # Clamp secure path for UNSAFE_CLAMPED
  target[mode == MODE_UNSAFE_CLAMPED] = np.clip(secure[mode == MODE_UNSAFE_CLAMPED], lower[mode == MODE_UNSAFE_CLAMPED], upper[mode == MODE_UNSAFE_CLAMPED])
  # Midpoint
  target[mode == MODE_MIDPOINT] = midpoint[mode == MODE_MIDPOINT]

  # Transition detection
  changed = mode != mode_prev
  # Initialise blend counters for changed samples
  newly_changed = changed & (blend_steps > 1)
  blend_left[newly_changed] = blend_steps

  fused = np.empty(n)
  if blend_steps <= 1:
    fused = target
    blend_left[:] = 0
  else:
    # Linear interpolate for samples still blending
    active = blend_left > 0
    # For active, compute alpha from remaining steps
    # When blend_left==blend_steps -> alpha=0 (start), when reaches 1 -> alpha≈(blend_steps-1)/blend_steps
    alpha = 1.0 - (blend_left[active] - 1) / blend_steps
    fused[active] = (1 - alpha) * fused_prev[active] + alpha * target[active]
    # Non-active simply target
    fused[~active] = target[~active]
    # Decrement counters (but not below 0)
    blend_left[active] -= 1
    blend_left[blend_left < 0] = 0

  # Safety clamp
  np.clip(fused, lower, upper, out=fused)

  # Stats
  meta = {
    "n_midpoint": int(np.sum(mode == MODE_MIDPOINT)),
    "n_unsafe": int(np.sum(mode == MODE_UNSAFE)),
    "n_unsafe_clamped": int(np.sum(mode == MODE_UNSAFE_CLAMPED)),
    "n_switch": int(np.sum(changed)),
  }

  new_state = RuleFusionState(fused=fused, mode=mode, blend_left=blend_left)
  return fused, new_state, meta


__all__ = [
  "fuse_pair",
  "rule_based_fusion",
  "RuleFusionState",
  "rule_based_fusion_step",
  "compute_secure_interval_bounds",
]