"""Adapt the rich 1,324-exercise dataset into the free-exercise-db raw schema.

The protocol engine's enrichment (``build_exercise_catalog.py``) and runtime
(``protocol_demo.py``) were written against the free-exercise-db record shape
(``id, name, force, mechanic, level, equipment, category, primaryMuscles,
secondaryMuscles, instructions, images``). Rather than teach that 38KB+ pipeline
a second schema, this converter reads the new dataset and emits raw records in
the *same* shape, so the enrichment runs unchanged.

Two realities of the new dataset drive the mapping logic here:

1. Its ``category``/``body_part`` field is a *body region* (back, chest, waist…),
   NOT a movement class. We must NOT pass it through as ``category`` — doing so
   would fail every ``category in {"strength", ...}`` check in the enrichment and
   zero out the resistance bonuses. We synthesize ``category`` (cardio vs strength).
2. It has no ``force``/``mechanic``/``level``. We synthesize these from the name
   (with conservative, ordered keyword rules) so goal scoring and joint stress
   stay meaningful. ``mechanic`` matters most (it drives strength scoring); the
   isolation keywords are checked *before* compound ones so single-joint arm work
   like "overhead triceps extension" stays isolation.

Muscle vocabularies are mapped to the engine's canonical 17 muscle groups
directly (``MUSCLE_MAP`` in the enrichment passes canonical tokens through its
fallback unchanged). For "advanced" difficulty we emit the raw token ``"expert"``
because ``LEVEL_MAP`` maps ``expert -> advanced`` (emitting ``"advanced"`` would
become ``"unknown"``).

Run (from the repo root or services/engine):
    python -m protocol_engine.convert_exercises_dataset \
        --input exercises-dataset/data/exercises.json \
        --output data/raw/exercises-richdb/dist/exercises.json
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from .pipeline_common import normalize_text, read_json, write_json
    from .settings import REPO_ROOT
except ImportError:  # pragma: no cover - allow running as a plain script
    from pipeline_common import normalize_text, read_json, write_json
    from settings import REPO_ROOT


# --- Muscle vocabularies -------------------------------------------------------------
# New dataset `target` -> engine canonical primary muscle. ``None`` means "no
# resistance-trained muscle" (cardio); such exercises get an empty primary list and
# never surface as a recommendation for any of the 17 muscle groups.
TARGET_TO_PRIMARY: dict[str, str | None] = {
    "abs": "abs",
    "pectorals": "chest",
    "biceps": "biceps",
    "glutes": "glutes",
    "delts": "delts",
    "triceps": "triceps",
    "upper back": "mid_back",
    "lats": "lats",
    "calves": "calves",
    "quads": "quads",
    "forearms": "forearms",
    "cardiovascular system": None,
    "hamstrings": "hamstrings",
    "spine": "spinal_erectors",
    "traps": "traps",
    "adductors": "hip_adductors",
    "serratus anterior": "chest",
    "abductors": "hip_abductors",
    "levator scapulae": "traps",
}

# New dataset `muscle_group` + `secondary_muscles` vocab -> canonical, or ``None`` to
# drop (pure stabilizers / no clean canonical bucket). Covers every value present in
# both fields so nothing leaks through as a non-canonical muscle.
SECONDARY_CLEAN: dict[str, str | None] = {
    "shoulders": "delts",
    "deltoids": "delts",
    "rear deltoids": "delts",
    "rotator cuff": "delts",
    "forearms": "forearms",
    "wrist flexors": "forearms",
    "wrist extensors": "forearms",
    "wrists": "forearms",
    "hands": "forearms",
    "grip muscles": "forearms",
    "biceps": "biceps",
    "brachialis": "biceps",
    "triceps": "triceps",
    "hamstrings": "hamstrings",
    "quadriceps": "quads",
    "glutes": "glutes",
    "calves": "calves",
    "soleus": "calves",
    "chest": "chest",
    "upper chest": "chest",
    "trapezius": "traps",
    "traps": "traps",
    "rhomboids": "mid_back",
    "upper back": "mid_back",
    "back": "lats",
    "latissimus dorsi": "lats",
    "lats": "lats",
    "lower back": "spinal_erectors",
    "abdominals": "abs",
    "obliques": "abs",
    "core": "abs",
    "lower abs": "abs",
    "groin": "hip_adductors",
    "inner thighs": "hip_adductors",
    "sternocleidomastoid": "neck",
    # Pure stabilizers with no canonical bucket — dropped to avoid noisy filters.
    "hip flexors": None,
    "ankles": None,
    "ankle stabilizers": None,
    "shins": None,
    "feet": None,
}

# --- Equipment vocabulary ------------------------------------------------------------
# New dataset `equipment` -> canonical token. Cardio machines collapse to
# ``cardio_machine`` (also a category signal). Resistance tokens new to the engine
# (leverage_machine, smith_machine, weighted, ...) are added to RESISTANCE_EQUIPMENT in
# build_exercise_catalog.py so they keep the resistance goal-score bonus.
EQUIPMENT_CLEAN: dict[str, str] = {
    "body weight": "bodyweight",
    "dumbbell": "dumbbell",
    "cable": "cable",
    "barbell": "barbell",
    "leverage machine": "leverage_machine",
    "band": "resistance_band",
    "resistance band": "resistance_band",
    "smith machine": "smith_machine",
    "kettlebell": "kettlebell",
    "weighted": "weighted",
    "stability ball": "stability_ball",
    "bosu ball": "stability_ball",
    "ez barbell": "ez_bar",
    "olympic barbell": "barbell",
    "trap bar": "barbell",
    "assisted": "assisted",
    "sled machine": "sled_machine",
    "medicine ball": "medicine_ball",
    "rope": "rope",
    "roller": "foam_roller",
    "wheel roller": "other",
    "hammer": "machine",
    "tire": "other",
    "upper body ergometer": "cardio_machine",
    "skierg machine": "cardio_machine",
    "stationary bike": "cardio_machine",
    "elliptical machine": "cardio_machine",
    "stepmill machine": "cardio_machine",
}

# Genuine beginner *movements* (bodyweight basics), NOT an equipment proxy. Tying
# difficulty to equipment would tag every machine as "beginner", and the enrichment's
# +0.04 beginner hypertrophy bonus would then float machine variants above free weights
# in every muscle ranking. Keep beginner narrow so rankings stay equipment-neutral.
BEGINNER_KEYWORDS = (
    "crunch", "plank", "sit up", "sit-up", "glute bridge", "bird dog", "dead bug",
    "wall sit", "leg raise", "mountain climber", "superman", "russian twist",
    "flutter kick", "knee push",
)

# --- Name-keyword synthesis ----------------------------------------------------------
# Checked FIRST so single-joint movements win — keeps e.g. "overhead triceps
# extension" classified isolation (which the comparative-evidence test relies on).
ISOLATION_KEYWORDS = (
    "curl", "extension", "raise", "fly", "flye", "pushdown", "kickback",
    "lateral", "crossover", "shrug", "concentration", "pullover", "adduction",
    "abduction", "spread", "pec deck", "pull apart", "rear delt", "reverse fly",
    "calf raise", "leg extension", "leg curl", "wrist curl",
)
COMPOUND_KEYWORDS = (
    "squat", "deadlift", "press", "bench", "row", "lunge", "dip", "clean",
    "snatch", "thruster", "thrust", "bridge", "pulldown", "pullup", "pushup",
    "chinup", "stepup", "jerk", "carry", "swing", "climb",
    "pull up", "pull-up", "push up", "push-up", "chin up", "chin-up",
    "step up", "step-up", "pull down", "hip thrust", "good morning",
    "muscle up", "get up", "clean and press",
)
# Cosmetic only (force adds +0.04 to both goals equally — push vs pull is irrelevant
# to scoring; we only distinguish dynamic push/pull from static).
PULL_KEYWORDS = (
    "row", "pull", "pulldown", "chin", "curl", "deadlift", "shrug", "clean",
    "snatch", "face pull",
)
PUSH_KEYWORDS = (
    "press", "push", "dip", "fly", "raise", "extension", "thruster", "jerk",
    "pushdown",
)
ADVANCED_KEYWORDS = (
    "muscle up", "muscle-up", "planche", "pistol", "nordic", "handstand",
    "front lever", "back lever", "human flag", "dragon flag", "snatch",
    "clean and jerk", "depth jump", "skin the cat", "iron cross",
)
CARDIO_EQUIPMENT = {"cardio_machine"}


def _has_keyword(normalized_name: str, keywords: tuple[str, ...]) -> bool:
    """Match keywords against a normalized name.

    Single-word keywords match a token *prefix* (so "row" matches "rows"/"rowing"
    but not "narrow"); multi-word keywords match as a substring.
    """
    tokens = normalized_name.split()
    for kw in keywords:
        if " " in kw or "-" in kw:
            if kw in normalized_name:
                return True
        elif any(tok.startswith(kw) for tok in tokens):
            return True
    return False


def synthesize_mechanic(normalized_name: str, muscle_count: int) -> str:
    if _has_keyword(normalized_name, ISOLATION_KEYWORDS):
        return "isolation"
    if _has_keyword(normalized_name, COMPOUND_KEYWORDS):
        return "compound"
    # Tiebreak on how many muscle groups the movement spans.
    return "compound" if muscle_count >= 3 else "isolation"


def synthesize_force(normalized_name: str) -> str | None:
    if _has_keyword(normalized_name, PULL_KEYWORDS):
        return "pull"
    if _has_keyword(normalized_name, PUSH_KEYWORDS):
        return "push"
    return None


def synthesize_level(normalized_name: str, equipment: str) -> str:
    # Emit raw free-exercise-db level tokens: "expert" -> "advanced" via LEVEL_MAP.
    if _has_keyword(normalized_name, ADVANCED_KEYWORDS):
        return "expert"
    if equipment == "bodyweight" and _has_keyword(normalized_name, BEGINNER_KEYWORDS):
        return "beginner"
    return "intermediate"


def synthesize_category(body_part: str, target: str, equipment: str) -> str:
    if body_part == "cardio" or target == "cardiovascular system" or equipment in CARDIO_EQUIPMENT:
        return "cardio"
    return "strength"


def clean_secondary(values: list[str], primary: list[str]) -> list[str]:
    primary_set = set(primary)
    out: list[str] = []
    for value in values:
        mapped = SECONDARY_CLEAN.get(value, "__unmapped__")
        if mapped == "__unmapped__":
            # Unknown value: keep visibility via a warn list rather than silently
            # leaking a non-canonical muscle. Skip it from the record.
            continue
        if mapped is None or mapped in primary_set:
            continue
        out.append(mapped)
    return sorted(set(out))


def convert_record(rec: dict[str, Any]) -> dict[str, Any]:
    name = str(rec.get("name", "")).strip()
    normalized_name = normalize_text(name)
    target = str(rec.get("target", "")).strip()
    body_part = str(rec.get("body_part", "")).strip()
    raw_equipment = str(rec.get("equipment", "")).strip()
    equipment = EQUIPMENT_CLEAN.get(raw_equipment, "other")

    primary_muscle = TARGET_TO_PRIMARY.get(target, None)
    primary = [primary_muscle] if primary_muscle else []

    # Fold the (noisy) muscle_group synergist into secondary alongside the
    # secondary_muscles list; the enrichment dedupes/sorts these.
    secondary_sources: list[str] = list(rec.get("secondary_muscles") or [])
    muscle_group = rec.get("muscle_group")
    if muscle_group:
        secondary_sources.append(str(muscle_group).strip())
    secondary = clean_secondary(secondary_sources, primary)

    category = synthesize_category(body_part, target, equipment)
    muscle_count = len(set(primary) | set(secondary))
    mechanic = synthesize_mechanic(normalized_name, muscle_count)
    force = synthesize_force(normalized_name)
    level = synthesize_level(normalized_name, equipment)

    steps = (rec.get("instruction_steps") or {}).get("en") or []
    if not steps:
        text = (rec.get("instructions") or {}).get("en")
        steps = [text] if text else []

    image = rec.get("image")
    return {
        "id": str(rec.get("id")),
        "name": name,
        "force": force,
        "level": level,
        "mechanic": mechanic,
        "equipment": equipment,
        "category": category,
        "primaryMuscles": primary,
        "secondaryMuscles": secondary,
        "instructions": list(steps),
        "images": [image] if image else [],
        # New field (free-exercise-db had no animations); passed through by the
        # enrichment via an additive `"gif": raw.get("gif")` line.
        "gif": rec.get("gif_url"),
    }


def _summarize(records: list[dict[str, Any]]) -> None:
    def dist(field: str) -> str:
        c = Counter(r[field] for r in records)
        return ", ".join(f"{k}={v}" for k, v in c.most_common())

    print(f"[convert] records: {len(records)}")
    print(f"[convert] category: {dist('category')}")
    print(f"[convert] mechanic: {dist('mechanic')}")
    print(f"[convert] level: {dist('level')}")
    eq = Counter(r["equipment"] for r in records)
    print(f"[convert] equipment ({len(eq)}): " + ", ".join(f"{k}={v}" for k, v in eq.most_common()))
    primary = Counter((r["primaryMuscles"] or ["<none>"])[0] for r in records)
    print(f"[convert] primary muscle ({len(primary)}): " + ", ".join(f"{k}={v}" for k, v in primary.most_common()))
    empty_primary = sum(1 for r in records if not r["primaryMuscles"])
    print(f"[convert] empty-primary (cardio): {empty_primary}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert the rich exercises dataset to free-exercise-db raw schema.")
    parser.add_argument("--input", default=str(REPO_ROOT / "exercises-dataset" / "data" / "exercises.json"))
    parser.add_argument("--output", default=str(REPO_ROOT / "data" / "raw" / "exercises-richdb" / "dist" / "exercises.json"))
    args = parser.parse_args()

    source = read_json(Path(args.input))
    records = [convert_record(rec) for rec in source]
    _summarize(records)

    write_json(args.output, records)
    print(f"[convert] wrote {len(records)} raw records -> {args.output}")


if __name__ == "__main__":
    main()
