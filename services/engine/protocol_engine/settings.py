"""Centralized path + configuration resolution for the protocol engine.

Stdlib-only on purpose: this module is imported by the runtime engine, the
offline pipeline scripts, and the test suite, none of which should require
FastAPI / pydantic to be installed. Every data location derives from
``PROTOCOL_DATA_DIR`` (default: ``<repo_root>/packages/data/processed``) so the
engine behaves identically whether it is launched from the CLI, the FastAPI
service, or a container with the data mounted elsewhere.
"""
from __future__ import annotations

import os
from pathlib import Path

# This file lives at services/engine/protocol_engine/settings.py
#   parents[1] -> services/engine        (the engine service root)
#   parents[3] -> <repo_root>
ENGINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]


def _path_env(name: str, default: Path) -> Path:
    """Return an absolute Path from ``name`` in the environment, else ``default``."""
    value = os.environ.get(name, "").strip()
    return Path(value).expanduser().resolve() if value else default


# --- Primary data + config locations -------------------------------------------------
DATA_DIR = _path_env("PROTOCOL_DATA_DIR", REPO_ROOT / "packages" / "data" / "processed")
CONFIG_DIR = _path_env("PROTOCOL_CONFIG_DIR", ENGINE_DIR / "config")
OUTPUT_DIR = _path_env("PROTOCOL_OUTPUT_DIR", REPO_ROOT / "data" / "demo_outputs")
ENV_PATH = _path_env("PROTOCOL_ENV_FILE", ENGINE_DIR / ".env")

# --- Derived data artefacts ----------------------------------------------------------
CATALOG_PATH = DATA_DIR / "exercise_catalog_enriched.json"
SCIENCE_PATH = DATA_DIR / "science_corpus.json"
VECTOR_STORE_PATH = DATA_DIR / "vector_store"
EXERCISE_MANUAL_REVIEW_PATH = DATA_DIR / "exercise_manual_review_queue.json"
SCIENCE_MANUAL_REVIEW_PATH = DATA_DIR / "science_manual_review_queue.json"

# --- Offline pipeline inputs (raw DB stays at the repo root, not in packages/data) ----
RAW_EXERCISES_PATH = _path_env(
    "PROTOCOL_RAW_EXERCISES",
    REPO_ROOT / "data" / "raw" / "exercises-richdb" / "dist" / "exercises.json",
)
PUBMED_QUERIES_PATH = CONFIG_DIR / "pubmed_queries.json"
COMPARATIVE_EVIDENCE_PATH = CONFIG_DIR / "comparative_exercise_evidence.json"

# --- Exercise media (thumbnails + animated GIFs) -------------------------------------
# The rich dataset ships its own images/ and videos/ dirs. The FastAPI app serves that
# directory at /media, and the API returns absolute URLs under MEDIA_BASE_URL so the
# cross-origin web app can render them with a plain <img>.
MEDIA_DIR = _path_env("PROTOCOL_MEDIA_DIR", REPO_ROOT / "exercises-dataset")
MEDIA_BASE_URL = (
    os.environ.get("PROTOCOL_MEDIA_BASE_URL", "").strip() or "http://127.0.0.1:8000/media/"
)

# --- Model defaults ------------------------------------------------------------------
DEFAULT_MODEL = os.environ.get("PROTOCOL_MODEL", "").strip() or "gemini-3.5-flash"
# Tried in order when the primary model fails with an API error (e.g. daily rate
# limit). Comma-separated. gemma-4-31b-it intermittently 500s on free-tier keys
# (observed 2026-07), so the faster gemma-4-26b-a4b-it backs it up.
DEFAULT_FALLBACK_MODEL = (
    os.environ.get("PROTOCOL_FALLBACK_MODEL", "").strip()
    or "gemma-4-31b-it,gemma-4-26b-a4b-it"
)
EMBEDDING_MODEL = os.environ.get("PROTOCOL_EMBEDDING_MODEL", "").strip() or "all-MiniLM-L6-v2"
VECTOR_COLLECTION_NAME = "science_corpus"
