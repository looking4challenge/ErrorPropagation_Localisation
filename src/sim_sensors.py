"""Sensor simulation stubs.

Implements simplified longitudinal error propagation for initial Monte Carlo.
Will be extended with time-dynamic behaviour later.
"""
from __future__ import annotations

from typing import Dict, Any
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
    return err_long


def simulate_gnss_bias_noise(cfg: Config, n: int, rng: np.random.Generator, mode: str) -> np.ndarray:
    gnss_mode = cfg.sensors["gnss"]["modes"][mode]
    bias = registry.sample(gnss_mode["bias"], n, rng)
    noise = registry.sample(gnss_mode["noise"], n, rng)
    tail = 0.0
    if "multipath_tail" in gnss_mode:
        tail_spec = gnss_mode["multipath_tail"]
        tail_vals = registry.sample(tail_spec, n, rng)
        tail = sample_mixture(np.zeros(n), tail_vals, tail_spec["weight"], rng)
    return bias + noise + tail


def simulate_map_error(cfg: Config, n: int, rng: np.random.Generator) -> np.ndarray:
    m = cfg.sensors["map"]
    long_ref = registry.sample(m["longitudinal"]["ref_error"], n, rng)
    interp_spec = m["longitudinal"]["interpolation"]
    interp_vals = registry.sample(interp_spec, n, rng)
    interp_mix = sample_mixture(np.zeros(n), interp_vals, interp_spec["weight"], rng)
    return long_ref + interp_mix


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
    # Simple double integration error: 0.5 * b * t^2
    return 0.5 * accel_bias * duration_s ** 2


__all__ = [
    "simulate_balise_errors",
    "simulate_gnss_bias_noise",
    "simulate_map_error",
    "simulate_odometry_segment_error",
    "simulate_imu_bias_position_error",
]