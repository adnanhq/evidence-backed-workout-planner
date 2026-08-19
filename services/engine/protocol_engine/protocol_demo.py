from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from .pipeline_common import clamp, normalize_text, read_json, write_json
except ImportError:  # pragma: no cover
    from pipeline_common import clamp, normalize_text, read_json, write_json


try:
    from . import settings
except ImportError:  # pragma: no cover
    import settings


REPO_ROOT = settings.REPO_ROOT
PROJECT_ENV_PATH = settings.ENV_PATH
DEFAULT_MODEL = settings.DEFAULT_MODEL
DEFAULT_OUTPUT_DIR = settings.OUTPUT_DIR
DEFAULT_CATALOG_PATH = settings.CATALOG_PATH
DEFAULT_SCIENCE_PATH = settings.SCIENCE_PATH
DEFAULT_VECTOR_STORE_PATH = settings.VECTOR_STORE_PATH
VECTOR_COLLECTION_NAME = "science_corpus"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
# Cosine-distance ceiling for semantic findings (all-MiniLM-L6-v2, cosine space).
# Calibrated 2026-07 via protocol_engine.calibrate_retrieval: legitimate builder
# queries score 0.23-0.45 against this corpus; off-topic probes (yoga, nutrition,
# swimming) score >= 0.51. Anything above the ceiling is dropped rather than cited.
MAX_FINDING_DISTANCE = 0.50
LLM_CANDIDATES_PER_MUSCLE = 3
LLM_TEMPERATURE = 0.4
# Per-attempt request timeout; two attempts stay within the web client's 220s budget.
LLM_TIMEOUT_MS = 90_000
# Gemma-family models routinely take 120-150s on the planning prompt (measured
# 2026-07), so they get a single-attempt-sized ceiling instead.
LLM_SLOW_MODEL_TIMEOUT_MS = 200_000

# Gemini structured-output schema for the plan JSON (types.Schema-compatible dict).
# sets/reps/rest_seconds are optional: gemma-family models (no schema support) and
# older mocks omit them, in which case the deterministic seed prescription applies.
PLAN_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "split_summary": {"type": "STRING"},
        "sessions": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "session_number": {"type": "INTEGER"},
                    "split_label": {"type": "STRING"},
                    "focus": {"type": "STRING"},
                    "exercises": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "exercise_id": {"type": "STRING"},
                                "target_muscle": {"type": "STRING"},
                                "sets": {"type": "INTEGER"},
                                "reps": {"type": "STRING"},
                                "rest_seconds": {"type": "INTEGER"},
                            },
                            "required": ["exercise_id", "target_muscle"],
                        },
                    },
                },
                "required": ["session_number", "split_label", "focus", "exercises"],
            },
        },
        "confidence_notes": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["sessions"],
}

# Goal-appropriate prescription bounds; LLM-chosen values are clamped into these.
PRESCRIPTION_BOUNDS = {
    "strength": {"sets": (3, 6), "reps": (3, 8), "rest_seconds": (120, 300)},
    "hypertrophy": {"sets": (2, 5), "reps": (5, 30), "rest_seconds": (45, 180)},
}

REPS_RANGE_PATTERN = re.compile(r"^\s*(\d+)\s*(?:-\s*(\d+))?\s*$")

GOAL_CHOICES = {"hypertrophy", "strength"}
EXPERIENCE_CHOICES = {"beginner", "intermediate", "advanced"}
SPLIT_TEMPLATE_CHOICES = {"auto", "full_body", "push_pull", "push_pull_legs", "upper_lower"}

PMID_PATTERN = re.compile(r"PMID:\s*(\d+)")
EXERCISE_LINE_PATTERN = re.compile(
    r"^-\s*(?P<target>[^:\n]+):\s*(?P<exercise>.+?)\s+-\s+\d+x",
    re.MULTILINE,
)

MUSCLE_ALIASES = {
    "bicep": "biceps",
    "quad": "quads",
    "quadricep": "quads",
    "quadriceps": "quads",
    "shoulder": "delts",
    "shoulders": "delts",
    "middle_back": "mid_back",
    "midback": "mid_back",
    "lower_back": "spinal_erectors",
    "erectors": "spinal_erectors",
    "abdominals": "abs",
    "core": "abs",
}

EQUIPMENT_ALIASES = {
    "bands": "resistance_band",
    "band": "resistance_band",
    "resistance_bands": "resistance_band",
    "resistance_band": "resistance_band",
    "dumbell": "dumbbell",
    "dumbells": "dumbbell",
    "dumbbells": "dumbbell",
    "barbells": "barbell",
    "cables": "cable",
    "kettlebells": "kettlebell",
    "ezbar": "ez_bar",
    "ez_bar": "ez_bar",
    "body_only": "bodyweight",
    "body_weight": "bodyweight",
    "smith": "smith_machine",
    "smith_machine": "smith_machine",
    "leverage": "leverage_machine",
    "leverage_machine": "leverage_machine",
}

EQUIPMENT_PRESETS = {
    "commercial_gym": ["barbell", "cable", "dumbbell", "ez_bar", "machine", "leverage_machine", "smith_machine", "resistance_band", "kettlebell"],
    "full_gym": ["barbell", "cable", "dumbbell", "ez_bar", "machine", "leverage_machine", "smith_machine", "resistance_band", "kettlebell"],
    "gym": ["barbell", "cable", "dumbbell", "ez_bar", "machine", "leverage_machine", "smith_machine", "resistance_band", "kettlebell"],
    "gym_setup": ["barbell", "cable", "dumbbell", "ez_bar", "machine", "leverage_machine", "smith_machine", "resistance_band", "kettlebell"],
}

JOINT_ALIASES = {
    "lower_back": "spine",
    "back": "spine",
}

MUSCLE_DISPLAY_LABELS = {
    "abs": "Abs",
    "biceps": "Biceps",
    "calves": "Calves",
    "chest": "Chest",
    "delts": "Shoulders",
    "forearms": "Forearms",
    "glutes": "Glutes",
    "hamstrings": "Hamstrings",
    "lats": "Lats",
    "mid_back": "Mid Back",
    "quads": "Quads",
    "spinal_erectors": "Lower Back",
    "traps": "Traps",
    "triceps": "Triceps",
}

CANONICAL_MUSCLE_ORDER = [
    "chest",
    "delts",
    "triceps",
    "lats",
    "mid_back",
    "traps",
    "biceps",
    "forearms",
    "quads",
    "hamstrings",
    "glutes",
    "calves",
    "hip_abductors",
    "hip_adductors",
    "abs",
    "spinal_erectors",
]
PUSH_MUSCLES = {"chest", "delts", "triceps"}
PULL_MUSCLES = {"lats", "mid_back", "traps", "biceps", "forearms"}
LEG_MUSCLES = {"quads", "hamstrings", "glutes", "calves", "hip_abductors", "hip_adductors"}
CORE_MUSCLES = {"abs", "spinal_erectors"}
ARM_MUSCLES = {"biceps", "triceps", "forearms"}

SIGNATURE_STOPWORDS = {
    "a",
    "alternate",
    "alternating",
    "an",
    "and",
    "arm",
    "arms",
    "attachment",
    "attachments",
    "barbell",
    "barbells",
    "bodyweight",
    "cable",
    "cables",
    "dumbbell",
    "dumbbells",
    "ez",
    "ezbar",
    "for",
    "full",
    "grip",
    "grips",
    "machine",
    "machines",
    "motion",
    "of",
    "one",
    "range",
    "rope",
    "seated",
    "single",
    "smith",
    "standing",
    "the",
    "to",
    "two",
    "with",
}

PLURAL_EXCEPTIONS = {"biceps", "triceps", "glutes", "lats", "abs"}
EXERCISE_MOVEMENT_TERMS = {
    "abduction",
    "abductions",
    "adduction",
    "adductions",
    "bridge",
    "bridges",
    "clean",
    "cleans",
    "crunch",
    "crunches",
    "curl",
    "curls",
    "deadlift",
    "dip",
    "dips",
    "extension",
    "extensions",
    "fly",
    "flye",
    "flyes",
    "hyperextension",
    "hyperextensions",
    "kickback",
    "kickbacks",
    "lunge",
    "lunges",
    "plank",
    "planks",
    "press",
    "presses",
    "pull",
    "pulldown",
    "pulldowns",
    "pullover",
    "pullovers",
    "pulls",
    "pullup",
    "pullups",
    "push",
    "pushes",
    "pushup",
    "pushups",
    "raise",
    "raises",
    "row",
    "rows",
    "shrug",
    "shrugs",
    "situp",
    "situps",
    "snatch",
    "snatches",
    "squat",
    "squats",
    "step",
    "swing",
    "swings",
    "thrust",
    "thrusts",
}

# Single-word study-text synonyms for canonical muscle tokens, so an alias like
# "calf raise" is recognized as muscle-specific for a "calves" exercise.
MUSCLE_TOKEN_SYNONYMS = {
    "abs": {"ab", "abdominal", "abdominals"},
    "biceps": {"bicep"},
    "calves": {"calf"},
    "delts": {"delt", "deltoid", "deltoids"},
    "forearms": {"forearm"},
    "glutes": {"glute", "gluteal", "gluteus"},
    "hamstrings": {"hamstring"},
    "lats": {"lat", "latissimus"},
    "quads": {"quad", "quadricep", "quadriceps"},
    "traps": {"trap", "trapezius"},
    "triceps": {"tricep"},
}
TARGET_TERM_EXPANSIONS = {
    "abs": ["abdominal", "abdominals", "core"],
    "biceps": ["bicep", "biceps", "biceps brachii", "curl", "curls", "elbow flexor", "elbow flexors"],
    "chest": ["chest", "pectoralis", "pec", "pecs", "bench press", "chest press"],
    "delts": [
        "deltoid",
        "deltoids",
        "shoulder",
        "shoulders",
        "shoulder press",
        "overhead press",
        "lateral raise",
        "delt raise",
    ],
    "glutes": ["glute", "glutes", "gluteus"],
    "lats": ["lat", "lats", "latissimus"],
    "quads": ["quad", "quads", "quadriceps"],
    "spinal_erectors": ["erector", "erectors", "lower back"],
    "triceps": [
        "tricep",
        "triceps",
        "elbow extensor",
        "elbow extensors",
        "elbow extension",
        "overhead triceps extension",
        "triceps pushdown",
    ],
}

DELT_REGION_LABELS = {
    "anterior": "anterior delt",
    "lateral": "lateral delt",
    "posterior": "rear delt",
}
DELT_REGION_ORDER = ["lateral", "posterior", "anterior"]
DELT_MULTI_SESSION_REGION_ORDER = ["lateral", "posterior", "anterior", "posterior"]

DELT_POSTERIOR_TERMS = {
    "rear delt",
    "rear deltoid",
    "reverse fly",
    "reverse flye",
    "reverse machine fly",
    "face pull",
    "band pull apart",
    "back fly",
}
DELT_LATERAL_TERMS = {
    "lateral raise",
    "side lateral",
    "low pulley deltoid raise",
    "deltoid raise",
    "scaption",
    "iron cross",
}
DELT_ANTERIOR_TERMS = {
    "shoulder press",
    "military press",
    "overhead press",
    "arnold press",
    "front raise",
}
DELT_REFERENCE_TERMS = [
    "anterior deltoid",
    "deltoid",
    "deltoids",
    "lateral deltoid",
    "medial deltoid",
    "shoulder press",
]

VARIATION_PENALTY_TERMS = {
    "alternate",
    "alternating",
    "car drivers",
    "power partials",
    "speed",
}

GOAL_DIRECT_EVIDENCE_TERMS = {
    "hypertrophy": {
        "hypertrophy",
        "muscle growth",
        "muscle size",
        "muscle thickness",
        "muscle volume",
        "cross sectional area",
        "cross-sectional area",
        "lean mass",
    },
    "strength": {
        "1rm",
        "one repetition maximum",
        "one-repetition maximum",
        "strength",
        "force",
        "power",
        "torque",
        "performance",
    },
}

class DemoConfigurationError(RuntimeError):
    """Raised when local data or runtime dependencies are missing."""


class DemoRequestError(ValueError):
    """Raised when user inputs cannot be normalized safely."""


@dataclass
class ProtocolRequest:
    goal: str
    muscles: list[str]
    sessions: int
    session_minutes: int
    exercises_per_session: int | None
    equipment: list[str]
    experience: str
    avoid_joints: list[str]
    notes: str
    split_template: str


def normalize_atom(raw_value: str, aliases: dict[str, str] | None = None) -> str:
    normalized = normalize_text(raw_value).replace(" ", "_")
    if aliases:
        return aliases.get(normalized, normalized)
    return normalized


def normalize_csv_arg(raw_value: str | None, aliases: dict[str, str] | None = None) -> list[str]:
    if not raw_value:
        return []
    values = []
    for chunk in raw_value.split(","):
        token = normalize_atom(chunk, aliases=aliases)
        if token:
            values.append(token)
    return sorted(set(values))


def normalize_equipment_arg(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    values = []
    for chunk in raw_value.split(","):
        token = normalize_atom(chunk, aliases=EQUIPMENT_ALIASES)
        if token in EQUIPMENT_PRESETS:
            values.extend(EQUIPMENT_PRESETS[token])
        elif token:
            values.append(token)
    return sorted(set(values))


def display_muscle_label(muscle: str) -> str:
    return MUSCLE_DISPLAY_LABELS.get(muscle, muscle.replace("_", " ").title())


def normalize_request(
    goal: str,
    muscles: str,
    sessions: int,
    session_minutes: int,
    exercises_per_session: int | None = None,
    equipment: str | None = None,
    experience: str = "intermediate",
    avoid_joints: str | None = None,
    notes: str = "",
    split_template: str = "auto",
) -> ProtocolRequest:
    normalized_goal = normalize_atom(goal)
    if normalized_goal not in GOAL_CHOICES:
        raise DemoRequestError(
            f"Unsupported goal '{goal}'. Choose one of: {', '.join(sorted(GOAL_CHOICES))}."
        )

    normalized_muscles = normalize_csv_arg(muscles, aliases=MUSCLE_ALIASES)
    if not normalized_muscles:
        raise DemoRequestError("At least one target muscle is required.")

    if sessions <= 0:
        raise DemoRequestError("`--sessions` must be a positive integer.")
    if session_minutes <= 0:
        raise DemoRequestError("`--session-minutes` must be a positive integer.")
    if exercises_per_session is not None and exercises_per_session <= 0:
        raise DemoRequestError("`--exercises-per-session` must be a positive integer.")
    if exercises_per_session is not None and exercises_per_session > 8:
        raise DemoRequestError("`--exercises-per-session` must be 8 or fewer for this demo.")

    normalized_experience = normalize_atom(experience)
    if normalized_experience not in EXPERIENCE_CHOICES:
        raise DemoRequestError(
            "Unsupported experience level. Choose beginner, intermediate, or advanced."
        )
    normalized_split_template = normalize_atom(split_template)
    if normalized_split_template not in SPLIT_TEMPLATE_CHOICES:
        raise DemoRequestError(
            "Unsupported split template. Choose auto, full_body, push_pull, push_pull_legs, or upper_lower."
        )

    normalized_equipment = normalize_equipment_arg(equipment)
    normalized_joints = normalize_csv_arg(avoid_joints, aliases=JOINT_ALIASES)

    return ProtocolRequest(
        goal=normalized_goal,
        muscles=normalized_muscles,
        sessions=sessions,
        session_minutes=session_minutes,
        exercises_per_session=exercises_per_session,
        equipment=normalized_equipment,
        experience=normalized_experience,
        avoid_joints=normalized_joints,
        notes=(notes or "").strip(),
        split_template=normalized_split_template,
    )


def resolve_api_key(cli_value: str | None) -> str:
    if cli_value:
        return cli_value.strip()
    load_project_env()
    env_value = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_value:
        return env_value
    raise DemoConfigurationError(
        "Missing Gemini API key. Set GEMINI_API_KEY, add it to .env, or pass --api-key."
    )


def load_project_env(path: Path = PROJECT_ENV_PATH) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if value.startswith(("\"", "'")) and value.endswith(("\"", "'")) and len(value) >= 2:
            value = value[1:-1]
        os.environ[key] = value


@lru_cache(maxsize=1)
def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> dict[str, Any]:
    if not path.exists():
        raise DemoConfigurationError(
            f"Exercise catalog not found at {path}. Run the existing pipeline first."
        )
    return read_json(path)


@lru_cache(maxsize=1)
def load_science_corpus(path: Path = DEFAULT_SCIENCE_PATH) -> dict[str, Any]:
    if not path.exists():
        raise DemoConfigurationError(
            f"Science corpus not found at {path}. Run the existing pipeline first."
        )
    return read_json(path)


def validate_request_against_taxonomies(
    request: ProtocolRequest,
    catalog_payload: dict[str, Any],
) -> None:
    taxonomies = catalog_payload.get("taxonomies", {})
    known_muscles = set(taxonomies.get("muscle_groups", []))
    unknown_muscles = [muscle for muscle in request.muscles if muscle not in known_muscles]
    if unknown_muscles:
        raise DemoRequestError(
            f"Unknown muscle(s): {', '.join(unknown_muscles)}. "
            f"Known options include: {', '.join(sorted(list(known_muscles))[:12])}."
        )

    known_equipment = set(taxonomies.get("equipment", []))
    unknown_equipment = [
        equipment for equipment in request.equipment if equipment not in known_equipment
    ]
    if unknown_equipment:
        raise DemoRequestError(
            f"Unknown equipment value(s): {', '.join(unknown_equipment)}."
        )

    known_joints = set(taxonomies.get("joints", []))
    unknown_joints = [joint for joint in request.avoid_joints if joint not in known_joints]
    if unknown_joints:
        raise DemoRequestError(
            f"Unknown joint value(s): {', '.join(unknown_joints)}."
        )


def singularize_token(token: str) -> str:
    if token in PLURAL_EXCEPTIONS:
        return token
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("s") and len(token) > 4:
        return token[:-1]
    return token


def derive_variation_signature(name: str) -> str:
    tokens = []
    for token in normalize_text(name).split():
        if token in SIGNATURE_STOPWORDS:
            continue
        tokens.append(singularize_token(token))
    if not tokens:
        return normalize_text(name)
    return " ".join(tokens[:4])


def variation_quality_score(name: str) -> float:
    name_text = normalize_text(name)
    penalty = sum(0.01 for term in VARIATION_PENALTY_TERMS if term in name_text)
    return round(1.0 - penalty, 4)


def classify_delt_region(candidate: dict[str, Any]) -> str | None:
    primary_targets = set(candidate.get("requested_primary_targets", []))
    if "delts" not in primary_targets:
        return None

    text = normalize_text(candidate.get("name", ""))
    if any(term in text for term in DELT_POSTERIOR_TERMS):
        return "posterior"
    if any(term in text for term in DELT_LATERAL_TERMS):
        return "lateral"
    if any(term in text for term in DELT_ANTERIOR_TERMS):
        return "anterior"
    if "raise" in text and "front" not in text and "rear" not in text:
        return "lateral"
    return "general"


def format_target_label(target_muscle: str, candidate: dict[str, Any]) -> str:
    label = display_muscle_label(target_muscle)
    if target_muscle == "delts":
        region = candidate.get("delt_region")
        region_label = DELT_REGION_LABELS.get(str(region))
        if region_label:
            return f"{label} ({region_label})"
    return label


def choose_display_rank(
    exercise: dict[str, Any],
    goal: str,
    target_muscles: list[str],
) -> dict[str, dict[str, int]]:
    rankings = exercise.get("muscle_group_rankings", {}).get(goal, {})
    selected: dict[str, dict[str, int]] = {}
    for muscle in target_muscles:
        rank_info = rankings.get(muscle)
        if rank_info:
            selected[muscle] = {
                "rank": int(rank_info["rank"]),
                "out_of": int(rank_info["out_of"]),
                "tie_size": int(rank_info.get("tie_size", 1) or 1),
            }
    return selected


def format_rank_token(rank_info: dict[str, int]) -> str:
    """Render a single rank as ``#R/M``, flagging ties honestly when present.

    When ``tie_size`` exceeds 1, several exercises are indistinguishable on every
    ranking signal, so the displayed position is not a precise unique rank.
    """
    token = f"#{rank_info['rank']}/{rank_info['out_of']}"
    tie_size = int(rank_info.get("tie_size", 1) or 1)
    if tie_size > 1:
        token = f"{token} · tied×{tie_size}"
    return token


def format_rank_summary(rank_summary: dict[str, dict[str, int]], target_muscle: str) -> str:
    rank_info = rank_summary.get(target_muscle)
    if rank_info:
        return format_rank_token(rank_info)

    if rank_summary:
        muscle, rank_info = sorted(rank_summary.items())[0]
        return f"{display_muscle_label(muscle)} {format_rank_token(rank_info)}"

    return ""


def format_candidate_rank_summary(candidate: dict[str, Any], target_muscle: str) -> str:
    overall_rank = format_rank_summary(candidate.get("rank_summary", {}), target_muscle)
    if target_muscle != "delts":
        return overall_rank

    region_rank = candidate.get("delt_region_rank")
    region = candidate.get("delt_region")
    region_label = DELT_REGION_LABELS.get(str(region))
    if not region_rank or not region_label:
        return overall_rank

    region_display = f"#{region_rank['rank']}/{region_rank['out_of']} {region_label}"
    if overall_rank:
        return f"{region_display}; {overall_rank} shoulders"
    return region_display


def get_requested_primary_targets(
    exercise: dict[str, Any],
    request: ProtocolRequest,
) -> list[str]:
    primary_muscles = set(exercise.get("muscles", {}).get("primary", []))
    return [muscle for muscle in request.muscles if muscle in primary_muscles]


def get_requested_all_targets(
    exercise: dict[str, Any],
    request: ProtocolRequest,
) -> list[str]:
    all_muscles = set(exercise.get("muscles", {}).get("all", []))
    return [muscle for muscle in request.muscles if muscle in all_muscles]


def build_prescription_seed(exercise: dict[str, Any], goal: str) -> dict[str, str]:
    # Neutral defaults used when the LLM does not supply a usable prescription.
    # The retrieval/ranking is evidence-based; exact loading prescriptions are
    # not extracted per exercise yet.
    if goal == "strength":
        return {"sets": "3", "reps": "5", "rest": "120 sec", "display": "3x5"}
    return {"sets": "3", "reps": "10", "rest": "90 sec", "display": "3x10"}


def normalize_llm_prescription(raw_exercise: dict[str, Any], goal: str) -> dict[str, str] | None:
    """Validate and clamp an LLM-chosen prescription into the goal's bounds.

    Returns ``None`` when no prescription fields are present, or when a supplied
    field is unparseable (e.g. reps "AMRAP") — we cannot infer intent from
    garbage, so the caller falls back to the neutral seed for that exercise.
    Out-of-range but parseable values are clamped rather than rejected: a hard
    reject would discard an otherwise valid plan over a fixable number.
    """
    raw_sets = raw_exercise.get("sets")
    raw_reps = raw_exercise.get("reps")
    raw_rest = raw_exercise.get("rest_seconds")
    if raw_sets is None and raw_reps is None and raw_rest is None:
        return None

    bounds = PRESCRIPTION_BOUNDS.get(goal, PRESCRIPTION_BOUNDS["hypertrophy"])

    def clamp_int(value: Any, low: int, high: int) -> int | None:
        try:
            number = int(str(value).strip())
        except (TypeError, ValueError):
            return None
        return max(low, min(high, number))

    seed = build_prescription_seed(raw_exercise, goal)

    if raw_sets is None:
        sets = int(seed["sets"])
    else:
        sets = clamp_int(raw_sets, *bounds["sets"])
        if sets is None:
            return None

    if raw_reps is None:
        reps_display = seed["reps"]
    else:
        match = REPS_RANGE_PATTERN.match(str(raw_reps))
        if not match:
            return None
        rep_low_bound, rep_high_bound = bounds["reps"]
        rep_low = max(rep_low_bound, min(rep_high_bound, int(match.group(1))))
        rep_high = (
            max(rep_low_bound, min(rep_high_bound, int(match.group(2))))
            if match.group(2)
            else rep_low
        )
        if rep_high < rep_low:
            rep_low, rep_high = rep_high, rep_low
        reps_display = str(rep_low) if rep_low == rep_high else f"{rep_low}-{rep_high}"

    if raw_rest is None:
        rest_seconds = int(seed["rest"].split()[0])
    else:
        rest_seconds = clamp_int(raw_rest, *bounds["rest_seconds"])
        if rest_seconds is None:
            return None

    return {
        "sets": str(sets),
        "reps": reps_display,
        "rest": f"{rest_seconds} sec",
        "display": f"{sets}x{reps_display}",
    }


def summarize_candidate_reason(candidate: dict[str, Any], request: ProtocolRequest) -> str:
    reasons = []
    if candidate["target_match"] == "primary":
        reasons.append("directly targets the requested muscle")
    else:
        reasons.append("supports the requested muscle as a secondary mover")

    if candidate["rank_summary"]:
        rank_chunks = [
            f"{muscle} rank #{rank['rank']}/{rank['out_of']}"
            for muscle, rank in sorted(candidate["rank_summary"].items())
        ]
        reasons.append(", ".join(rank_chunks))

    if candidate["non_reviewed_direct_evidence"] > 0:
        reasons.append(
            f"{candidate['non_reviewed_direct_evidence']} direct study match(es) not flagged for manual review"
        )
    elif candidate["lower_trust_evidence"]:
        reasons.append("direct exercise-name evidence exists but is lower-trust")
    else:
        reasons.append("supported mainly by catalog ranking plus general retrieved science")

    favored_comparison = any(
        item.get("role") == "favored" and float(item.get("score_adjustment", 0.0) or 0.0) > 0.0
        for item in candidate.get("comparative_findings", [])
    )
    if favored_comparison:
        reasons.append("vetted comparative evidence favors it for this goal")

    if request.avoid_joints:
        reasons.append("passes the requested joint-stress exclusions")

    return "; ".join(reasons)


def get_target_terms(request: ProtocolRequest, candidate: dict[str, Any] | None = None) -> list[str]:
    terms = set()
    for muscle in request.muscles:
        terms.add(muscle.replace("_", " "))
        for expanded in TARGET_TERM_EXPANSIONS.get(muscle, []):
            terms.add(expanded)

    if candidate:
        terms.update(token for token in candidate.get("signature", "").split() if token)
        terms.update(candidate.get("muscles", {}).get("primary", []))
        terms.update(candidate.get("muscles", {}).get("secondary", []))

    return sorted(term for term in terms if term)


def get_candidate_specific_terms(candidate: dict[str, Any]) -> list[str]:
    terms = set()
    terms.update(token for token in candidate.get("signature", "").split() if token)
    terms.update(
        token
        for token in normalize_text(candidate.get("name", "")).split()
        if token not in SIGNATURE_STOPWORDS
    )
    return sorted(term for term in terms if term)


def score_text_relevance(text: str, terms: list[str]) -> int:
    normalized_text = normalize_text(text)
    score = 0
    for term in terms:
        normalized_term = normalize_text(term)
        if normalized_term and normalized_term in normalized_text:
            score += 1
    return score


def apply_ambiguity_penalty(text: str, request: ProtocolRequest, score: int) -> int:
    normalized_text = normalize_text(text)
    adjusted = score
    if "biceps" in request.muscles and (
        "biceps femoris" in normalized_text
        or "hamstring" in normalized_text
        or "hamstrings" in normalized_text
        or "femoris" in normalized_text
    ):
        adjusted -= 2
    return max(0, adjusted)


def is_specific_study_match(
    exercise: dict[str, Any],
    study: dict[str, Any],
) -> bool:
    matched_alias = normalize_text(str(study.get("matched_alias", "")))
    if not matched_alias:
        return False

    alias_tokens = {
        token for token in matched_alias.split() if token and token not in SIGNATURE_STOPWORDS
    }
    if not alias_tokens:
        return False

    # Compare against the full name's tokens, not the 4-token variation
    # signature — the signature truncation would drop the movement words from
    # long names (e.g. "band straight back stiff leg deadlift").
    candidate_tokens = {
        singularize_token(token)
        for token in normalize_text(str(exercise.get("name", ""))).split()
        if token and token not in SIGNATURE_STOPWORDS
    }
    muscle_tokens = set(exercise.get("muscles", {}).get("primary", [])) | set(
        exercise.get("muscles", {}).get("secondary", [])
    )
    for muscle in list(muscle_tokens):
        muscle_tokens |= MUSCLE_TOKEN_SYNONYMS.get(muscle, set())
    overlap_tokens = alias_tokens.intersection(candidate_tokens | muscle_tokens)
    has_specific_movement = bool(alias_tokens.intersection(EXERCISE_MOVEMENT_TERMS))
    has_specific_muscle = bool(alias_tokens.intersection(muscle_tokens))

    return bool(overlap_tokens) and (has_specific_movement or has_specific_muscle)


def is_goal_relevant_direct_study(study: dict[str, Any], goal: str) -> bool:
    methods = {
        normalize_text(str(method))
        for method in study.get("measurement_method", [])
        if str(method).strip()
    }
    text = normalize_text(f"{study.get('title', '')} {study.get('study_summary', '')}")

    if goal == "hypertrophy" and "hypertrophy" in methods:
        return True
    if goal == "strength" and "performance" in methods:
        return True

    return any(term in text for term in GOAL_DIRECT_EVIDENCE_TERMS.get(goal, set()))


def normalize_candidate_studies(
    request: ProtocolRequest,
    exercise: dict[str, Any],
) -> list[dict[str, Any]]:
    reliable_studies = []
    for study in exercise.get("evidence", {}).get("studies", []):
        if not is_specific_study_match(exercise, study):
            continue
        if not is_goal_relevant_direct_study(study, request.goal):
            continue
        relevance_score = score_text_relevance(
            f"{study.get('title', '')} {study.get('study_summary', '')}",
            get_target_terms(request),
        )
        reliable_studies.append(
            {
                "pmid": str(study.get("pmid")),
                "title": study.get("title", ""),
                "publication_year": study.get("publication_year"),
                "evidence_tier": study.get("evidence_tier"),
                "manual_review_required": bool(study.get("manual_review_required", False)),
                "study_summary": study.get("study_summary", ""),
                "matched_alias": study.get("matched_alias", ""),
                "request_relevance_score": relevance_score,
            }
        )

    reliable_studies.sort(
        key=lambda item: (
            not item["manual_review_required"],
            item["request_relevance_score"],
            item.get("publication_year") or 0,
        ),
        reverse=True,
    )
    return reliable_studies


def has_request_relevant_direct_evidence(study: dict[str, Any]) -> bool:
    return int(study.get("request_relevance_score", 0) or 0) > 0


def determine_exercises_per_session(request: ProtocolRequest) -> int:
    if request.exercises_per_session is not None:
        return request.exercises_per_session

    if request.session_minutes <= 35:
        base = 3
    elif request.session_minutes <= 55:
        base = 4
    else:
        base = 5

    if len(request.muscles) == 1:
        return min(base, 3)
    return base


def determine_min_exercises_per_session(
    request: ProtocolRequest,
    candidate_pool: dict[str, Any] | None = None,
) -> int:
    max_exercises = determine_exercises_per_session(request)
    if request.exercises_per_session is not None:
        return max(1, max_exercises)

    if request.session_minutes <= 35:
        minimum = 2
    elif request.session_minutes <= 55:
        minimum = 3
    else:
        minimum = 4

    if len(request.muscles) == 1:
        minimum = min(3, max(2, minimum))

    minimum = min(minimum, max_exercises)
    if candidate_pool is not None:
        allowed_count = len(set(candidate_pool.get("allowed_exercise_ids", [])))
        if allowed_count:
            minimum = min(minimum, allowed_count)
    return max(1, minimum)


def determine_unique_exercise_cap(request: ProtocolRequest, exercises_per_session: int) -> int:
    if len(request.muscles) == 1:
        return min(3, exercises_per_session)
    return max(exercises_per_session, min(len(request.muscles) * 2, exercises_per_session + 1))


def minimum_primary_candidate_count(request: ProtocolRequest) -> int:
    return max(2, determine_unique_exercise_cap(request, determine_exercises_per_session(request)))


def filter_and_score_exercises(
    request: ProtocolRequest,
    exercises: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for exercise in exercises:
        all_muscles = set(exercise.get("muscles", {}).get("all", []))
        primary_muscles = set(exercise.get("muscles", {}).get("primary", []))
        if not all_muscles.intersection(request.muscles):
            continue

        allowed_goals = set(exercise.get("filter_metadata", {}).get("training_goals", []))
        if request.goal not in allowed_goals:
            continue

        equipment_name = exercise.get("movement", {}).get("equipment")
        if request.equipment and equipment_name not in request.equipment:
            continue

        difficulty = exercise.get("movement", {}).get("difficulty", "unknown")
        if request.experience != "advanced" and difficulty == "advanced":
            continue

        joint_profile = exercise.get("joint_stress", {}).get("profile", {})
        blocked_joint = False
        for joint in request.avoid_joints:
            if joint_profile.get(joint, {}).get("label") == "high":
                blocked_joint = True
                break
        if blocked_joint:
            continue

        studies = normalize_candidate_studies(request, exercise)
        request_relevant_studies = [
            study for study in studies if has_request_relevant_direct_evidence(study)
        ]

        unreviewed_direct = sum(
            1
            for study in request_relevant_studies
            if not bool(study.get("manual_review_required", False))
        )
        flagged_direct = sum(
            1
            for study in request_relevant_studies
            if bool(study.get("manual_review_required", False))
        )
        lower_trust = bool(exercise.get("evidence", {}).get("manual_review_required", False))
        comparative_findings = [
            finding
            for finding in exercise.get("evidence", {}).get("comparative_findings", [])
            if finding.get("goal") == request.goal
        ]
        comparative_adjustment = float(
            exercise.get("evidence", {})
            .get("comparative_score_adjustments", {})
            .get(request.goal, 0.0)
            or 0.0
        )
        requested_primary_targets = get_requested_primary_targets(exercise, request)
        requested_all_targets = get_requested_all_targets(exercise, request)
        target_match = "primary" if requested_primary_targets else "secondary"
        base_score = float(exercise.get("ranking_scores", {}).get(request.goal, 0.0))
        primary_bonus = 0.05 if target_match == "primary" else 0.02
        evidence_bonus = min(0.06, unreviewed_direct * 0.03)
        confidence_bonus = max(
            0.0,
            float(exercise.get("evidence", {}).get("confidence_score", 0.0)) - 0.55,
        ) * 0.05
        review_penalty = 0.04 if lower_trust and unreviewed_direct == 0 else 0.015 if lower_trust else 0.0
        provisional_delt_region = classify_delt_region(
            {
                "name": exercise["name"],
                "requested_primary_targets": requested_primary_targets,
                "requested_all_targets": requested_all_targets,
            }
        )
        shoulder_region_bonus = (
            0.012
            if requested_primary_targets
            and "delts" in requested_primary_targets
            and provisional_delt_region in {"lateral", "posterior"}
            else 0.0
        )
        variation_penalty = 0.008 if variation_quality_score(exercise["name"]) < 1.0 else 0.0

        candidate = {
            "exercise_id": exercise["exercise_id"],
            "name": exercise["name"],
            "signature": derive_variation_signature(exercise["name"]),
            "target_match": target_match,
            "requested_primary_targets": requested_primary_targets,
            "requested_all_targets": requested_all_targets,
            "movement": exercise["movement"],
            "muscles": exercise["muscles"],
            "equipment": equipment_name,
            "difficulty": difficulty,
            "ranking_score": round(base_score, 4),
            "final_score": round(
                clamp(
                    base_score
                    + primary_bonus
                    + evidence_bonus
                    + confidence_bonus
                    + shoulder_region_bonus
                    - variation_penalty
                    - review_penalty
                ),
                4,
            ),
            "score_breakdown": {
                "base_ranking_score": round(base_score, 4),
                "primary_match_bonus": round(primary_bonus, 4),
                "unreviewed_evidence_bonus": round(evidence_bonus, 4),
                "confidence_bonus": round(confidence_bonus, 4),
                "manual_review_penalty": round(review_penalty, 4),
                "shoulder_region_bonus": round(shoulder_region_bonus, 4),
                "variation_penalty": round(variation_penalty, 4),
                "catalog_comparative_adjustment": round(comparative_adjustment, 4),
            },
            "goal_profile": exercise.get("goal_profiles", {}).get(request.goal, {}),
            "joint_stress": exercise.get("joint_stress", {}),
            "rank_summary": choose_display_rank(exercise, request.goal, request.muscles),
            "non_reviewed_direct_evidence": unreviewed_direct,
            "flagged_direct_evidence": flagged_direct,
            "lower_trust_evidence": lower_trust,
            "evidence_confidence": exercise.get("evidence", {}).get("confidence_score"),
            "comparative_findings": comparative_findings[:3],
            "top_studies": request_relevant_studies,
            "prescription_seed": build_prescription_seed(exercise, request.goal),
            "delt_region": provisional_delt_region,
            "variation_quality_score": variation_quality_score(exercise["name"]),
        }
        candidate["selection_reason"] = summarize_candidate_reason(candidate, request)
        candidates.append(candidate)

    candidates.sort(
        key=lambda item: (
            item["final_score"],
            item["non_reviewed_direct_evidence"],
            item["ranking_score"],
        ),
        reverse=True,
    )
    primary_candidates = [item for item in candidates if item["target_match"] == "primary"]
    if len(primary_candidates) >= minimum_primary_candidate_count(request):
        return primary_candidates
    return candidates


def dedupe_candidates(
    candidates: list[dict[str, Any]],
    max_candidates: int | None = None,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate["signature"], []).append(candidate)

    deduped = []
    for signature, grouped_candidates in grouped.items():
        ordered = sorted(
            grouped_candidates,
            key=lambda item: (
                item["final_score"],
                item.get("variation_quality_score", 1.0),
                item["ranking_score"],
            ),
            reverse=True,
        )
        representative = dict(ordered[0])
        representative["collapsed_variations"] = [item["name"] for item in ordered[1:]]
        representative["signature"] = signature
        deduped.append(representative)

    deduped.sort(key=lambda item: item["final_score"], reverse=True)
    assign_delt_region_ranks(deduped)
    if max_candidates is None:
        return deduped
    return deduped[:max_candidates]


def assign_delt_region_ranks(candidates: list[dict[str, Any]]) -> None:
    by_region: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        region = candidate.get("delt_region")
        if region not in DELT_REGION_LABELS:
            continue
        if "delts" not in candidate.get("requested_primary_targets", []):
            continue
        by_region.setdefault(region, []).append(candidate)

    for region, items in by_region.items():
        ordered = sorted(
            items,
            key=lambda item: (
                item["final_score"],
                item.get("variation_quality_score", 1.0),
                item["ranking_score"],
            ),
            reverse=True,
        )
        total = len(ordered)
        for index, candidate in enumerate(ordered, start=1):
            candidate["delt_region_rank"] = {
                "region": region,
                "rank": index,
                "out_of": total,
            }


def compact_candidate_for_llm(candidate: dict[str, Any], target_muscle: str) -> dict[str, Any]:
    top_studies = []
    for study in candidate.get("top_studies", [])[:3]:
        top_studies.append(
            {
                "pmid": study.get("pmid"),
                "title": study.get("title"),
                "publication_year": study.get("publication_year"),
                "evidence_tier": study.get("evidence_tier"),
                "manual_review_required": bool(study.get("manual_review_required", False)),
            }
        )

    comparative_findings = []
    for finding in candidate.get("comparative_findings", [])[:2]:
        comparative_findings.append(
            {
                "pmid": finding.get("pmid"),
                "effect": finding.get("effect"),
                "role": finding.get("role"),
                "finding": finding.get("finding"),
            }
        )

    return {
        "exercise_id": candidate["exercise_id"],
        "name": candidate["name"],
        "target_muscle": target_muscle,
        "target_label": format_target_label(target_muscle, candidate),
        "rank_display": format_candidate_rank_summary(candidate, target_muscle),
        "final_score": candidate["final_score"],
        "ranking_score": candidate["ranking_score"],
        "equipment": candidate["equipment"],
        "difficulty": candidate["difficulty"],
        # compound vs isolation (and push/pull) so the model can order sessions
        # compound-first and pick sensible rep ranges.
        "mechanic": candidate.get("movement", {}).get("mechanic", "unknown"),
        "force": candidate.get("movement", {}).get("force", "unknown"),
        "delt_region": candidate.get("delt_region"),
        "direct_evidence_count": candidate.get("non_reviewed_direct_evidence", 0),
        "lower_trust_evidence": candidate.get("lower_trust_evidence", False),
        "selection_reason": candidate.get("selection_reason", ""),
        "top_studies": top_studies,
        "comparative_findings": comparative_findings,
    }


def select_candidates_for_llm_target(
    target_muscle: str,
    candidates: list[dict[str, Any]],
    per_muscle: int,
) -> list[dict[str, Any]]:
    target_candidates = [
        candidate
        for candidate in candidates
        if target_muscle in candidate_balance_targets(candidate)
    ]
    if target_muscle == "delts":
        return select_delt_candidates_for_llm(target_candidates, per_muscle)
    sorted_candidates = sort_candidates_for_target(target_muscle, target_candidates)
    strict_top_ranked = [
        candidate
        for candidate in sorted_candidates
        if (candidate_target_rank(candidate, target_muscle) or 10**9) <= per_muscle
    ]
    if strict_top_ranked:
        return strict_top_ranked[:per_muscle]
    # None of the muscle's global top-N survived the request filters (e.g. the
    # top biceps exercises are all barbell but the user only has dumbbells).
    # Offer the best-ranked eligible candidates instead of an empty pool —
    # rank_display stays honest about their global position (e.g. "#17/151").
    return sorted_candidates[:per_muscle]


def candidate_target_rank(candidate: dict[str, Any], target_muscle: str) -> int | None:
    rank_info = candidate.get("rank_summary", {}).get(target_muscle)
    if not rank_info:
        return None
    try:
        return int(rank_info["rank"])
    except (KeyError, TypeError, ValueError):
        return None


def sort_candidates_for_target(
    target_muscle: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    indexed_candidates = list(enumerate(candidates))

    def sort_key(item: tuple[int, dict[str, Any]]) -> tuple[Any, ...]:
        index, candidate = item
        rank = candidate_target_rank(candidate, target_muscle)
        return (
            rank is None,
            rank if rank is not None else 10**9,
            -float(candidate.get("final_score", 0.0) or 0.0),
            -float(candidate.get("variation_quality_score", 1.0) or 0.0),
            -float(candidate.get("ranking_score", 0.0) or 0.0),
            index,
        )

    return [candidate for _, candidate in sorted(indexed_candidates, key=sort_key)]


def candidate_delt_region_rank(candidate: dict[str, Any], region: str) -> int | None:
    rank_info = candidate.get("delt_region_rank")
    if not rank_info or rank_info.get("region") != region:
        return None
    try:
        return int(rank_info["rank"])
    except (KeyError, TypeError, ValueError):
        return None


def sort_delt_candidates_for_region(
    region: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    indexed_candidates = list(enumerate(candidates))

    def sort_key(item: tuple[int, dict[str, Any]]) -> tuple[Any, ...]:
        index, candidate = item
        region_rank = candidate_delt_region_rank(candidate, region)
        overall_rank = candidate_target_rank(candidate, "delts")
        return (
            region_rank is None,
            region_rank if region_rank is not None else 10**9,
            overall_rank is None,
            overall_rank if overall_rank is not None else 10**9,
            -float(candidate.get("final_score", 0.0) or 0.0),
            index,
        )

    return [candidate for _, candidate in sorted(indexed_candidates, key=sort_key)]


def select_delt_candidates_for_llm(
    target_candidates: list[dict[str, Any]],
    per_head: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    missing_region_slots = 0

    for region in DELT_REGION_ORDER:
        region_candidates = sort_delt_candidates_for_region(
            region,
            [
                candidate
                for candidate in target_candidates
                if candidate.get("delt_region") == region
            ],
        )
        selected_for_region = region_candidates[:per_head]
        missing_region_slots += max(0, per_head - len(selected_for_region))
        for candidate in selected_for_region:
            if candidate["exercise_id"] in selected_ids:
                continue
            selected.append(candidate)
            selected_ids.add(candidate["exercise_id"])

    if missing_region_slots:
        general_candidates = sort_candidates_for_target(
            "delts",
            [
                candidate
                for candidate in target_candidates
                if candidate.get("delt_region") not in DELT_REGION_LABELS
            ],
        )
        for candidate in general_candidates:
            if len(selected) >= (per_head * len(DELT_REGION_ORDER)):
                break
            if candidate["exercise_id"] in selected_ids:
                continue
            selected.append(candidate)
            selected_ids.add(candidate["exercise_id"])
            missing_region_slots -= 1
            if missing_region_slots <= 0:
                break

    return selected


def build_llm_candidate_pool(
    request: ProtocolRequest,
    candidates: list[dict[str, Any]],
    per_muscle: int = LLM_CANDIDATES_PER_MUSCLE,
) -> dict[str, Any]:
    assign_delt_region_ranks(candidates)
    by_target: dict[str, list[dict[str, Any]]] = {}
    allowed_ids: set[str] = set()
    for muscle in request.muscles:
        selected = select_candidates_for_llm_target(muscle, candidates, per_muscle)
        by_target[muscle] = [
            compact_candidate_for_llm(candidate, muscle)
            for candidate in selected
        ]
        allowed_ids.update(candidate["exercise_id"] for candidate in selected)

    return {
        "selection_policy": "top_3_per_muscle_top_3_per_delt_head",
        "per_muscle_limit": per_muscle,
        "per_delt_head_limit": per_muscle,
        "by_target": by_target,
        "allowed_exercise_ids": sorted(allowed_ids),
    }


def build_candidate_lookup_from_pool(
    candidate_pool: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    allowed_ids = set(candidate_pool.get("allowed_exercise_ids", []))
    return {
        candidate["exercise_id"]: candidate
        for candidate in candidates
        if candidate["exercise_id"] in allowed_ids
    }


def build_allowed_targets_from_pool(candidate_pool: dict[str, Any]) -> dict[str, set[str]]:
    allowed: dict[str, set[str]] = {}
    for target, target_candidates in candidate_pool.get("by_target", {}).items():
        allowed[target] = {
            item.get("exercise_id", "")
            for item in target_candidates
            if item.get("exercise_id")
        }
    return allowed


def candidate_balance_targets(candidate: dict[str, Any]) -> list[str]:
    primary_targets = candidate.get("requested_primary_targets", [])
    if primary_targets:
        return list(primary_targets)
    return list(candidate.get("requested_all_targets", []))


def build_delt_balanced_pool(
    candidates: list[dict[str, Any]],
    cap: int,
    region_order: list[str] | None = None,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    for region in region_order or DELT_REGION_ORDER:
        for candidate in candidates:
            if candidate["exercise_id"] in selected_ids:
                continue
            if candidate.get("delt_region") != region:
                continue
            selected.append(candidate)
            selected_ids.add(candidate["exercise_id"])
            break

    for candidate in candidates:
        if len(selected) >= cap:
            break
        if candidate["exercise_id"] in selected_ids:
            continue
        selected.append(candidate)
        selected_ids.add(candidate["exercise_id"])

    return selected[:cap]


def ordered_muscles(muscles: set[str] | list[str]) -> list[str]:
    muscle_set = set(muscles)
    ordered = [muscle for muscle in CANONICAL_MUSCLE_ORDER if muscle in muscle_set]
    ordered.extend(sorted(muscle_set - set(ordered)))
    return ordered


def split_part(label: str, muscles: set[str] | list[str]) -> dict[str, Any] | None:
    return split_part_with_regions(label=label, muscles=muscles)


def split_part_with_regions(
    label: str,
    muscles: set[str] | list[str],
    delt_regions: list[str] | None = None,
) -> dict[str, Any] | None:
    ordered = ordered_muscles(muscles)
    if not ordered:
        return None
    part = {
        "label": label,
        "target_muscles": ordered,
        "focus": f"{label}: {', '.join(display_muscle_label(muscle) for muscle in ordered)}",
    }
    if delt_regions:
        part["delt_regions"] = list(delt_regions)
    return part


def push_split_part(push_muscles: set[str], split_rear_delts: bool) -> dict[str, Any] | None:
    regions = ["lateral", "anterior"] if split_rear_delts and "delts" in push_muscles else None
    return split_part_with_regions("Push", push_muscles, delt_regions=regions)


def pull_split_part(
    pull_muscles: set[str],
    requested: set[str],
    split_rear_delts: bool,
) -> dict[str, Any] | None:
    targets = set(pull_muscles)
    if split_rear_delts and "delts" in requested:
        targets.add("delts")
    label = "Pull/Rear Delts" if "delts" in targets else "Pull"
    regions = ["posterior"] if "delts" in targets else None
    return split_part_with_regions(label, targets, delt_regions=regions)


def compact_split_parts(parts: list[dict[str, Any] | None]) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for part in parts:
        if not part:
            continue
        if part["target_muscles"] not in [item["target_muscles"] for item in compacted]:
            compacted.append(part)
    return compacted


def build_split_pattern(request: ProtocolRequest) -> list[dict[str, Any]]:
    requested = set(request.muscles)
    push = requested & PUSH_MUSCLES
    pull = requested & PULL_MUSCLES
    legs = requested & LEG_MUSCLES
    core = requested & CORE_MUSCLES
    arms = requested & ARM_MUSCLES
    upper = push | pull
    split_rear_delts = "delts" in requested and bool(pull or (arms - {"triceps"}))

    if request.split_template == "full_body" or len(request.muscles) == 1:
        return compact_split_parts([split_part("Full Body", requested)])

    if request.split_template == "push_pull_legs":
        return compact_split_parts(
            [
                push_split_part(push, split_rear_delts),
                pull_split_part(pull, requested, split_rear_delts),
                split_part("Legs", legs | core),
            ]
        )

    if request.split_template == "push_pull":
        return compact_split_parts(
            [
                push_split_part(push, split_rear_delts),
                pull_split_part(pull, requested, split_rear_delts),
                split_part("Legs/Core", legs | core),
            ]
        )

    if request.split_template == "upper_lower":
        return compact_split_parts(
            [
                split_part("Upper", upper),
                split_part("Lower/Core", legs | core),
            ]
        )

    # Auto keeps this intentionally simple: choose a familiar split family, then
    # rank exercises inside each bucket using the existing evidence-aware scorer.
    if legs and upper and request.sessions >= 3:
        return compact_split_parts(
            [
                push_split_part(push, split_rear_delts),
                pull_split_part(pull, requested, split_rear_delts),
                split_part("Legs/Core", legs | core),
            ]
        )
    if legs and upper:
        return compact_split_parts(
            [
                split_part("Upper", upper),
                split_part("Lower/Core", legs | core),
            ]
        )
    if upper and arms and not (pull - ARM_MUSCLES) and request.sessions >= 2:
        pull_side_arms = requested & (PULL_MUSCLES | {"biceps", "forearms"})
        return compact_split_parts(
            [
                push_split_part(push, split_rear_delts),
                pull_split_part(pull_side_arms, requested, split_rear_delts),
            ]
        )
    if push and pull and request.sessions >= 2:
        return compact_split_parts(
            [
                push_split_part(push, split_rear_delts),
                pull_split_part(pull, requested, split_rear_delts),
            ]
        )

    return compact_split_parts(
        [
            split_part("Upper", upper),
            split_part("Legs/Core", legs | core),
            split_part("Full Body", requested),
        ]
    )


def build_split_schedule(request: ProtocolRequest) -> list[dict[str, Any]]:
    pattern = build_split_pattern(request)
    if not pattern:
        pattern = compact_split_parts([split_part("Full Body", set(request.muscles))])
    return [pattern[index % len(pattern)] for index in range(request.sessions)]


def build_balanced_candidate_pool(
    request: ProtocolRequest,
    candidates: list[dict[str, Any]],
    exercises_per_session: int,
) -> list[dict[str, Any]]:
    if len(request.muscles) == 1:
        unique_exercise_cap = min(
            len(candidates),
            determine_unique_exercise_cap(request, exercises_per_session),
        )
        if request.muscles == ["delts"]:
            return build_delt_balanced_pool(candidates, unique_exercise_cap)
        return candidates[:unique_exercise_cap]

    desired_pool_size = min(
        len(candidates),
        max(
            exercises_per_session * 2,
            (len(request.muscles) * 2) + (2 if "delts" in request.muscles else 0),
        ),
    )
    per_muscle_cap = max(1, (desired_pool_size + len(request.muscles) - 1) // len(request.muscles))
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    muscle_counts = {muscle: 0 for muscle in request.muscles}

    # First ensure every requested muscle gets at least one representative if possible.
    for muscle in request.muscles:
        for candidate in candidates:
            if candidate["exercise_id"] in selected_ids:
                continue
            if muscle not in candidate_balance_targets(candidate):
                continue
            selected.append(candidate)
            selected_ids.add(candidate["exercise_id"])
            for target in candidate_balance_targets(candidate):
                muscle_counts[target] += 1
            break

    if "delts" in request.muscles:
        delt_region_order = (
            DELT_MULTI_SESSION_REGION_ORDER
            if request.sessions >= 4
            else DELT_REGION_ORDER
        )
        for candidate in build_delt_balanced_pool(
            candidates,
            len(delt_region_order),
            region_order=delt_region_order,
        ):
            if len(selected) >= desired_pool_size:
                break
            if candidate["exercise_id"] in selected_ids:
                continue
            selected.append(candidate)
            selected_ids.add(candidate["exercise_id"])
            for target in candidate_balance_targets(candidate):
                muscle_counts[target] += 1

    # For repeated weekly splits, keep more than one option for each non-shoulder
    # target before letting the highest-scoring muscles consume the pool.
    minimum_repeated_target_count = 2 if request.sessions >= 2 else 1
    for muscle in request.muscles:
        if muscle == "delts":
            continue
        while (
            len(selected) < desired_pool_size
            and muscle_counts.get(muscle, 0) < min(per_muscle_cap, minimum_repeated_target_count)
        ):
            added = False
            for candidate in candidates:
                if candidate["exercise_id"] in selected_ids:
                    continue
                if muscle not in candidate_balance_targets(candidate):
                    continue
                selected.append(candidate)
                selected_ids.add(candidate["exercise_id"])
                for target in candidate_balance_targets(candidate):
                    muscle_counts[target] += 1
                added = True
                break
            if not added:
                break

    # Then fill the pool while capping how much any one muscle can dominate.
    for candidate in candidates:
        if len(selected) >= desired_pool_size:
            break
        if candidate["exercise_id"] in selected_ids:
            continue
        targets = candidate_balance_targets(candidate)
        if not targets:
            continue
        if all(muscle_counts.get(target, 0) >= per_muscle_cap for target in targets):
            continue
        selected.append(candidate)
        selected_ids.add(candidate["exercise_id"])
        for target in targets:
            muscle_counts[target] += 1

    # Final backfill in case strict caps leave the pool too small.
    for candidate in candidates:
        if len(selected) >= desired_pool_size:
            break
        if candidate["exercise_id"] in selected_ids:
            continue
        selected.append(candidate)
        selected_ids.add(candidate["exercise_id"])

    return selected[:desired_pool_size]


def select_session_candidates(
    request: ProtocolRequest,
    selected_pool: list[dict[str, Any]],
    session_index: int,
    exercises_per_session: int,
    target_muscles: list[str] | None = None,
    delt_regions: list[str] | None = None,
) -> list[dict[str, Any]]:
    if not selected_pool:
        return []

    session_targets = target_muscles or request.muscles
    target_set = set(session_targets)
    session_pool = [
        candidate
        for candidate in selected_pool
        if candidate_matches_session(candidate, target_set, delt_regions)
    ]
    if not session_pool:
        session_pool = selected_pool

    session_slot_count = max(exercises_per_session, len(session_targets))
    if len(request.muscles) == 1:
        return session_pool[:session_slot_count]

    ordered_pool = session_pool[session_index:] + session_pool[:session_index]
    chosen: list[dict[str, Any]] = []
    covered_muscles: set[str] = set()

    for candidate in ordered_pool:
        if len(chosen) >= session_slot_count:
            break
        targets = [
            target for target in candidate_balance_targets(candidate) if target in target_set
        ]
        if any(target not in covered_muscles for target in targets):
            chosen.append(candidate)
            covered_muscles.update(targets)

    for candidate in ordered_pool:
        if len(chosen) >= session_slot_count:
            break
        if candidate["exercise_id"] in {item["exercise_id"] for item in chosen}:
            continue
        chosen.append(candidate)

    return chosen[:session_slot_count]


def candidate_matches_session(
    candidate: dict[str, Any],
    target_set: set[str],
    delt_regions: list[str] | None = None,
) -> bool:
    targets = set(candidate_balance_targets(candidate))
    if not target_set.intersection(targets):
        return False
    if "delts" in targets and "delts" in target_set and delt_regions:
        return candidate.get("delt_region") in set(delt_regions)
    return True


def assign_reference_pmids(
    candidate: dict[str, Any],
    findings: list[dict[str, Any]],
    request: ProtocolRequest,
) -> list[str]:
    return [evidence["pmid"] for evidence in assign_reference_evidence(candidate, findings, request)]


def finding_text_for_relevance(finding: dict[str, Any]) -> str:
    return f"{finding.get('title', '')} {finding.get('snippet', '')}"


def is_goal_relevant_finding(finding: dict[str, Any], goal: str) -> bool:
    text = normalize_text(finding_text_for_relevance(finding))
    return any(term in text for term in GOAL_DIRECT_EVIDENCE_TERMS.get(goal, set()))


def is_reference_finding_relevant_to_candidate(
    candidate: dict[str, Any],
    finding: dict[str, Any],
    request: ProtocolRequest,
) -> bool:
    text = finding_text_for_relevance(finding)
    candidate_terms = [
        term for term in get_candidate_specific_terms(candidate) if len(term) >= 4
    ]
    target_relevance = score_text_relevance(text, get_target_terms(request, candidate))

    targets = set(candidate_balance_targets(candidate))
    if "delts" in targets:
        return score_text_relevance(text, DELT_REFERENCE_TERMS) > 0

    candidate_relevance = score_text_relevance(text, candidate_terms)
    if candidate_relevance > 0:
        return True

    return target_relevance >= 2


def reference_finding_relevance_score(
    candidate: dict[str, Any],
    finding: dict[str, Any],
    request: ProtocolRequest,
) -> int:
    text = finding_text_for_relevance(finding)
    if "delts" in candidate_balance_targets(candidate):
        return score_text_relevance(text, DELT_REFERENCE_TERMS)
    return score_text_relevance(text, get_target_terms(request, candidate))


def fallback_reference_evidence_from_findings(
    candidate: dict[str, Any],
    findings: list[dict[str, Any]],
    request: ProtocolRequest,
    existing_pmids: set[str],
) -> list[dict[str, Any]]:
    fallback_items = []
    for finding in findings:
        pmid = str(finding.get("pmid", "")).strip()
        if not pmid or pmid in existing_pmids:
            continue
        if not is_goal_relevant_finding(finding, request.goal):
            continue
        if not is_reference_finding_relevant_to_candidate(candidate, finding, request):
            continue
        fallback_items.append(
            {
                "pmid": pmid,
                "title": finding.get("title", "Retrieved science finding"),
                "publication_year": finding.get("publication_year"),
                "evidence_tier": finding.get("evidence_tier", "other"),
                "trust_label": finding.get("trust_label", "standard"),
                "manual_review_required": bool(finding.get("manual_review_required", False)),
                "snippet": finding.get("snippet", ""),
            }
        )
        existing_pmids.add(pmid)
        if len(fallback_items) >= 1:
            break
    return fallback_items


def assign_reference_evidence(
    candidate: dict[str, Any],
    findings: list[dict[str, Any]],
    request: ProtocolRequest,
) -> list[dict[str, Any]]:
    standard_items = []
    lower_trust_items = []
    for study in candidate.get("top_studies", []):
        if (
            study.get("pmid")
            and not study.get("manual_review_required", False)
            and has_request_relevant_direct_evidence(study)
        ):
            standard_items.append(
                {
                    "pmid": study["pmid"],
                    "title": study.get("title", "Direct exercise study"),
                    "publication_year": study.get("publication_year"),
                    "evidence_tier": study.get("evidence_tier", "other"),
                    "trust_label": "standard",
                    "manual_review_required": False,
                    "snippet": study.get("study_summary", ""),
                }
            )

    for study in candidate.get("top_studies", []):
        if (
            study.get("pmid")
            and study.get("manual_review_required", False)
            and has_request_relevant_direct_evidence(study)
        ):
            lower_trust_items.append(
                {
                    "pmid": study["pmid"],
                    "title": study.get("title", "Direct exercise study"),
                    "publication_year": study.get("publication_year"),
                    "evidence_tier": study.get("evidence_tier", "other"),
                    "trust_label": "lower-trust",
                    "manual_review_required": True,
                    "snippet": study.get("study_summary", ""),
                }
            )

    direct_items = standard_items + lower_trust_items
    if direct_items:
        return direct_items

    existing_pmids = {item["pmid"] for item in direct_items if item.get("pmid")}
    return fallback_reference_evidence_from_findings(
        candidate,
        findings,
        request,
        existing_pmids,
    )


def build_protocol_outline(
    request: ProtocolRequest,
    candidates: list[dict[str, Any]],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    exercises_per_session = determine_exercises_per_session(request)
    selected_pool = build_balanced_candidate_pool(request, candidates, exercises_per_session)
    split_schedule = build_split_schedule(request)

    sessions = []
    for session_index in range(request.sessions):
        split_part_for_session = split_schedule[session_index]
        session_target_muscles = split_part_for_session["target_muscles"]
        exercises_for_session = []
        session_candidates = select_session_candidates(
            request=request,
            selected_pool=selected_pool,
            session_index=session_index,
            exercises_per_session=exercises_per_session,
            target_muscles=session_target_muscles,
            delt_regions=split_part_for_session.get("delt_regions"),
        )
        for candidate in session_candidates:
            reference_evidence = assign_reference_evidence(candidate, findings, request)
            balance_targets = candidate_balance_targets(candidate)
            target_muscle = next(
                (muscle for muscle in session_target_muscles if muscle in balance_targets),
                next(
                    (muscle for muscle in request.muscles if muscle in balance_targets),
                    balance_targets[0] if balance_targets else request.muscles[0],
                ),
            )
            entry = {
                "exercise_id": candidate["exercise_id"],
                "name": candidate["name"],
                "target_muscle": target_muscle,
                "target_label": format_target_label(target_muscle, candidate),
                "rank_display": format_candidate_rank_summary(candidate, target_muscle),
                "prescription": candidate["prescription_seed"],
                "selection_reason": candidate["selection_reason"],
                "reference_pmids": [item["pmid"] for item in reference_evidence],
                "reference_evidence": reference_evidence,
                "lower_trust_evidence": any(
                    item.get("manual_review_required", False) for item in reference_evidence
                ),
            }
            exercises_for_session.append(entry)
        sessions.append(
            {
                "session_number": session_index + 1,
                "focus": split_part_for_session["focus"],
                "split_label": split_part_for_session["label"],
                "target_muscles": session_target_muscles,
                "delt_regions": split_part_for_session.get("delt_regions", []),
                "exercises": exercises_for_session,
            }
        )

    return {
        "sessions": sessions,
        "exercises_per_session": exercises_per_session,
        "selected_pool_size": len(selected_pool),
        "split_template": request.split_template,
        "split_pattern": build_split_pattern(request),
    }


def normalize_plan_muscle(raw_value: Any) -> str:
    return normalize_atom(str(raw_value or ""), aliases=MUSCLE_ALIASES)


def extract_json_object(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None, ["Gemma did not return a JSON object."]
        try:
            parsed = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            return None, [f"Gemma returned invalid JSON: {exc.msg}."]

    if not isinstance(parsed, dict):
        return None, ["Gemma JSON response must be an object."]
    return parsed, []


def validate_llm_protocol_plan(
    plan: dict[str, Any],
    request: ProtocolRequest,
    candidate_pool: dict[str, Any],
) -> list[str]:
    errors = []
    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        return ["Gemma plan must include a sessions array."]
    if len(sessions) != request.sessions:
        errors.append(
            f"Gemma plan has {len(sessions)} session(s), expected {request.sessions}."
        )

    expected_numbers = set(range(1, request.sessions + 1))
    seen_numbers: set[int] = set()
    allowed_ids = set(candidate_pool.get("allowed_exercise_ids", []))
    allowed_by_target = build_allowed_targets_from_pool(candidate_pool)
    max_exercises_per_session = determine_exercises_per_session(request)
    min_exercises_per_session = determine_min_exercises_per_session(request, candidate_pool)
    target_session_numbers = {muscle: set() for muscle in request.muscles}

    for raw_session in sessions:
        if not isinstance(raw_session, dict):
            errors.append("Every session must be a JSON object.")
            continue
        session_number = raw_session.get("session_number")
        if not isinstance(session_number, int):
            errors.append("Every session must include an integer session_number.")
            continue
        if session_number not in expected_numbers:
            errors.append(f"Unexpected session_number: {session_number}.")
        if session_number in seen_numbers:
            errors.append(f"Duplicate session_number: {session_number}.")
        seen_numbers.add(session_number)

        if not str(raw_session.get("split_label", "")).strip():
            errors.append(f"Session {session_number} is missing split_label.")
        if not str(raw_session.get("focus", "")).strip():
            errors.append(f"Session {session_number} is missing focus.")

        exercises = raw_session.get("exercises")
        if not isinstance(exercises, list):
            errors.append(f"Session {session_number} must include an exercises array.")
            continue
        if not exercises:
            errors.append(f"Session {session_number} has no exercises.")
        if len(exercises) < min_exercises_per_session:
            errors.append(
                f"Session {session_number} has {len(exercises)} exercise(s); min is {min_exercises_per_session}."
            )
        if len(exercises) > max_exercises_per_session:
            errors.append(
                f"Session {session_number} has {len(exercises)} exercises; max is {max_exercises_per_session}."
            )

        seen_session_ids: set[str] = set()
        for raw_exercise in exercises:
            if not isinstance(raw_exercise, dict):
                errors.append(f"Session {session_number} has a non-object exercise entry.")
                continue
            exercise_id = str(raw_exercise.get("exercise_id", "")).strip()
            target_muscle = normalize_plan_muscle(raw_exercise.get("target_muscle"))
            if not exercise_id:
                errors.append(f"Session {session_number} has an exercise without exercise_id.")
                continue
            if exercise_id in seen_session_ids:
                errors.append(
                    f"Session {session_number} repeats exercise_id {exercise_id}."
                )
            seen_session_ids.add(exercise_id)
            if exercise_id not in allowed_ids:
                errors.append(f"Unknown or disallowed exercise_id: {exercise_id}.")
            if target_muscle not in request.muscles:
                errors.append(
                    f"Exercise {exercise_id} uses unsupported target_muscle '{raw_exercise.get('target_muscle')}'."
                )
                continue
            if exercise_id not in allowed_by_target.get(target_muscle, set()):
                errors.append(
                    f"Exercise {exercise_id} is not allowed for target_muscle {target_muscle}."
                )
                continue
            target_session_numbers[target_muscle].add(session_number)

    missing_numbers = sorted(expected_numbers - seen_numbers)
    if missing_numbers:
        errors.append(
            "Missing session_number(s): " + ", ".join(str(number) for number in missing_numbers) + "."
        )

    for muscle in request.muscles:
        if allowed_by_target.get(muscle) and not target_session_numbers[muscle]:
            errors.append(f"Requested target muscle was not scheduled: {muscle}.")

    if len(request.muscles) > 1 and request.sessions >= 3:
        for muscle, session_numbers in target_session_numbers.items():
            if len(session_numbers) == request.sessions:
                errors.append(
                    f"Target muscle {muscle} appears in every session; distribute recovery better."
                )

    return sorted(set(errors))


def build_outline_from_llm_plan(
    plan: dict[str, Any],
    request: ProtocolRequest,
    candidate_lookup: dict[str, dict[str, Any]],
    findings: list[dict[str, Any]],
    candidate_pool: dict[str, Any],
) -> dict[str, Any]:
    sessions = []
    split_pattern = []
    for raw_session in sorted(plan.get("sessions", []), key=lambda item: item["session_number"]):
        exercises_for_session = []
        target_muscles = []
        for raw_exercise in raw_session.get("exercises", []):
            exercise_id = str(raw_exercise["exercise_id"]).strip()
            target_muscle = normalize_plan_muscle(raw_exercise["target_muscle"])
            candidate = candidate_lookup[exercise_id]
            reference_evidence = assign_reference_evidence(candidate, findings, request)
            if target_muscle not in target_muscles:
                target_muscles.append(target_muscle)
            exercises_for_session.append(
                {
                    "exercise_id": candidate["exercise_id"],
                    "name": candidate["name"],
                    "target_muscle": target_muscle,
                    "target_label": format_target_label(target_muscle, candidate),
                    "rank_display": format_candidate_rank_summary(candidate, target_muscle),
                    "prescription": normalize_llm_prescription(raw_exercise, request.goal)
                    or candidate["prescription_seed"],
                    "selection_reason": candidate["selection_reason"],
                    "reference_pmids": [item["pmid"] for item in reference_evidence],
                    "reference_evidence": reference_evidence,
                    "lower_trust_evidence": any(
                        item.get("manual_review_required", False)
                        for item in reference_evidence
                    ),
                }
            )

        label = str(raw_session.get("split_label", "")).strip()
        focus = str(raw_session.get("focus", "")).strip()
        sessions.append(
            {
                "session_number": raw_session["session_number"],
                "focus": focus,
                "split_label": label,
                "target_muscles": target_muscles,
                "delt_regions": [],
                "exercises": exercises_for_session,
            }
        )
        if label and label not in [item.get("label") for item in split_pattern]:
            split_pattern.append(
                {
                    "label": label,
                    "target_muscles": target_muscles,
                    "focus": focus,
                }
            )

    split_summary = str(plan.get("split_summary", "")).strip()
    if not split_summary:
        split_summary = " / ".join(item["label"] for item in split_pattern if item.get("label"))

    return {
        "sessions": sessions,
        "exercises_per_session": determine_exercises_per_session(request),
        "selected_pool_size": len(candidate_pool.get("allowed_exercise_ids", [])),
        "split_template": request.split_template,
        "split_pattern": split_pattern,
        "split_summary": split_summary,
        "confidence_notes": [
            str(note).strip()
            for note in plan.get("confidence_notes", [])
            if str(note).strip()
        ]
        if isinstance(plan.get("confidence_notes", []), list)
        else [],
        "planner": "llm",
    }


def build_semantic_query(request: ProtocolRequest, candidates: list[dict[str, Any]]) -> str:
    """The text embedded to retrieve science findings for a request.

    Scoped to what the science should be *about*: the target muscles, the training goal,
    and anything the user wrote. Session count, split template, equipment and candidate
    exercise names are deliberately excluded -- they describe how a plan is laid out
    rather than what to retrieve, and catalog product names carry variant and equipment
    words that abstracts never use, so including them pulls the embedding off-topic.

    Measured over 49 labelled topic queries (research/s2c_query_repair): this scoping
    reaches nDCG@10 0.215 on held-out queries against 0.091 for the same request
    rendered as a full field list, p = 0.0088, with no change in how often a request
    yields any citation.

    ``candidates`` stays in the signature because exercise-specificity is enforced
    downstream, by the lexical re-rank and acceptance gate in query_findings.
    """
    parts = [f"{', '.join(request.muscles)} {request.goal} resistance training"]
    if request.notes:
        parts.append(request.notes)
    return " | ".join(parts)


@lru_cache(maxsize=1)
def get_vector_collection(vector_store_path: Path = DEFAULT_VECTOR_STORE_PATH):
    if not vector_store_path.exists():
        raise DemoConfigurationError(
            f"Vector store not found at {vector_store_path}. Run `python3 scripts/build_vector_store.py` first."
        )

    try:
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    except ImportError as exc:  # pragma: no cover
        raise DemoConfigurationError(
            "Missing vector-store dependencies. Install requirements with `python3 -m pip install -r requirements.txt`."
        ) from exc

    client = chromadb.PersistentClient(path=str(vector_store_path))
    collection_names = {collection.name for collection in client.list_collections()}
    if VECTOR_COLLECTION_NAME not in collection_names:
        raise DemoConfigurationError(
            "The Chroma collection 'science_corpus' is missing. Run `python3 scripts/build_vector_store.py` first."
        )

    embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return client.get_collection(name=VECTOR_COLLECTION_NAME, embedding_function=embedding_fn)


def dedupe_findings(raw_findings: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    ordered = []
    seen_doc_ids = set()
    for finding in raw_findings:
        doc_id = finding.get("doc_id")
        if doc_id in seen_doc_ids:
            continue
        ordered.append(finding)
        seen_doc_ids.add(doc_id)
        if len(ordered) >= limit:
            break
    return ordered


def query_findings(
    request: ProtocolRequest,
    candidates: list[dict[str, Any]],
    science_payload: dict[str, Any],
    limit: int = 6,
) -> list[dict[str, Any]]:
    if not candidates:
        return []

    docs_by_id = {
        document["doc_id"]: document for document in science_payload.get("documents", [])
    }
    collection = get_vector_collection()
    query_text = build_semantic_query(request, candidates)

    base_include = ["documents", "metadatas", "distances"]
    raw_findings = []

    def run_query(where_filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        response = collection.query(
            query_texts=[query_text],
            n_results=max(limit * 2, 8),
            include=base_include,
            where=where_filter,
        )
        findings = []
        documents = response.get("documents", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        distances = response.get("distances", [[]])[0]
        for document_text, metadata, distance in zip(documents, metadatas, distances):
            if float(distance) > MAX_FINDING_DISTANCE:
                continue
            doc_id = metadata.get("doc_id")
            source_doc = docs_by_id.get(doc_id, {})
            findings.append(
                {
                    "doc_id": doc_id,
                    "pmid": str(metadata.get("pmid")),
                    "title": source_doc.get("title", "Unknown title"),
                    "publication_year": metadata.get(
                        "publication_year", source_doc.get("publication_year")
                    ),
                    "evidence_tier": metadata.get(
                        "evidence_tier", source_doc.get("evidence_tier", "other")
                    ),
                    "retrieval_weight": round(float(metadata.get("retrieval_weight", 0.0)), 4),
                    "distance": round(float(distance), 4),
                    "manual_review_required": bool(
                        metadata.get("manual_review_required", False)
                    ),
                    "topic_clusters": [
                        cluster
                        for cluster in str(metadata.get("topic_clusters", "")).split(",")
                        if cluster
                    ],
                    "snippet": " ".join(str(document_text).split()),
                    "trust_label": (
                        "lower-trust"
                        if bool(metadata.get("manual_review_required", False))
                        else "standard"
                    ),
                }
            )
        return findings

    raw_findings.extend(run_query(where_filter={"manual_review_required": False}))
    raw_findings = dedupe_findings(raw_findings, limit * 2)

    if len(raw_findings) < limit:
        unrestricted = run_query(where_filter=None)
        raw_findings.extend(unrestricted)
        raw_findings = dedupe_findings(raw_findings, limit * 2)

    ranked_findings = []
    target_terms = get_target_terms(request)
    for finding in raw_findings:
        finding_text = f"{finding.get('title', '')} {finding.get('snippet', '')}"
        request_relevance = score_text_relevance(
            finding_text,
            target_terms,
        )
        request_relevance = apply_ambiguity_penalty(finding_text, request, request_relevance)
        candidate_relevance = 0
        for candidate in candidates[:4]:
            candidate_relevance = max(
                candidate_relevance,
                score_text_relevance(
                    finding_text,
                    get_candidate_specific_terms(candidate),
                ),
            )
        candidate_relevance = apply_ambiguity_penalty(finding_text, request, candidate_relevance)
        finding["request_relevance_score"] = request_relevance
        finding["candidate_relevance_score"] = candidate_relevance
        finding["target_relevance_score"] = (candidate_relevance * 2) + request_relevance
        ranked_findings.append(finding)

    ranked_findings.sort(
        key=lambda item: (
            item.get("target_relevance_score", 0),
            float(item.get("retrieval_weight", 0.0)),
            -(float(item.get("distance", 0.0))),
        ),
        reverse=True,
    )

    relevant_findings = [
        finding
        for finding in ranked_findings
        if (
            (
                finding["candidate_relevance_score"] > 0
                and finding["request_relevance_score"] > 0
            )
            or finding["request_relevance_score"] >= 2
        )
    ]
    if relevant_findings:
        return relevant_findings[:limit]

    # Nothing passed both the distance ceiling and the keyword-relevance bar.
    # Returning weak top-k here would put off-topic citations in the appendix;
    # an honestly empty findings list is better.
    return []


def build_finding_from_science_document(document: dict[str, Any]) -> dict[str, Any]:
    snippet_source = str(document.get("abstract") or document.get("text") or "")
    snippet = " ".join(snippet_source.split())
    return {
        "doc_id": document.get("doc_id"),
        "pmid": str(document.get("pmid", "")),
        "title": document.get("title", "Unknown title"),
        "publication_year": document.get("publication_year"),
        "evidence_tier": document.get("evidence_tier", "other"),
        "retrieval_weight": round(float(document.get("retrieval_weight", 0.0) or 0.0), 4),
        "manual_review_required": bool(document.get("manual_review_required", False)),
        "topic_clusters": document.get("topic_clusters", []),
        "snippet": snippet[:700],
        "trust_label": (
            "lower-trust"
            if bool(document.get("manual_review_required", False))
            else "standard"
        ),
    }


def enrich_findings_with_target_documents(
    request: ProtocolRequest,
    candidates: list[dict[str, Any]],
    science_payload: dict[str, Any],
    findings: list[dict[str, Any]],
    limit: int = 8,
) -> list[dict[str, Any]]:
    existing_pmids = {
        str(finding.get("pmid", "")).strip()
        for finding in findings
        if str(finding.get("pmid", "")).strip()
    }
    candidates_needing_reference = [
        candidate
        for candidate in candidates
        if not candidate.get("top_studies")
        and "delts" in candidate_balance_targets(candidate)
    ]
    if not candidates_needing_reference:
        return findings

    scored_findings = []
    for document in science_payload.get("documents", []):
        finding = build_finding_from_science_document(document)
        pmid = str(finding.get("pmid", "")).strip()
        if not pmid or pmid in existing_pmids:
            continue
        if not is_goal_relevant_finding(finding, request.goal):
            continue

        relevance = 0
        for candidate in candidates_needing_reference:
            if not is_reference_finding_relevant_to_candidate(candidate, finding, request):
                continue
            relevance = max(
                relevance,
                reference_finding_relevance_score(candidate, finding, request),
            )
        if relevance <= 0:
            continue
        scored_findings.append(
            (
                relevance,
                float(document.get("retrieval_weight", 0.0) or 0.0),
                float(document.get("quality_score", 0.0) or 0.0),
                int(document.get("publication_year", 0) or 0),
                finding,
            )
        )

    enriched = list(findings)
    for *_score, finding in sorted(
        scored_findings,
        key=lambda item: item[:4],
        reverse=True,
    ):
        if len(enriched) >= limit:
            break
        pmid = str(finding.get("pmid", "")).strip()
        if pmid in existing_pmids:
            continue
        enriched.append(finding)
        existing_pmids.add(pmid)
    return enriched


def build_warning_notes(
    request: ProtocolRequest,
    candidates: list[dict[str, Any]],
    outline: dict[str, Any],
    findings: list[dict[str, Any]],
) -> list[str]:
    warnings = []
    recommended_pool = request.sessions * determine_exercises_per_session(request)
    if len(candidates) < recommended_pool:
        warnings.append(
            "Candidate pool is limited for these constraints, so some sessions may reuse close substitutes or lower-confidence options."
        )

    selected_entries = [
        exercise
        for session in outline.get("sessions", [])
        for exercise in session.get("exercises", [])
    ]
    if any(entry.get("lower_trust_evidence", False) for entry in selected_entries):
        warnings.append(
            "Some direct exercise-name studies in this demo are flagged for manual review and should be treated as lower-trust support."
        )

    if not any(candidate.get("non_reviewed_direct_evidence", 0) > 0 for candidate in candidates[:6]):
        warnings.append(
            "The selected exercises rely more on catalog scoring and general retrieved science than on direct exercise-name study matches."
        )

    if not findings:
        warnings.append(
            "No strongly matching studies passed the retrieval quality bar for this request, "
            "so the evidence appendix only lists direct per-exercise studies, if any."
        )

    return warnings


def build_planning_constraints(request: ProtocolRequest) -> dict[str, Any]:
    max_exercises = determine_exercises_per_session(request)
    min_exercises = determine_min_exercises_per_session(request)
    if request.goal == "strength":
        goal_guidance = (
            "Prioritize high-loading strength-compatible exercises, direct strength evidence, "
            "and enough recovery between repeated target muscles."
        )
    else:
        goal_guidance = (
            "Prioritize direct hypertrophy evidence, strong target-muscle matches, sensible weekly "
            "frequency, and balanced exposure across requested muscles."
        )

    if request.exercises_per_session is not None:
        session_fill_guidance = (
            f"Every session must include exactly {max_exercises} exercises because the user "
            "provided exercises_per_session. Do not underfill or overfill sessions."
        )
    else:
        session_fill_guidance = (
            f"Every session must include {min_exercises}-{max_exercises} exercises. "
            "Do not create a one-exercise session for a multi-exercise weekly protocol."
        )

    return {
        "goal_guidance": goal_guidance,
        "exact_session_count": request.sessions,
        "min_exercises_per_session": min_exercises,
        "max_exercises_per_session": max_exercises,
        "session_fill_guidance": session_fill_guidance,
        "weekly_frequency_guidance": (
            "For multi-muscle requests with enough sessions, aim for about 2 exposures per requested "
            "muscle. Do not place the same requested muscle in every session when recovery-friendly "
            "alternatives exist. Prefer repeating the strongest 1-2 exercises for a repeated muscle "
            "over adding lower-ranked variety for novelty."
        ),
        "shoulder_guidance": (
            "If shoulders/delts are requested, treat anterior, lateral, and rear delts as meaningful "
            "regions. Lateral/anterior delt work can pair with push days; rear delt work can pair with "
            "pull or biceps days. A third shoulder exercise is reasonable when it covers a different "
            "delt region."
        ),
        "ordering_guidance": (
            "Within a session, place compound (mechanic=compound) exercises before isolation work. "
            "Only break this order when a deliberate pre-exhaust is justified in confidence_notes."
        ),
        "volume_guidance": (
            "Soft weekly target per requested muscle: about 10-20 working sets for hypertrophy, "
            "roughly 8-15 heavier sets for strength. Stay in range given the session count rather "
            "than maximizing exercise count."
        ),
        "prescription_guidance": build_prescription_guidance(request.goal),
        "split_guidance": (
            "split_template is 'auto': you choose the weekly split structure (full body, "
            "upper/lower, push/pull, push/pull/legs, or a sensible hybrid) that best fits the "
            "requested muscles and session count."
            if request.split_template == "auto"
            else (
                f"The user chose the '{request.split_template}' template; keep session labels "
                "and muscle placement consistent with it."
            )
        ),
        "allowed_output": (
            "Return JSON only. Use only exercise_id values from candidate_pool.allowed_exercise_ids. "
            "Do not cite PMIDs or invent exercise names in the JSON; Python will add exact names, "
            "ranks, and evidence citations after validation. Sets, reps, and rest_seconds are yours "
            "to choose within constraints.prescription_guidance; out-of-range values are clamped."
        ),
    }


def build_prescription_guidance(goal: str) -> str:
    bounds = PRESCRIPTION_BOUNDS.get(goal, PRESCRIPTION_BOUNDS["hypertrophy"])
    set_low, set_high = bounds["sets"]
    rep_low, rep_high = bounds["reps"]
    rest_low, rest_high = bounds["rest_seconds"]
    return (
        f"For {goal}: {set_low}-{set_high} sets, {rep_low}-{rep_high} reps "
        f"(state ranges like '8-12'), {rest_low}-{rest_high} sec rest. Give heavier, "
        "lower-rep prescriptions with longer rest to compound lifts and higher-rep, "
        "shorter-rest prescriptions to isolation work."
    )


def build_prompt_payload(
    request: ProtocolRequest,
    candidate_pool: dict[str, Any],
    findings: list[dict[str, Any]],
    warnings: list[str],
    retry_errors: list[str] | None = None,
) -> dict[str, Any]:
    system_prompt = (
        "You are the planning component of a science-backed workout protocol demo. "
        "Python has already retrieved, filtered, ranked, and evidence-checked the exercise candidates. "
        "Your job is to choose the weekly split, place exercises intelligently, and prescribe sets, "
        "reps, and rest for each exercise using only the supplied candidate pool and constraints. "
        "Return JSON only. Do not return Markdown. Do not invent exercise IDs, exercise names, "
        "PMIDs, or studies."
    )
    json_schema = {
        "split_summary": "Push / Pull",
        "sessions": [
            {
                "session_number": 1,
                "split_label": "Push",
                "focus": "Chest, triceps, lateral/anterior delts",
                "exercises": [
                    {
                        "exercise_id": "0025",
                        "target_muscle": "chest",
                        "sets": 4,
                        "reps": "6-10",
                        "rest_seconds": 150,
                    },
                    {
                        "exercise_id": "0178",
                        "target_muscle": "delts",
                        "sets": 3,
                        "reps": "10-15",
                        "rest_seconds": 90,
                    },
                    {
                        "exercise_id": "0092",
                        "target_muscle": "triceps",
                        "sets": 3,
                        "reps": "10-15",
                        "rest_seconds": 90,
                    }
                ],
            }
        ],
        "confidence_notes": ["Short note if constraints forced a compromise."],
    }

    prompt_request = asdict(request)

    context = {
        "request": prompt_request,
        "constraints": build_planning_constraints(request),
        "candidate_pool": candidate_pool,
        "evidence_findings": findings,
        "warnings": warnings,
        "retry_errors": retry_errors or [],
    }

    user_prompt = (
        "Build a 1-week protocol plan as JSON. Choose split labels and exercise placement yourself, "
        "but obey every hard constraint. Use exact canonical target_muscle values from request.muscles. "
        "Use ONLY the literal exercise_id strings listed in candidate_pool.allowed_exercise_ids; "
        "never invent or rename IDs. "
        "Prefer higher-ranked candidates and direct evidence, but distribute recovery sensibly. "
        "Do not chase exercise variety: when a muscle is trained twice, usually repeat the best "
        "candidate or pair the top two candidates unless a distinct shoulder region or arm emphasis "
        "justifies the third candidate. "
        "Order exercises within each session compound-first: place mechanic=compound candidates "
        "before mechanic=isolation ones unless a pre-exhaust is explicitly justified in "
        "confidence_notes. "
        "Give every exercise sets, reps, and rest_seconds following "
        "constraints.prescription_guidance; Python clamps out-of-range values. "
        "Fill every session within constraints.min_exercises_per_session and "
        "constraints.max_exercises_per_session; do not leave a normal session with only one exercise. "
        "For the common upper-body case, avoid scheduling triceps, biceps, chest, or shoulders in every "
        "session when there are enough sessions to alternate emphasis. "
        f"Return exactly this JSON shape:\n{json.dumps(json_schema, indent=2)}\n\n"
        f"Context JSON:\n{json.dumps(context, indent=2, ensure_ascii=True)}"
    )

    return {
        "system_prompt": system_prompt,
        "json_schema": json_schema,
        "context": context,
        "user_prompt": user_prompt,
    }


def extract_response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return str(text).strip()

    candidates = getattr(response, "candidates", None) or []
    text_parts = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []):
            value = getattr(part, "text", None)
            if value:
                text_parts.append(str(value))
    return "\n".join(text_parts).strip()


def supports_structured_output(model: str) -> bool:
    # Gemma-family models on the Gemini API reject response_schema / system_instruction;
    # they get the combined free-text prompt and rely on extract_json_object instead.
    return not str(model).lower().startswith("gemma")


def build_plan_response_schema(
    allowed_exercise_ids: list[str] | None = None,
    allowed_muscles: list[str] | None = None,
) -> dict[str, Any]:
    """PLAN_RESPONSE_SCHEMA, with exercise_id/target_muscle enum-locked to the
    request's shortlist so JSON mode cannot emit hallucinated IDs (observed with
    gemini-3.5-flash inventing ids like "cable_bicep_curl")."""
    schema = json.loads(json.dumps(PLAN_RESPONSE_SCHEMA))
    exercise_props = schema["properties"]["sessions"]["items"]["properties"]["exercises"][
        "items"
    ]["properties"]
    if allowed_exercise_ids:
        exercise_props["exercise_id"]["enum"] = [str(i) for i in allowed_exercise_ids]
    if allowed_muscles:
        exercise_props["target_muscle"]["enum"] = [str(m) for m in allowed_muscles]
    return schema


def build_llm_generation_config(model: str, response_schema: dict[str, Any] | None = None) -> Any:
    from google.genai import types

    structured = supports_structured_output(model)
    timeout_ms = LLM_TIMEOUT_MS if structured else LLM_SLOW_MODEL_TIMEOUT_MS
    kwargs: dict[str, Any] = {
        "temperature": LLM_TEMPERATURE,
        "http_options": types.HttpOptions(timeout=timeout_ms),
    }
    if structured:
        kwargs["response_mime_type"] = "application/json"
        kwargs["response_schema"] = response_schema or PLAN_RESPONSE_SCHEMA
    return types.GenerateContentConfig(**kwargs)


def generate_with_gemma(api_key: str, model: str, prompt_payload: dict[str, Any]) -> str:
    try:
        from google import genai
    except ImportError as exc:  # pragma: no cover
        raise DemoConfigurationError(
            "Missing google-genai. Install dependencies with `python3 -m pip install -r requirements.txt`."
        ) from exc

    client = genai.Client(api_key=api_key)
    context = prompt_payload.get("context", {}) or {}
    response_schema = build_plan_response_schema(
        allowed_exercise_ids=(context.get("candidate_pool") or {}).get("allowed_exercise_ids"),
        allowed_muscles=(context.get("request") or {}).get("muscles"),
    )
    config = build_llm_generation_config(model, response_schema=response_schema)
    if supports_structured_output(model):
        config.system_instruction = prompt_payload["system_prompt"]
        contents = prompt_payload["user_prompt"]
    else:
        contents = (
            f"SYSTEM INSTRUCTIONS:\n{prompt_payload['system_prompt']}\n\n"
            f"USER TASK:\n{prompt_payload['user_prompt']}"
        )
    response = client.models.generate_content(model=model, contents=contents, config=config)
    text = extract_response_text(response)
    if not text:
        raise DemoConfigurationError("The planner model returned an empty response.")
    return text


def validate_generated_markdown(
    markdown_text: str,
    outline: dict[str, Any],
    findings: list[dict[str, Any]],
    request: ProtocolRequest | None = None,
) -> list[str]:
    errors = []
    required_sections = [
        "# 1-Week Demo Protocol",
        "## Request Summary",
        "## 1-Week Protocol",
        "## Evidence Appendix",
        "## Confidence Notes",
    ]
    for section in required_sections:
        if section not in markdown_text:
            errors.append(f"Missing required section: {section}")

    for session in outline.get("sessions", []):
        split_label = session.get("split_label")
        if not split_label:
            continue
        expected_heading = f"### Session {session['session_number']} - {split_label}"
        if expected_heading not in markdown_text:
            errors.append(f"Missing required session heading: {expected_heading}")

    allowed_exercises = {
        exercise["name"]
        for session in outline.get("sessions", [])
        for exercise in session.get("exercises", [])
    }
    allowed_targets = {
        exercise.get("target_label")
        for session in outline.get("sessions", [])
        for exercise in session.get("exercises", [])
        if exercise.get("target_label")
    }
    mentioned_lines = list(EXERCISE_LINE_PATTERN.finditer(markdown_text))
    mentioned_targets = set()
    if not mentioned_lines:
        errors.append(
            "No exercise lines matched the required '- <Target muscle>: <name> - <prescription>' format."
        )
    else:
        for match in mentioned_lines:
            target_label = match.group("target").strip()
            exercise_name = match.group("exercise").strip()
            mentioned_targets.add(target_label)
            if allowed_targets and target_label not in allowed_targets:
                errors.append(f"Unknown target label mentioned in output: {target_label}")
            if exercise_name not in allowed_exercises:
                errors.append(f"Unknown exercise mentioned in output: {exercise_name}")
    if request:
        required_targets = {display_muscle_label(muscle) for muscle in request.muscles}
        missing_targets = []
        for required_target in sorted(required_targets):
            if any(
                mentioned == required_target
                or mentioned.startswith(f"{required_target} (")
                for mentioned in mentioned_targets
            ):
                continue
            missing_targets.append(required_target)
        if missing_targets:
            errors.append(
                f"Missing requested target muscle group(s): {', '.join(missing_targets)}"
            )

    allowed_pmids = {finding["pmid"] for finding in findings if finding.get("pmid")}
    for session in outline.get("sessions", []):
        for exercise in session.get("exercises", []):
            allowed_pmids.update(
                item["pmid"]
                for item in exercise.get("reference_evidence", [])
                if item.get("pmid")
            )
    found_pmids = PMID_PATTERN.findall(markdown_text)
    if allowed_pmids:
        if not found_pmids:
            errors.append("No PMIDs were cited in the output.")
        for pmid in found_pmids:
            if pmid not in allowed_pmids:
                errors.append(f"Unknown PMID cited in output: {pmid}")
    if found_pmids and "## Evidence Appendix" in markdown_text:
        appendix_text = markdown_text.split("## Evidence Appendix", 1)[1]
        if "## Confidence Notes" in appendix_text:
            appendix_text = appendix_text.split("## Confidence Notes", 1)[0]
        appendix_pmids = set(PMID_PATTERN.findall(appendix_text))
        missing_appendix_pmids = sorted(set(found_pmids) - appendix_pmids)
        if missing_appendix_pmids:
            errors.append(
                "Cited PMID(s) missing from Evidence Appendix: "
                + ", ".join(missing_appendix_pmids)
            )

    return sorted(set(errors))


def render_protocol_markdown(
    request: ProtocolRequest,
    outline: dict[str, Any],
    findings: list[dict[str, Any]],
    warnings: list[str],
    used_fallback: bool = False,
) -> str:
    lines = ["# 1-Week Demo Protocol", ""]
    lines.append("## Request Summary")
    lines.append(f"- Goal: {request.goal}")
    lines.append(f"- Target muscles: {', '.join(request.muscles)}")
    lines.append(f"- Sessions per week: {request.sessions}")
    split_summary = outline.get("split_summary", "")
    if not split_summary:
        split_labels = " / ".join(
            part.get("label", "") for part in outline.get("split_pattern", []) if part.get("label")
        )
        split_summary = request.split_template
        if split_labels:
            split_summary = f"{split_summary} ({split_labels})"
    lines.append(f"- Split: {split_summary}")
    lines.append(
        "- Equipment: "
        + (", ".join(request.equipment) if request.equipment else "any available equipment")
    )
    lines.append(f"- Experience level: {request.experience}")
    lines.append(
        "- Joint exclusions: "
        + (", ".join(request.avoid_joints) if request.avoid_joints else "none")
    )
    lines.append(f"- Notes: {request.notes or 'none'}")
    lines.append("")

    lines.append("## 1-Week Protocol")
    for session in outline.get("sessions", []):
        session_heading = f"### Session {session['session_number']}"
        if session.get("split_label"):
            session_heading = f"{session_heading} - {session['split_label']}"
        lines.append(session_heading)
        for exercise in session.get("exercises", []):
            prescription = exercise["prescription"]
            display_prescription = prescription.get(
                "display",
                f"{prescription['sets']}x{prescription['reps']}",
            )
            evidence_refs = " ".join(
                f"[PMID: {pmid}]" for pmid in exercise.get("reference_pmids", [])
            )
            rationale_suffix = (
                " Lower-trust evidence was used here."
                if exercise.get("lower_trust_evidence", False)
                else ""
            )
            exercise_line = (
                f"- {exercise.get('target_label', 'Target')}: {exercise['name']} - "
                f"{display_prescription}, {prescription['rest']} rest"
            )
            if exercise.get("rank_display"):
                exercise_line = f"{exercise_line} ({exercise['rank_display']})"
            if evidence_refs:
                exercise_line = f"{exercise_line} {evidence_refs}"
            if rationale_suffix:
                exercise_line = f"{exercise_line} ({rationale_suffix.strip()})"
            lines.append(exercise_line)
        lines.append("")

    lines.append("## Evidence Appendix")
    appendix_items = []
    appendix_by_pmid = {}
    for finding in findings:
        pmid = finding.get("pmid")
        if pmid and pmid not in appendix_by_pmid:
            appendix_by_pmid[pmid] = finding
            appendix_items.append(finding)
    for session in outline.get("sessions", []):
        for exercise in session.get("exercises", []):
            for evidence_item in exercise.get("reference_evidence", []):
                pmid = evidence_item.get("pmid")
                if pmid and pmid not in appendix_by_pmid:
                    appendix_by_pmid[pmid] = evidence_item
                    appendix_items.append(evidence_item)

    if appendix_items:
        for finding in appendix_items:
            lines.append(
                f"- PMID: {finding['pmid']} | {finding['title']} | {finding['publication_year']} | {finding['evidence_tier']} | {finding['trust_label']}"
            )
            lines.append(f"- Finding: {finding['snippet']}")
            lines.append("")
    else:
        lines.append("- PMID: none")
        lines.append(
            "- Finding: No strongly matching studies were found in the local science corpus "
            "for this request, so no general findings are cited."
        )
        lines.append("")

    lines.append("## Confidence Notes")
    if used_fallback:
        lines.append(
            "- Gemma output did not pass the local guardrails, so this file was rendered from the deterministic protocol outline instead."
        )
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- The current constraints produced a reasonable candidate pool and at least one usable evidence trail.")

    return "\n".join(lines).strip() + "\n"


def write_demo_outputs(
    markdown_text: str,
    debug_payload: dict[str, Any],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "latest_protocol.md"
    debug_path = output_dir / "latest_debug.json"
    markdown_path.write_text(markdown_text, encoding="utf-8")
    write_json(debug_path, debug_payload)
    return {"markdown_path": str(markdown_path), "debug_path": str(debug_path)}


def run_protocol_dry_run(request: ProtocolRequest) -> dict[str, Any]:
    """Deterministic preview of a request — no LLM call, API key, or vector store.

    Returns the shortlisted candidate pool the planner would choose from, plus the
    deterministic fallback protocol (the same outline the engine renders when the LLM
    is unavailable). Useful for inspecting *which* exercises a request surfaces.
    """
    catalog_payload = load_catalog()
    validate_request_against_taxonomies(request, catalog_payload)
    exercises = catalog_payload.get("exercises", [])

    filtered_candidates = filter_and_score_exercises(request, exercises)
    candidate_pool = build_llm_candidate_pool(request, filtered_candidates)
    candidate_lookup = build_candidate_lookup_from_pool(candidate_pool, filtered_candidates)
    planning_candidates = list(candidate_lookup.values()) or filtered_candidates

    # findings=[] keeps this offline (no Chroma / embedding model); exercise
    # selection is identical, only the evidence citations are omitted.
    outline = build_protocol_outline(request, planning_candidates, findings=[])
    warnings = build_warning_notes(request, filtered_candidates, outline, findings=[])
    markdown_text = render_protocol_markdown(request, outline, findings=[], warnings=warnings)

    return {
        "request": request,
        "filtered_candidate_count": len(filtered_candidates),
        "candidate_pool": candidate_pool,
        "outline": outline,
        "warnings": warnings,
        "markdown_text": markdown_text,
    }


def run_protocol_demo(
    request: ProtocolRequest,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    persist: bool = True,
    fallback_model: str | None = None,
) -> dict[str, Any]:
    catalog_payload = load_catalog()
    validate_request_against_taxonomies(request, catalog_payload)
    exercises = catalog_payload.get("exercises", [])
    science_payload = load_science_corpus()

    filtered_candidates = filter_and_score_exercises(request, exercises)
    deduped_candidates = dedupe_candidates(filtered_candidates)
    llm_candidate_pool = build_llm_candidate_pool(request, filtered_candidates)
    candidate_lookup = build_candidate_lookup_from_pool(
        llm_candidate_pool,
        filtered_candidates,
    )
    planning_candidates = list(candidate_lookup.values()) or filtered_candidates
    findings = query_findings(request, planning_candidates, science_payload)
    findings = enrich_findings_with_target_documents(
        request,
        planning_candidates,
        science_payload,
        findings,
    )
    fallback_outline = build_protocol_outline(request, planning_candidates, findings)
    warnings = build_warning_notes(request, filtered_candidates, fallback_outline, findings)
    prompt_payload = build_prompt_payload(
        request=request,
        candidate_pool=llm_candidate_pool,
        findings=findings,
        warnings=warnings,
    )

    raw_response = ""
    raw_response_attempts: list[dict[str, Any]] = []
    validation_errors: list[str] = []
    llm_plan: dict[str, Any] | None = None
    llm_error: str | None = None
    planner_model: str | None = None
    outline = fallback_outline
    used_fallback = False

    # fallback_model accepts a comma-separated chain, tried in order on API errors.
    model_chain = [model]
    for candidate_model in (fallback_model or "").split(","):
        candidate_model = candidate_model.strip()
        if candidate_model and candidate_model not in model_chain:
            model_chain.append(candidate_model)

    if not candidate_lookup:
        used_fallback = True
    else:
        resolved_api_key = resolve_api_key(api_key)
        retry_errors: list[str] = []
        attempt = 0
        for chain_index, chain_model in enumerate(model_chain):
            # The primary model gets a validation retry; backup models (slow
            # gemma family) get a single shot to stay within the client budget.
            attempts_for_model = 2 if chain_index == 0 else 1
            api_error = False
            for _ in range(attempts_for_model):
                attempt += 1
                prompt_payload = build_prompt_payload(
                    request=request,
                    candidate_pool=llm_candidate_pool,
                    findings=findings,
                    warnings=warnings,
                    retry_errors=retry_errors,
                )
                try:
                    raw_response = generate_with_gemma(
                        resolved_api_key, chain_model, prompt_payload
                    )
                except Exception as exc:  # API failure (rate limit, 5xx) -> next model in chain
                    llm_error = str(exc)
                    retry_errors = [f"Model request failed: {exc}"]
                    validation_errors = retry_errors
                    raw_response_attempts.append(
                        {"attempt": attempt, "model": chain_model, "error": str(exc)}
                    )
                    api_error = True
                    break
                raw_response_attempts.append(
                    {"attempt": attempt, "model": chain_model, "text": raw_response}
                )
                parsed_plan, parse_errors = extract_json_object(raw_response)
                validation_errors = parse_errors
                if parsed_plan is not None:
                    validation_errors = validate_llm_protocol_plan(
                        parsed_plan,
                        request,
                        llm_candidate_pool,
                    )
                if not validation_errors and parsed_plan is not None:
                    llm_plan = parsed_plan
                    planner_model = chain_model
                    outline = build_outline_from_llm_plan(
                        plan=parsed_plan,
                        request=request,
                        candidate_lookup=candidate_lookup,
                        findings=findings,
                        candidate_pool=llm_candidate_pool,
                    )
                    break
                retry_errors = validation_errors
            if llm_plan is not None or not api_error:
                # Done on success or validation exhaustion; only API errors
                # escalate to the next model in the chain.
                break
        used_fallback = llm_plan is None

    final_warnings = build_warning_notes(request, filtered_candidates, outline, findings)
    final_warnings.extend(outline.get("confidence_notes", []))
    if llm_plan is not None and planner_model and planner_model != model:
        final_warnings.insert(
            0,
            f"The primary AI model was unavailable (likely rate-limited), so this plan was "
            f"generated by the backup model ({planner_model}).",
        )
    if used_fallback and llm_error:
        final_warnings.insert(
            0,
            "The AI planner was temporarily unavailable, so this plan uses the evidence-ranked "
            "fallback selection. Try again in a moment for an AI-tailored split.",
        )
    elif used_fallback and candidate_lookup:
        final_warnings.insert(
            0,
            "The AI planner's response failed local validation, so this plan uses the "
            "evidence-ranked deterministic selection instead. Regenerate to retry the AI planner.",
        )
    markdown_text = render_protocol_markdown(
        request=request,
        outline=outline,
        findings=findings,
        warnings=final_warnings,
        used_fallback=used_fallback,
    )

    # Citation containment is checked on every generation: every cited PMID must come
    # from the allowed set and must also appear in the Evidence Appendix. The check
    # returns a list of strings and never raises, so it cannot alter the output.
    # Results are recorded in the debug payload rather than shown to the user, pending
    # a false-positive rate measured on live output.
    markdown_validation_errors = validate_generated_markdown(
        markdown_text, outline, findings, request=request
    )

    debug_payload = {
        "request": asdict(request),
        "selected_model": model,
        "fallback_model": fallback_model,
        "planner_model": planner_model,
        "filtered_candidate_count": len(filtered_candidates),
        "deduped_candidate_count": len(deduped_candidates),
        "filtered_candidates": filtered_candidates,
        "deduped_candidates": deduped_candidates,
        "llm_candidate_pool": llm_candidate_pool,
        "science_findings": findings,
        "protocol_outline": outline,
        "fallback_protocol_outline": fallback_outline,
        "warnings": final_warnings,
        "prompt_payload": prompt_payload,
        "raw_response_text": raw_response,
        "raw_response_attempts": raw_response_attempts,
        "llm_protocol_plan": llm_plan,
        "validation_errors": validation_errors,
        "markdown_validation_errors": markdown_validation_errors,
        "used_fallback_renderer": used_fallback,
        "used_deterministic_fallback": used_fallback,
    }

    output_paths = write_demo_outputs(markdown_text, debug_payload) if persist else {}
    return {
        "markdown_text": markdown_text,
        "debug_payload": debug_payload,
        "output_paths": output_paths,
    }
