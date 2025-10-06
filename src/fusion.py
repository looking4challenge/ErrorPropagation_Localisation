"""Fusion proxy (variance inverse weighting as per report)."""
from __future__ import annotations

import numpy as np


def fuse_pair(x_a: np.ndarray, var_a: np.ndarray, x_b: np.ndarray, var_b: np.ndarray):
    # Avoid divide by zero
    var_a = np.clip(var_a, 1e-12, None)
    var_b = np.clip(var_b, 1e-12, None)
    w_a = var_b / (var_a + var_b)
    w_b = var_a / (var_a + var_b)
    x_f = w_a * x_a + w_b * x_b
    var_f = (var_a * var_b) / (var_a + var_b)
    return x_f, var_f


__all__ = ["fuse_pair"]