"""S3c - adjudicate citations at three levels of claim specificity.

The system attaches a study to an exercise; the interface shows that as evidence.
Whether that is warranted depends entirely on how specific a claim the reader takes
from it, so a single "is this citation relevant?" verdict would hide the finding.
Each pair is judged three times, at increasing specificity:

  movement   did participants actually perform this movement, or a close variant?
  goal       does the study report a hypertrophy or strength outcome for it?
  variant    did the study use this specific variant - same equipment and position?

Both attachment mechanisms are judged on the identical rubric, so the paper can
compare them rather than only report that one is weak.

Judgments are cached per pair, so re-running costs nothing and an interrupted run
resumes. A stratified subset is exported separately for human annotation, and
agreement between the human and the model is reported by research.s3d_agreement.

    ./.venv/bin/python -m research.s3c_judge
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import re
import threading
import time
from itertools import zip_longest
from pathlib import Path
from typing import Any

from research.common import (
    RESEARCH_DIR,
    banner,
    environment_snapshot,
    mean,
    read_results,
    write_csv,
    write_results,
)

CACHE = RESEARCH_DIR / ".cache" / "judgments"
CACHE.mkdir(parents=True, exist_ok=True)
JUDGE_MODEL = "gemini-3.5-flash"
MAX_WORKERS = 2
# The free tier allows 20 generate_content requests per minute. Exceeding it returns
# 429 with a server-supplied retry delay, so requests are paced below the limit and
# the delay is honoured rather than guessed at.
MIN_SECONDS_BETWEEN_REQUESTS = 60.0 / 15.0

FAILURE_TAXONOMY = [
    "supports_specific_variant",
    "supports_movement_not_variant",
    "supports_muscle_not_movement",
    "movement_named_only_incidentally",
    "term_is_a_clinical_test_not_an_exercise",
    "different_population_or_modality",
    "unrelated_topic",
]

RUBRIC = """You are auditing whether a scientific citation supports an exercise recommendation.

EXERCISE: {exercise_name}
Primary muscles: {muscles} | Equipment: {equipment} | Mechanic: {mechanic}

CITED STUDY (PMID {pmid}, {year}, indexed as {tier}):
Title: {title}
Abstract: {abstract}

Answer three questions at increasing specificity. Answer "no" when the abstract does
not provide the information; do not give credit for what is merely plausible.

1. movement_involved: Did participants in this study actually PERFORM this movement
   (or a clearly equivalent variant of it) as part of the intervention or measurement?
   Beware: a phrase like "leg raise" or "straight leg raise" is often the name of a
   CLINICAL ASSESSMENT TEST, not a training exercise. If the movement appears only as
   a test, or only in a passing mention, answer "no".

2. goal_supported: Does this study report a muscle-growth (hypertrophy) or
   strength/performance OUTCOME that bears on using this exercise for training?

3. variant_exact: Did the study use this SPECIFIC variant - same equipment and same
   body position (e.g. incline vs flat, cable vs dumbbell, seated vs standing)?

Then choose exactly one category from this list that best describes the link:
{taxonomy}

Return JSON only."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "movement_involved": {"type": "STRING", "enum": ["yes", "no"]},
        "goal_supported": {"type": "STRING", "enum": ["yes", "no"]},
        "variant_exact": {"type": "STRING", "enum": ["yes", "no"]},
        "category": {"type": "STRING", "enum": FAILURE_TAXONOMY},
        "reason": {"type": "STRING"},
    },
    "required": ["movement_involved", "goal_supported", "variant_exact", "category", "reason"],
}


def load_api_key() -> str:
    for path in (RESEARCH_DIR.parent / "services" / "engine" / ".env",
                 RESEARCH_DIR.parent / ".env"):
        if path.exists():
            for line in path.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("GEMINI_API_KEY", "")


_throttle_lock = threading.Lock()
_last_request = [0.0]


def _throttle() -> None:
    """Serialise request starts so the whole process stays under the rate limit."""
    with _throttle_lock:
        wait = MIN_SECONDS_BETWEEN_REQUESTS - (time.time() - _last_request[0])
        if wait > 0:
            time.sleep(wait)
        _last_request[0] = time.time()


def _retry_delay(message: str, attempt: int) -> float:
    """Prefer the delay the server asks for; fall back to exponential backoff."""
    match = re.search(r"retry in ([0-9.]+)s", message)
    if match:
        return float(match.group(1)) + 1.0
    return min(60.0, 4.0 * (2 ** attempt))


def cache_path(pair_id: str) -> Any:
    return CACHE / ("%s.json" % re.sub(r"[^A-Za-z0-9_.-]", "_", pair_id))


def judge_one(client: Any, pair: dict[str, Any]) -> dict[str, Any]:
    cached = cache_path(pair["pair_id"])
    if cached.exists():
        return json.loads(cached.read_text())
    if os.environ.get("JUDGE_CACHED_ONLY"):
        # Rebuild the summary from what is already on disk, without any network use.
        return {"pair_id": pair["pair_id"], "error": "not judged (cached-only mode)"}

    from google.genai import types

    prompt = RUBRIC.format(
        exercise_name=pair["exercise_name"],
        muscles=", ".join(pair["primary_muscles"]),
        equipment=pair.get("equipment", "unknown"),
        mechanic=pair.get("mechanic", "unknown"),
        pmid=pair["pmid"],
        year=pair.get("publication_year"),
        tier=pair.get("evidence_tier"),
        title=pair["study_title"],
        abstract=(pair.get("study_abstract") or "(no abstract available)")[:5000],
        taxonomy="\n".join("  - %s" % c for c in FAILURE_TAXONOMY),
    )
    last_error = ""
    for attempt in range(8):
        try:
            _throttle()
            response = client.models.generate_content(
                model=JUDGE_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,  # judgments must be reproducible
                    response_mime_type="application/json",
                    response_schema=SCHEMA,
                ),
            )
            verdict = json.loads(response.text)
            verdict["pair_id"] = pair["pair_id"]
            cached.write_text(json.dumps(verdict, indent=2, sort_keys=True))
            return verdict
        except Exception as error:  # noqa: BLE001 - rate limits and transient 5xx
            last_error = str(error)[:300]
            if "RESOURCE_EXHAUSTED" not in last_error and "429" not in last_error \
                    and attempt >= 2:
                break  # a non-quota failure is not going to fix itself
            time.sleep(_retry_delay(last_error, attempt))
    return {"pair_id": pair["pair_id"], "error": last_error}


def summarise(verdicts: list[dict[str, Any]], pairs_by_id: dict[str, dict]) -> dict[str, Any]:
    """Support rate at each specificity level, split by attachment mechanism."""
    out: dict[str, Any] = {}
    by_path: dict[str, list[dict[str, Any]]] = {}
    for verdict in verdicts:
        if "error" in verdict:
            continue
        path = pairs_by_id[verdict["pair_id"]]["attachment_path"]
        by_path.setdefault(path, []).append(verdict)
        by_path.setdefault("all", []).append(verdict)
    for path, group in by_path.items():
        out[path] = {
            "n": len(group),
            "movement_involved_rate": mean([v["movement_involved"] == "yes" for v in group]),
            "goal_supported_rate": mean([v["goal_supported"] == "yes" for v in group]),
            "variant_exact_rate": mean([v["variant_exact"] == "yes" for v in group]),
            "all_three_rate": mean([
                v["movement_involved"] == "yes" and v["goal_supported"] == "yes"
                and v["variant_exact"] == "yes" for v in group
            ]),
            "categories": {
                c: sum(1 for v in group if v["category"] == c) for c in FAILURE_TAXONOMY
            },
        }
    return out


def main() -> None:
    from google import genai

    alias_pairs = read_results("s3_judgment_sample")["pairs"]
    semantic_pairs = read_results("s3b_semantic_pairs")["pairs"]
    # Interleave the two mechanisms. The free tier can exhaust mid-run, and a run
    # that stops early must still leave a balanced sample rather than one arm only.
    pairs = [
        pair
        for group in zip_longest(alias_pairs, semantic_pairs)
        for pair in group if pair is not None
    ]
    limit = int(os.environ.get("JUDGE_LIMIT", "0"))
    if limit:
        pairs = pairs[:limit]
    pairs_by_id = {p["pair_id"]: p for p in pairs}

    banner("S3c - citation support at three levels of claim specificity")
    print("pairs to judge: %d (%d alias-match, %d semantic-fallback)"
          % (len(pairs),
             sum(1 for p in pairs if p["attachment_path"] == "alias_match"),
             sum(1 for p in pairs if p["attachment_path"] == "semantic_fallback")))

    key = load_api_key()
    if os.environ.get("JUDGE_CACHED_ONLY"):
        key = key or "cached-only"
    if not key:
        raise SystemExit("no GEMINI_API_KEY found in services/engine/.env, .env, or the environment")
    client = genai.Client(api_key=key)

    todo = sum(1 for p in pairs if not cache_path(p["pair_id"]).exists())
    print("already cached: %d | to fetch: %d | paced at %.0f requests/min"
          % (len(pairs) - todo, todo, 60.0 / MIN_SECONDS_BETWEEN_REQUESTS))
    start = time.time()
    done = [0]

    def run(pair: dict[str, Any]) -> dict[str, Any]:
        verdict = judge_one(client, pair)
        done[0] += 1
        if done[0] % 20 == 0:
            print("  %d / %d  (%.0fs elapsed)" % (done[0], len(pairs), time.time() - start),
                  flush=True)
        return verdict

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        verdicts = list(pool.map(run, pairs))
    failed = [v for v in verdicts if "error" in v]
    print("judged %d pairs in %.0fs (%d failed)" % (len(verdicts), time.time() - start, len(failed)))
    if failed:
        print("  first error: %s" % failed[0]["error"])

    summary = summarise(verdicts, pairs_by_id)
    print("\nsupport rate at increasing claim specificity")
    print("%-22s %5s %12s %12s %12s %12s" % (
        "attachment mechanism", "n", "movement", "goal", "variant", "all three"))
    for path in ("alias_match", "semantic_fallback", "all"):
        if path not in summary:
            continue
        row = summary[path]
        print("%-22s %5d %11.1f%% %11.1f%% %11.1f%% %11.1f%%" % (
            path, row["n"], 100 * row["movement_involved_rate"],
            100 * row["goal_supported_rate"], 100 * row["variant_exact_rate"],
            100 * row["all_three_rate"]))

    print("\nfailure taxonomy (all pairs)")
    for category, count in sorted(summary["all"]["categories"].items(),
                                  key=lambda kv: -kv[1]):
        if count:
            print("   %-42s %4d (%4.1f%%)" % (category, count, 100 * count / summary["all"]["n"]))

    write_csv(
        "s3c_judgments",
        ["pair_id", "attachment_path", "exercise_name", "pmid", "matched_alias",
         "movement_involved", "goal_supported", "variant_exact", "category"],
        [[v["pair_id"], pairs_by_id[v["pair_id"]]["attachment_path"],
          pairs_by_id[v["pair_id"]]["exercise_name"], pairs_by_id[v["pair_id"]]["pmid"],
          pairs_by_id[v["pair_id"]].get("matched_alias", ""),
          v["movement_involved"], v["goal_supported"], v["variant_exact"], v["category"]]
         for v in verdicts if "error" not in v],
    )
    print("\nNOTE: judged n is bounded by the API's free-tier quota. The harness caches "
          "every verdict,\nso re-running later resumes and only fetches what is missing.")
    write_results("s3c_judgments", {
        "environment": environment_snapshot(),
        "judge_model": JUDGE_MODEL,
        "temperature": 0.0,
        "rubric": RUBRIC,
        "taxonomy": FAILURE_TAXONOMY,
        "n_judged": len(verdicts) - len(failed),
        "n_failed": len(failed),
        "summary": summary,
        "verdicts": verdicts,
    })
    print("\nwrote results/s3c_judgments.json")


if __name__ == "__main__":
    main()
