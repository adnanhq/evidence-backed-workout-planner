"""Build the comparison arm: citations attached by meaning rather than by name.

When an exercise has no directly-linked study, the engine attaches exactly one
retrieved finding instead (``fallback_reference_evidence_from_findings``). Those
citations go through a completely different mechanism from alias matching, and
judging both on one rubric is what lets the paper say which mechanism grounds
better rather than only that one of them is weak.

Findings are reconstructed from the cached MiniLM embeddings using the same
distance ceiling and ordering as ``query_findings``; the acceptance decision is
then made by the engine's own gate functions, unmodified. This avoids opening the
committed Chroma store, which mutates on read.

    ./.venv/bin/python -m research.s3b_build_semantic_pairs
"""
from __future__ import annotations

import collections
from typing import Any

import numpy as np

from research.common import banner, environment_snapshot, load_catalog, load_corpus, write_results
from research.s2_retrieval_eval import ARMS, MAX_FINDING_DISTANCE, cosine_distance, encode

BASELINE = ARMS[0]


def findings_for(query_text: str, corpus: dict, corpus_vectors: np.ndarray, limit: int = 6):
    """Reproduce query_findings' candidate set: trusted-only, distance-capped, deduped."""
    chunks = corpus["chunks"]
    docs_by_id = {d["doc_id"]: d for d in corpus["documents"]}
    distances = cosine_distance(_encode_one(query_text), corpus_vectors)[0]
    findings, seen = [], set()
    for index in np.argsort(distances, kind="stable"):
        if float(distances[index]) > MAX_FINDING_DISTANCE:
            break
        chunk = chunks[index]
        if chunk.get("manual_review_required") or chunk["doc_id"] in seen:
            continue
        seen.add(chunk["doc_id"])
        source = docs_by_id.get(chunk["doc_id"], {})
        findings.append({
            "doc_id": chunk["doc_id"],
            "pmid": str(chunk["pmid"]),
            "title": source.get("title", ""),
            "publication_year": chunk.get("publication_year"),
            "evidence_tier": chunk.get("evidence_tier", "other"),
            "retrieval_weight": float(chunk.get("retrieval_weight", 0.0)),
            "distance": float(distances[index]),
            "manual_review_required": False,
            "topic_clusters": chunk.get("topic_clusters") or [],
            "snippet": " ".join(str(chunk["text"]).split()),
            "trust_label": "standard",
        })
        if len(findings) >= limit * 2:
            break
    return findings[:limit]


_MODEL = {}


def _encode_one(text: str) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    if "m" not in _MODEL:
        _MODEL["m"] = SentenceTransformer(BASELINE["model"])
    return _MODEL["m"].encode(
        [text], convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
    ).astype(np.float32)


def main() -> None:
    from protocol_engine.protocol_demo import (
        build_semantic_query,
        fallback_reference_evidence_from_findings,
        filter_and_score_exercises,
        normalize_request,
    )

    catalog, corpus = load_catalog(), load_corpus()
    corpus_vectors = encode(BASELINE, [c["text"] for c in corpus["chunks"]], "corpus")
    docs_by_pmid = {d["pmid"]: d for d in corpus["documents"]}

    banner("S3b - citations attached by meaning (the semantic fallback path)")

    # Muscles whose exercises most often lack direct evidence are where this path
    # actually fires in production, so sample requests across the full range.
    muscles = sorted({m for e in catalog["exercises"] for m in e["muscles"]["primary"]})
    pairs: list[dict[str, Any]] = []
    for goal in ("hypertrophy", "strength"):
        for muscle in muscles:
            try:
                request = normalize_request(
                    goal=goal, muscles=muscle, sessions=3, session_minutes=60, equipment="",
                    experience="intermediate", avoid_joints="", notes="",
                )
            except Exception:  # noqa: BLE001 - a muscle the request layer rejects
                continue
            candidates = filter_and_score_exercises(request, catalog["exercises"])
            no_evidence = [
                c for c in candidates
                if not (c.get("top_studies") or [])
            ][:3]
            if not no_evidence:
                continue
            findings = findings_for(build_semantic_query(request, candidates[:5]),
                                    corpus, corpus_vectors)
            if not findings:
                continue
            for candidate in no_evidence:
                attached = fallback_reference_evidence_from_findings(
                    candidate, findings, request, set()
                )
                for item in attached:
                    document = docs_by_pmid.get(item["pmid"], {})
                    pairs.append({
                        "pair_id": "sem:%s:%s:%s" % (goal, candidate["exercise_id"], item["pmid"]),
                        "exercise_id": candidate["exercise_id"],
                        "exercise_name": candidate["name"],
                        "primary_muscles": candidate["muscles"]["primary"],
                        "equipment": candidate.get("equipment", ""),
                        "mechanic": candidate.get("movement", {}).get("mechanic", ""),
                        "goal": goal,
                        "matched_alias": "",
                        "alias_fanout": 0,
                        "pmid": item["pmid"],
                        "study_title": item["title"],
                        "study_abstract": document.get("abstract", ""),
                        "publication_year": item.get("publication_year"),
                        "evidence_tier": item.get("evidence_tier"),
                        "attachment_path": "semantic_fallback",
                        "stratum": "semantic_fallback",
                        "url": "https://pubmed.ncbi.nlm.nih.gov/%s/" % item["pmid"],
                    })

    unique: dict[str, dict[str, Any]] = {}
    for pair in pairs:
        unique.setdefault((pair["exercise_id"], pair["pmid"]), pair)
    deduped = [unique[k] for k in sorted(unique)]
    print("semantic-path pairs built: %d raw, %d unique (exercise, study)"
          % (len(pairs), len(deduped)))
    print("distinct studies used: %d | distinct exercises: %d"
          % (len({p["pmid"] for p in deduped}), len({p["exercise_id"] for p in deduped})))
    print("by muscle: %s" % dict(collections.Counter(
        p["primary_muscles"][0] for p in deduped if p["primary_muscles"]).most_common(8)))

    write_results("s3b_semantic_pairs", {
        "environment": environment_snapshot(),
        "n_pairs": len(deduped),
        "method": "engine gate functions over findings reconstructed from cached MiniLM "
                  "embeddings at the production distance ceiling",
        "pairs": deduped,
    })
    print("wrote results/s3b_semantic_pairs.json")


if __name__ == "__main__":
    main()
