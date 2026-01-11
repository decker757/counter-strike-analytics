"""Configuration loader for YAML config files."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# Config directory relative to project root
# __file__ = src/utils/config.py -> parent.parent.parent = project root
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


@lru_cache(maxsize=32)
def _load_yaml(path: Path) -> dict[str, Any]:
    """Load and cache a YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def get_config(name: str) -> dict[str, Any]:
    """Load a config file by name (without .yaml extension)."""
    path = CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    return _load_yaml(path)


def get_map_config(map_name: str) -> dict[str, Any]:
    """Load map-specific configuration (boundaries, bombsites, zones)."""
    path = CONFIG_DIR / "maps" / f"{map_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Map config not found: {path}")
    return _load_yaml(path)


def get_economy_config() -> dict[str, Any]:
    """Load economy configuration (thresholds, buy types)."""
    return get_config("economy")


def get_weapons_config() -> dict[str, Any]:
    """Load weapons configuration (categories, prices)."""
    return get_config("weapons")


def clear_config_cache() -> None:
    """Clear the config cache (useful for testing or hot-reloading)."""
    _load_yaml.cache_clear()
