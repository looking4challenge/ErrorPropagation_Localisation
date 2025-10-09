import numpy as np
import copy
from src.config import load_config, get_seed, Config
from src.sim_sensors import (
    simulate_balise_errors,
    simulate_map_error,
    simulate_odometry_segment_error,
)
from src.time_sim import simulate_time_series


def _single_bias(cfg: Config, n: int, rng: np.random.Generator):
    bal = simulate_balise_errors(cfg, n, rng)
    map_err = simulate_map_error(cfg, n, rng)
    odo = simulate_odometry_segment_error(cfg, n, rng)
    secure = bal + map_err + odo
    p99_bal = np.percentile(np.abs(bal), 99)
    p99_map = np.percentile(np.abs(map_err), 99)
    p99_odo = np.percentile(np.abs(odo), 99)
    additive = p99_bal + p99_map + p99_odo
    joint = np.percentile(np.abs(secure), 99)
    return additive, joint


def test_secure_interval_additive_bias_positive_and_stable():
    """Additive P99 (sum of component P99) must be ≥ joint P99 and show consistent positive bias across replications.

    Uses multiple independent RNG seeds to reduce fluke risk. Ensures a minimum relative bias (>=2%).
    """
    cfg = load_config("config/model.yml")
    base_seed = get_seed(cfg) + 7700
    n = 4000  # trade-off runtime vs. tail stability (~40 samples in top 1%)
    biases = []
    rel_biases = []
    for i in range(3):  # 3 replications
        rng = np.random.default_rng(base_seed + i)
        additive, joint = _single_bias(cfg, n, rng)
        assert additive + 1e-12 >= joint, f"Replication {i}: additive < joint (unexpected conservative violation)"
        bias = additive - joint
        rel = bias / joint if joint > 0 else 0.0
        biases.append(bias)
        rel_biases.append(rel)
    mean_bias = float(np.mean(biases))
    mean_rel = float(np.mean(rel_biases))
    # Expect at least ~2% mean relative bias (empirically observed for current model); keep threshold lenient to avoid fragility
    assert mean_rel >= 0.02, f"Mean relative bias too low: {mean_rel:.4f} (<2%)"  # documents conservatism
    # Ensure all replications show >0.5 mm absolute bias
    assert all(b > 0.0005 for b in biases), f"Absolute bias below expectation in some replication: {biases}"


def test_secure_interval_growth_bias_timeseries_non_negative():
    """Time-series secure interval growth: additive bias percentage should remain non-negative and typically > 0.

    We run a shortened time horizon for speed.
    """
    cfg_full = load_config("config/model.yml")
    data_copy = copy.deepcopy(cfg_full.raw)
    # Shorten horizon & reduce N for test speed
    data_copy["sim"]["time_horizon_s"] = 20.0  # 20 s
    data_copy["sim"]["dt_s"] = 0.5
    data_copy["sim"]["N_samples"] = 2500  # tail resolution ~25 values for P99
    cfg = Config(raw=data_copy)
    rng = np.random.default_rng(get_seed(cfg_full) + 8800)
    ts_res = simulate_time_series(cfg, rng, threshold_oos=0.2, with_lateral=False)
    # Basic existence
    assert ts_res.si_bias_pct is not None and ts_res.si_bias_pct.size > 0, "No secure interval bias time-series produced"
    # Non-negative (allow tiny negative due to sampling jitter but within tolerance)
    min_bias = float(np.min(ts_res.si_bias_pct))
    assert min_bias > -0.5, f"Unexpected large negative bias {min_bias:.3f}% (should remain conservative)"
    # Typical bias > 0% (mean positive)
    mean_bias_pct = float(np.mean(ts_res.si_bias_pct))
    assert mean_bias_pct > 0.5, f"Mean bias percentage too low / non-positive: {mean_bias_pct:.3f}%"