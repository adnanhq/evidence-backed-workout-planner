"""Protocol generation: normalize the request, call the engine off the event
loop, and shape the response. Concurrency is bounded so torch/LLM work doesn't
oversubscribe the process."""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from fastapi.concurrency import run_in_threadpool

from protocol_engine.protocol_demo import normalize_request, run_protocol_demo

from .config import get_settings
from .data import exercises_by_id
from .mappers import map_protocol_response
from .schemas import GenerateRequest

_semaphore: Optional[asyncio.Semaphore] = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(get_settings().max_concurrency)
    return _semaphore


def _generate_sync(req: GenerateRequest) -> dict[str, Any]:
    settings = get_settings()
    request = normalize_request(
        goal=req.goal,
        muscles=",".join(req.muscles),
        sessions=req.sessions,
        session_minutes=req.session_minutes,
        exercises_per_session=req.exercises_per_session,
        equipment=",".join(req.equipment),
        experience=req.experience,
        avoid_joints=",".join(req.avoid_joints),
        notes=req.notes,
        split_template=req.split_template,
    )
    result = run_protocol_demo(
        request=request,
        model=req.model or settings.protocol_model,
        api_key=settings.gemini_api_key or None,
        persist=False,
        fallback_model=settings.protocol_fallback_model or None,
    )
    return map_protocol_response(
        result["debug_payload"], result["markdown_text"], exercises_by_id()
    )


async def generate_protocol(req: GenerateRequest) -> dict[str, Any]:
    async with _get_semaphore():
        return await run_in_threadpool(_generate_sync, req)
