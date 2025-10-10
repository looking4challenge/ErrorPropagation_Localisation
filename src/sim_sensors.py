"""Sensor simulation stubs.

Implements simplified longitudinal error propagation for initial Monte Carlo.
Will be extended with time-dynamic behaviour later.
"""
from __future__ import annotations

from typing import Dict, Any, Tuple
import numpy as np

from .config import Config
from .distributions import registry, sample_mixture


def simulate_balise_errors(cfg: Config, n: int, rng: np.random.Generator) -> np.ndarray:
    bal = cfg.sensors["balise"]
    latency = registry.sample(bal["latency_ms"], n, rng) / 1000.0  # s
    antenna = registry.sample(bal["antenna_offset_m"], n, rng)
    em = registry.sample(bal["em_disturbance_m"], n, rng)
    base_tail = registry.sample(bal["multipath_tail_m"], n, rng)
    multipath = base_tail  # already truncated exp; mixture weight applied below
    weather = registry.sample(bal["weather_uniform_m"], n, rng)
    # Vehicle speed placeholder: assume uniform 0..16.7 m/s (60 km/h)
    v = rng.uniform(0, 16.7, size=n)
    heavy = sample_mixture(np.zeros(n), multipath, bal["multipath_tail_m"]["weight"], rng)
    err_long = v * latency + antenna + em + heavy + weather
    # Early detection model: d_const - v * delta_t  (delta_t limited by cap)
    ed_cfg = bal.get("early_detection", {})
    if ed_cfg.get("enabled", False):
        c1 = float(ed_cfg.get("c1_ms_per_mps", 0.0)) / 1000.0  # convert ms/(m/s) -> s/(m/s) = s^2/m
        cap_ms = float(ed_cfg.get("cap_ms", 0.0))
        cap_s = cap_ms / 1000.0
        d_const = float(ed_cfg.get("d_const_m", 0.0))  # constant early trigger advance in meters
        # Effective time advance per sample (s) limited by cap
        dt_adv = np.minimum(c1 * v, cap_s)
        early_term = d_const - v * dt_adv
        err_long += early_term
    return err_long


def simulate_balise_errors_2d(cfg: Config, n: int, rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray]:
    """Return longitudinal and lateral balise errors separately.

    Lateral distribution added in config (normal). Independence between axes assumed
    (first-order; cross-axis correlation negligible at cm-level for SIL1 context).
    """
    long = simulate_balise_errors(cfg, n, rng)
    lat_spec = cfg.sensors["balise"].get("lateral")
    if lat_spec is None:
        lat = np.zeros(n)
    else:
        lat = registry.sample(lat_spec, n, rng)
    return long, lat


def simulate_gnss_bias_noise(cfg: Config, n: int, rng: np.random.Generator, mode: str) -> np.ndarray:
    gnss_mode = cfg.sensors["gnss"]["modes"][mode]
    # Tunnel-Modus kann vollständigen Ausfall haben -> fallback Nullfehler (Hold-Last wird upstream modelliert)
    if "bias" in gnss_mode and "noise" in gnss_mode:
        bias = registry.sample(gnss_mode["bias"], n, rng)
        noise = registry.sample(gnss_mode["noise"], n, rng)
    else:
        bias = np.zeros(n)
        noise = np.zeros(n)
    tail = 0.0
    if "multipath_tail" in gnss_mode:
        tail_spec = gnss_mode["multipath_tail"]
        tail_vals = registry.sample(tail_spec, n, rng)
        tail = sample_mixture(np.zeros(n), tail_vals, tail_spec["weight"], rng)
    samples = bias + noise + tail
    # Apply outage probability (Bernoulli) if specified. Outage -> GNSS unavailable -> set contribution to 0.
    # (IMU dead-reckoning bridging is modelled separately; here we simply drop GNSS error when unavailable.)
    outage_p = float(gnss_mode.get("outage_prob", 0.0))
    if outage_p > 0.0:
        available_mask = rng.random(n) >= outage_p  # True where GNSS available
        samples = samples * available_mask  # zero where outage
    return samples


def simulate_gnss_bias_noise_2d(cfg: Config, n: int, rng: np.random.Generator, mode: str) -> Tuple[np.ndarray, np.ndarray]:
    """Return longitudinal & lateral GNSS error using dedicated lateral specs if present.

    Assumes independence between axes conditional on mode (first-order; cross-correlation typically small for metre-level biases).
    """
    gnss_mode = cfg.sensors["gnss"]["modes"][mode]
    long = simulate_gnss_bias_noise(cfg, n, rng, mode)
    bias_lat_spec = gnss_mode.get("bias_lat", gnss_mode.get("bias"))
    noise_lat_spec = gnss_mode.get("noise_lat", gnss_mode.get("noise"))
    if bias_lat_spec and noise_lat_spec:
        bias_lat = registry.sample(bias_lat_spec, n, rng)
        noise_lat = registry.sample(noise_lat_spec, n, rng)
    else:
        bias_lat = np.zeros(n)
        noise_lat = np.zeros(n)
    tail_lat = 0.0  # Lateral multipath tail not yet parameterised
    lat_samples = bias_lat + noise_lat + tail_lat
    # Re-apply same outage mask logic to lateral axis to keep consistency.
    outage_p = float(gnss_mode.get("outage_prob", 0.0))
    if outage_p > 0.0:
        available_mask = rng.random(n) >= outage_p
        long = long * available_mask
        lat_samples = lat_samples * available_mask
    return long, lat_samples


def simulate_map_error(cfg: Config, n: int, rng: np.random.Generator) -> np.ndarray:
    m = cfg.sensors["map"]
    long_ref = registry.sample(m["longitudinal"]["ref_error"], n, rng)
    interp_spec = m["longitudinal"]["interpolation"]
    interp_vals = registry.sample(interp_spec, n, rng)
    interp_mix = sample_mixture(np.zeros(n), interp_vals, interp_spec["weight"], rng)
    return long_ref + interp_mix


def simulate_map_error_2d(cfg: Config, n: int, rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray]:
    """Return longitudinal, lateral map errors (independent distributions)."""
    long = simulate_map_error(cfg, n, rng)
    lat_spec = cfg.sensors["map"].get("lateral", {}).get("ref_error")
    if lat_spec:
        lat = registry.sample(lat_spec, n, rng)
    else:
        lat = np.zeros(n)
    return long, lat


def simulate_odometry_segment_error(cfg: Config, n: int, rng: np.random.Generator, segment_m: float = 500.0) -> np.ndarray:
    o = cfg.sensors["odometry"]
    quant_step = o["quant_step_m"]
    # Rough quantization variance: sum of uniform errors; approximate by single uniform scaled
    increments = int(max(1, segment_m / quant_step))
    quant = rng.uniform(-quant_step/2, quant_step/2, size=(n, increments)).sum(axis=1)
    residual = registry.sample(o["residual_circumference_m"], n, rng)
    drift_sigma = o["drift_per_km_m"] * (segment_m / 1000.0)
    drift = rng.normal(0.0, drift_sigma, size=n)
    return quant + residual + drift


def simulate_imu_bias_position_error(cfg: Config, n: int, rng: np.random.Generator, duration_s: float = 10.0) -> np.ndarray:
    imu = cfg.sensors["imu"]
    accel_bias = registry.sample(imu["accel_bias_mps2"], n, rng)
    # Reparametrisiertes (reduziertes) Modell:
    # Ursprünglich: 0.5 * b * t^2 erzeugt unrealistisch große Drift (Quadratwachstum),
    # obwohl im realen EKF der Bias regelmäßig (Stillstand / ZUPT / Filter) kompensiert wird.
    # Neues vereinfachtes Surrogat: linear skalierter Residualpositionsfehler nach partieller Kompensation.
    # position_bias_factor (konfigurierbar) bestimmt effektive Projektion des Bias in die Positionsdomäne.
    # -> error ≈ factor * b * t   (kein t^2).
    factor = float(imu.get("position_bias_factor", 0.001))
    return factor * accel_bias * duration_s


def combine_2d(long: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Return 2D radial error magnitude sqrt(long^2 + lat^2)."""
    return np.sqrt(long**2 + lat**2)


__all__ = [
    "simulate_balise_errors",
    "simulate_balise_errors_2d",
    "simulate_gnss_bias_noise",
    "simulate_gnss_bias_noise_2d",
    "simulate_map_error",
    "simulate_map_error_2d",
    "simulate_odometry_segment_error",
    "simulate_imu_bias_position_error",
    "combine_2d",
]