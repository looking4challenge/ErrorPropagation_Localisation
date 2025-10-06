"""Time-series Monte Carlo simulation for longitudinal (and basic lateral placeholder) localisation errors.

Implements user-selected options:
1:A dt=cfg.sim.dt_s
2:D Balisen-Abstand: vorerst vereinfachte konstante mittlere Distanz 400 m (TODO: echte Verteilungsanpassung an min=10,max=1200,mean=400)
3:A GNSS Outage: unabhängige Bernoulli je Zeitschritt
4:A Odometrie Drift: additiver Random Walk (σ_step ∝ sqrt(Δs_km))
5:A IMU Bias: konstant über gesamten Horizont → pos-Fehler ~ 0.5*b*t^2
6:A Lateral: einfache σ-Werte für Map/Balise/GNSS (noch nicht voll integriert in Fusion; placeholder)
7:A Volle N_samples aus Config (Achtung Performance); streaming Approach speichert nur Zeit-Metriken
8:A Zeitreihen-Metriken: RMSE(t), P95(t), Var_secure(t), Var_unsafe(t), share_out_of_spec(t)

Memory Strategy: O(N) arrays für aktuellen Schritt; O(T) für Metrik-Zeitreihen.
Potential Optimisation: Chunked processing falls zukünftige Erweiterungen mehr States benötigen.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import numpy as np

from .config import Config
from .sim_sensors import (
    simulate_balise_errors,
    simulate_map_error,
)
from .distributions import registry
from .fusion import fuse_pair


@dataclass
class TimeSeriesResult:
    times: np.ndarray
    rmse: np.ndarray
    p95: np.ndarray
    var_secure: np.ndarray
    var_unsafe: np.ndarray
    share_oos: np.ndarray


def _prepare_static_components(cfg: Config, n: int, rng: np.random.Generator):
    """Sample static per-sample components (map error, gnss bias, imu bias)."""
    # Map longitudinal reference error (per sample constant offset)
    map_err = simulate_map_error(cfg, n, rng)
    # GNSS bias per sample
    gnss_bias = registry.sample(cfg.sensors["gnss"]["modes"]["open"]["bias"], n, rng)
    # IMU accel bias per sample (constant)
    imu_bias = registry.sample(cfg.sensors["imu"]["accel_bias_mps2"], n, rng)
    return map_err, gnss_bias, imu_bias


def simulate_time_series(cfg: Config, rng: np.random.Generator, threshold_oos: float = 0.2) -> TimeSeriesResult:
    sim = cfg.sim
    dt = float(sim.get("dt_s", 0.1))
    horizon = float(sim.get("time_horizon_s", 3600.0))
    n_steps = int(horizon / dt)
    n = int(sim.get("N_samples", 1000))

    # Speeds (konstant je Sample) Uniform 0..60 km/h (0..16.7 m/s)
    speeds = rng.uniform(0.0, 16.7, size=n)

    map_err, gnss_bias, imu_bias = _prepare_static_components(cfg, n, rng)

    # GNSS noise spec & outage prob (open mode user selected for baseline)
    gnss_mode = cfg.sensors["gnss"]["modes"]["open"]
    gnss_noise_spec = gnss_mode["noise"]
    p_out = float(gnss_mode.get("outage_prob", 0.0))

    # Odometry parameters
    drift_per_km = float(cfg.sensors["odometry"]["drift_per_km_m"])  # σ per km

    # Balise parameters (simplified constant spacing = 400 m; TODO advanced distribution) Option 2:D simplified
    balise_spacing = 400.0
    next_balise_dist = np.full(n, balise_spacing)
    dist_since_balise = np.zeros(n)
    last_balise_error = np.zeros(n)

    # GNSS state (hold-last-valid if outage)
    gnss_current = gnss_bias + registry.sample(gnss_noise_spec, n, rng)

    # IMU position error accumulative expression uses t^2 scaling; compute on the fly

    # Odometry drift state since last balise reset
    odo_drift = np.zeros(n)

    # Metrics arrays (time series)
    rmse_t = np.zeros(n_steps)
    p95_t = np.zeros(n_steps)
    var_secure_t = np.zeros(n_steps)
    var_unsafe_t = np.zeros(n_steps)
    share_oos_t = np.zeros(n_steps)

    # Pre-allocate arrays reused each step
    secure = np.zeros(n)
    unsafe = np.zeros(n)

    # Loop
    for k in range(n_steps):
        t = (k + 1) * dt  # time at end of step
        # Distance increment
        ds = speeds * dt
        dist_since_balise += ds

        # Odometry drift increment (σ_step = drift_per_km * sqrt(ds_km))
        sigma_step = drift_per_km * np.sqrt(ds / 1000.0)
        odo_drift += rng.normal(0.0, sigma_step)

        # Balise event?
        event_mask = dist_since_balise >= next_balise_dist
        if np.any(event_mask):
            # Sample new balise measurement error for events
            # Re-use simulate_balise_errors but only for subset → sample larger and pick slice for simplicity
            m_cnt = int(event_mask.sum())
            bal_subset = simulate_balise_errors(cfg, m_cnt, rng)
            last_balise_error[event_mask] = bal_subset
            # Reset odometry drift at balise (anchoring)
            odo_drift[event_mask] = 0.0
            # Reset distance and schedule next
            dist_since_balise[event_mask] = 0.0
            next_balise_dist[event_mask] = balise_spacing  # TODO advanced variable spacing

        # Secure path error = balise anchor + map error + odometry drift
        secure = last_balise_error + map_err + odo_drift

        # GNSS update (outage Bernoulli)
        outage = rng.random(n) < p_out
        if np.any(~outage):
            gnss_current[~outage] = gnss_bias[~outage] + registry.sample(gnss_noise_spec, (~outage).sum(), rng)
        # IMU position error (0.5 * b * t^2)
        imu_pos_err = 0.5 * imu_bias * (t ** 2)

        unsafe = gnss_current + imu_pos_err

        # Fusion (variance inverse weighting)
        var_sec = np.var(secure, ddof=1)
        var_uns = np.var(unsafe, ddof=1)
        fused, _ = fuse_pair(secure, np.full(n, var_sec), unsafe, np.full(n, var_uns))

        # Metrics
        rmse_t[k] = np.sqrt(np.mean(fused ** 2))
        p95_t[k] = np.percentile(fused, 95)
        var_secure_t[k] = var_sec
        var_unsafe_t[k] = var_uns
        share_oos_t[k] = np.mean(np.abs(fused) > threshold_oos)

    times = dt * (np.arange(n_steps) + 1)
    return TimeSeriesResult(times=times, rmse=rmse_t, p95=p95_t, var_secure=var_secure_t, var_unsafe=var_unsafe_t, share_oos=share_oos_t)


__all__ = ["simulate_time_series", "TimeSeriesResult"]
