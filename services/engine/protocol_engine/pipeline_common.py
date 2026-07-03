from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")
NON_ALNUM_SPACE_PATTERN = re.compile(r"[^a-z0-9\s]+")
MULTI_SPACE_PATTERN = re.compile(r"\s+")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def normalize_text(text: str) -> str:
    lowered = text.lower()
    lowered = NON_ALNUM_SPACE_PATTERN.sub(" ", lowered)
    lowered = MULTI_SPACE_PATTERN.sub(" ", lowered).strip()
    return lowered


def slugify(text: str) -> str:
    normalized = normalize_text(text)
    return normalized.replace(" ", "-")


def parse_year(raw_value: str | None) -> int | None:
    if not raw_value:
        return None
    match = YEAR_PATTERN.search(raw_value)
    if not match:
        return None
    return int(match.group(0))


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def mean(values: Iterable[float]) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(items) / len(items)


def split_sentences(text: str) -> list[str]:
    normalized = MULTI_SPACE_PATTERN.sub(" ", text.strip())
    if not normalized:
        return []
    parts = SENTENCE_SPLIT_PATTERN.split(normalized)
    return [part.strip() for part in parts if part.strip()]


def chunk_sentences(
    sentences: Sequence[str],
    max_chars: int = 900,
    min_chars: int = 250,
) -> list[str]:
    if not sentences:
        return []
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        candidate_len = current_len + len(sentence) + (1 if current else 0)
        if current and candidate_len > max_chars:
            chunks.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
            continue
        current.append(sentence)
        current_len = candidate_len

    if current:
        chunks.append(" ".join(current))

    if len(chunks) > 1 and len(chunks[-1]) < min_chars:
        chunks[-2] = f"{chunks[-2]} {chunks[-1]}".strip()
        chunks.pop()
    return chunks


def chunk_text(text: str, max_chars: int = 900, min_chars: int = 250) -> list[str]:
    return chunk_sentences(split_sentences(text), max_chars=max_chars, min_chars=min_chars)
