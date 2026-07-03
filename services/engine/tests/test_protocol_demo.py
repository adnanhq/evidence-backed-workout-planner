from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from protocol_engine.protocol_demo import (
    PROJECT_ENV_PATH,
    DemoConfigurationError,
    DemoRequestError,
    build_llm_candidate_pool,
    build_llm_generation_config,
    build_plan_response_schema,
    build_outline_from_llm_plan,
    build_prompt_payload,
    build_protocol_outline,
    normalize_llm_prescription,
    query_findings,
    supports_structured_output,
    choose_display_rank,
    dedupe_candidates,
    determine_exercises_per_session,
    determine_min_exercises_per_session,
    extract_json_object,
    filter_and_score_exercises,
    format_rank_summary,
    load_project_env,
    normalize_request,
    render_protocol_markdown,
    resolve_api_key,
    run_protocol_demo,
    run_protocol_dry_run,
    validate_generated_markdown,
    validate_llm_protocol_plan,
)
from protocol_engine.build_exercise_catalog import (
    apply_muscle_corrections,
    assign_muscle_rankings,
    filter_studies_for_goal,
    format_exercise_name,
    get_aliases,
    is_resistance_evidence_eligible,
    load_comparative_evidence,
    match_exercise_studies,
    score_comparative_evidence,
)


def make_exercise(
    name: str,
    exercise_id: str,
    equipment: str,
    ranking_score: float,
    direct_studies: list[dict],
    manual_review_required: bool,
) -> dict:
    return {
        "exercise_id": exercise_id,
        "name": name,
        "movement": {
            "force": "pull",
            "mechanic": "isolation",
            "category": "strength",
            "difficulty": "beginner",
            "equipment": equipment,
            "equipment_raw": equipment,
        },
        "muscles": {
            "primary": ["biceps"],
            "secondary": ["forearms"] if "Preacher" in name or "Curl" in name else [],
            "all": ["biceps", "forearms"],
        },
        "filter_metadata": {
            "equipment": [equipment],
            "muscle_groups": ["biceps", "forearms"],
            "difficulty": "beginner",
            "training_goals": ["hypertrophy", "strength"],
        },
        "goal_profiles": {
            "hypertrophy": {"score": 0.95, "recommended": True, "rationale": []},
            "strength": {"score": 0.76, "recommended": True, "rationale": []},
        },
        "joint_stress": {
            "profile": {
                "neck": {"score": 0, "label": "none"},
                "shoulder": {"score": 1, "label": "low"},
                "elbow": {"score": 2, "label": "moderate"},
                "wrist": {"score": 1, "label": "low"},
                "spine": {"score": 0, "label": "none"},
                "hip": {"score": 0, "label": "none"},
                "knee": {"score": 0, "label": "none"},
                "ankle": {"score": 0, "label": "none"},
            },
            "high_stress_joints": [],
        },
        "evidence": {
            "confidence_score": 0.82 if direct_studies else 0.62,
            "manual_review_required": manual_review_required,
            "studies": direct_studies,
        },
        "ranking_scores": {
            "hypertrophy": ranking_score,
            "strength": ranking_score - 0.12,
        },
        "muscle_group_rankings": {
            "hypertrophy": {"biceps": {"rank": 1 if ranking_score > 0.88 else 6, "out_of": 20}},
            "strength": {"biceps": {"rank": 2 if ranking_score > 0.88 else 8, "out_of": 20}},
        },
    }


def make_target_exercise(
    name: str,
    exercise_id: str,
    equipment: str,
    ranking_score: float,
    primary_muscles: list[str],
    secondary_muscles: list[str],
    mechanic: str = "isolation",
    direct_studies: list[dict] | None = None,
    manual_review_required: bool = False,
    instructions: list[str] | None = None,
) -> dict:
    exercise = make_exercise(
        name=name,
        exercise_id=exercise_id,
        equipment=equipment,
        ranking_score=ranking_score,
        direct_studies=direct_studies or [],
        manual_review_required=manual_review_required,
    )
    all_muscles = sorted(set(primary_muscles + secondary_muscles))
    exercise["movement"]["mechanic"] = mechanic
    exercise["movement"]["force"] = "push"
    exercise["muscles"] = {
        "primary": primary_muscles,
        "secondary": secondary_muscles,
        "all": all_muscles,
    }
    exercise["filter_metadata"]["muscle_groups"] = all_muscles
    exercise["muscle_group_rankings"] = {
        "hypertrophy": {
            muscle: {"rank": 1, "out_of": 20}
            for muscle in primary_muscles
        },
        "strength": {},
    }
    exercise["instructions"] = instructions or []
    return exercise


def set_muscle_rank(
    exercise: dict,
    muscle: str,
    rank: int,
    out_of: int = 20,
    goal: str = "hypertrophy",
) -> dict:
    exercise.setdefault("muscle_group_rankings", {}).setdefault(goal, {})[muscle] = {
        "rank": rank,
        "out_of": out_of,
    }
    return exercise


class ProtocolDemoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = normalize_request(
            goal="hypertrophy",
            muscles="bicep",
            sessions=2,
            session_minutes=45,
            equipment="cable,dumbbell",
            experience="beginner",
            avoid_joints="",
            notes="demo check",
        )
        self.exercises = [
            make_exercise(
                name="Standing Biceps Cable Curl",
                exercise_id="Standing_Biceps_Cable_Curl",
                equipment="cable",
                ranking_score=0.91,
                manual_review_required=False,
                direct_studies=[
                    {
                        "pmid": "39077025",
                        "title": "Effects of 12 Weeks of Resistance Training",
                        "publication_year": 2023,
                        "evidence_tier": "controlled_trial",
                        "measurement_method": ["Hypertrophy"],
                        "manual_review_required": False,
                        "study_summary": "Included biceps curl work within the intervention.",
                        "matched_alias": "biceps curl",
                    }
                ],
            ),
            make_exercise(
                name="Cable Preacher Curl",
                exercise_id="Cable_Preacher_Curl",
                equipment="cable",
                ranking_score=0.90,
                manual_review_required=True,
                direct_studies=[
                    {
                        "pmid": "40082069",
                        "title": "Preacher versus Bayesian Cable Curls",
                        "publication_year": 2025,
                        "evidence_tier": "rct",
                        "manual_review_required": False,
                        "study_summary": "Shoulder position influences regional elbow-flexor hypertrophy.",
                    },
                    {
                        "pmid": "37559762",
                        "title": "Exercises at Long and Short Muscle Lengths",
                        "publication_year": 2023,
                        "evidence_tier": "other",
                        "manual_review_required": True,
                        "study_summary": "Incline and preacher curls produced different regional growth patterns.",
                    },
                ],
            ),
            make_exercise(
                name="Two-Arm Dumbbell Preacher Curl",
                exercise_id="Two-Arm_Dumbbell_Preacher_Curl",
                equipment="dumbbell",
                ranking_score=0.89,
                manual_review_required=True,
                direct_studies=[
                    {
                        "pmid": "40082069",
                        "title": "Preacher versus Bayesian Cable Curls",
                        "publication_year": 2025,
                        "evidence_tier": "rct",
                        "manual_review_required": False,
                        "study_summary": "Shoulder position influences regional elbow-flexor hypertrophy.",
                    }
                ],
            ),
            make_exercise(
                name="Incline Dumbbell Curl",
                exercise_id="Incline_Dumbbell_Curl",
                equipment="dumbbell",
                ranking_score=0.84,
                manual_review_required=False,
                direct_studies=[],
            ),
            {
                "exercise_id": "Lat_Pulldown",
                "name": "Full Range-Of-Motion Lat Pulldown",
                "movement": {
                    "force": "pull",
                    "mechanic": "compound",
                    "category": "strength",
                    "difficulty": "beginner",
                    "equipment": "cable",
                    "equipment_raw": "cable",
                },
                "muscles": {
                    "primary": ["lats"],
                    "secondary": ["biceps"],
                    "all": ["lats", "biceps"],
                },
                "filter_metadata": {
                    "equipment": ["cable"],
                    "muscle_groups": ["lats", "biceps"],
                    "difficulty": "beginner",
                    "training_goals": ["hypertrophy", "strength"],
                },
                "goal_profiles": {
                    "hypertrophy": {"score": 0.93, "recommended": True, "rationale": []},
                    "strength": {"score": 0.85, "recommended": True, "rationale": []},
                },
                "joint_stress": {
                    "profile": {
                        "neck": {"score": 0, "label": "none"},
                        "shoulder": {"score": 1, "label": "low"},
                        "elbow": {"score": 1, "label": "low"},
                        "wrist": {"score": 0, "label": "none"},
                        "spine": {"score": 0, "label": "none"},
                        "hip": {"score": 0, "label": "none"},
                        "knee": {"score": 0, "label": "none"},
                        "ankle": {"score": 0, "label": "none"},
                    },
                    "high_stress_joints": [],
                },
                "evidence": {
                    "confidence_score": 0.95,
                    "manual_review_required": False,
                    "studies": [
                        {
                            "pmid": "40911904",
                            "title": "Quadriceps paper with full range wording",
                            "publication_year": 2025,
                            "evidence_tier": "rct",
                            "manual_review_required": False,
                            "study_summary": "Not actually about lat pulldowns.",
                            "matched_alias": "full range",
                        }
                    ],
                },
                "ranking_scores": {"hypertrophy": 0.96, "strength": 0.90},
                "muscle_group_rankings": {
                    "hypertrophy": {},
                    "strength": {},
                },
            },
        ]
        self.findings = [
            {
                "doc_id": "pmid-40082069",
                "pmid": "40082069",
                "title": "Preacher versus Bayesian Cable Curls",
                "publication_year": 2025,
                "evidence_tier": "rct",
                "retrieval_weight": 0.77,
                "distance": 0.43,
                "manual_review_required": False,
                "topic_clusters": ["exercise_selection"],
                "snippet": "The preacher variation outperformed the extended shoulder position at some elbow-flexor sites.",
                "trust_label": "standard",
            },
            {
                "doc_id": "pmid-40570881",
                "pmid": "40570881",
                "title": "Does Muscle Length Influence Regional Hypertrophy?",
                "publication_year": 2025,
                "evidence_tier": "meta_analysis",
                "retrieval_weight": 0.89,
                "distance": 0.42,
                "manual_review_required": False,
                "topic_clusters": ["muscle_length"],
                "snippet": "Longer muscle lengths can meaningfully affect regional hypertrophy outcomes.",
                "trust_label": "standard",
            },
        ]

    def test_normalize_request_applies_aliases(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="bicep,shoulders",
            sessions=2,
            session_minutes=40,
            equipment="bands,ezbar",
            experience="intermediate",
            avoid_joints="back",
        )
        self.assertEqual(request.muscles, ["biceps", "delts"])
        self.assertEqual(request.equipment, ["ez_bar", "resistance_band"])
        self.assertEqual(request.avoid_joints, ["spine"])
        self.assertIsNone(request.exercises_per_session)

    def test_normalize_request_expands_gym_equipment_preset(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="triceps",
            sessions=2,
            session_minutes=45,
            equipment="gym,dumbells",
            experience="intermediate",
        )

        # The gym preset was widened to surface the rich dataset's machine variants
        # (smith/leverage) and bands/kettlebells; "dumbells" still dedupes into "dumbbell".
        self.assertEqual(
            request.equipment,
            [
                "barbell",
                "cable",
                "dumbbell",
                "ez_bar",
                "kettlebell",
                "leverage_machine",
                "machine",
                "resistance_band",
                "smith_machine",
            ],
        )
        self.assertIn("smith_machine", request.equipment)
        self.assertNotIn("foam_roller", request.equipment)

    def test_exercises_per_session_override_controls_session_size(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="chest,triceps,biceps,shoulders",
            sessions=4,
            session_minutes=45,
            exercises_per_session=3,
            experience="intermediate",
        )

        candidates = dedupe_candidates(filter_and_score_exercises(request, [
            make_target_exercise("Bench Press", "Bench_Press", "barbell", 0.95, ["chest"], []),
            make_target_exercise("Cable Curl", "Cable_Curl", "cable", 0.93, ["biceps"], []),
            make_target_exercise("Triceps Pushdown", "Triceps_Pushdown", "cable", 0.94, ["triceps"], []),
            make_target_exercise("Cable Lateral Raise", "Cable_Lateral_Raise", "cable", 0.88, ["delts"], []),
        ]))
        candidate_pool = build_llm_candidate_pool(request, candidates)
        payload = build_prompt_payload(
            request=request,
            candidate_pool=candidate_pool,
            findings=[],
            warnings=[],
        )

        self.assertEqual(determine_exercises_per_session(request), 3)
        self.assertEqual(determine_min_exercises_per_session(request), 3)
        self.assertEqual(candidate_pool["per_muscle_limit"], 3)
        self.assertEqual(payload["context"]["constraints"]["min_exercises_per_session"], 3)
        self.assertEqual(payload["context"]["constraints"]["max_exercises_per_session"], 3)
        self.assertIn("exactly 3 exercises", payload["user_prompt"])

    def test_multi_muscle_candidate_pool_stays_top_three_with_larger_sessions(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="chest,triceps,biceps,shoulders",
            sessions=4,
            session_minutes=45,
            exercises_per_session=4,
            experience="intermediate",
        )
        exercises = [
            make_target_exercise(f"Triceps Exercise {index}", f"Triceps_{index}", "cable", 0.99 - index * 0.01, ["triceps"], [])
            for index in range(5)
        ] + [
            make_target_exercise("Bench Press", "Bench_Press", "barbell", 0.95, ["chest"], []),
            make_target_exercise("Cable Curl", "Cable_Curl", "cable", 0.93, ["biceps"], []),
            make_target_exercise("Cable Lateral Raise", "Cable_Lateral_Raise", "cable", 0.88, ["delts"], []),
        ]
        candidates = filter_and_score_exercises(request, exercises)
        candidate_pool = build_llm_candidate_pool(request, candidates)

        self.assertEqual(candidate_pool["selection_policy"], "top_3_per_muscle_top_3_per_delt_head")
        self.assertEqual(candidate_pool["per_muscle_limit"], 3)
        self.assertEqual(len(candidate_pool["by_target"]["triceps"]), 3)
        self.assertLessEqual(len(candidate_pool["by_target"]["chest"]), 3)
        self.assertLessEqual(len(candidate_pool["by_target"]["biceps"]), 3)

    def test_llm_candidate_pool_uses_raw_top_ranked_variants_before_dedupe(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="biceps",
            sessions=2,
            session_minutes=45,
            equipment="cable,dumbbell,machine,barbell",
            experience="intermediate",
        )
        exercises = [
            set_muscle_rank(
                make_exercise("Machine Preacher Curls", "Machine_Preacher_Curls", "machine", 0.95, [], False),
                "biceps",
                1,
                10,
            ),
            set_muscle_rank(
                make_exercise("Cable Preacher Curl", "Cable_Preacher_Curl", "cable", 0.94, [], False),
                "biceps",
                2,
                10,
            ),
            set_muscle_rank(
                make_exercise("One Arm Dumbbell Preacher Curl", "One_Arm_Dumbbell_Preacher_Curl", "dumbbell", 0.93, [], False),
                "biceps",
                3,
                10,
            ),
            set_muscle_rank(
                make_exercise("Reverse Barbell Preacher Curls", "Reverse_Barbell_Preacher_Curls", "barbell", 0.92, [], False),
                "biceps",
                6,
                10,
            ),
        ]
        raw_candidates = filter_and_score_exercises(request, exercises)
        deduped_candidates = dedupe_candidates(raw_candidates)
        candidate_pool = build_llm_candidate_pool(request, raw_candidates)
        biceps_ids = [
            item["exercise_id"] for item in candidate_pool["by_target"]["biceps"]
        ]

        self.assertEqual(len(deduped_candidates), 2)
        self.assertEqual(
            biceps_ids,
            [
                "Machine_Preacher_Curls",
                "Cable_Preacher_Curl",
                "One_Arm_Dumbbell_Preacher_Curl",
            ],
        )
        self.assertNotIn("Reverse_Barbell_Preacher_Curls", candidate_pool["allowed_exercise_ids"])

    def test_llm_candidate_pool_excludes_global_rank_four_even_when_third_eligible(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="chest,triceps",
            sessions=2,
            session_minutes=45,
            equipment="barbell,cable",
            experience="intermediate",
        )
        exercises = [
            set_muscle_rank(
                make_target_exercise("Bench Press", "Bench_Press", "barbell", 0.99, ["chest"], []),
                "chest",
                1,
                10,
            ),
            set_muscle_rank(
                make_target_exercise("Incline Bench Press", "Incline_Bench_Press", "barbell", 0.98, ["chest"], []),
                "chest",
                2,
                10,
            ),
            set_muscle_rank(
                make_target_exercise("Decline Bench Press", "Decline_Bench_Press", "barbell", 0.97, ["chest"], []),
                "chest",
                4,
                10,
            ),
            set_muscle_rank(
                make_target_exercise("Overhead Triceps Extension", "Overhead_Triceps_Extension", "cable", 0.99, ["triceps"], []),
                "triceps",
                1,
                10,
            ),
            set_muscle_rank(
                make_target_exercise("Standing Overhead Triceps Extension", "Standing_Overhead_Triceps_Extension", "barbell", 0.98, ["triceps"], []),
                "triceps",
                3,
                10,
            ),
            set_muscle_rank(
                make_target_exercise("Rope Overhead Triceps Extension", "Rope_Overhead_Triceps_Extension", "cable", 0.97, ["triceps"], []),
                "triceps",
                4,
                10,
            ),
        ]
        candidate_pool = build_llm_candidate_pool(
            request,
            filter_and_score_exercises(request, exercises),
        )

        self.assertEqual(
            [item["exercise_id"] for item in candidate_pool["by_target"]["chest"]],
            ["Bench_Press", "Incline_Bench_Press"],
        )
        self.assertEqual(
            [item["exercise_id"] for item in candidate_pool["by_target"]["triceps"]],
            ["Overhead_Triceps_Extension", "Standing_Overhead_Triceps_Extension"],
        )
        self.assertNotIn("Decline_Bench_Press", candidate_pool["allowed_exercise_ids"])
        self.assertNotIn("Rope_Overhead_Triceps_Extension", candidate_pool["allowed_exercise_ids"])

    def test_shoulder_candidate_pool_keeps_top_three_per_delt_head(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="shoulders",
            sessions=3,
            session_minutes=45,
            experience="intermediate",
        )
        exercises = [
            make_target_exercise("Cable Lateral Raise 1", "Cable_Lateral_Raise_1", "cable", 0.99, ["delts"], []),
            make_target_exercise("Dumbbell Lateral Raise 2", "Dumbbell_Lateral_Raise_2", "dumbbell", 0.98, ["delts"], []),
            make_target_exercise("Seated Side Lateral Raise 3", "Seated_Side_Lateral_Raise_3", "dumbbell", 0.97, ["delts"], []),
            make_target_exercise("One-Arm Side Laterals 4", "One-Arm_Side_Laterals_4", "dumbbell", 0.96, ["delts"], []),
            make_target_exercise("Cable Rear Delt Fly 1", "Cable_Rear_Delt_Fly_1", "cable", 0.95, ["delts"], []),
            make_target_exercise("Reverse Flyes 2", "Reverse_Flyes_2", "dumbbell", 0.94, ["delts"], []),
            make_target_exercise("Face Pull 3", "Face_Pull_3", "cable", 0.93, ["delts"], []),
            make_target_exercise("Band Pull Apart 4", "Band_Pull_Apart_4", "cable", 0.92, ["delts"], []),
            make_target_exercise("Cable Shoulder Press 1", "Cable_Shoulder_Press_1", "cable", 0.91, ["delts"], []),
            make_target_exercise("Dumbbell Shoulder Press 2", "Dumbbell_Shoulder_Press_2", "dumbbell", 0.90, ["delts"], []),
            make_target_exercise("Arnold Press 3", "Arnold_Press_3", "dumbbell", 0.89, ["delts"], []),
            make_target_exercise("Front Cable Raise 4", "Front_Cable_Raise_4", "cable", 0.88, ["delts"], []),
        ]
        candidates = filter_and_score_exercises(request, exercises)
        candidate_pool = build_llm_candidate_pool(request, candidates)
        shoulder_candidates = candidate_pool["by_target"]["delts"]
        by_region = {
            region: [
                item["exercise_id"]
                for item in shoulder_candidates
                if item.get("delt_region") == region
            ]
            for region in ["lateral", "posterior", "anterior"]
        }

        self.assertEqual(len(shoulder_candidates), 9)
        self.assertEqual(len(by_region["lateral"]), 3)
        self.assertEqual(len(by_region["posterior"]), 3)
        self.assertEqual(len(by_region["anterior"]), 3)
        self.assertNotIn("One-Arm_Side_Laterals_4", candidate_pool["allowed_exercise_ids"])
        self.assertNotIn("Band_Pull_Apart_4", candidate_pool["allowed_exercise_ids"])
        self.assertNotIn("Front_Cable_Raise_4", candidate_pool["allowed_exercise_ids"])

    def test_shoulder_markdown_uses_goal_relevant_retrieved_pmid_when_direct_study_missing(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="shoulders",
            sessions=1,
            session_minutes=30,
            equipment="cable",
            experience="intermediate",
        )
        exercises = [
            make_target_exercise("Cable Lateral Raise", "Cable_Lateral_Raise", "cable", 0.90, ["delts"], []),
        ]
        candidates = filter_and_score_exercises(request, exercises)
        findings = [
            {
                "doc_id": "pmid-39593465",
                "pmid": "39593465",
                "title": "Muscle hypertrophy response across four muscles involved in the bench press exercise",
                "publication_year": 2024,
                "evidence_tier": "rct",
                "manual_review_required": False,
                "snippet": "Resistance training increased hypertrophy of the anterior and medial deltoid.",
                "trust_label": "standard",
            }
        ]
        outline = build_protocol_outline(request, candidates, findings)
        markdown = render_protocol_markdown(request, outline, findings, warnings=[])

        self.assertIn("- Shoulders (lateral delt): Cable Lateral Raise - 3x10", markdown)
        self.assertIn("[PMID: 39593465]", markdown)

    def test_llm_plan_validation_rejects_rank_outside_raw_top_three_pool(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="biceps",
            sessions=1,
            session_minutes=45,
            equipment="cable,dumbbell,machine,barbell",
            experience="intermediate",
        )
        exercises = [
            set_muscle_rank(
                make_exercise("Machine Preacher Curls", "Machine_Preacher_Curls", "machine", 0.95, [], False),
                "biceps",
                1,
                10,
            ),
            set_muscle_rank(
                make_exercise("Cable Preacher Curl", "Cable_Preacher_Curl", "cable", 0.94, [], False),
                "biceps",
                2,
                10,
            ),
            set_muscle_rank(
                make_exercise("One Arm Dumbbell Preacher Curl", "One_Arm_Dumbbell_Preacher_Curl", "dumbbell", 0.93, [], False),
                "biceps",
                3,
                10,
            ),
            set_muscle_rank(
                make_exercise("Reverse Barbell Preacher Curls", "Reverse_Barbell_Preacher_Curls", "barbell", 0.92, [], False),
                "biceps",
                6,
                10,
            ),
        ]
        candidates = filter_and_score_exercises(request, exercises)
        candidate_pool = build_llm_candidate_pool(request, candidates)
        plan = {
            "split_summary": "Biceps Focus",
            "sessions": [
                {
                    "session_number": 1,
                    "split_label": "Curl",
                    "focus": "Biceps",
                    "exercises": [
                        {"exercise_id": "Machine_Preacher_Curls", "target_muscle": "biceps"},
                        {"exercise_id": "Cable_Preacher_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Reverse_Barbell_Preacher_Curls", "target_muscle": "biceps"},
                    ],
                }
            ],
            "confidence_notes": [],
        }

        errors = validate_llm_protocol_plan(plan, request, candidate_pool)
        self.assertTrue(any("Unknown or disallowed exercise_id" in error for error in errors))

    def test_exercises_per_session_override_rejects_non_positive_values(self) -> None:
        with self.assertRaises(DemoRequestError):
            normalize_request(
                goal="hypertrophy",
                muscles="biceps",
                sessions=2,
                session_minutes=45,
                exercises_per_session=0,
            )

    def test_resolve_api_key_requires_value(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch("protocol_engine.protocol_demo.load_project_env", return_value=None):
                with self.assertRaises(DemoConfigurationError):
                    resolve_api_key(None)

    def test_load_project_env_reads_dotenv_without_overwriting_existing_env(self) -> None:
        original = PROJECT_ENV_PATH.read_text(encoding="utf-8") if PROJECT_ENV_PATH.exists() else None
        try:
            PROJECT_ENV_PATH.write_text(
                'GEMINI_API_KEY="from-dotenv"\nEXTRA_VALUE=test-value\n',
                encoding="utf-8",
            )
            with patch.dict("os.environ", {"GEMINI_API_KEY": "from-env"}, clear=True):
                load_project_env()
                self.assertEqual(resolve_api_key(None), "from-env")
                self.assertEqual(__import__("os").environ.get("EXTRA_VALUE"), "test-value")
        finally:
            if original is None:
                if PROJECT_ENV_PATH.exists():
                    PROJECT_ENV_PATH.unlink()
            else:
                PROJECT_ENV_PATH.write_text(original, encoding="utf-8")

    def test_filter_and_score_prefers_unreviewed_direct_evidence(self) -> None:
        candidates = filter_and_score_exercises(self.request, self.exercises)
        self.assertEqual(candidates[0]["name"], "Standing Biceps Cable Curl")
        self.assertEqual(candidates[0]["non_reviewed_direct_evidence"], 1)
        self.assertGreater(candidates[0]["final_score"], candidates[-1]["final_score"])
        self.assertNotIn(
            "Full Range-Of-Motion Lat Pulldown",
            [candidate["name"] for candidate in candidates],
        )

    def test_dedupe_collapses_variations(self) -> None:
        candidates = filter_and_score_exercises(self.request, self.exercises)
        deduped = dedupe_candidates(candidates)
        top_names = [candidate["name"] for candidate in deduped]
        self.assertIn("Cable Preacher Curl", top_names)
        preacher_candidate = next(candidate for candidate in deduped if candidate["name"] == "Cable Preacher Curl")
        self.assertIn("Two-Arm Dumbbell Preacher Curl", preacher_candidate["collapsed_variations"])

    def test_prompt_payload_contains_candidate_pool_and_planning_constraints(self) -> None:
        candidates = dedupe_candidates(filter_and_score_exercises(self.request, self.exercises))
        candidate_pool = build_llm_candidate_pool(self.request, candidates)
        payload = build_prompt_payload(
            request=self.request,
            candidate_pool=candidate_pool,
            findings=self.findings,
            warnings=["limited pool"],
        )
        self.assertIn("choose the weekly split", payload["system_prompt"])
        self.assertIn("Return JSON only", payload["system_prompt"])
        self.assertEqual(candidate_pool["per_muscle_limit"], 3)
        self.assertLessEqual(len(candidate_pool["by_target"]["biceps"]), 3)
        self.assertEqual(payload["context"]["constraints"]["min_exercises_per_session"], 3)
        self.assertIn("do not leave a normal session with only one exercise", payload["user_prompt"])
        self.assertIn("candidate_pool", payload["user_prompt"])
        self.assertIn("Cable Preacher Curl", payload["user_prompt"])
        self.assertIn("40082069", payload["user_prompt"])
        self.assertIn("Do not chase exercise variety", payload["user_prompt"])
        self.assertNotIn("protocol_outline", payload["user_prompt"])
        self.assertNotIn("Full Range-Of-Motion Lat Pulldown", payload["user_prompt"])
        # The model gets ordering + prescription levers and the data to use them.
        constraints = payload["context"]["constraints"]
        self.assertIn("prescription_guidance", constraints)
        self.assertIn("ordering_guidance", constraints)
        self.assertIn("volume_guidance", constraints)
        self.assertIn("split_guidance", constraints)
        self.assertIn("compound-first", payload["user_prompt"])
        self.assertIn("sets, reps, and rest_seconds", payload["user_prompt"])
        first_candidate = candidate_pool["by_target"]["biceps"][0]
        self.assertIn("mechanic", first_candidate)
        self.assertIn("force", first_candidate)

    def test_compact_candidates_expose_mechanic_and_force(self) -> None:
        candidates = dedupe_candidates(filter_and_score_exercises(self.request, self.exercises))
        candidate_pool = build_llm_candidate_pool(self.request, candidates)
        for compact in candidate_pool["by_target"]["biceps"]:
            self.assertEqual(compact["mechanic"], "isolation")
            self.assertEqual(compact["force"], "pull")

    def test_llm_prescription_in_bounds_passes_through(self) -> None:
        prescription = normalize_llm_prescription(
            {"sets": 4, "reps": "8-12", "rest_seconds": 120}, "hypertrophy"
        )
        self.assertEqual(
            prescription,
            {"sets": "4", "reps": "8-12", "rest": "120 sec", "display": "4x8-12"},
        )

    def test_llm_prescription_out_of_bounds_is_clamped(self) -> None:
        prescription = normalize_llm_prescription(
            {"sets": 8, "reps": "1-2", "rest_seconds": 600}, "strength"
        )
        self.assertEqual(
            prescription,
            {"sets": "6", "reps": "3", "rest": "300 sec", "display": "6x3"},
        )

    def test_llm_prescription_garbage_falls_back_to_seed(self) -> None:
        self.assertIsNone(
            normalize_llm_prescription({"sets": 3, "reps": "AMRAP"}, "hypertrophy")
        )

    def test_llm_prescription_absent_returns_none(self) -> None:
        self.assertIsNone(normalize_llm_prescription({}, "hypertrophy"))

    def test_llm_prescription_partial_fields_filled_from_seed(self) -> None:
        prescription = normalize_llm_prescription({"sets": 4}, "hypertrophy")
        self.assertEqual(
            prescription,
            {"sets": "4", "reps": "10", "rest": "90 sec", "display": "4x10"},
        )

    def test_llm_plan_prescriptions_flow_into_outline(self) -> None:
        candidates = filter_and_score_exercises(self.request, self.exercises)
        candidate_pool = build_llm_candidate_pool(self.request, candidates)
        candidate_lookup = {
            candidate["exercise_id"]: candidate
            for candidate in candidates
            if candidate["exercise_id"] in candidate_pool["allowed_exercise_ids"]
        }
        plan = {
            "split_summary": "Biceps Focus",
            "sessions": [
                {
                    "session_number": 1,
                    "split_label": "Curl A",
                    "focus": "Biceps",
                    "exercises": [
                        {
                            "exercise_id": "Cable_Preacher_Curl",
                            "target_muscle": "biceps",
                            "sets": 4,
                            "reps": "8-12",
                            "rest_seconds": 120,
                        },
                        {"exercise_id": "Standing_Biceps_Cable_Curl", "target_muscle": "biceps"},
                    ],
                },
            ],
            "confidence_notes": [],
        }
        outline = build_outline_from_llm_plan(
            plan=plan,
            request=self.request,
            candidate_lookup=candidate_lookup,
            findings=self.findings,
            candidate_pool=candidate_pool,
        )
        prescriptions = [
            exercise["prescription"] for exercise in outline["sessions"][0]["exercises"]
        ]
        self.assertEqual(prescriptions[0]["display"], "4x8-12")
        self.assertEqual(prescriptions[0]["rest"], "120 sec")
        # No prescription in the plan -> deterministic seed.
        self.assertEqual(prescriptions[1]["display"], "3x10")

    def test_generation_config_gemini_sets_json_mode_and_timeout(self) -> None:
        self.assertTrue(supports_structured_output("gemini-2.5-flash"))
        config = build_llm_generation_config("gemini-2.5-flash")
        self.assertEqual(config.temperature, 0.4)
        self.assertEqual(config.response_mime_type, "application/json")
        self.assertIsNotNone(config.response_schema)
        self.assertEqual(config.http_options.timeout, 90_000)

    def test_generation_config_gemma_skips_response_schema(self) -> None:
        self.assertFalse(supports_structured_output("gemma-4-26b-a4b-it"))
        config = build_llm_generation_config("gemma-4-26b-a4b-it")
        self.assertEqual(config.temperature, 0.4)
        self.assertIsNone(config.response_mime_type)
        self.assertIsNone(config.response_schema)
        # Slow gemma-family models get a single-attempt-sized timeout.
        self.assertEqual(config.http_options.timeout, 200_000)

    def test_llm_pool_offers_best_eligible_when_global_top_ranks_filtered_out(self) -> None:
        # Regression: the global top-3 for a muscle can all be excluded by the
        # request's equipment filter (e.g. top biceps curls are barbell-only).
        # The pool must then contain the best eligible candidates, not be empty.
        request = normalize_request(
            goal="hypertrophy",
            muscles="biceps",
            sessions=2,
            session_minutes=30,
            equipment="cable",
            experience="beginner",
        )
        exercises = []
        for index, (name, exercise_id, equipment) in enumerate(
            [
                ("Barbell Preacher Curl", "Barbell_Preacher_Curl", "barbell"),
                ("Barbell Reverse Curl", "Barbell_Reverse_Curl", "barbell"),
                ("Barbell Drag Curl", "Barbell_Drag_Curl", "barbell"),
                ("Cable Preacher Curl", "Cable_Preacher_Curl", "cable"),
                ("Cable Hammer Curl", "Cable_Hammer_Curl", "cable"),
            ]
        ):
            exercise = make_exercise(name, exercise_id, equipment, 0.95 - index * 0.01, [], False)
            exercise["muscle_group_rankings"] = {
                "hypertrophy": {"biceps": {"rank": index + 1, "out_of": 5}},
                "strength": {},
            }
            exercises.append(exercise)

        candidates = dedupe_candidates(filter_and_score_exercises(request, exercises))
        pool = build_llm_candidate_pool(request, candidates)
        names = [c["name"] for c in pool["by_target"]["biceps"]]
        self.assertEqual(names, ["Cable Preacher Curl", "Cable Hammer Curl"])
        self.assertEqual(len(pool["allowed_exercise_ids"]), 2)

    def test_plan_response_schema_enum_locks_ids_and_muscles(self) -> None:
        schema = build_plan_response_schema(
            allowed_exercise_ids=["0025", "0885"],
            allowed_muscles=["biceps"],
        )
        exercise_props = schema["properties"]["sessions"]["items"]["properties"][
            "exercises"
        ]["items"]["properties"]
        self.assertEqual(exercise_props["exercise_id"]["enum"], ["0025", "0885"])
        self.assertEqual(exercise_props["target_muscle"]["enum"], ["biceps"])
        # The shared base schema must stay un-mutated between requests.
        from protocol_engine.protocol_demo import PLAN_RESPONSE_SCHEMA
        base_props = PLAN_RESPONSE_SCHEMA["properties"]["sessions"]["items"][
            "properties"
        ]["exercises"]["items"]["properties"]
        self.assertNotIn("enum", base_props["exercise_id"])

    @staticmethod
    def make_vector_stub(rows: list[tuple[str, str, float, str]]):
        """rows: (doc_id, pmid, distance, snippet) returned for every query."""

        class StubCollection:
            def query(self, query_texts, n_results, include, where=None):
                return {
                    "documents": [[snippet for _, _, _, snippet in rows]],
                    "metadatas": [
                        [
                            {
                                "doc_id": doc_id,
                                "pmid": pmid,
                                "publication_year": 2023,
                                "evidence_tier": "rct",
                                "retrieval_weight": 0.7,
                                "manual_review_required": False,
                                "topic_clusters": "",
                            }
                            for doc_id, pmid, _, _ in rows
                        ]
                    ],
                    "distances": [[distance for _, _, distance, _ in rows]],
                }

        return StubCollection()

    def test_query_findings_rejects_far_matches_and_returns_empty(self) -> None:
        stub = self.make_vector_stub(
            [
                ("doc-1", "111", 0.62, "biceps curl hypertrophy trial in trained men"),
                ("doc-2", "222", 0.75, "elbow flexor training with cable curls"),
            ]
        )
        science_payload = {"documents": [{"doc_id": "doc-1"}, {"doc_id": "doc-2"}]}
        candidates = filter_and_score_exercises(self.request, self.exercises)
        with patch("protocol_engine.protocol_demo.get_vector_collection", return_value=stub):
            findings = query_findings(self.request, candidates, science_payload)
        self.assertEqual(findings, [])

    def test_query_findings_keeps_near_relevant_matches(self) -> None:
        stub = self.make_vector_stub(
            [
                ("doc-1", "111", 0.31, "biceps curl hypertrophy trial in trained men"),
                ("doc-2", "222", 0.74, "off-topic endurance swimming study"),
            ]
        )
        science_payload = {
            "documents": [
                {"doc_id": "doc-1", "title": "Biceps curl hypertrophy trial"},
                {"doc_id": "doc-2", "title": "Swimming endurance"},
            ]
        }
        candidates = filter_and_score_exercises(self.request, self.exercises)
        with patch("protocol_engine.protocol_demo.get_vector_collection", return_value=stub):
            findings = query_findings(self.request, candidates, science_payload)
        self.assertEqual([finding["pmid"] for finding in findings], ["111"])

    def test_render_markdown_with_no_findings_is_valid(self) -> None:
        candidates = dedupe_candidates(filter_and_score_exercises(self.request, self.exercises))
        outline = build_protocol_outline(self.request, candidates, [])
        markdown = render_protocol_markdown(
            request=self.request,
            outline=outline,
            findings=[],
            warnings=[],
        )
        # Direct per-exercise studies still populate the appendix without
        # semantic findings, and the markdown stays valid.
        self.assertIn("## Evidence Appendix", markdown)
        self.assertEqual(validate_generated_markdown(markdown, outline, []), [])

        # With no direct evidence either, the appendix says so honestly.
        for session in outline["sessions"]:
            for exercise in session["exercises"]:
                exercise["reference_evidence"] = []
                exercise["reference_pmids"] = []
        bare_markdown = render_protocol_markdown(
            request=self.request,
            outline=outline,
            findings=[],
            warnings=[],
        )
        self.assertIn("No strongly matching studies were found", bare_markdown)
        self.assertEqual(validate_generated_markdown(bare_markdown, outline, []), [])

    def test_render_and_validate_markdown(self) -> None:
        candidates = dedupe_candidates(filter_and_score_exercises(self.request, self.exercises))
        outline = build_protocol_outline(self.request, candidates, self.findings)
        markdown = render_protocol_markdown(
            request=self.request,
            outline=outline,
            findings=self.findings,
            warnings=["limited pool"],
            used_fallback=True,
        )
        self.assertIn("## Evidence Appendix", markdown)
        self.assertIn("- Biceps: Cable Preacher Curl - 3x10", markdown)
        self.assertNotIn("Session length:", markdown)
        self.assertEqual(validate_generated_markdown(markdown, outline, self.findings), [])

    def test_valid_llm_json_plan_builds_renderable_outline(self) -> None:
        candidates = filter_and_score_exercises(self.request, self.exercises)
        candidate_pool = build_llm_candidate_pool(self.request, candidates)
        candidate_lookup = {
            candidate["exercise_id"]: candidate
            for candidate in candidates
            if candidate["exercise_id"] in candidate_pool["allowed_exercise_ids"]
        }
        plan = {
            "split_summary": "Biceps Focus",
            "sessions": [
                {
                    "session_number": 1,
                    "split_label": "Curl A",
                    "focus": "Preacher curl emphasis",
                    "exercises": [
                        {"exercise_id": "Cable_Preacher_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Standing_Biceps_Cable_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Two-Arm_Dumbbell_Preacher_Curl", "target_muscle": "biceps"},
                    ],
                },
                {
                    "session_number": 2,
                    "split_label": "Curl B",
                    "focus": "Cable curl emphasis",
                    "exercises": [
                        {"exercise_id": "Standing_Biceps_Cable_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Cable_Preacher_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Two-Arm_Dumbbell_Preacher_Curl", "target_muscle": "biceps"},
                    ],
                },
            ],
            "confidence_notes": ["Used two biceps exposures for the requested week."],
        }

        self.assertEqual(validate_llm_protocol_plan(plan, self.request, candidate_pool), [])
        outline = build_outline_from_llm_plan(
            plan=plan,
            request=self.request,
            candidate_lookup=candidate_lookup,
            findings=self.findings,
            candidate_pool=candidate_pool,
        )
        markdown = render_protocol_markdown(
            request=self.request,
            outline=outline,
            findings=self.findings,
            warnings=outline["confidence_notes"],
        )

        self.assertIn("### Session 1 - Curl A", markdown)
        self.assertIn("- Biceps: Cable Preacher Curl - 3x10", markdown)
        self.assertIn("Used two biceps exposures", markdown)

    def test_llm_plan_validation_rejects_unknown_exercise(self) -> None:
        candidates = dedupe_candidates(filter_and_score_exercises(self.request, self.exercises))
        candidate_pool = build_llm_candidate_pool(self.request, candidates)
        plan = {
            "split_summary": "Biceps Focus",
            "sessions": [
                {
                    "session_number": 1,
                    "split_label": "Curl A",
                    "focus": "Biceps",
                    "exercises": [
                        {"exercise_id": "Invented_Curl", "target_muscle": "biceps"}
                    ],
                },
                {
                    "session_number": 2,
                    "split_label": "Curl B",
                    "focus": "Biceps",
                    "exercises": [
                        {"exercise_id": "Cable_Preacher_Curl", "target_muscle": "biceps"}
                    ],
                },
            ],
            "confidence_notes": [],
        }

        errors = validate_llm_protocol_plan(plan, self.request, candidate_pool)
        self.assertTrue(any("Unknown or disallowed exercise_id" in error for error in errors))

    def test_llm_plan_validation_rejects_underfilled_session(self) -> None:
        candidates = filter_and_score_exercises(self.request, self.exercises)
        candidate_pool = build_llm_candidate_pool(self.request, candidates)
        plan = {
            "split_summary": "Sparse Biceps",
            "sessions": [
                {
                    "session_number": 1,
                    "split_label": "Curl A",
                    "focus": "Biceps",
                    "exercises": [
                        {"exercise_id": "Cable_Preacher_Curl", "target_muscle": "biceps"}
                    ],
                },
                {
                    "session_number": 2,
                    "split_label": "Curl B",
                    "focus": "Biceps",
                    "exercises": [
                        {"exercise_id": "Standing_Biceps_Cable_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Cable_Preacher_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Two-Arm_Dumbbell_Preacher_Curl", "target_muscle": "biceps"},
                    ],
                },
            ],
            "confidence_notes": [],
        }

        errors = validate_llm_protocol_plan(plan, self.request, candidate_pool)
        self.assertTrue(any("Session 1 has 1 exercise(s); min is 3" in error for error in errors))

    def test_llm_plan_validation_rejects_missing_requested_muscle(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="chest,biceps",
            sessions=2,
            session_minutes=45,
            experience="intermediate",
        )
        exercises = [
            make_target_exercise("Bench Press", "Bench_Press", "barbell", 0.95, ["chest"], []),
            make_target_exercise("Cable Curl", "Cable_Curl", "cable", 0.93, ["biceps"], []),
        ]
        candidates = dedupe_candidates(filter_and_score_exercises(request, exercises))
        candidate_pool = build_llm_candidate_pool(request, candidates)
        plan = {
            "split_summary": "Chest Only",
            "sessions": [
                {
                    "session_number": 1,
                    "split_label": "Push",
                    "focus": "Chest",
                    "exercises": [{"exercise_id": "Bench_Press", "target_muscle": "chest"}],
                },
                {
                    "session_number": 2,
                    "split_label": "Push",
                    "focus": "Chest",
                    "exercises": [{"exercise_id": "Bench_Press", "target_muscle": "chest"}],
                },
            ],
            "confidence_notes": [],
        }

        errors = validate_llm_protocol_plan(plan, request, candidate_pool)
        self.assertTrue(any("Requested target muscle was not scheduled: biceps" in error for error in errors))

    def test_llm_plan_validation_rejects_triceps_every_session(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="chest,triceps,biceps,shoulders",
            sessions=4,
            session_minutes=45,
            experience="intermediate",
        )
        exercises = [
            make_target_exercise("Bench Press", "Bench_Press", "barbell", 0.95, ["chest"], ["triceps"]),
            make_target_exercise("Cable Curl", "Cable_Curl", "cable", 0.93, ["biceps"], []),
            make_target_exercise("Triceps Pushdown", "Triceps_Pushdown", "cable", 0.94, ["triceps"], []),
            make_target_exercise("Cable Lateral Raise", "Cable_Lateral_Raise", "cable", 0.88, ["delts"], []),
        ]
        candidates = dedupe_candidates(filter_and_score_exercises(request, exercises))
        candidate_pool = build_llm_candidate_pool(request, candidates)
        plan = {
            "split_summary": "Bad Full Triceps",
            "sessions": [
                {
                    "session_number": session_number,
                    "split_label": "Upper",
                    "focus": "Upper",
                    "exercises": [
                        {"exercise_id": "Triceps_Pushdown", "target_muscle": "triceps"},
                        {"exercise_id": "Bench_Press", "target_muscle": "chest"},
                        {"exercise_id": "Cable_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Cable_Lateral_Raise", "target_muscle": "delts"},
                    ],
                }
                for session_number in range(1, 5)
            ],
            "confidence_notes": [],
        }

        errors = validate_llm_protocol_plan(plan, request, candidate_pool)
        self.assertTrue(any("Target muscle triceps appears in every session" in error for error in errors))

    def test_extract_json_object_rejects_invalid_json(self) -> None:
        parsed, errors = extract_json_object("not json")

        self.assertIsNone(parsed)
        self.assertTrue(errors)

    def test_run_protocol_demo_uses_valid_llm_json_plan(self) -> None:
        catalog_payload = {
            "taxonomies": {
                "muscle_groups": ["biceps", "forearms"],
                "equipment": ["cable", "dumbbell"],
                "joints": ["neck", "shoulder", "elbow", "wrist", "spine", "hip", "knee", "ankle"],
            },
            "exercises": self.exercises,
        }
        gemma_plan = {
            "split_summary": "Biceps Focus",
            "sessions": [
                {
                    "session_number": 1,
                    "split_label": "Preacher",
                    "focus": "Preacher curl emphasis",
                    "exercises": [
                        {"exercise_id": "Cable_Preacher_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Standing_Biceps_Cable_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Two-Arm_Dumbbell_Preacher_Curl", "target_muscle": "biceps"},
                    ],
                },
                {
                    "session_number": 2,
                    "split_label": "Cable",
                    "focus": "Cable curl emphasis",
                    "exercises": [
                        {"exercise_id": "Standing_Biceps_Cable_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Cable_Preacher_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Two-Arm_Dumbbell_Preacher_Curl", "target_muscle": "biceps"},
                    ],
                },
            ],
            "confidence_notes": ["LLM selected alternating biceps emphases."],
        }

        with patch("protocol_engine.protocol_demo.load_catalog", return_value=catalog_payload), \
            patch("protocol_engine.protocol_demo.load_science_corpus", return_value={"documents": []}), \
            patch("protocol_engine.protocol_demo.query_findings", return_value=self.findings), \
            patch("protocol_engine.protocol_demo.resolve_api_key", return_value="test-key"), \
            patch("protocol_engine.protocol_demo.generate_with_gemma", return_value=json.dumps(gemma_plan)):
            result = run_protocol_demo(request=self.request)

        self.assertFalse(result["debug_payload"]["used_deterministic_fallback"])
        self.assertEqual(result["debug_payload"]["protocol_outline"]["planner"], "llm")
        self.assertIn("### Session 1 - Preacher", result["markdown_text"])
        self.assertIn("- Biceps: Cable Preacher Curl - 3x10", result["markdown_text"])
        self.assertIn("LLM selected alternating biceps emphases.", result["markdown_text"])

    def test_run_protocol_demo_api_error_escalates_to_backup_model(self) -> None:
        catalog_payload = {
            "taxonomies": {
                "muscle_groups": ["biceps", "forearms"],
                "equipment": ["cable", "dumbbell"],
                "joints": ["neck", "shoulder", "elbow", "wrist", "spine", "hip", "knee", "ankle"],
            },
            "exercises": self.exercises,
        }
        backup_plan = {
            "split_summary": "Biceps Focus",
            "sessions": [
                {
                    "session_number": 1,
                    "split_label": "Preacher",
                    "focus": "Preacher curl emphasis",
                    "exercises": [
                        {"exercise_id": "Cable_Preacher_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Standing_Biceps_Cable_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Two-Arm_Dumbbell_Preacher_Curl", "target_muscle": "biceps"},
                    ],
                },
                {
                    "session_number": 2,
                    "split_label": "Cable",
                    "focus": "Cable curl emphasis",
                    "exercises": [
                        {"exercise_id": "Standing_Biceps_Cable_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Cable_Preacher_Curl", "target_muscle": "biceps"},
                        {"exercise_id": "Two-Arm_Dumbbell_Preacher_Curl", "target_muscle": "biceps"},
                    ],
                },
            ],
            "confidence_notes": [],
        }

        with patch("protocol_engine.protocol_demo.load_catalog", return_value=catalog_payload), \
            patch("protocol_engine.protocol_demo.load_science_corpus", return_value={"documents": []}), \
            patch("protocol_engine.protocol_demo.query_findings", return_value=self.findings), \
            patch("protocol_engine.protocol_demo.resolve_api_key", return_value="test-key"), \
            patch(
                "protocol_engine.protocol_demo.generate_with_gemma",
                side_effect=[Exception("429 RESOURCE_EXHAUSTED"), json.dumps(backup_plan)],
            ) as mock_generate:
            result = run_protocol_demo(
                request=self.request,
                model="gemini-3.5-flash",
                fallback_model="gemma-4-31b-it",
            )

        payload = result["debug_payload"]
        self.assertFalse(payload["used_deterministic_fallback"])
        self.assertEqual(payload["protocol_outline"]["planner"], "llm")
        self.assertEqual(payload["planner_model"], "gemma-4-31b-it")
        models_called = [call.args[1] for call in mock_generate.call_args_list]
        self.assertEqual(models_called, ["gemini-3.5-flash", "gemma-4-31b-it"])
        self.assertTrue(
            any("backup model (gemma-4-31b-it)" in w for w in payload["warnings"])
        )

    def test_run_protocol_demo_api_error_on_both_models_uses_deterministic(self) -> None:
        catalog_payload = {
            "taxonomies": {
                "muscle_groups": ["biceps", "forearms"],
                "equipment": ["cable", "dumbbell"],
                "joints": ["neck", "shoulder", "elbow", "wrist", "spine", "hip", "knee", "ankle"],
            },
            "exercises": self.exercises,
        }
        with patch("protocol_engine.protocol_demo.load_catalog", return_value=catalog_payload), \
            patch("protocol_engine.protocol_demo.load_science_corpus", return_value={"documents": []}), \
            patch("protocol_engine.protocol_demo.query_findings", return_value=self.findings), \
            patch("protocol_engine.protocol_demo.resolve_api_key", return_value="test-key"), \
            patch(
                "protocol_engine.protocol_demo.generate_with_gemma",
                side_effect=[Exception("429"), Exception("503")],
            ) as mock_generate:
            result = run_protocol_demo(
                request=self.request,
                model="gemini-3.5-flash",
                fallback_model="gemma-4-31b-it",
            )

        payload = result["debug_payload"]
        self.assertTrue(payload["used_deterministic_fallback"])
        self.assertEqual(len(mock_generate.call_args_list), 2)
        self.assertTrue(
            any("temporarily unavailable" in w for w in payload["warnings"])
        )

    def test_run_protocol_demo_walks_comma_separated_fallback_chain(self) -> None:
        catalog_payload = {
            "taxonomies": {
                "muscle_groups": ["biceps", "forearms"],
                "equipment": ["cable", "dumbbell"],
                "joints": ["neck", "shoulder", "elbow", "wrist", "spine", "hip", "knee", "ankle"],
            },
            "exercises": self.exercises,
        }
        with patch("protocol_engine.protocol_demo.load_catalog", return_value=catalog_payload), \
            patch("protocol_engine.protocol_demo.load_science_corpus", return_value={"documents": []}), \
            patch("protocol_engine.protocol_demo.query_findings", return_value=self.findings), \
            patch("protocol_engine.protocol_demo.resolve_api_key", return_value="test-key"), \
            patch(
                "protocol_engine.protocol_demo.generate_with_gemma",
                side_effect=[Exception("429"), Exception("500"), Exception("500")],
            ) as mock_generate:
            result = run_protocol_demo(
                request=self.request,
                model="gemini-3.5-flash",
                fallback_model="gemma-4-31b-it, gemma-4-26b-a4b-it",
            )

        models_called = [call.args[1] for call in mock_generate.call_args_list]
        self.assertEqual(
            models_called,
            ["gemini-3.5-flash", "gemma-4-31b-it", "gemma-4-26b-a4b-it"],
        )
        self.assertTrue(result["debug_payload"]["used_deterministic_fallback"])

    def test_run_protocol_demo_retries_invalid_json_then_falls_back(self) -> None:
        catalog_payload = {
            "taxonomies": {
                "muscle_groups": ["biceps", "forearms"],
                "equipment": ["cable", "dumbbell"],
                "joints": ["neck", "shoulder", "elbow", "wrist", "spine", "hip", "knee", "ankle"],
            },
            "exercises": self.exercises,
        }

        with patch("protocol_engine.protocol_demo.load_catalog", return_value=catalog_payload), \
            patch("protocol_engine.protocol_demo.load_science_corpus", return_value={"documents": []}), \
            patch("protocol_engine.protocol_demo.query_findings", return_value=self.findings), \
            patch("protocol_engine.protocol_demo.resolve_api_key", return_value="test-key"), \
            patch("protocol_engine.protocol_demo.generate_with_gemma", side_effect=["not json", "still not json"]):
            result = run_protocol_demo(request=self.request)

        self.assertTrue(result["debug_payload"]["used_deterministic_fallback"])
        self.assertEqual(len(result["debug_payload"]["raw_response_attempts"]), 2)
        self.assertTrue(result["debug_payload"]["validation_errors"])
        self.assertIn("Gemma output did not pass the local guardrails", result["markdown_text"])

    def test_single_muscle_outline_repeats_top_pool(self) -> None:
        candidates = dedupe_candidates(filter_and_score_exercises(self.request, self.exercises))
        outline = build_protocol_outline(self.request, candidates, self.findings)
        session_1 = [exercise["name"] for exercise in outline["sessions"][0]["exercises"]]
        session_2 = [exercise["name"] for exercise in outline["sessions"][1]["exercises"]]
        self.assertEqual(session_1, session_2)
        self.assertEqual(len(session_1), 3)
        self.assertEqual(
            session_1,
            ["Standing Biceps Cable Curl", "Cable Preacher Curl", "Incline Dumbbell Curl"],
        )

    def test_multi_muscle_outline_balances_selected_pool(self) -> None:
        multi_request = normalize_request(
            goal="hypertrophy",
            muscles="chest,lats,delts,triceps,biceps",
            sessions=4,
            session_minutes=45,
            experience="intermediate",
        )
        exercises = [
            make_exercise("Smith Machine Bench Press", "Smith_Machine_Bench_Press", "machine", 0.95, [], False),
            make_exercise("Incline Cable Flye", "Incline_Cable_Flye", "cable", 0.93, [], False),
            make_exercise("Bent Over Barbell Row", "Bent_Over_Barbell_Row", "barbell", 0.92, [], False),
            make_exercise("Face Pull", "Face_Pull", "cable", 0.91, [], False),
            make_exercise("Cable Pushdown", "Cable_Pushdown", "cable", 0.90, [], False),
            make_exercise("Standing Biceps Cable Curl", "Standing_Biceps_Cable_Curl", "cable", 0.89, [], False),
        ]
        # Re-map the fixtures to different primary muscles while keeping the same shape.
        exercises[0]["muscles"] = {"primary": ["chest"], "secondary": ["triceps"], "all": ["chest", "triceps"]}
        exercises[0]["muscle_group_rankings"] = {"hypertrophy": {"chest": {"rank": 1, "out_of": 20}}, "strength": {}}
        exercises[1]["muscles"] = {"primary": ["chest"], "secondary": ["delts"], "all": ["chest", "delts"]}
        exercises[1]["muscle_group_rankings"] = {"hypertrophy": {"chest": {"rank": 2, "out_of": 20}}, "strength": {}}
        exercises[2]["muscles"] = {"primary": ["lats"], "secondary": ["biceps"], "all": ["lats", "biceps"]}
        exercises[2]["muscle_group_rankings"] = {"hypertrophy": {"lats": {"rank": 1, "out_of": 20}}, "strength": {}}
        exercises[3]["muscles"] = {"primary": ["delts"], "secondary": ["lats"], "all": ["delts", "lats"]}
        exercises[3]["muscle_group_rankings"] = {"hypertrophy": {"delts": {"rank": 1, "out_of": 20}}, "strength": {}}
        exercises[4]["muscles"] = {"primary": ["triceps"], "secondary": ["chest"], "all": ["triceps", "chest"]}
        exercises[4]["muscle_group_rankings"] = {"hypertrophy": {"triceps": {"rank": 1, "out_of": 20}}, "strength": {}}
        exercises[5]["muscles"] = {"primary": ["biceps"], "secondary": [], "all": ["biceps"]}
        exercises[5]["muscle_group_rankings"] = {"hypertrophy": {"biceps": {"rank": 1, "out_of": 20}}, "strength": {}}

        candidates = dedupe_candidates(filter_and_score_exercises(multi_request, exercises))
        outline = build_protocol_outline(multi_request, candidates, [])
        all_selected_names = [
            exercise["name"]
            for session in outline["sessions"]
            for exercise in session["exercises"]
        ]
        all_target_muscles = {
            exercise["target_muscle"]
            for session in outline["sessions"]
            for exercise in session["exercises"]
        }
        self.assertIn("Bent Over Barbell Row", all_selected_names)
        self.assertIn("Cable Pushdown", all_selected_names)
        self.assertIn("Standing Biceps Cable Curl", all_selected_names)
        self.assertEqual(
            all_target_muscles,
            {"biceps", "chest", "delts", "lats", "triceps"},
        )
        self.assertLessEqual(
            sum("Bench" in name or "Flye" in name for name in outline["sessions"][0]["exercises"]),
            2,
        )

    def test_multi_muscle_outline_is_not_allowed_to_drop_targets_for_short_sessions(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="chest,triceps,biceps,shoulders",
            sessions=4,
            session_minutes=20,
            equipment="barbell,dumbbell,cable",
            experience="intermediate",
        )
        exercises = [
            make_target_exercise("Bench Press", "Bench_Press", "barbell", 0.95, ["chest"], ["triceps"]),
            make_target_exercise("Cable Pushdown", "Cable_Pushdown", "cable", 0.94, ["triceps"], []),
            make_target_exercise("Cable Curl", "Cable_Curl", "cable", 0.93, ["biceps"], []),
            make_target_exercise("Cable Shoulder Press", "Cable_Shoulder_Press", "cable", 0.70, ["delts"], []),
        ]

        candidates = dedupe_candidates(filter_and_score_exercises(request, exercises))
        outline = build_protocol_outline(request, candidates, [])
        selected_targets = {
            exercise["target_muscle"]
            for session in outline["sessions"]
            for exercise in session["exercises"]
        }

        session_targets = [
            {exercise["target_muscle"] for exercise in session["exercises"]}
            for session in outline["sessions"]
        ]
        self.assertEqual(outline["exercises_per_session"], 3)
        self.assertEqual(selected_targets, {"biceps", "chest", "delts", "triceps"})
        self.assertTrue(any(targets != selected_targets for targets in session_targets))

    def test_shoulder_outline_covers_delt_regions(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="shoulders",
            sessions=2,
            session_minutes=45,
            equipment="cable,dumbbell",
            experience="intermediate",
        )
        exercises = [
            make_target_exercise(
                "Alternating Cable Shoulder Press",
                "Alternating_Cable_Shoulder_Press",
                "cable",
                0.96,
                ["delts"],
                ["triceps"],
                mechanic="compound",
            ),
            make_target_exercise(
                "Cable Shoulder Press",
                "Cable_Shoulder_Press",
                "cable",
                0.95,
                ["delts"],
                ["triceps"],
                mechanic="compound",
            ),
            make_target_exercise(
                "Cable Seated Lateral Raise",
                "Cable_Seated_Lateral_Raise",
                "cable",
                0.88,
                ["delts"],
                [],
            ),
            make_target_exercise(
                "Cable Rear Delt Fly",
                "Cable_Rear_Delt_Fly",
                "cable",
                0.87,
                ["delts"],
                [],
            ),
        ]

        candidates = dedupe_candidates(filter_and_score_exercises(request, exercises))
        outline = build_protocol_outline(request, candidates, [])
        labels = {
            exercise["target_label"]
            for session in outline["sessions"]
            for exercise in session["exercises"]
        }
        selected_names = [
            exercise["name"]
            for session in outline["sessions"]
            for exercise in session["exercises"]
        ]

        self.assertIn("Shoulders (anterior delt)", labels)
        self.assertIn("Shoulders (lateral delt)", labels)
        self.assertIn("Shoulders (rear delt)", labels)
        self.assertIn("Cable Shoulder Press", selected_names)
        self.assertNotIn("Alternating Cable Shoulder Press", selected_names)

    def test_auto_upper_split_does_not_schedule_triceps_every_session(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="chest,triceps,biceps,shoulders",
            sessions=4,
            session_minutes=45,
            experience="intermediate",
        )
        exercises = [
            make_target_exercise("Bench Press", "Bench_Press", "barbell", 0.95, ["chest"], ["triceps"]),
            make_target_exercise("Incline Bench Press", "Incline_Bench_Press", "barbell", 0.94, ["chest"], ["triceps"]),
            make_target_exercise("Overhead Triceps Extension", "Overhead_Triceps_Extension", "cable", 0.96, ["triceps"], []),
            make_target_exercise("Triceps Pushdown", "Triceps_Pushdown", "cable", 0.90, ["triceps"], []),
            make_target_exercise("Cable Preacher Curl", "Cable_Preacher_Curl", "cable", 0.93, ["biceps"], []),
            make_target_exercise("Incline Dumbbell Curl", "Incline_Dumbbell_Curl", "dumbbell", 0.89, ["biceps"], []),
            make_target_exercise("Cable Lateral Raise", "Cable_Lateral_Raise", "cable", 0.88, ["delts"], []),
            make_target_exercise("Cable Rear Delt Fly", "Cable_Rear_Delt_Fly", "cable", 0.87, ["delts"], []),
            make_target_exercise("Shoulder Press", "Shoulder_Press", "dumbbell", 0.84, ["delts"], ["triceps"], mechanic="compound"),
        ]

        outline = build_protocol_outline(
            request,
            dedupe_candidates(filter_and_score_exercises(request, exercises)),
            [],
        )
        triceps_sessions = [
            session["split_label"]
            for session in outline["sessions"]
            if any(exercise["target_muscle"] == "triceps" for exercise in session["exercises"])
        ]
        biceps_sessions = [
            session["split_label"]
            for session in outline["sessions"]
            if any(exercise["target_muscle"] == "biceps" for exercise in session["exercises"])
        ]

        self.assertEqual(triceps_sessions, ["Push", "Push"])
        self.assertEqual(biceps_sessions, ["Pull/Rear Delts", "Pull/Rear Delts"])

    def test_shoulder_region_rank_display_includes_region_and_overall_rank(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="shoulders",
            sessions=1,
            session_minutes=45,
            equipment="cable,dumbbell",
            experience="intermediate",
        )
        exercises = [
            make_target_exercise("Cable Rear Delt Fly", "Cable_Rear_Delt_Fly", "cable", 0.87, ["delts"], []),
            make_target_exercise("Reverse Flyes", "Reverse_Flyes", "dumbbell", 0.86, ["delts"], []),
            make_target_exercise("Cable Lateral Raise", "Cable_Lateral_Raise", "cable", 0.88, ["delts"], []),
            make_target_exercise("Shoulder Press", "Shoulder_Press", "dumbbell", 0.84, ["delts"], ["triceps"], mechanic="compound"),
        ]

        outline = build_protocol_outline(
            request,
            dedupe_candidates(filter_and_score_exercises(request, exercises)),
            [],
        )
        rank_displays = [
            exercise["rank_display"]
            for session in outline["sessions"]
            for exercise in session["exercises"]
            if exercise["target_label"] == "Shoulders (rear delt)"
        ]

        self.assertTrue(rank_displays)
        self.assertIn("rear delt", rank_displays[0])
        self.assertIn("shoulders", rank_displays[0])

    def test_triceps_hypertrophy_prefers_overhead_extension_over_press_evidence(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="triceps",
            sessions=2,
            session_minutes=45,
            equipment="barbell,cable",
            experience="intermediate",
        )
        exercises = [
            make_target_exercise(
                name="Bench Press - Powerlifting",
                exercise_id="Bench_Press_-_Powerlifting",
                equipment="barbell",
                ranking_score=0.8794,
                primary_muscles=["triceps"],
                secondary_muscles=["chest", "delts"],
                mechanic="compound",
                direct_studies=[
                    {
                        "pmid": "39593465",
                        "title": "Muscle hypertrophy response across four muscles involved in the bench press exercise",
                        "publication_year": 2024,
                        "evidence_tier": "rct",
                        "manual_review_required": False,
                        "study_summary": "Bench press training increased pectoralis major thickness.",
                        "matched_alias": "bench press",
                    }
                ],
            ),
            make_target_exercise(
                name="Cable Rope Overhead Triceps Extension",
                exercise_id="Cable_Rope_Overhead_Triceps_Extension",
                equipment="cable",
                ranking_score=0.8837,
                primary_muscles=["triceps"],
                secondary_muscles=[],
                direct_studies=[
                    {
                        "pmid": "35819335",
                        "title": "Triceps brachii hypertrophy is substantially greater after elbow extension training performed in the overhead versus neutral arm position.",
                        "publication_year": 2023,
                        "evidence_tier": "controlled_trial",
                        "manual_review_required": False,
                        "study_summary": "Overhead elbow extension produced greater triceps hypertrophy than neutral arm extension.",
                        "matched_alias": "overhead triceps extension",
                    }
                ],
                instructions=[
                    "Position your hands behind your head with your elbows pointing up.",
                    "Extend through the elbow while keeping the upper arm in position.",
                ],
            ),
            make_target_exercise(
                name="Triceps Pushdown - Rope Attachment",
                exercise_id="Triceps_Pushdown_-_Rope_Attachment",
                equipment="cable",
                ranking_score=0.8345,
                primary_muscles=["triceps"],
                secondary_muscles=[],
            ),
        ]

        candidates = filter_and_score_exercises(request, exercises)

        self.assertEqual(candidates[0]["name"], "Cable Rope Overhead Triceps Extension")
        self.assertEqual(candidates[0]["non_reviewed_direct_evidence"], 1)
        bench_candidate = next(
            candidate for candidate in candidates if candidate["name"] == "Bench Press - Powerlifting"
        )
        self.assertEqual(bench_candidate["non_reviewed_direct_evidence"], 0)

    def test_catalog_corrects_plain_bench_press_primary_muscle(self) -> None:
        primary, secondary = apply_muscle_corrections(
            "Bench Press - Powerlifting",
            primary_muscles=["triceps"],
            secondary_muscles=["chest", "delts"],
        )

        self.assertIn("chest", primary)
        self.assertNotIn("triceps", primary)
        self.assertIn("triceps", secondary)

    def test_catalog_aliases_do_not_link_nested_equipment_as_exercise(self) -> None:
        aliases = get_aliases(
            "Calf Press On The Leg Press Machine",
            "Calf_Press_On_The_Leg_Press_Machine",
        )

        self.assertIn("calf press", aliases)
        self.assertNotIn("leg press", aliases)
        self.assertNotIn("smith machine", get_aliases("Smith Machine Bench Press", "Smith_Machine_Bench_Press"))
        self.assertNotIn(
            "bench press",
            get_aliases("Close-Grip Barbell Bench Press", "Close-Grip_Barbell_Bench_Press"),
        )

    def test_catalog_skips_resistance_evidence_for_non_resistance_categories(self) -> None:
        self.assertTrue(is_resistance_evidence_eligible("strength"))
        self.assertFalse(is_resistance_evidence_eligible("stretching"))
        self.assertFalse(is_resistance_evidence_eligible("cardio"))

    def test_catalog_goal_evidence_filter_ignores_off_goal_papers(self) -> None:
        studies = [
            {
                "title": "Bench press inter-set rest strategy",
                "study_summary": "Compared fixed and adjustable rest intervals.",
                "measurement_method": ["Performance"],
            },
            {
                "title": "Bench press acute oxygenation response",
                "study_summary": "Measured muscle oxygenation during a single exercise session.",
                "measurement_method": ["Imaging"],
            },
            {
                "title": "Bench press hypertrophy response",
                "study_summary": "Measured pectoralis muscle thickness and hypertrophy.",
                "measurement_method": ["Imaging", "Hypertrophy"],
            },
        ]

        hypertrophy_studies = filter_studies_for_goal(studies, "hypertrophy")
        self.assertEqual(len(hypertrophy_studies), 1)
        self.assertEqual(hypertrophy_studies[0]["title"], "Bench press hypertrophy response")

    def test_catalog_does_not_treat_program_lists_as_direct_exercise_evidence(self) -> None:
        docs = [
            {
                "pmid": "39077025",
                "doc_id": "pmid-39077025",
                "title": "Effects of 12 Weeks of Resistance Training on Body Composition",
                "abstract": (
                    "The resistance training program composed of deadlift, squat, leg extension, "
                    "leg curl, bench press, preacher bench biceps curl, barbell rowing, and "
                    "dumbbell shoulder press. Outcomes measured thigh muscle CSA."
                ),
                "evidence_tier": "controlled_trial",
                "measurement_modalities_detected": ["Imaging", "Hypertrophy"],
                "quality_score": 0.75,
                "retrieval_weight": 0.4,
                "manual_review_required": False,
                "source": {"url": "https://pubmed.ncbi.nlm.nih.gov/39077025/"},
            }
        ]

        matches = match_exercise_studies(["shoulder press"], docs)
        self.assertEqual(matches, [])

    def test_catalog_attach_gate_drops_muscle_mismatched_alias_matches(self) -> None:
        docs = [
            {
                "pmid": "40000001",
                "doc_id": "pmid-40000001",
                "title": "Quadriceps hypertrophy with full range of motion leg training",
                "abstract": (
                    "Participants trained knee extension through a full range of motion and "
                    "quadriceps cross-sectional area was measured."
                ),
                "evidence_tier": "rct",
                "measurement_modalities_detected": ["Imaging", "Hypertrophy"],
                "quality_score": 0.8,
                "retrieval_weight": 0.6,
                "manual_review_required": False,
                "source": {"url": "https://pubmed.ncbi.nlm.nih.gov/40000001/"},
            }
        ]

        # Without exercise context the generic alias attaches (legacy behavior).
        ungated = match_exercise_studies(["full range"], docs)
        self.assertEqual(len(ungated), 1)

        # With context, a quad study cannot attach to a lat pulldown via "full range".
        gated = match_exercise_studies(
            ["full range"],
            docs,
            exercise_name="Full Range-Of-Motion Lat Pulldown",
            primary_muscles=["lats"],
            secondary_muscles=["biceps", "mid_back"],
        )
        self.assertEqual(gated, [])

        # A genuinely muscle/movement-specific alias still attaches with context.
        specific = match_exercise_studies(
            ["lat pulldown"],
            [
                {
                    **docs[0],
                    "pmid": "40000002",
                    "doc_id": "pmid-40000002",
                    "title": "Lat pulldown grip width and latissimus activation",
                    "abstract": "Compared lat pulldown grip widths on latissimus dorsi thickness.",
                }
            ],
            exercise_name="Full Range-Of-Motion Lat Pulldown",
            primary_muscles=["lats"],
            secondary_muscles=["biceps", "mid_back"],
        )
        self.assertEqual(len(specific), 1)

    def test_format_exercise_name_title_cases_for_display(self) -> None:
        cases = {
            "barbell bench press": "Barbell Bench Press",
            "pull-up": "Pull-Up",
            "ez barbell curl": "EZ Barbell Curl",
            "exercise ball on the wall calf raise": "Exercise Ball on the Wall Calf Raise",
            "cable hammer curl (with rope)": "Cable Hammer Curl (With Rope)",
            "3/4 sit-up": "3/4 Sit-Up",
        }
        for raw_name, expected in cases.items():
            self.assertEqual(format_exercise_name(raw_name), expected)

    def test_catalog_uses_curated_comparative_direction_without_guessing(self) -> None:
        findings, loaded = load_comparative_evidence("config/comparative_exercise_evidence.json")
        self.assertTrue(loaded)

        overhead_adjustments, overhead_matches = score_comparative_evidence(
            exercise_name="Cable Rope Overhead Triceps Extension",
            exercise_id="Cable_Rope_Overhead_Triceps_Extension",
            exercise_aliases=get_aliases(
                "Cable Rope Overhead Triceps Extension",
                "Cable_Rope_Overhead_Triceps_Extension",
            ),
            primary_muscles=["triceps"],
            comparative_findings=findings,
        )
        self.assertEqual(overhead_adjustments["hypertrophy"], 0.035)
        self.assertEqual(overhead_adjustments["strength"], 0.0)
        self.assertEqual(overhead_matches[0]["pmid"], "35819335")
        self.assertEqual(overhead_matches[0]["role"], "favored")

        neutral_adjustments, neutral_matches = score_comparative_evidence(
            exercise_name="Neutral Arm Triceps Extension",
            exercise_id="Neutral_Arm_Triceps_Extension",
            exercise_aliases=["neutral arm triceps extension"],
            primary_muscles=["triceps"],
            comparative_findings=findings,
        )
        self.assertEqual(neutral_adjustments["hypertrophy"], -0.01)
        self.assertEqual(neutral_matches[0]["role"], "comparator")

        preacher_adjustments, preacher_matches = score_comparative_evidence(
            exercise_name="Cable Preacher Curl",
            exercise_id="Cable_Preacher_Curl",
            exercise_aliases=get_aliases("Cable Preacher Curl", "Cable_Preacher_Curl"),
            primary_muscles=["biceps"],
            comparative_findings=findings,
        )
        self.assertEqual(preacher_adjustments["hypertrophy"], 0.0)
        self.assertTrue(any(match["pmid"] == "40082069" for match in preacher_matches))

    def test_assign_muscle_rankings_breaks_ties_by_evidence_then_deterministic(self) -> None:
        def ranking_fixture(exercise_id: str, evidence_count: int) -> dict:
            return {
                "exercise_id": exercise_id,
                "name": exercise_id.replace("_", " "),
                "muscles": {"primary": ["biceps"], "secondary": [], "all": ["biceps"]},
                "ranking_scores": {"hypertrophy": 0.80, "strength": 0.70},
                "goal_profiles": {
                    "hypertrophy": {"score": 0.50},
                    "strength": {"score": 0.50},
                },
                "evidence": {"direct_evidence_count": evidence_count, "confidence_score": 0.60},
            }

        exercises = [
            ranking_fixture("Z_High_Evidence", 3),
            ranking_fixture("A_No_Evidence", 0),
            ranking_fixture("M_No_Evidence", 0),
        ]
        assign_muscle_rankings(exercises)
        ranks = {
            ex["exercise_id"]: ex["muscle_group_rankings"]["hypertrophy"]["biceps"]
            for ex in exercises
        }

        # More direct evidence wins the tie even though the id sorts last.
        self.assertEqual(ranks["Z_High_Evidence"]["rank"], 1)
        self.assertEqual(ranks["Z_High_Evidence"]["tie_size"], 1)
        # The two evidence-less exercises are a genuine 2-way tie, ordered by id.
        self.assertEqual(ranks["A_No_Evidence"]["rank"], 2)
        self.assertEqual(ranks["M_No_Evidence"]["rank"], 3)
        self.assertEqual(ranks["A_No_Evidence"]["tie_size"], 2)
        self.assertEqual(ranks["M_No_Evidence"]["tie_size"], 2)

    def test_format_rank_summary_flags_ties_only_when_present(self) -> None:
        tied = choose_display_rank(
            {"muscle_group_rankings": {"hypertrophy": {"biceps": {"rank": 1, "out_of": 12, "tie_size": 12}}}},
            "hypertrophy",
            ["biceps"],
        )
        self.assertEqual(tied["biceps"]["tie_size"], 12)
        self.assertEqual(format_rank_summary(tied, "biceps"), "#1/12 · tied×12")

        unique = choose_display_rank(
            {"muscle_group_rankings": {"hypertrophy": {"biceps": {"rank": 3, "out_of": 50, "tie_size": 1}}}},
            "hypertrophy",
            ["biceps"],
        )
        self.assertEqual(format_rank_summary(unique, "biceps"), "#3/50")

    def test_run_protocol_dry_run_shortlists_without_api_key(self) -> None:
        catalog_payload = {
            "taxonomies": {
                "muscle_groups": ["biceps", "forearms"],
                "equipment": ["cable", "dumbbell"],
                "joints": ["neck", "shoulder", "elbow", "wrist", "spine", "hip", "knee", "ankle"],
            },
            "exercises": self.exercises,
        }
        # No resolve_api_key / generate_with_gemma patches: a dry run must not touch them.
        with patch("protocol_engine.protocol_demo.load_catalog", return_value=catalog_payload):
            result = run_protocol_dry_run(self.request)

        self.assertTrue(result["candidate_pool"]["by_target"]["biceps"])
        self.assertIn("## 1-Week Protocol", result["markdown_text"])
        self.assertEqual(
            result["filtered_candidate_count"],
            len(filter_and_score_exercises(self.request, self.exercises)),
        )

    def test_apply_muscle_corrections_reassigns_mislabeled_hip_movements(self) -> None:
        adduction_primary, _ = apply_muscle_corrections("Cable Hip Adduction", ["quads"], [])
        self.assertIn("hip_adductors", adduction_primary)
        self.assertNotIn("quads", adduction_primary)

        flexion_primary, flexion_secondary = apply_muscle_corrections(
            "Hip Flexion with Band", ["quads"], []
        )
        self.assertNotIn("quads", flexion_primary)
        self.assertIn("quads", flexion_secondary)

        # A genuine quad lift is left untouched.
        squat_primary, _ = apply_muscle_corrections("Barbell Full Squat", ["quads"], ["glutes"])
        self.assertIn("quads", squat_primary)

    def test_validate_generated_markdown_rejects_unknown_references(self) -> None:
        candidates = dedupe_candidates(filter_and_score_exercises(self.request, self.exercises))
        outline = build_protocol_outline(self.request, candidates, self.findings)
        bad_markdown = (
            "# 1-Week Demo Protocol\n\n"
            "## Request Summary\n\n"
            "## 1-Week Protocol\n"
            "### Session 1\n"
            "- Biceps: Invented Curl - 3x10, 90 sec rest [PMID: 99999999]\n\n"
            "## Evidence Appendix\n"
            "- PMID: 99999999 | Invented paper\n"
            "- Finding: fake\n\n"
            "## Confidence Notes\n"
            "- none\n"
        )
        errors = validate_generated_markdown(bad_markdown, outline, self.findings)
        self.assertTrue(any("Unknown exercise" in error for error in errors))
        self.assertTrue(any("Unknown PMID" in error for error in errors))

    def test_validate_generated_markdown_rejects_missing_requested_target(self) -> None:
        request = normalize_request(
            goal="hypertrophy",
            muscles="chest,shoulders",
            sessions=1,
            session_minutes=30,
            equipment="barbell,cable",
            experience="intermediate",
        )
        exercises = [
            make_target_exercise("Bench Press", "Bench_Press", "barbell", 0.95, ["chest"], []),
            make_target_exercise("Cable Shoulder Press", "Cable_Shoulder_Press", "cable", 0.90, ["delts"], []),
        ]
        outline = build_protocol_outline(
            request,
            dedupe_candidates(filter_and_score_exercises(request, exercises)),
            [],
        )
        markdown = (
            "# 1-Week Demo Protocol\n\n"
            "## Request Summary\n\n"
            "## 1-Week Protocol\n"
            "### Session 1\n"
            "- Chest: Bench Press - 3x10, 90 sec rest\n\n"
            "## Evidence Appendix\n"
            "- PMID: none\n"
            "- Finding: none\n\n"
            "## Confidence Notes\n"
            "- none\n"
        )

        errors = validate_generated_markdown(markdown, outline, [], request=request)
        self.assertTrue(any("Missing requested target muscle" in error for error in errors))

    def test_validate_generated_markdown_requires_cited_pmids_in_appendix(self) -> None:
        candidates = dedupe_candidates(filter_and_score_exercises(self.request, self.exercises))
        outline = build_protocol_outline(self.request, candidates, self.findings)
        broken = (
            "# 1-Week Demo Protocol\n\n"
            "## Request Summary\n\n"
            "## 1-Week Protocol\n"
            "### Session 1\n"
            "- Biceps: Cable Preacher Curl - 3x10, 90 sec rest [PMID: 40082069]\n\n"
            "## Evidence Appendix\n"
            "- PMID: 11111111 | Wrong appendix paper\n"
            "- Finding: wrong\n\n"
            "## Confidence Notes\n"
            "- none\n"
        )

        errors = validate_generated_markdown(broken, outline, self.findings, request=self.request)
        self.assertTrue(any("missing from Evidence Appendix" in error for error in errors))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
