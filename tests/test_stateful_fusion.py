import numpy as np
from src.fusion import (
    RuleFusionState,
    rule_based_fusion_step,
)


def _init_state(n: int):
    return RuleFusionState(fused=np.zeros(n), mode=np.zeros(n, dtype=int), blend_left=np.zeros(n, dtype=int))


def test_rule_based_blend_monotonic_and_bounded():
    """Verify that blending transitions do not overshoot and remain within interval bounds.

    Scenario: unsafe becomes available and within bounds after outage midpoint phase.
    """
    n = 200
    rng = np.random.default_rng(42)
    # Secure path small noise around 0
    secure = rng.normal(0, 0.05, size=n)
    # Unsafe target larger magnitude but within final bounds
    unsafe_base = rng.normal(0.08, 0.02, size=n)
    lower = -np.full(n, 0.20)
    upper = np.full(n, 0.20)
    state = _init_state(n)
    blend_steps = 6
    # Step 0: outage -> midpoint (0)
    outage = np.ones(n, dtype=bool)
    fused_prev = state.fused.copy()
    fused, state, meta = rule_based_fusion_step(secure, unsafe_base, lower, upper, outage, state, blend_steps=blend_steps)
    assert meta['n_midpoint'] == n, "All samples expected in midpoint during outage"
    # Steps 1..blend_steps: outage cleared, unsafe within bounds -> blend
    outage = np.zeros(n, dtype=bool)
    last = fused
    for step in range(blend_steps):
        fused, state, meta = rule_based_fusion_step(secure, unsafe_base, lower, upper, outage, state, blend_steps=blend_steps)
        # No value should exceed bounds
        assert np.all(fused <= upper + 1e-12) and np.all(fused >= lower - 1e-12), "Clamping invariant violated"
        # Monotonic movement toward unsafe target (approx) for majority
        progress = fused - last
        # allow some negative due to secure noise but majority should move towards +0.08 mean
        assert np.mean(progress) >= -0.005, "Unexpected negative mean progress during blend"
        last = fused
    # Final fused close to unsafe target
    assert np.allclose(fused.mean(), unsafe_base.mean(), atol=0.02)


def test_rule_based_clamping_for_out_of_bounds_unsafe():
    """If unsafe outside interval, fused should clamp secure path not raw unsafe."""
    n = 300
    rng = np.random.default_rng(123)
    secure = rng.normal(0, 0.04, size=n)
    unsafe = rng.normal(0.5, 0.05, size=n)  # clearly outside upper bound 0.2
    lower = -np.full(n, 0.2)
    upper = np.full(n, 0.2)
    state = _init_state(n)
    outage = np.zeros(n, dtype=bool)
    fused, state, meta = rule_based_fusion_step(secure, unsafe, lower, upper, outage, state, blend_steps=3)
    # All should be unsafe_clamped mode
    assert meta['n_unsafe_clamped'] == n, f"Expected all clamped, got {meta}"
    assert np.max(fused) <= 0.2 + 1e-12


def test_asymmetry_midpoint_shift():
    """Artificial asymmetric interval (upper=2*|lower|) should shift midpoint positive."""
    n = 100
    secure = np.zeros(n)
    unsafe = np.zeros(n)
    lower = -np.full(n, 0.10)
    upper = np.full(n, 0.20)
    state = _init_state(n)
    outage = np.ones(n, dtype=bool)  # force midpoint usage
    fused, state, meta = rule_based_fusion_step(secure, unsafe, lower, upper, outage, state, blend_steps=1)
    # Midpoint should be +0.05
    assert np.allclose(fused, 0.05)


def test_switch_rate_counts_changes():
    """Ensure mode switch count increments when outage pattern changes."""
    n = 150
    secure = np.zeros(n)
    unsafe = np.zeros(n)
    lower = -np.full(n, 0.15)
    upper = np.full(n, 0.15)
    state = _init_state(n)
    # Start outage
    outage = np.ones(n, dtype=bool)
    fused, state, meta0 = rule_based_fusion_step(secure, unsafe, lower, upper, outage, state, blend_steps=2)
    # Clear outage -> switch to unsafe (within bounds)
    outage = np.zeros(n, dtype=bool)
    fused, state, meta1 = rule_based_fusion_step(secure, unsafe, lower, upper, outage, state, blend_steps=2)
    assert meta1['n_switch'] > 0, "Expected positive switch count"