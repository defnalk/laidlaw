"""Loads and exposes the JSON knowledge base in /data.

All numerical assumptions live in JSON so the engine stays a pure
calculation kernel. To extend the model, edit the JSON files — no
code changes needed.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _load(name: str) -> Any:
    with open(DATA_DIR / name) as f:
        return json.load(f)


@lru_cache(maxsize=1)
def assumptions() -> dict:
    return _load("assumptions.json")


@lru_cache(maxsize=1)
def technologies() -> dict:
    return _load("technologies.json")


@lru_cache(maxsize=1)
def sites() -> list[dict]:
    return _load("sites.json")


@lru_cache(maxsize=1)
def sdg_mapping() -> dict:
    return _load("sdg_mapping.json")


def reload_all() -> None:
    """Clear caches — useful for hot-reloading data during workshops."""
    for fn in (assumptions, technologies, sites, sdg_mapping):
        fn.cache_clear()
