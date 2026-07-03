"""Request models for the API. Responses are returned as plain dicts from
``mappers`` so the engine's evolving output shape never breaks serialization."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

Goal = str
Experience = str
SplitTemplate = str


class GenerateRequest(BaseModel):
    """Accepts camelCase (from the web app) or snake_case (CLI/tests)."""

    model_config = ConfigDict(populate_by_name=True)

    goal: Goal = Field(default="hypertrophy")
    muscles: list[str] = Field(min_length=1)
    sessions: int = Field(default=3, ge=1, le=7)
    session_minutes: int = Field(default=60, ge=10, le=180, alias="sessionMinutes")
    exercises_per_session: Optional[int] = Field(
        default=None, ge=1, le=10, alias="exercisesPerSession"
    )
    equipment: list[str] = Field(default_factory=list)
    experience: Experience = Field(default="intermediate")
    avoid_joints: list[str] = Field(default_factory=list, alias="avoidJoints")
    notes: str = Field(default="")
    split_template: SplitTemplate = Field(default="auto", alias="splitTemplate")
    model: Optional[str] = Field(default=None)
