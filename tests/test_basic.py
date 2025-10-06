import numpy as np
from src.config import load_config, get_seed
from src.sim_sensors import simulate_balise_errors, simulate_gnss_bias_noise
from src.distributions import sample_correlated_gaussian, empirical_corr


def _extract_rho(cfg):
    corr = cfg.correlations
    return np.array(corr["rho_matrix"], dtype=float)


def test_seed_reproducibility():
    cfg = load_config("config/model.yml")
    seed = get_seed(cfg)
    rng1 = np.random.default_rng(seed)
    rng2 = np.random.default_rng(seed)
    a = simulate_balise_errors(cfg, 1000, rng1)
    b = simulate_balise_errors(cfg, 1000, rng2)
    assert np.allclose(a, b), "Simulation not reproducible for identical seeds"


def test_balise_error_scale():
    cfg = load_config("config/model.yml")
    rng = np.random.default_rng(get_seed(cfg))
    errs = simulate_balise_errors(cfg, 2000, rng)
    # Expect realistic scale < 1 m (rough heuristic)
    assert np.percentile(np.abs(errs), 99) < 1.0


def test_correlation_matrix_sampling():
    cfg = load_config("config/model.yml")
    rho = _extract_rho(cfg)
    rng = np.random.default_rng(get_seed(cfg))
    samples = sample_correlated_gaussian(rho, 20000, rng)
    emp = empirical_corr(samples)
    tol = cfg.sim.get("rho_tol", 0.05) + 0.02  # allow slight MC slack
    diff = np.abs(emp - rho)
    assert np.all(diff <= tol), f"Empirical correlations deviate > tol. max diff={diff.max():.3f}"


def test_gnss_noise_sensitivity():
    cfg = load_config("config/model.yml")
    seed = get_seed(cfg)
    rng = np.random.default_rng(seed)
    base = simulate_gnss_bias_noise(cfg, 5000, rng, mode="open")
    # Increase noise std artificially by +50% and expect RMSE increase
    orig_std = cfg.sensors["gnss"]["modes"]["open"]["noise"]["std"]
    cfg.sensors["gnss"]["modes"]["open"]["noise"]["std"] = orig_std * 1.5
    rng2 = np.random.default_rng(seed)  # same seed for comparability
    mod = simulate_gnss_bias_noise(cfg, 5000, rng2, mode="open")
    cfg.sensors["gnss"]["modes"]["open"]["noise"]["std"] = orig_std  # restore
    assert np.std(mod) > np.std(base), "GNSS noise increase did not raise std"