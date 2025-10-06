"""Configuration loading and validation utilities.

Loads the YAML model configuration and exposes a lightweight dict-based
object. Pydantic could be added later if stricter validation is needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
import yaml


@dataclass
class Config:
    raw: Dict[str, Any]

    @property
    def sim(self) -> Dict[str, Any]:
        return self.raw.get("sim", {})

    @property
    def sensors(self) -> Dict[str, Any]:
        return self.raw.get("sensors", {})

    @property
    def correlations(self) -> Dict[str, Any]:
        return self.raw.get("correlations", {})


def load_config(path: str | Path) -> Config:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # Minimal sanity checks
    required_top = ["project", "sim", "sensors"]
    for k in required_top:
        if k not in data:
            raise ValueError(f"Missing top-level section '{k}' in config {path}")
    return Config(raw=data)


def get_seed(cfg: Config) -> int:
    return int(cfg.sim.get("random_seed", 0))


__all__ = ["Config", "load_config", "get_seed"]