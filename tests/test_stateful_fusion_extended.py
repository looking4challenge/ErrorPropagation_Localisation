import numpy as np
from src.fusion import RuleFusionState, rule_based_fusion_step


def _init(n):
    return RuleFusionState(fused=np.zeros(n), mode=np.zeros(n, dtype=int), blend_left=np.zeros(n, dtype=int))


def test_linear_blend_step_max_delta():
    """Ensure each blend step delta does not exceed theoretical maximum |target-start|/blend_steps.

    Construct scenario: outage -> midpoint (0), then unsafe target constant positive inside bounds.
    """
    n = 300
    rng = np.random.default_rng(10)
    secure = rng.normal(0.0, 0.01, size=n)
    unsafe = np.full(n, 0.12)
    lower = -np.full(n, 0.25)
    upper = np.full(n, 0.25)
    blend_steps = 8
    state = _init(n)
    # Step 0 outage so fused=midpoint=0
    outage = np.ones(n, dtype=bool)
    fused, state, _ = rule_based_fusion_step(secure, unsafe, lower, upper, outage, state, blend_steps=blend_steps)
    assert np.allclose(fused, 0.0, atol=1e-9)
    start = fused.copy()
    # Release outage -> blend to unsafe
    outage = np.zeros(n, dtype=bool)
    for s in range(blend_steps):
        prev = state.fused.copy()
        fused, state, _ = rule_based_fusion_step(secure, unsafe, lower, upper, outage, state, blend_steps=blend_steps)
        # Max theoretical increment per step (allow small numerical slack)
        max_allowed = (np.abs(unsafe - start) / blend_steps) + 1e-12
        delta = np.abs(fused - prev)
        assert np.all(delta <= max_allowed + 1e-9), f"Blend step {s}: delta exceeds bound (max {max_allowed.max():.4g})"
    # Final close to target
    assert np.allclose(fused.mean(), unsafe.mean(), atol=0.01)


def test_outlier_triggers_clamped_mode():
    """Inject single-sample outlier in unsafe -> expect that sample enters unsafe_clamped mode.

    We generate baseline inside-bounds unsafe then set one index >> upper.
    """
    n = 500
    secure = np.zeros(n)
    unsafe = np.zeros(n)
    lower = -np.full(n, 0.15)
    upper = np.full(n, 0.15)
    state = _init(n)
    outage = np.zeros(n, dtype=bool)
    # first step within bounds
    fused, state, meta = rule_based_fusion_step(secure, unsafe, lower, upper, outage, state, blend_steps=4)
    assert meta['n_unsafe'] == n, "All should be unsafe initially (within bounds)."
    # Inject outlier at index 10
    unsafe2 = unsafe.copy()
    unsafe2[10] = 0.5  # beyond upper
    fused2, state, meta2 = rule_based_fusion_step(secure, unsafe2, lower, upper, outage, state, blend_steps=2)
    # That index should now be in clamped mode; others remain unsafe (some blending allowed)
    # Count clamped (allow >1 if blending classification picks more due to equal values)
    assert meta2['n_unsafe_clamped'] >= 1, "Expected at least one unsafe_clamped sample after outlier injection"
    assert np.isclose(fused2[10], upper[10]) or np.isclose(fused2[10], lower[10]), "Outlier not clamped to interval bounds"


def test_outage_transition_blend_towards_midpoint():
    """Start with unsafe active then outage forces midpoint; blending should move towards midpoint without overshoot."""
    n = 400
    secure = np.zeros(n)
    unsafe = np.full(n, -0.18)  # inside bounds ([-0.3,0.3])
    lower = -np.full(n, 0.30)
    upper = np.full(n, 0.30)
    blend_steps = 5
    state = _init(n)
    # Initial step no outage -> adopt unsafe
    outage = np.zeros(n, dtype=bool)
    fused, state, meta0 = rule_based_fusion_step(secure, unsafe, lower, upper, outage, state, blend_steps=blend_steps)
    assert meta0['n_unsafe'] == n
    # Introduce outage -> target midpoint = 0, expect blended ascent towards 0
    outage = np.ones(n, dtype=bool)
    prev = fused.copy()
    for s in range(blend_steps):
        fused, state, meta = rule_based_fusion_step(secure, unsafe, lower, upper, outage, state, blend_steps=blend_steps)
        # Fused should move towards 0 (increase since starting negative) without overshoot above +midpoint
        assert np.mean(fused) >= np.mean(prev) - 1e-6, "Mean moved opposite direction (not towards midpoint)"
        assert np.all(fused <= upper + 1e-12) and np.all(fused >= lower - 1e-12)
        prev = fused
    # End near midpoint
    assert abs(fused.mean()) < 0.02, "Did not approach midpoint sufficiently"
