"""Protocol Engine API — FastAPI wrapper over the science-backed protocol builder."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings

# Push secrets/overrides into the environment before the engine resolves them.
_settings = get_settings()
if _settings.gemini_api_key:
    os.environ.setdefault("GEMINI_API_KEY", _settings.gemini_api_key)
if _settings.protocol_data_dir:
    os.environ.setdefault("PROTOCOL_DATA_DIR", _settings.protocol_data_dir)

from protocol_engine import protocol_demo as engine  # noqa: E402
from protocol_engine import settings as engine_paths  # noqa: E402
from protocol_engine.protocol_demo import (  # noqa: E402
    DemoConfigurationError,
    DemoRequestError,
)

from . import data, mappers  # noqa: E402
from .schemas import GenerateRequest  # noqa: E402
from .service import generate_protocol  # noqa: E402

logger = logging.getLogger("engine.api")

STATE: dict[str, Any] = {
    "warm": False,
    "catalog_exercises": 0,
    "science_docs": 0,
    "vector_chunks": 0,
    "warmup_error": None,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        STATE["catalog_exercises"] = len(data.exercises())
        STATE["science_docs"] = len(data.science().get("documents", []))
        collection = engine.get_vector_collection()  # loads MiniLM + opens Chroma
        STATE["vector_chunks"] = collection.count()
        STATE["warm"] = True
        print(
            f"[warmup] ready — {STATE['catalog_exercises']} exercises, "
            f"{STATE['science_docs']} studies, {STATE['vector_chunks']} chunks",
            flush=True,
        )
    except Exception as exc:  # pragma: no cover - surfaced via /api/health
        STATE["warmup_error"] = str(exc)
        print(f"[warmup] FAILED: {exc}", flush=True)
    yield


app = FastAPI(title="Protocol Engine API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.origins_list,
    allow_origin_regex=_settings.origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the rich dataset's exercise thumbnails + animated GIFs at /media. Guarded so a
# missing media directory degrades gracefully (API still boots; media URLs 404) instead
# of crashing startup.
_media_dir = Path(engine_paths.MEDIA_DIR)
if _media_dir.is_dir():
    app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")
    print(f"[media] serving {_media_dir} at /media", flush=True)
else:
    print(f"[media] directory not found; /media not mounted: {_media_dir}", flush=True)


@app.get("/api/health")
def health() -> dict[str, Any]:
    settings = get_settings()
    return {
        "status": "ok",
        "warm": STATE["warm"],
        "catalogExercises": STATE["catalog_exercises"],
        "scienceDocs": STATE["science_docs"],
        "vectorChunks": STATE["vector_chunks"],
        "model": settings.protocol_model,
        "embeddingModel": engine.EMBEDDING_MODEL,
        "hasApiKey": bool(settings.gemini_api_key),
        "warmupError": STATE["warmup_error"],
    }


@app.get("/api/taxonomies")
def taxonomies() -> dict[str, Any]:
    tax = data.taxonomies()
    return {
        "goals": sorted(engine.GOAL_CHOICES),
        "muscleGroups": data.primary_muscle_groups(),
        "equipment": tax.get("equipment", []),
        "difficulty": tax.get("difficulty", []),
        "joints": tax.get("joints", []),
        "splitTemplates": sorted(engine.SPLIT_TEMPLATE_CHOICES),
        "experienceLevels": sorted(engine.EXPERIENCE_CHOICES),
        "displayLabels": {"muscles": engine.MUSCLE_DISPLAY_LABELS},
        "equipmentPresets": engine.EQUIPMENT_PRESETS,
    }


@app.post("/api/protocol/generate")
async def generate(req: GenerateRequest) -> dict[str, Any]:
    try:
        return await generate_protocol(req)
    except DemoRequestError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except DemoConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Protocol generation failed")
        raise HTTPException(
            status_code=502,
            detail="Protocol generation failed due to an internal error. Please try again.",
        )


@app.get("/api/exercises")
def list_exercises(
    q: str = "",
    muscle: str = "",
    equipment: str = "",
    difficulty: str = "",
    goal: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
) -> dict[str, Any]:
    ql = q.strip().lower()

    def matches(ex: dict[str, Any]) -> bool:
        fm = ex.get("filter_metadata", {}) or {}
        if ql:
            haystack = ex.get("name", "").lower() + " " + " ".join(ex.get("aliases", []))
            if ql not in haystack.lower():
                return False
        # Match primary movers only — secondary synergists (e.g. mid_back on a
        # shoulder press) would otherwise flood every muscle filter with noise.
        if muscle and muscle not in (ex.get("muscles", {}) or {}).get("primary", []):
            return False
        if equipment and equipment not in fm.get("equipment", []):
            return False
        if difficulty and fm.get("difficulty") != difficulty:
            return False
        if goal and goal not in fm.get("training_goals", []):
            return False
        return True

    filtered = [e for e in data.exercises() if matches(e)]
    # Surface the best-evidenced, most-confident exercises first.
    filtered.sort(
        key=lambda e: (
            -(e.get("evidence", {}).get("direct_evidence_count", 0)),
            -(e.get("evidence", {}).get("confidence_score", 0) or 0),
            e.get("name", ""),
        )
    )
    total = len(filtered)
    start = (page - 1) * page_size
    items = [mappers.exercise_summary(e) for e in filtered[start : start + page_size]]
    return {"total": total, "page": page, "pageSize": page_size, "items": items}


@app.get("/api/exercises/{exercise_id}")
def get_exercise(exercise_id: str) -> dict[str, Any]:
    ex = data.exercises_by_id().get(exercise_id)
    if ex is None:
        raise HTTPException(status_code=404, detail=f"Unknown exercise: {exercise_id}")
    return mappers.exercise_detail(ex)


@app.get("/api/evidence/{pmid}")
def get_evidence(pmid: str) -> dict[str, Any]:
    doc = data.docs_by_pmid().get(str(pmid))
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Unknown PMID: {pmid}")
    return mappers.evidence_detail(doc)
