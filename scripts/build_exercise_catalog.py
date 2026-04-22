from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pipeline_common import clamp, mean, normalize_text, now_utc_iso, read_json, write_json


GOALS = ("hypertrophy", "strength")
JOINTS = ("neck", "shoulder", "elbow", "wrist", "spine", "hip", "knee", "ankle")

EQUIPMENT_MAP = {
    "body only": "bodyweight",
    "barbell": "barbell",
    "dumbbell": "dumbbell",
    "cable": "cable",
    "machine": "machine",
    "kettlebells": "kettlebell",
    "bands": "resistance_band",
    "medicine ball": "medicine_ball",
    "exercise ball": "stability_ball",
    "foam roll": "foam_roller",
    "e-z curl bar": "ez_bar",
    "other": "other",
    None: "unknown",
}

CATEGORY_MAP = {
    "strength": "strength",
    "powerlifting": "powerlifting",
    "olympic weightlifting": "olympic_weightlifting",
    "strongman": "strongman",
    "plyometrics": "plyometrics",
    "stretching": "stretching",
    "cardio": "cardio",
}

LEVEL_MAP = {
    "beginner": "beginner",
    "intermediate": "intermediate",
    "expert": "advanced",
    None: "unknown",
}

MUSCLE_MAP = {
    "abdominals": "abs",
    "abductors": "hip_abductors",
    "adductors": "hip_adductors",
    "biceps": "biceps",
    "calves": "calves",
    "chest": "chest",
    "forearms": "forearms",
    "glutes": "glutes",
    "hamstrings": "hamstrings",
    "lats": "lats",
    "lower back": "spinal_erectors",
    "middle back": "mid_back",
    "neck": "neck",
    "quadriceps": "quads",
    "shoulders": "delts",
    "traps": "traps",
    "triceps": "triceps",
}

MUSCLE_JOINT_STRESS = {
    "abs": {"spine": 1.0, "hip": 0.5},
    "hip_abductors": {"hip": 1.5, "knee": 0.5},
    "hip_adductors": {"hip": 1.4, "knee": 0.5},
    "biceps": {"elbow": 1.5, "wrist": 0.6, "shoulder": 0.3},
    "calves": {"ankle": 1.6, "knee": 0.6},
    "chest": {"shoulder": 1.4, "elbow": 0.7, "wrist": 0.2},
    "forearms": {"wrist": 1.5, "elbow": 0.8},
    "glutes": {"hip": 1.6, "knee": 0.8, "spine": 0.3},
    "hamstrings": {"hip": 1.5, "knee": 1.0, "spine": 0.5},
    "lats": {"shoulder": 1.0, "elbow": 0.8, "spine": 0.4},
    "spinal_erectors": {"spine": 1.9, "hip": 0.7},
    "mid_back": {"shoulder": 0.8, "elbow": 0.5, "spine": 0.6},
    "neck": {"neck": 2.0, "spine": 0.6},
    "quads": {"knee": 1.8, "hip": 0.6, "ankle": 0.3},
    "delts": {"shoulder": 1.9, "elbow": 0.5, "wrist": 0.3},
    "traps": {"shoulder": 0.9, "neck": 0.7, "spine": 0.4},
    "triceps": {"elbow": 1.6, "shoulder": 0.6, "wrist": 0.3},
}

KEYWORD_JOINT_STRESS = {
    "squat": {"knee": 0.6, "hip": 0.5, "spine": 0.3},
    "lunge": {"knee": 0.6, "hip": 0.5, "ankle": 0.3},
    "step up": {"knee": 0.6, "hip": 0.4, "ankle": 0.2},
    "deadlift": {"spine": 0.8, "hip": 0.5, "knee": 0.3},
    "good morning": {"spine": 0.8, "hip": 0.5},
    "press": {"shoulder": 0.6, "elbow": 0.4, "wrist": 0.2},
    "overhead": {"shoulder": 0.8, "spine": 0.2},
    "curl": {"elbow": 0.7, "wrist": 0.4},
    "extension": {"elbow": 0.3, "knee": 0.3, "spine": 0.2},
    "sit up": {"spine": 0.6, "hip": 0.3},
    "crunch": {"spine": 0.5},
    "pull up": {"shoulder": 0.7, "elbow": 0.4},
    "row": {"shoulder": 0.5, "elbow": 0.3, "spine": 0.4},
    "jump": {"knee": 0.7, "ankle": 0.6},
    "plyometric": {"knee": 0.7, "ankle": 0.6},
}

RESISTANCE_EQUIPMENT = {
    "barbell",
    "dumbbell",
    "cable",
    "machine",
    "kettlebell",
    "bodyweight",
    "ez_bar",
    "resistance_band",
}

PREFIX_MODIFIERS = {
    "barbell",
    "dumbbell",
    "cable",
    "machine",
    "smith",
    "seated",
    "standing",
    "incline",
    "decline",
    "alternating",
    "alternate",
    "one",
    "single",
    "kettlebell",
    "bodyweight",
}

TIER_SCORES = {
    "meta_analysis": 1.0,
    "systematic_review": 0.92,
    "rct": 0.85,
    "controlled_trial": 0.75,
    "observational": 0.6,
    "narrative_review": 0.5,
    "other": 0.4,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an enriched exercise catalog with filter metadata, joint stress, "
            "and evidence confidence signals."
        )
    )
    parser.add_argument(
        "--input",
        default="data/raw/free-exercise-db/dist/exercises.json",
        help="Raw free-exercise-db JSON path.",
    )
    parser.add_argument(
        "--science-corpus",
        default="data/processed/science_corpus.json",
        help="Optional science corpus JSON for PMID/doc/chunk evidence links.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/exercise_catalog_enriched.json",
        help="Output JSON path for enriched exercise catalog.",
    )
    parser.add_argument(
        "--manual-review-output",
        default="data/processed/exercise_manual_review_queue.json",
        help="Output path for exercises that should be reviewed manually.",
    )
    return parser.parse_args()


def normalize_equipment(raw_value: str | None) -> str:
    normalized = EQUIPMENT_MAP.get(raw_value)
    if normalized:
        return normalized
    return normalize_text(raw_value or "unknown").replace(" ", "_")


def normalize_category(raw_value: str | None) -> str:
    normalized = CATEGORY_MAP.get(raw_value)
    if normalized:
        return normalized
    return normalize_text(raw_value or "unknown").replace(" ", "_")


def normalize_difficulty(raw_value: str | None) -> str:
    return LEVEL_MAP.get(raw_value, "unknown")


def normalize_muscles(items: list[str]) -> list[str]:
    normalized = []
    for item in items:
        mapped = MUSCLE_MAP.get(item, normalize_text(item).replace(" ", "_"))
        normalized.append(mapped)
    return sorted(set(normalized))


def score_goal_profiles(
    category: str,
    mechanic: str,
    equipment: str,
    difficulty: str,
    force: str,
) -> dict[str, dict[str, Any]]:
    hypertrophy_score = 0.35
    hypertrophy_reasons = []
    strength_score = 0.25
    strength_reasons = []

    if category in {"strength", "powerlifting", "olympic_weightlifting", "strongman"}:
        hypertrophy_score += 0.20
        hypertrophy_reasons.append("resistance-focused category")
        strength_score += 0.30
        strength_reasons.append("strength sport compatible category")
    if category in {"plyometrics"}:
        strength_score += 0.10
        strength_reasons.append("rate-of-force style movement")
    if category in {"stretching", "cardio"}:
        hypertrophy_score -= 0.35
        strength_score -= 0.35
        hypertrophy_reasons.append("non-primary resistance category")
        strength_reasons.append("non-primary resistance category")

    if mechanic == "isolation":
        hypertrophy_score += 0.20
        strength_score += 0.05
        hypertrophy_reasons.append("single-muscle focus")
    elif mechanic == "compound":
        hypertrophy_score += 0.15
        strength_score += 0.20
        hypertrophy_reasons.append("high loading potential")
        strength_reasons.append("multi-joint loading")

    if equipment in RESISTANCE_EQUIPMENT:
        hypertrophy_score += 0.12
        strength_score += 0.12
        hypertrophy_reasons.append("resistance equipment available")
        strength_reasons.append("resistance equipment available")

    if difficulty == "advanced":
        strength_score += 0.08
        strength_reasons.append("advanced loading coordination")
    elif difficulty == "beginner":
        hypertrophy_score += 0.04
        hypertrophy_reasons.append("high accessibility for volume")

    if force in {"push", "pull"}:
        hypertrophy_score += 0.04
        strength_score += 0.04

    return {
        "hypertrophy": {
            "score": round(clamp(hypertrophy_score), 4),
            "recommended": clamp(hypertrophy_score) >= 0.55,
            "rationale": sorted(set(hypertrophy_reasons)),
        },
        "strength": {
            "score": round(clamp(strength_score), 4),
            "recommended": clamp(strength_score) >= 0.55,
            "rationale": sorted(set(strength_reasons)),
        },
    }


def joint_label(score: int) -> str:
    if score <= 0:
        return "none"
    if score == 1:
        return "low"
    if score == 2:
        return "moderate"
    return "high"


def score_joint_stress(
    name: str,
    primary_muscles: list[str],
    secondary_muscles: list[str],
    mechanic: str,
    category: str,
    difficulty: str,
) -> dict[str, Any]:
    stress_scores = {joint: 0.0 for joint in JOINTS}

    for muscle in primary_muscles:
        for joint, score in MUSCLE_JOINT_STRESS.get(muscle, {}).items():
            stress_scores[joint] += score
    for muscle in secondary_muscles:
        for joint, score in MUSCLE_JOINT_STRESS.get(muscle, {}).items():
            stress_scores[joint] += score * 0.55

    name_lower = normalize_text(name)
    for keyword, adjustments in KEYWORD_JOINT_STRESS.items():
        if keyword in name_lower:
            for joint, score in adjustments.items():
                stress_scores[joint] += score

    if mechanic == "compound":
        for joint in ("spine", "hip", "knee", "shoulder"):
            stress_scores[joint] += 0.2
    if category == "plyometrics":
        stress_scores["knee"] += 0.4
        stress_scores["ankle"] += 0.4
    if difficulty == "advanced":
        for joint, score in stress_scores.items():
            if score > 0.0:
                stress_scores[joint] += 0.15

    joint_profile: dict[str, Any] = {}
    high_stress_joints = []
    for joint in JOINTS:
        numeric = int(round(clamp(stress_scores[joint] / 1.25, 0.0, 3.0)))
        label = joint_label(numeric)
        joint_profile[joint] = {"score": numeric, "label": label}
        if label == "high":
            high_stress_joints.append(joint)

    return {
        "profile": joint_profile,
        "high_stress_joints": high_stress_joints,
    }


def get_aliases(name: str, exercise_id: str) -> list[str]:
    base = normalize_text(name)
    aliases = {base}
    aliases.add(normalize_text(exercise_id.replace("_", " ")))

    tokens = [token for token in base.split() if token]
    trimmed_tokens = [token for token in tokens if token not in PREFIX_MODIFIERS]
    if len(trimmed_tokens) >= 2:
        aliases.add(" ".join(trimmed_tokens))
    if len(tokens) >= 3:
        aliases.add(" ".join(tokens[:2]))
    aliases = {alias.strip() for alias in aliases if alias.strip()}
    filtered = []
    for alias in aliases:
        if len(alias) < 6:
            continue
        if len(alias.split()) < 2 and len(alias) < 10:
            continue
        filtered.append(alias)
    return sorted(set(filtered))


def phrase_in_text(phrase: str, text: str) -> bool:
    pattern = rf"\b{re.escape(phrase)}\b"
    return re.search(pattern, text) is not None


def summarize_abstract(abstract: str, max_len: int = 240) -> str:
    compact = " ".join(abstract.split())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 3].rstrip() + "..."


def load_science_corpus(path: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]], bool]:
    corpus_path = Path(path)
    if not corpus_path.exists():
        return {}, {}, False
    payload = read_json(corpus_path)
    docs = {doc["doc_id"]: doc for doc in payload.get("documents", [])}
    pmid_index: dict[str, dict[str, Any]] = {}
    for doc in docs.values():
        pmid = str(doc.get("pmid", "")).strip()
        if pmid:
            pmid_index[pmid] = doc
    return payload, pmid_index, True


def match_exercise_studies(
    exercise_aliases: list[str],
    corpus_docs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    for doc in corpus_docs:
        title = str(doc.get("title", "")).strip()
        abstract = str(doc.get("abstract", "")).strip()
        text = normalize_text(f"{title} {abstract}")
        matched_alias = None
        for alias in exercise_aliases:
            if phrase_in_text(alias, text):
                matched_alias = alias
                break
        if not matched_alias:
            continue

        tier = str(doc.get("evidence_tier", "other"))
        quality_score = float(doc.get("quality_score", TIER_SCORES.get(tier, 0.4)))
        retrieval_weight = float(doc.get("retrieval_weight", 0.4))
        summary = summarize_abstract(abstract or title, max_len=220)
        modalities = doc.get("measurement_modalities_detected", ["Unspecified"])
        study = {
            "pmid": doc.get("pmid"),
            "doc_id": doc.get("doc_id"),
            "chunk_ids": doc.get("chunk_ids", []),
            "title": title,
            "publication_year": doc.get("publication_year"),
            "evidence_tier": tier,
            "measurement_method": modalities,
            "participant_count": doc.get("participant_count_estimate"),
            "retrieval_weight": round(retrieval_weight, 4),
            "quality_score": round(quality_score, 4),
            "manual_review_required": bool(doc.get("manual_review_required", False)),
            "matched_alias": matched_alias,
            "study_summary": summary,
            "source_url": doc.get("source", {}).get("url"),
        }
        matched.append(study)

    matched.sort(
        key=lambda item: (
            item["quality_score"],
            item["retrieval_weight"],
            item.get("publication_year") or 0,
        ),
        reverse=True,
    )

    deduped = []
    seen_pmids = set()
    for study in matched:
        pmid = study.get("pmid")
        if pmid in seen_pmids:
            continue
        deduped.append(study)
        seen_pmids.add(pmid)
    return deduped[:8]


def score_evidence_confidence(
    studies: list[dict[str, Any]],
    category: str,
    mechanic: str,
) -> tuple[float, str, list[str], dict[str, int]]:
    fallback_basis = []
    tier_counts = Counter(study.get("evidence_tier", "other") for study in studies)
    if studies:
        max_quality = max(float(study.get("quality_score", 0.4)) for study in studies)
        avg_retrieval = mean(float(study.get("retrieval_weight", 0.4)) for study in studies)
        direct_evidence_bonus = min(0.2, len(studies) * 0.04)
        confidence = clamp((0.35 * max_quality) + (0.35 * avg_retrieval) + 0.20 + direct_evidence_bonus)
        fallback_basis.append("Direct PubMed-linked exercise evidence available")
    else:
        confidence = 0.42
        if category in {"strength", "powerlifting", "olympic_weightlifting", "strongman"}:
            confidence += 0.12
            fallback_basis.append("Aligned with resistance training categories")
        elif category == "plyometrics":
            confidence += 0.06
            fallback_basis.append("Explosive training transfer supported by programming literature")
        elif category in {"stretching", "cardio"}:
            confidence -= 0.14
            fallback_basis.append("Indirect carryover to resistance-focused goals")
        if mechanic == "compound":
            confidence += 0.10
            fallback_basis.append("Compound mechanics with broad transfer potential")
        elif mechanic == "isolation":
            confidence += 0.08
            fallback_basis.append("Isolation mechanics with clear target muscle intent")
        fallback_basis.append("Included by biomechanical reasoning and expert-practice consensus")
        confidence = clamp(confidence, 0.0, 0.72)

    if confidence >= 0.75:
        level = "high"
    elif confidence >= 0.55:
        level = "moderate"
    else:
        level = "low"
    return round(confidence, 4), level, sorted(set(fallback_basis)), dict(tier_counts)


def build_filter_metadata(
    equipment: str,
    primary_muscles: list[str],
    secondary_muscles: list[str],
    difficulty: str,
    goal_profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "equipment": [equipment],
        "muscle_groups": sorted(set(primary_muscles + secondary_muscles)),
        "difficulty": difficulty,
        "training_goals": [
            goal for goal in GOALS if bool(goal_profiles.get(goal, {}).get("recommended"))
        ],
    }


def compute_ranking_score(goal_score: float, evidence_score: float) -> float:
    return round(clamp((goal_score * 0.65) + (evidence_score * 0.35)), 4)


def assign_muscle_rankings(exercises: list[dict[str, Any]]) -> None:
    for goal in GOALS:
        by_muscle: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for exercise in exercises:
            for muscle in exercise["muscles"]["primary"]:
                by_muscle[muscle].append(exercise)

        for muscle, items in by_muscle.items():
            ordered = sorted(
                items,
                key=lambda ex: (
                    ex["ranking_scores"][goal],
                    ex["evidence"]["confidence_score"],
                    ex["goal_profiles"][goal]["score"],
                ),
                reverse=True,
            )
            total = len(ordered)
            for idx, exercise in enumerate(ordered, start=1):
                exercise.setdefault("muscle_group_rankings", {}).setdefault(goal, {})[muscle] = {
                    "rank": idx,
                    "out_of": total,
                }


def main() -> None:
    args = parse_args()
    raw_exercises = read_json(args.input)
    science_payload, science_docs_by_pmid, has_science_corpus = load_science_corpus(
        args.science_corpus
    )
    science_docs = science_payload.get("documents", []) if has_science_corpus else []

    enriched: list[dict[str, Any]] = []
    manual_review_queue: list[dict[str, Any]] = []
    unique_equipment = set()
    unique_muscles = set()

    for raw in raw_exercises:
        exercise_id = raw["id"]
        name = raw["name"]
        equipment = normalize_equipment(raw.get("equipment"))
        difficulty = normalize_difficulty(raw.get("level"))
        mechanic = raw.get("mechanic") or "unknown"
        force = raw.get("force") or "unknown"
        category = normalize_category(raw.get("category"))

        primary_muscles = normalize_muscles(raw.get("primaryMuscles", []))
        secondary_muscles = normalize_muscles(raw.get("secondaryMuscles", []))
        all_muscles = sorted(set(primary_muscles + secondary_muscles))

        goal_profiles = score_goal_profiles(
            category=category,
            mechanic=mechanic,
            equipment=equipment,
            difficulty=difficulty,
            force=force,
        )
        stress = score_joint_stress(
            name=name,
            primary_muscles=primary_muscles,
            secondary_muscles=secondary_muscles,
            mechanic=mechanic,
            category=category,
            difficulty=difficulty,
        )

        aliases = get_aliases(name=name, exercise_id=exercise_id)
        evidence_studies = match_exercise_studies(aliases, science_docs) if has_science_corpus else []
        confidence_score, confidence_level, fallback_basis, tier_counts = score_evidence_confidence(
            studies=evidence_studies,
            category=category,
            mechanic=mechanic,
        )

        ranking_scores = {
            goal: compute_ranking_score(
                goal_score=float(goal_profiles[goal]["score"]),
                evidence_score=confidence_score,
            )
            for goal in GOALS
        }

        pmids = [str(study["pmid"]) for study in evidence_studies if study.get("pmid")]
        manual_review = confidence_score < 0.50 or any(
            study.get("manual_review_required") for study in evidence_studies
        )

        exercise_payload = {
            "exercise_id": exercise_id,
            "name": name,
            "aliases": aliases,
            "movement": {
                "force": force,
                "mechanic": mechanic,
                "category": category,
                "difficulty": difficulty,
                "equipment": equipment,
                "equipment_raw": raw.get("equipment"),
            },
            "muscles": {
                "primary": primary_muscles,
                "secondary": secondary_muscles,
                "all": all_muscles,
            },
            "filter_metadata": build_filter_metadata(
                equipment=equipment,
                primary_muscles=primary_muscles,
                secondary_muscles=secondary_muscles,
                difficulty=difficulty,
                goal_profiles=goal_profiles,
            ),
            "goal_profiles": goal_profiles,
            "joint_stress": {
                "profile": stress["profile"],
                "high_stress_joints": stress["high_stress_joints"],
            },
            "evidence": {
                "confidence_score": confidence_score,
                "confidence_level": confidence_level,
                "direct_evidence_count": len(evidence_studies),
                "pmids": sorted(set(pmids)),
                "tier_counts": tier_counts,
                "studies": evidence_studies,
                "fallback_basis": fallback_basis,
                "manual_review_required": manual_review,
            },
            "ranking_scores": ranking_scores,
            "instructions": raw.get("instructions", []),
            "images": raw.get("images", []),
            "source": {
                "dataset": "free-exercise-db",
                "record_id": exercise_id,
                "repo": "https://github.com/yuhonas/free-exercise-db",
            },
        }
        enriched.append(exercise_payload)

        if manual_review:
            manual_review_queue.append(
                {
                    "exercise_id": exercise_id,
                    "name": name,
                    "confidence_level": confidence_level,
                    "confidence_score": confidence_score,
                    "direct_evidence_count": len(evidence_studies),
                    "pmids": sorted(set(pmids)),
                    "reason": (
                        "low_confidence_without_direct_studies"
                        if not evidence_studies
                        else "linked_study_requires_review"
                    ),
                }
            )

        unique_equipment.add(equipment)
        unique_muscles.update(all_muscles)

    assign_muscle_rankings(enriched)

    metadata = {
        "generated_at_utc": now_utc_iso(),
        "source_path": str(Path(args.input).resolve()),
        "source_record_count": len(raw_exercises),
        "science_corpus_path": str(Path(args.science_corpus).resolve()),
        "science_corpus_used": has_science_corpus,
        "science_document_count": len(science_docs_by_pmid),
        "enriched_record_count": len(enriched),
        "manual_review_count": len(manual_review_queue),
        "goals_supported": list(GOALS),
    }
    taxonomies = {
        "equipment": sorted(unique_equipment),
        "muscle_groups": sorted(unique_muscles),
        "difficulty": ["beginner", "intermediate", "advanced", "unknown"],
        "joints": list(JOINTS),
    }
    output_payload = {
        "metadata": metadata,
        "taxonomies": taxonomies,
        "exercises": enriched,
    }
    write_json(args.output, output_payload)

    manual_review_payload = {
        "metadata": {
            "generated_at_utc": now_utc_iso(),
            "source_catalog_path": str(Path(args.output).resolve()),
            "exercise_count": len(manual_review_queue),
        },
        "exercises": manual_review_queue,
    }
    write_json(args.manual_review_output, manual_review_payload)

    print(
        (
            f"Exercise catalog written: {args.output} | exercises={len(enriched)} "
            f"manual_review={len(manual_review_queue)} science_linked={has_science_corpus}"
        )
    )


if __name__ == "__main__":
    main()
