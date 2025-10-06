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
    rmse: np.ndarray              # longitudinal fused RMSE
    p95: np.ndarray               # longitudinal fused P95
    var_secure: np.ndarray        # longitudinal secure variance
    var_unsafe: np.ndarray        # longitudinal unsafe variance
    share_oos: np.ndarray         # longitudinal out-of-spec share
    rmse_lat: np.ndarray | None = None  # lateral fused RMSE
    p95_lat: np.ndarray | None = None   # lateral fused P95
    rmse_2d: np.ndarray | None = None   # radial fused RMSE
    p95_2d: np.ndarray | None = None    # radial fused P95


def _prepare_static_components(cfg: Config, n: int, rng: np.random.Generator):
    """Sample static per-sample components including lateral parts.

    Assumptions:
    - GNSS lateral bias distribution ~ longitudinal bias distribution (symmetry, first-order).
    - IMU lateral contribution vernachlässigt (Querfehler dominiert durch Map/Balise/GNSS) → documented in decisions.log.
    """
    map_err_long = simulate_map_error(cfg, n, rng)
    map_lat_spec = cfg.sensors["map"].get("lateral", {}).get("ref_error")
    map_err_lat = registry.sample(map_lat_spec, n, rng) if map_lat_spec else np.zeros(n)
    gnss_bias_long = registry.sample(cfg.sensors["gnss"]["modes"]["open"]["bias"], n, rng)
    # Prefer dedicated lateral bias if present
    gnss_mode_open = cfg.sensors["gnss"]["modes"]["open"]
    gnss_bias_lat_spec = gnss_mode_open.get("bias_lat", gnss_mode_open["bias"])
    gnss_bias_lat = registry.sample(gnss_bias_lat_spec, n, rng)
    imu_bias = registry.sample(cfg.sensors["imu"]["accel_bias_mps2"], n, rng)
    return map_err_long, map_err_lat, gnss_bias_long, gnss_bias_lat, imu_bias


def simulate_time_series(cfg: Config, rng: np.random.Generator, threshold_oos: float = 0.2, with_lateral: bool = True) -> TimeSeriesResult:
    sim = cfg.sim
    dt = float(sim.get("dt_s", 0.1))
    horizon = float(sim.get("time_horizon_s", 3600.0))
    n_steps = int(horizon / dt)
    n = int(sim.get("N_samples", 1000))

    # Speeds (konstant je Sample) Uniform 0..60 km/h (0..16.7 m/s)
    speeds = rng.uniform(0.0, 16.7, size=n)

    map_err_long, map_err_lat, gnss_bias_long, gnss_bias_lat, imu_bias = _prepare_static_components(cfg, n, rng)

    # GNSS noise spec & outage prob (open mode user selected for baseline)
    gnss_mode = cfg.sensors["gnss"]["modes"]["open"]
    gnss_noise_spec = gnss_mode["noise"]
    gnss_noise_lat_spec = gnss_mode.get("noise_lat", gnss_mode["noise"])
    p_out = float(gnss_mode.get("outage_prob", 0.0))

    # Odometry parameters
    drift_per_km = float(cfg.sensors["odometry"]["drift_per_km_m"])  # σ per km

    # Balise parameters (simplified constant spacing = 400 m; TODO advanced distribution) Option 2:D simplified
    balise_spacing = 400.0
    next_balise_dist = np.full(n, balise_spacing)
    dist_since_balise = np.zeros(n)
    last_balise_error = np.zeros(n)

    # GNSS state (hold-last-valid if outage)
    gnss_current = gnss_bias_long + registry.sample(gnss_noise_spec, n, rng)
    gnss_current_lat = gnss_bias_lat + registry.sample(gnss_noise_lat_spec, n, rng) if with_lateral else None

    # IMU position error accumulative expression uses t^2 scaling; compute on the fly

    # Odometry drift state since last balise reset
    odo_drift = np.zeros(n)

    # Metrics arrays (time series)
    rmse_t = np.zeros(n_steps)
    p95_t = np.zeros(n_steps)
    var_secure_t = np.zeros(n_steps)
    var_unsafe_t = np.zeros(n_steps)
    share_oos_t = np.zeros(n_steps)
    rmse_lat_t = np.zeros(n_steps) if with_lateral else None
    p95_lat_t = np.zeros(n_steps) if with_lateral else None
    rmse_2d_t = np.zeros(n_steps) if with_lateral else None
    p95_2d_t = np.zeros(n_steps) if with_lateral else None

    # Pre-allocate arrays reused each step
    secure = np.zeros(n)
    unsafe = np.zeros(n)
    last_balise_lat_error = np.zeros(n) if with_lateral else None
    secure_lat = np.zeros(n) if with_lateral else None
    unsafe_lat = np.zeros(n) if with_lateral else None
    fused_lat = None

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
            # Use the dedicated 2D simulator for correctness
            from .sim_sensors import simulate_balise_errors_2d
            bal_long_vals, bal_lat_vals = simulate_balise_errors_2d(cfg, m_cnt, rng)
            last_balise_error[event_mask] = bal_long_vals
            if with_lateral and last_balise_lat_error is not None:
                last_balise_lat_error[event_mask] = bal_lat_vals
            # Reset odometry drift at balise (anchoring)
            odo_drift[event_mask] = 0.0
            # Reset distance and schedule next
            dist_since_balise[event_mask] = 0.0
            next_balise_dist[event_mask] = balise_spacing  # TODO advanced variable spacing

        # Secure path error = balise anchor + map error + odometry drift
        secure = last_balise_error + map_err_long + odo_drift
        if with_lateral and last_balise_lat_error is not None and secure_lat is not None:
            secure_lat = last_balise_lat_error + map_err_lat  # odometry lateral drift neglected

        # GNSS update (outage Bernoulli)
        outage = rng.random(n) < p_out
        if np.any(~outage):
            gnss_current[~outage] = gnss_bias_long[~outage] + registry.sample(gnss_noise_spec, (~outage).sum(), rng)
            if with_lateral and gnss_current_lat is not None:
                gnss_current_lat[~outage] = gnss_bias_lat[~outage] + registry.sample(gnss_noise_lat_spec, (~outage).sum(), rng)
        # IMU position error (0.5 * b * t^2)
        imu_pos_err = 0.5 * imu_bias * (t ** 2)

        unsafe = gnss_current + imu_pos_err
        if with_lateral and gnss_current_lat is not None and unsafe_lat is not None:
            unsafe_lat = gnss_current_lat  # lateral IMU bias neglected

        # Fusion (variance inverse weighting)
        var_sec = np.var(secure, ddof=1)
        var_uns = np.var(unsafe, ddof=1)
        fused, _ = fuse_pair(secure, np.full(n, var_sec), unsafe, np.full(n, var_uns))
        if with_lateral and last_balise_lat_error is not None and secure_lat is not None and unsafe_lat is not None:
            var_sec_lat = np.var(secure_lat, ddof=1)
            var_uns_lat = np.var(unsafe_lat, ddof=1)
            fused_lat, _ = fuse_pair(secure_lat, np.full(n, var_sec_lat), unsafe_lat, np.full(n, var_uns_lat))

        # Metrics
        rmse_t[k] = np.sqrt(np.mean(fused ** 2))
        p95_t[k] = np.percentile(fused, 95)
        if with_lateral and last_balise_lat_error is not None and fused_lat is not None:
            if rmse_lat_t is not None and p95_lat_t is not None:
                rmse_lat_t[k] = np.sqrt(np.mean(fused_lat ** 2))
                p95_lat_t[k] = np.percentile(fused_lat, 95)
            if rmse_2d_t is not None and p95_2d_t is not None:
                fused_2d = np.sqrt(fused**2 + fused_lat**2)
                rmse_2d_t[k] = np.sqrt(np.mean(fused_2d ** 2))
                p95_2d_t[k] = np.percentile(fused_2d, 95)
        var_secure_t[k] = var_sec
        var_unsafe_t[k] = var_uns
        share_oos_t[k] = np.mean(np.abs(fused) > threshold_oos)

    times = dt * (np.arange(n_steps) + 1)
    return TimeSeriesResult(
        times=times,
        rmse=rmse_t,
        p95=p95_t,
        var_secure=var_secure_t,
        var_unsafe=var_unsafe_t,
        share_oos=share_oos_t,
        rmse_lat=rmse_lat_t,
        p95_lat=p95_lat_t,
        rmse_2d=rmse_2d_t,
        p95_2d=p95_2d_t,
    )


__all__ = ["simulate_time_series", "TimeSeriesResult"]
