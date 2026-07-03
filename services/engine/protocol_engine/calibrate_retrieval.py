"""Calibration helper for MAX_FINDING_DISTANCE.

Runs representative builder requests through the real semantic query + Chroma
collection and prints the cosine-distance distribution of the top hits, so the
distance ceiling in ``query_findings`` is chosen from observed data instead of
guessed. Re-run after changing the embedding model or rebuilding the corpus:

    cd services/engine && ../../.venv/bin/python -m protocol_engine.calibrate_retrieval
"""
from __future__ import annotations

try:
    from .protocol_demo import (
        build_semantic_query,
        filter_and_score_exercises,
        get_vector_collection,
        load_catalog,
        normalize_request,
    )
except ImportError:  # pragma: no cover - direct script execution
    from protocol_demo import (
        build_semantic_query,
        filter_and_score_exercises,
        get_vector_collection,
        load_catalog,
        normalize_request,
    )

# (goal, muscles, notes) — the last case is deliberately off-corpus to show
# where clearly-weak matches land.
CALIBRATION_REQUESTS = [
    ("hypertrophy", "biceps", ""),
    ("strength", "quads,glutes", ""),
    ("hypertrophy", "delts", ""),
    ("hypertrophy", "mid_back,lats", ""),
    ("strength", "chest,triceps", ""),
    ("hypertrophy", "forearms", "grip endurance for climbing"),
]


def main() -> None:
    exercises = load_catalog()["exercises"]
    collection = get_vector_collection()

    for goal, muscles, notes in CALIBRATION_REQUESTS:
        request = normalize_request(
            goal=goal,
            muscles=muscles,
            sessions=3,
            session_minutes=60,
            equipment="",
            experience="intermediate",
            avoid_joints="",
            notes=notes,
        )
        candidates = filter_and_score_exercises(request, exercises)[:5]
        query_text = build_semantic_query(request, candidates)
        response = collection.query(
            query_texts=[query_text],
            n_results=12,
            include=["documents", "metadatas", "distances"],
        )
        distances = [round(float(d), 3) for d in response["distances"][0]]
        metadatas = response["metadatas"][0]
        print(f"\n=== {goal} / {muscles}" + (f" ({notes})" if notes else ""))
        print(f"    distances: {distances}")
        for distance, metadata in list(zip(distances, metadatas))[:4]:
            print(f"    {distance:.3f}  pmid={metadata.get('pmid')}")


if __name__ == "__main__":
    main()
