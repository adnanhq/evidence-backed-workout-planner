"""Cached accessors over the engine's catalog + science corpus.

``engine.load_catalog`` / ``load_science_corpus`` are themselves ``lru_cache``d,
so these wrappers just build cheap in-memory indices once."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from protocol_engine import protocol_demo as engine


@lru_cache(maxsize=1)
def catalog() -> dict[str, Any]:
    return engine.load_catalog()


@lru_cache(maxsize=1)
def science() -> dict[str, Any]:
    return engine.load_science_corpus()


@lru_cache(maxsize=1)
def exercises() -> list[dict[str, Any]]:
    return catalog().get("exercises", [])


@lru_cache(maxsize=1)
def exercises_by_id() -> dict[str, dict[str, Any]]:
    return {e.get("exercise_id"): e for e in exercises()}


@lru_cache(maxsize=1)
def docs_by_pmid() -> dict[str, dict[str, Any]]:
    return {str(d.get("pmid")): d for d in science().get("documents", [])}


@lru_cache(maxsize=1)
def taxonomies() -> dict[str, Any]:
    return catalog().get("taxonomies", {})


@lru_cache(maxsize=1)
def primary_muscle_groups() -> list[str]:
    """Taxonomy muscles that at least one exercise trains as a primary mover.

    The catalog taxonomy also lists muscles that only ever appear as secondary
    synergists (e.g. ``neck``); those would yield zero results under the
    primary-muscle filter, so they are excluded from filter options."""
    known = set(taxonomies().get("muscle_groups", []))
    with_primary = {
        m
        for e in exercises()
        for m in (e.get("muscles", {}) or {}).get("primary", [])
    }
    return sorted(known & with_primary)
