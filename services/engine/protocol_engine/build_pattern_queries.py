"""Generate exercise-pattern + muscle-gap PubMed query clusters for the new dataset.

The base ``pubmed_queries.json`` covers training *principles* (volume, frequency,
rep ranges, ...) and is largely exercise-agnostic. This generator adds the second
half of the hybrid corpus the migration calls for:

1. **Exercise-pattern clusters** — the 1,324 exercises are collapsed to canonical
   movement patterns (e.g. every "... bench press" variant -> "bench press"), and
   each well-represented resistance pattern gets ONE disambiguated PubMed query so
   genuinely-studied movements pick up their *own* direct evidence. Patterns are
   derived from the data (not hardcoded) so coverage tracks the actual dataset,
   but a movement-term filter + minimum-count threshold keep the queries clean and
   avoid the long tail of unstudied novelty variants. Per-cluster ``retmax`` is kept
   low because each pattern is narrow.
2. **Muscle-gap clusters** — curated queries for muscle groups the base config
   covers thinly (calves, forearms/grip, hip abductors/adductors, direct core,
   plus kettlebell and machine-vs-free-weight modalities) now that the richer
   dataset surfaces many more of those exercises.

Output is a standalone cluster config merged at build time via
``build_science_corpus.py --extra-query-config``.

Run:
    python -m protocol_engine.build_pattern_queries \
        --catalog data/raw/exercises-richdb/dist/exercises.json \
        --output services/engine/config/pubmed_queries_generated.json
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from .pipeline_common import normalize_text, read_json, write_json
    from .settings import REPO_ROOT
except ImportError:  # pragma: no cover - allow running as a plain script
    from pipeline_common import normalize_text, read_json, write_json
    from settings import REPO_ROOT


# Tokens stripped when reducing an exercise name to a movement pattern: equipment,
# stance, grip width, unilateral markers, and gendered demo suffixes. We deliberately
# KEEP movement-defining qualifiers (leg, calf, hip, lateral, front, rear, overhead,
# preacher, romanian, nordic, hack, ...) so distinct movements never collapse together
# ("leg press" must not become "press").
MODIFIER_TOKENS = {
    # equipment
    "barbell", "dumbbell", "cable", "machine", "smith", "kettlebell", "band",
    "bands", "ez", "leverage", "lever", "sled", "assisted", "weighted",
    "resistance", "bosu", "stability", "medicine", "suspension", "trap",
    "olympic", "ball", "rope", "roller", "wheel", "tire", "weight",
    # stance / setup -- note: "bench" is intentionally NOT stripped, so "bench press"
    # survives as its own pattern instead of collapsing to a bare "press".
    "seated", "standing", "incline", "declined", "decline", "lying", "prone",
    "supine", "kneeling", "bent", "flat", "floor", "wall", "over",
    # grip / width / direction qualifiers that don't change the studied movement
    "wide", "close", "narrow", "grip", "overhand", "underhand", "supinated",
    "pronated", "mixed",
    # unilateral / count
    "one", "single", "two", "double", "alternating", "alternate", "alternated",
    "unilateral", "arm", "arms",
    # gendered demo variants + filler
    "male", "female", "version", "exercise", "with", "the", "a", "an", "and",
    "of", "to", "on", "your", "body", "in", "for",
}

# A reduced pattern is kept only if it contains one of these movement heads — this
# is what separates real exercises from leftover descriptive noise.
MOVEMENT_TERMS = (
    "press", "squat", "deadlift", "row", "curl", "extension", "raise", "fly",
    "flye", "pulldown", "pushdown", "lunge", "thrust", "dip", "pullup", "pull up",
    "pushup", "push up", "chinup", "chin up", "shrug", "crunch", "situp",
    "sit up", "bridge", "kickback", "thruster", "pullover", "crossover",
    "hyperextension", "good morning", "calf raise", "leg raise", "face pull",
    "step up", "hip thrust", "muscle up", "clean", "snatch", "jerk", "swing",
)

# Disambiguation context appended to every pattern query so generic exercise names
# don't pull in unrelated medical literature.
QUERY_CONTEXT = "resistance training OR strength training OR hypertrophy OR electromyography OR muscle activation"

PRIMARY_LABELS = {
    "abs": "abdominal", "chest": "chest pectoralis", "biceps": "biceps brachii",
    "glutes": "gluteus", "delts": "deltoid shoulder", "triceps": "triceps brachii",
    "mid_back": "upper back", "lats": "latissimus", "calves": "calf gastrocnemius",
    "quads": "quadriceps", "forearms": "forearm", "hamstrings": "hamstring",
    "spinal_erectors": "erector spinae", "traps": "trapezius",
    "hip_adductors": "hip adductor", "hip_abductors": "hip abductor gluteus medius",
}

# Curated clusters for muscle groups / modalities the base config under-covers.
MUSCLE_GAP_CLUSTERS = [
    {
        "id": "gap_calves",
        "topic": "Calf (gastrocnemius/soleus) training",
        "keywords": ["calf", "gastrocnemius", "soleus", "plantar flexion", "calf raise"],
        "retmax": 20,
        "queries": [
            "calf raise gastrocnemius soleus hypertrophy resistance training",
            "plantar flexion training muscle hypertrophy randomized trial",
            "seated standing calf raise soleus gastrocnemius muscle growth",
        ],
    },
    {
        "id": "gap_forearms_grip",
        "topic": "Forearm and grip training",
        "keywords": ["forearm", "grip strength", "wrist flexion", "wrist extension"],
        "retmax": 20,
        "queries": [
            "forearm wrist flexor extensor resistance training hypertrophy",
            "grip strength training intervention randomized controlled trial",
            "wrist curl forearm muscle activation electromyography",
        ],
    },
    {
        "id": "gap_hip_abductors",
        "topic": "Hip abductor / gluteus medius training",
        "keywords": ["hip abductor", "gluteus medius", "abduction", "hip stability"],
        "retmax": 20,
        "queries": [
            "hip abduction gluteus medius activation resistance exercise",
            "gluteus medius strengthening exercise electromyography",
            "hip abductor training strength hypertrophy randomized trial",
        ],
    },
    {
        "id": "gap_hip_adductors",
        "topic": "Hip adductor / groin training",
        "keywords": ["hip adductor", "adduction", "groin", "adductor magnus"],
        "retmax": 20,
        "queries": [
            "hip adductor strengthening exercise muscle activation",
            "adductor magnus hypertrophy resistance training squat",
            "groin adductor training injury prevention randomized trial",
        ],
    },
    {
        "id": "gap_core_abs",
        "topic": "Direct abdominal / core training",
        "keywords": ["abdominal", "core", "rectus abdominis", "oblique", "trunk"],
        "retmax": 20,
        "queries": [
            "abdominal exercise rectus abdominis muscle activation electromyography",
            "core training trunk muscle hypertrophy resistance exercise",
            "oblique abdominal exercise electromyography comparison",
        ],
    },
    {
        "id": "gap_kettlebell",
        "topic": "Kettlebell training",
        "keywords": ["kettlebell", "swing", "ballistic", "power"],
        "retmax": 20,
        "queries": [
            "kettlebell training strength power randomized controlled trial",
            "kettlebell swing muscle activation electromyography",
            "kettlebell exercise conditioning intervention strength",
        ],
    },
    {
        "id": "gap_machine_vs_free",
        "topic": "Machine vs free-weight resistance training",
        "keywords": ["machine", "free weight", "resistance training", "stability"],
        "retmax": 20,
        "queries": [
            "machine versus free weight resistance training hypertrophy strength",
            "guided machine free weight muscle activation comparison",
            "resistance machine free weight strength transfer trial",
        ],
    },
]


def _singularize(token: str) -> str:
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def derive_pattern(name: str) -> str | None:
    """Reduce an exercise name to a canonical movement pattern, or None if it has no
    recognizable resistance movement (cardio, stretches, novelty holds)."""
    tokens = [
        _singularize(tok)
        for tok in normalize_text(name).split()
        if tok and tok not in MODIFIER_TOKENS and not tok.isdigit()
    ]
    if not tokens:
        return None
    # Keep the trailing (most movement-defining) tokens; cap length for clean queries.
    pattern = " ".join(tokens[-3:])
    if not any(term in pattern for term in MOVEMENT_TERMS):
        # try the full reduced phrase before giving up
        pattern_full = " ".join(tokens)
        if not any(term in pattern_full for term in MOVEMENT_TERMS):
            return None
        pattern = " ".join(tokens[:4])
    return pattern


def build_pattern_clusters(catalog_records: list[dict[str, Any]], min_count: int, retmax: int) -> list[dict[str, Any]]:
    pattern_counts: Counter[str] = Counter()
    pattern_primary: dict[str, Counter] = defaultdict(Counter)
    for rec in catalog_records:
        # Skip cardio / no-primary records — they have no resistance evidence to find.
        primary = rec.get("primaryMuscles") or []
        if not primary or rec.get("category") == "cardio":
            continue
        pattern = derive_pattern(str(rec.get("name", "")))
        if not pattern:
            continue
        pattern_counts[pattern] += 1
        pattern_primary[pattern][primary[0]] += 1

    clusters: list[dict[str, Any]] = []
    for pattern, count in pattern_counts.most_common():
        if count < min_count:
            continue
        primary = pattern_primary[pattern].most_common(1)[0][0]
        muscle_label = PRIMARY_LABELS.get(primary, primary.replace("_", " "))
        slug = re.sub(r"[^a-z0-9]+", "_", pattern).strip("_")
        clusters.append(
            {
                "id": f"exercise_{slug}",
                "topic": f"Exercise-specific evidence: {pattern}",
                "keywords": list(dict.fromkeys(pattern.split() + muscle_label.split())),
                "retmax": retmax,
                "exercise_count": count,
                "queries": [f'("{pattern}") AND ({muscle_label}) AND ({QUERY_CONTEXT})'],
            }
        )
    return clusters


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate exercise-pattern + muscle-gap PubMed query clusters.")
    parser.add_argument("--catalog", default=str(REPO_ROOT / "data" / "raw" / "exercises-richdb" / "dist" / "exercises.json"))
    parser.add_argument("--output", default=str(REPO_ROOT / "services" / "engine" / "config" / "pubmed_queries_generated.json"))
    parser.add_argument("--min-count", type=int, default=5, help="Minimum exercises per pattern to emit a query.")
    parser.add_argument("--pattern-retmax", type=int, default=8, help="PubMed retmax per pattern query.")
    parser.add_argument("--dry-run", action="store_true", help="Print clusters without writing.")
    args = parser.parse_args()

    records = read_json(Path(args.catalog))
    pattern_clusters = build_pattern_clusters(records, args.min_count, args.pattern_retmax)
    clusters = pattern_clusters + MUSCLE_GAP_CLUSTERS

    payload = {
        "version": "generated-exercise-patterns",
        "default_retmax": args.pattern_retmax,
        "clusters": clusters,
    }

    print(f"[gen] exercise-pattern clusters: {len(pattern_clusters)} (min_count={args.min_count}, retmax={args.pattern_retmax})")
    print(f"[gen] muscle-gap clusters: {len(MUSCLE_GAP_CLUSTERS)}")
    total_queries = sum(len(c['queries']) for c in clusters)
    print(f"[gen] total clusters: {len(clusters)} | total queries: {total_queries}")
    print("[gen] top pattern queries:")
    for c in pattern_clusters[:35]:
        print(f"    [{c['exercise_count']:3d}x] {c['queries'][0]}")

    if not args.dry_run:
        write_json(args.output, payload)
        print(f"[gen] wrote -> {args.output}")


if __name__ == "__main__":
    main()
