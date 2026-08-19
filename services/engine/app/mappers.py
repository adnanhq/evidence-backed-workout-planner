"""Transform engine output (snake_case ``debug_payload`` / catalog records) into
clean camelCase API payloads, attaching a derived PubMed ``url`` to every study."""
from __future__ import annotations

from typing import Any, Optional

from protocol_engine.settings import MEDIA_BASE_URL

PUBMED_URL = "https://pubmed.ncbi.nlm.nih.gov/{}/"
# The engine serves the dataset's images/ and videos/ dirs at /media; the catalog stores
# relative paths like "images/0001-x.jpg" and "videos/0001-x.gif" which we make absolute.
IMAGE_BASE = MEDIA_BASE_URL


def pubmed_url(pmid: Any) -> Optional[str]:
    if pmid is None:
        return None
    pmid = str(pmid).strip()
    return PUBMED_URL.format(pmid) if pmid else None


def _trust_label(item: dict[str, Any]) -> str:
    label = item.get("trust_label")
    if label:
        return label
    return "lower-trust" if item.get("manual_review_required") else "standard"


def map_evidence(item: dict[str, Any]) -> dict[str, Any]:
    """Maps a reference_evidence item, a science_finding, or a catalog study."""
    pmid = item.get("pmid")
    return {
        "pmid": str(pmid) if pmid is not None else None,
        "title": item.get("title"),
        "year": item.get("publication_year"),
        "tier": item.get("evidence_tier") or "other",
        "trustLabel": _trust_label(item),
        "snippet": item.get("snippet") or item.get("study_summary"),
        "url": item.get("source_url") or pubmed_url(pmid),
        "manualReviewRequired": bool(item.get("manual_review_required", False)),
    }


def _map_exercise(
    ex: dict[str, Any], catalog_by_id: Optional[dict[str, dict[str, Any]]] = None
) -> dict[str, Any]:
    presc = ex.get("prescription", {}) or {}
    # Protocol outline exercises carry no media; resolve it from the catalog record.
    entry = (catalog_by_id or {}).get(ex.get("exercise_id"), {})
    images = _image_urls(entry)
    return {
        "exerciseId": ex.get("exercise_id"),
        "name": ex.get("name"),
        "targetMuscle": ex.get("target_muscle"),
        "targetLabel": ex.get("target_label"),
        "rankDisplay": ex.get("rank_display"),
        "selectionReason": ex.get("selection_reason"),
        "lowerTrustEvidence": bool(ex.get("lower_trust_evidence", False)),
        "thumbnail": images[0] if images else None,
        "prescription": {
            "sets": presc.get("sets"),
            "reps": presc.get("reps"),
            "rest": presc.get("rest"),
            "display": presc.get("display"),
        },
        "referencePmids": [str(p) for p in ex.get("reference_pmids", [])],
        "referenceEvidence": [map_evidence(e) for e in ex.get("reference_evidence", [])],
    }


def _map_session(
    session: dict[str, Any], catalog_by_id: Optional[dict[str, dict[str, Any]]] = None
) -> dict[str, Any]:
    return {
        "sessionNumber": session.get("session_number"),
        "splitLabel": session.get("split_label"),
        "focus": session.get("focus"),
        "targetMuscles": session.get("target_muscles", []),
        "exercises": [_map_exercise(e, catalog_by_id) for e in session.get("exercises", [])],
    }


def _map_request(req: dict[str, Any]) -> dict[str, Any]:
    return {
        "goal": req.get("goal"),
        "muscles": req.get("muscles", []),
        "sessions": req.get("sessions"),
        "sessionMinutes": req.get("session_minutes"),
        "exercisesPerSession": req.get("exercises_per_session"),
        "equipment": req.get("equipment", []),
        "experience": req.get("experience"),
        "avoidJoints": req.get("avoid_joints", []),
        "notes": req.get("notes", ""),
        "splitTemplate": req.get("split_template"),
    }


def map_protocol_response(
    debug_payload: dict[str, Any],
    markdown_text: str,
    catalog_by_id: Optional[dict[str, dict[str, Any]]] = None,
) -> dict[str, Any]:
    outline = debug_payload.get("protocol_outline", {}) or {}
    findings = debug_payload.get("science_findings", []) or []

    appendix: list[dict[str, Any]] = []
    seen: set[str] = set()
    for finding in findings:
        pmid = str(finding.get("pmid"))
        if pmid in seen:
            continue
        seen.add(pmid)
        appendix.append(map_evidence(finding))
    # Studies attached directly to an exercise belong in the appendix alongside the
    # corpus-level findings, so the study count and bibliography cover every PMID the
    # response displays on its exercise rows. Mirrors render_protocol_markdown.
    for session in outline.get("sessions", []) or []:
        for exercise in session.get("exercises", []) or []:
            for evidence_item in exercise.get("reference_evidence", []) or []:
                raw_pmid = evidence_item.get("pmid")
                if not raw_pmid or str(raw_pmid) in seen:
                    continue
                seen.add(str(raw_pmid))
                appendix.append(map_evidence(evidence_item))

    return {
        "request": _map_request(debug_payload.get("request", {})),
        "splitSummary": outline.get("split_summary"),
        "splitTemplate": outline.get("split_template"),
        "planner": outline.get("planner"),
        "plannerModel": debug_payload.get("planner_model"),
        "usedFallback": bool(debug_payload.get("used_fallback_renderer", False)),
        "exercisesPerSession": outline.get("exercises_per_session"),
        "warnings": debug_payload.get("warnings", []),
        "sessions": [_map_session(s, catalog_by_id) for s in outline.get("sessions", [])],
        "evidenceAppendix": appendix,
        "markdown": markdown_text,
    }


# --- Exercise library -----------------------------------------------------------------

def _image_urls(ex: dict[str, Any]) -> list[str]:
    return [IMAGE_BASE + str(p) for p in ex.get("images", []) if p]


def _gif_url(ex: dict[str, Any]) -> Optional[str]:
    gif = ex.get("gif")
    return IMAGE_BASE + str(gif) if gif else None


def exercise_summary(ex: dict[str, Any]) -> dict[str, Any]:
    movement = ex.get("movement", {}) or {}
    muscles = ex.get("muscles", {}) or {}
    fm = ex.get("filter_metadata", {}) or {}
    evidence = ex.get("evidence", {}) or {}
    images = _image_urls(ex)
    return {
        "exerciseId": ex.get("exercise_id"),
        "name": ex.get("name"),
        "primaryMuscles": muscles.get("primary", []),
        "secondaryMuscles": muscles.get("secondary", []),
        "equipment": fm.get("equipment", []),
        "difficulty": fm.get("difficulty") or movement.get("difficulty"),
        "mechanic": movement.get("mechanic"),
        "force": movement.get("force"),
        "category": movement.get("category"),
        "trainingGoals": fm.get("training_goals", []),
        "evidenceCount": evidence.get("direct_evidence_count", 0),
        "confidenceLevel": evidence.get("confidence_level"),
        "confidenceScore": evidence.get("confidence_score"),
        "bestTier": _best_tier(evidence.get("studies", [])),
        "thumbnail": images[0] if images else None,
        "gif": _gif_url(ex),
    }


_TIER_RANK = {
    "meta_analysis": 0,
    "rct": 1,
    "systematic_review": 2,
    "controlled_trial": 3,
    "observational": 4,
    "narrative_review": 5,
    "other": 6,
}


def _best_tier(studies: list[dict[str, Any]]) -> Optional[str]:
    tiers = [s.get("evidence_tier") for s in studies if s.get("evidence_tier")]
    if not tiers:
        return None
    return min(tiers, key=lambda t: _TIER_RANK.get(t, 99))


def exercise_detail(ex: dict[str, Any]) -> dict[str, Any]:
    evidence = ex.get("evidence", {}) or {}
    studies = [
        {
            **map_evidence(s),
            "qualityScore": s.get("quality_score"),
            "matchedAlias": s.get("matched_alias"),
            "participantCount": s.get("participant_count"),
            "measurementMethod": s.get("measurement_method", []),
        }
        for s in evidence.get("studies", [])
    ]
    return {
        **exercise_summary(ex),
        "aliases": ex.get("aliases", []),
        "images": _image_urls(ex),
        "instructions": ex.get("instructions", []),
        "goalProfiles": ex.get("goal_profiles", {}),
        "jointStress": ex.get("joint_stress", {}),
        "rankingScores": ex.get("ranking_scores", {}),
        "muscleGroupRankings": ex.get("muscle_group_rankings", {}),
        "evidence": {
            "confidenceScore": evidence.get("confidence_score"),
            "confidenceLevel": evidence.get("confidence_level"),
            "directEvidenceCount": evidence.get("direct_evidence_count", 0),
            "tierCounts": evidence.get("tier_counts", {}),
            "fallbackBasis": evidence.get("fallback_basis", []),
            "studies": studies,
            "comparativeFindings": evidence.get("comparative_findings", []),
        },
    }


def evidence_detail(doc: dict[str, Any]) -> dict[str, Any]:
    source = doc.get("source", {}) or {}
    pmid = doc.get("pmid")
    return {
        "pmid": str(pmid) if pmid is not None else None,
        "docId": doc.get("doc_id"),
        "title": doc.get("title"),
        "abstract": doc.get("abstract"),
        "authors": doc.get("authors", []),
        "journal": doc.get("journal"),
        "year": doc.get("publication_year"),
        "publicationTypes": doc.get("publication_types", []),
        "doi": doc.get("doi"),
        "tier": doc.get("evidence_tier") or "other",
        "topicClusters": doc.get("topic_clusters", []),
        "participantCount": doc.get("participant_count_estimate"),
        "measurementModalities": doc.get("measurement_modalities_detected", []),
        "manualReviewRequired": bool(doc.get("manual_review_required", False)),
        "url": source.get("url") or pubmed_url(pmid),
    }
