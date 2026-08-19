"""S3 - attribution: does the retrieved science actually reach a recommendation?

The engine links a study to an exercise by matching the exercise's *aliases*
against the study's title and abstract (``build_exercise_catalog.match_exercise_studies``).
That is a documented design decision, not a defect: the README states evidence is
attributed at the movement level because abstracts rarely distinguish close
variants. This study measures what that decision costs.

Everything here is deterministic and uses the engine's own gate functions, so the
funnel we report is the funnel the running system applies. The final section draws
a stratified sample of (exercise, study) pairs for adjudication, which is the only
part of the study that needs a judge.

    ./.venv/bin/python -m research.s3_attribution_audit
"""
from __future__ import annotations

import collections
import random
import re
import statistics
from typing import Any

from research.common import (
    SEED,
    banner,
    environment_snapshot,
    load_catalog,
    load_corpus,
    load_query_config,
    mean,
    write_csv,
    write_results,
)

GOALS = ("hypertrophy", "strength")


def muscle_search_terms(muscle: str) -> set[str]:
    """The engine's own vocabulary for a muscle, so the supply measure is not ours."""
    from protocol_engine.protocol_demo import MUSCLE_TOKEN_SYNONYMS

    return {muscle, muscle.replace("_", " ")} | set(MUSCLE_TOKEN_SYNONYMS.get(muscle, set()))


def engine_has_synonyms(muscle: str) -> bool:
    """Does the engine know any literature term for this muscle beyond its own label?

    Five of the sixteen catalog muscles have no entry in MUSCLE_TOKEN_SYNONYMS, so
    the engine can only recognise them if a study happens to use the catalog's exact
    word. "mid_back" and "spinal_erectors" never appear in abstracts, which the
    literature writes as rhomboid/trapezius and erector spinae.
    """
    from protocol_engine.protocol_demo import MUSCLE_TOKEN_SYNONYMS

    return bool(MUSCLE_TOKEN_SYNONYMS.get(muscle))


def mentions(text: str, terms: set[str]) -> bool:
    """Word-boundary match. Substring matching would count "lat" inside "related"."""
    return any(re.search(r"\b%s\b" % re.escape(term), text) for term in terms)


def section_coverage(catalog: dict, corpus: dict) -> dict[str, Any]:
    """A. How much of the catalog is evidenced, and how much of the corpus is used."""
    exercises = catalog["exercises"]
    documents = corpus["documents"]

    linked_pmids: set[str] = set()
    edges = 0
    for exercise in exercises:
        pmids = exercise["evidence"].get("pmids") or []
        linked_pmids.update(pmids)
        edges += len(pmids)

    evidenced = [e for e in exercises if e["evidence"].get("direct_evidence_count", 0) > 0]
    return {
        "n_exercises": len(exercises),
        "n_exercises_with_evidence": len(evidenced),
        "exercise_coverage_rate": len(evidenced) / len(exercises),
        "n_corpus_studies": len(documents),
        "n_studies_ever_linked": len(linked_pmids),
        "corpus_utilisation_rate": len(linked_pmids) / len(documents),
        "n_edges": edges,
        "direct_evidence_count_histogram": dict(
            sorted(collections.Counter(
                e["evidence"].get("direct_evidence_count", 0) for e in exercises
            ).items())
        ),
        "studies_per_exercise_cap": 8,  # build_exercise_catalog.py:828
    }


def section_muscle_disconnect(catalog: dict, corpus: dict) -> dict[str, Any]:
    """B. Corpus supply per muscle against attribution coverage per muscle.

    Supply counts corpus studies that mention the muscle in the engine's own
    vocabulary. If supply is high and coverage is low, the science was fetched and
    then lost between the corpus and the catalog.
    """
    from protocol_engine.pipeline_common import normalize_text

    documents = corpus["documents"]
    doc_text = [
        (d["pmid"], normalize_text("%s %s" % (d.get("title", ""), d.get("abstract", ""))))
        for d in documents
    ]
    linked_pmids: set[str] = set()
    for exercise in catalog["exercises"]:
        linked_pmids.update(exercise["evidence"].get("pmids") or [])

    per_muscle: dict[str, dict[str, Any]] = {}
    by_primary = collections.defaultdict(list)
    for exercise in catalog["exercises"]:
        for muscle in exercise["muscles"]["primary"]:
            by_primary[muscle].append(exercise)

    for muscle, group in by_primary.items():
        terms = {normalize_text(t) for t in muscle_search_terms(muscle)}
        supply = [pmid for pmid, text in doc_text if mentions(text, terms)]
        evidenced = [e for e in group if e["evidence"].get("direct_evidence_count", 0) > 0]
        per_muscle[muscle] = {
            "n_exercises": len(group),
            "n_exercises_with_evidence": len(evidenced),
            "coverage_rate": len(evidenced) / len(group),
            "corpus_supply": len(supply),
            "corpus_supply_ever_linked": len(set(supply) & linked_pmids),
            "supply_delivered_rate": (
                len(set(supply) & linked_pmids) / len(supply) if supply else None
            ),
            "engine_has_muscle_synonyms": engine_has_synonyms(muscle),
        }

    # The gap_* clusters are the sharpest case: queries written specifically to fill
    # a muscle's evidence gap. Did the studies they fetched ever arrive?
    clusters = load_query_config()
    gap_clusters: dict[str, dict[str, Any]] = {}
    for cluster_id in sorted(c for c in clusters if c.startswith("gap_")):
        pmids = {
            d["pmid"] for d in documents if cluster_id in (d.get("topic_clusters") or [])
        }
        gap_clusters[cluster_id] = {
            "topic": clusters[cluster_id].get("topic", ""),
            "studies_fetched": len(pmids),
            "studies_ever_linked": len(pmids & linked_pmids),
            "delivery_rate": len(pmids & linked_pmids) / len(pmids) if pmids else None,
        }
    return {"per_muscle": per_muscle, "gap_clusters": gap_clusters}


def section_alias_mechanism(catalog: dict) -> dict[str, Any]:
    """C. Which aliases actually fire, and why that determines everything else."""
    exercises = catalog["exercises"]
    matched = collections.Counter()
    for exercise in exercises:
        for study in exercise["evidence"].get("studies") or []:
            alias = study.get("matched_alias")
            if alias:
                matched[alias] += 1

    all_aliases = [a for e in exercises for a in (e.get("aliases") or [])]
    matched_words = [len(a.split()) for a in matched]
    all_words = [len(a.split()) for a in all_aliases]

    from protocol_engine.build_exercise_catalog import GENERIC_ALIAS_BLOCKLIST

    return {
        "n_distinct_aliases_in_catalog": len(set(all_aliases)),
        "n_alias_slots_in_catalog": len(all_aliases),
        "n_distinct_aliases_that_ever_match": len(matched),
        "alias_firing_rate": len(matched) / len(set(all_aliases)),
        "matched_alias_word_count": {
            "mean": mean(matched_words),
            "median": statistics.median(matched_words),
            "histogram": dict(sorted(collections.Counter(matched_words).items())),
        },
        "catalog_alias_word_count": {
            "mean": mean(all_words),
            "median": statistics.median(all_words),
            "histogram": dict(sorted(collections.Counter(all_words).items())),
        },
        "n_blocklisted_generic_aliases": len(GENERIC_ALIAS_BLOCKLIST),
        "top_matched_aliases": [
            {"alias": alias, "edges": count, "words": len(alias.split())}
            for alias, count in matched.most_common(25)
        ],
    }


def section_fanout(catalog: dict) -> dict[str, Any]:
    """D. One study cited for many exercises, and citation lists collapsing."""
    exercises = catalog["exercises"]
    fanout = collections.Counter()
    for exercise in exercises:
        for pmid in exercise["evidence"].get("pmids") or []:
            fanout[pmid] += 1

    citation_sets = collections.Counter(
        tuple(sorted(e["evidence"].get("pmids") or []))
        for e in exercises
        if e["evidence"].get("pmids")
    )
    values = list(fanout.values())
    return {
        "n_linked_studies": len(fanout),
        "fanout_mean": mean(values),
        "fanout_median": statistics.median(values),
        "fanout_max": max(values),
        "most_reused_studies": fanout.most_common(10),
        "n_evidenced_exercises": sum(citation_sets.values()),
        "n_distinct_citation_lists": len(citation_sets),
        "largest_identical_citation_group": max(citation_sets.values()),
        "citation_list_group_sizes": sorted(citation_sets.values(), reverse=True)[:12],
    }


def section_runtime_funnel(catalog: dict) -> dict[str, Any]:
    """E. The offline links are gated again at request time; how many survive?

    Also measures how permissive the goal gate is. ``is_goal_relevant_direct_study``
    passes a strength request whenever the study's inferred modality contains
    "performance", and ``PERFORMANCE_PATTERNS`` includes the bare token "strength",
    so most resistance-training abstracts satisfy it automatically.
    """
    from protocol_engine.protocol_demo import (
        is_goal_relevant_direct_study,
        is_specific_study_match,
    )

    exercises = catalog["exercises"]
    funnel: dict[str, Any] = {}
    for goal in GOALS:
        offline = specific = goal_ok = 0
        exercises_surviving = set()
        modality_only = 0
        for exercise in exercises:
            for study in exercise["evidence"].get("studies") or []:
                offline += 1
                if not is_specific_study_match(exercise, study):
                    continue
                specific += 1
                if not is_goal_relevant_direct_study(study, goal):
                    continue
                goal_ok += 1
                exercises_surviving.add(exercise["exercise_id"])
                # Did it pass on the inferred-modality shortcut alone?
                methods = {str(m).strip().lower() for m in study.get("measurement_method", [])}
                shortcut = (goal == "hypertrophy" and "hypertrophy" in methods) or (
                    goal == "strength" and "performance" in methods
                )
                if shortcut:
                    modality_only += 1
        funnel[goal] = {
            "offline_links": offline,
            "pass_specificity_gate": specific,
            "pass_goal_gate": goal_ok,
            "exercises_with_a_surviving_citation": len(exercises_surviving),
            "exercise_coverage_at_request_time": len(exercises_surviving) / len(exercises),
            "passed_via_modality_shortcut": modality_only,
            "modality_shortcut_share": modality_only / goal_ok if goal_ok else float("nan"),
        }
    return funnel


def section_ranking(catalog: dict) -> dict[str, Any]:
    """F. Does the ranking prefer evidenced exercises, and can it discriminate?"""
    exercises = catalog["exercises"]
    out: dict[str, Any] = {}
    for goal in GOALS:
        top, rest = [], []
        for exercise in exercises:
            ranks = (exercise.get("muscle_group_rankings") or {}).get(goal) or {}
            if not ranks:
                continue
            best = min(entry.get("rank", 10 ** 9) for entry in ranks.values())
            evidenced = exercise["evidence"].get("direct_evidence_count", 0) > 0
            (top if best <= 5 else rest).append(evidenced)
        top_rate = sum(top) / len(top) if top else float("nan")
        rest_rate = sum(rest) / len(rest) if rest else float("nan")
        ties = [
            {"muscle": muscle, "tie_size": entry["tie_size"], "out_of": entry["out_of"]}
            for exercise in exercises
            for muscle, entry in ((exercise.get("muscle_group_rankings") or {}).get(goal) or {}).items()
            if entry.get("rank") == 1
        ]
        deduped = {(t["muscle"], t["tie_size"], t["out_of"]) for t in ties}
        out[goal] = {
            "n_top5": len(top),
            "top5_evidenced_rate": top_rate,
            "n_rest": len(rest),
            "rest_evidenced_rate": rest_rate,
            "evidence_enrichment": top_rate / rest_rate if rest_rate else float("nan"),
            "rank1_ties": [
                {"muscle": m, "tie_size": t, "out_of": o, "tied_share": t / o}
                for m, t, o in sorted(deduped)
            ],
            "mean_rank1_tied_share": mean([t / o for _, t, o in sorted(deduped)]),
        }
    return out


def section_judgment_sample(catalog: dict, corpus: dict) -> list[dict[str, Any]]:
    """G. A stratified sample of (exercise, study) pairs to adjudicate.

    Stratified by how widely the matched alias fans out, because the mechanism
    predicts that broad, generic aliases produce the weakest links.
    """
    docs_by_pmid = {d["pmid"]: d for d in corpus["documents"]}
    alias_edges = collections.Counter()
    pairs: list[dict[str, Any]] = []
    for exercise in catalog["exercises"]:
        for study in exercise["evidence"].get("studies") or []:
            alias_edges[study.get("matched_alias", "")] += 1
    for exercise in catalog["exercises"]:
        for study in exercise["evidence"].get("studies") or []:
            document = docs_by_pmid.get(study["pmid"], {})
            pairs.append({
                "pair_id": "%s:%s" % (exercise["exercise_id"], study["pmid"]),
                "exercise_id": exercise["exercise_id"],
                "exercise_name": exercise["name"],
                "primary_muscles": exercise["muscles"]["primary"],
                "equipment": exercise["movement"]["equipment"],
                "mechanic": exercise["movement"]["mechanic"],
                "matched_alias": study.get("matched_alias", ""),
                "alias_fanout": alias_edges[study.get("matched_alias", "")],
                "pmid": study["pmid"],
                "study_title": study.get("title", ""),
                "study_abstract": document.get("abstract", ""),
                "publication_year": study.get("publication_year"),
                "evidence_tier": study.get("evidence_tier"),
                "attachment_path": "alias_match",
                "url": "https://pubmed.ncbi.nlm.nih.gov/%s/" % study["pmid"],
            })

    # Terciles of alias fan-out, sampled evenly so the sample is not dominated by
    # the handful of aliases that produce hundreds of edges.
    ordered = sorted(pairs, key=lambda p: (p["alias_fanout"], p["pair_id"]))
    third = len(ordered) // 3
    strata = {
        "narrow_alias": ordered[:third],
        "medium_alias": ordered[third: 2 * third],
        "broad_alias": ordered[2 * third:],
    }
    rng = random.Random(SEED)
    sample: list[dict[str, Any]] = []
    for name in ("narrow_alias", "medium_alias", "broad_alias"):
        pool = list(strata[name])
        rng.shuffle(pool)
        for item in pool[:34]:
            sample.append({**item, "stratum": name})
    return sample[:100]


def main() -> None:
    catalog, corpus = load_catalog(), load_corpus()

    banner("S3 - attribution: does the retrieved science reach a recommendation?")

    coverage = section_coverage(catalog, corpus)
    print("A. coverage")
    print("   exercises with >=1 linked study : %d / %d (%.1f%%)" % (
        coverage["n_exercises_with_evidence"], coverage["n_exercises"],
        100 * coverage["exercise_coverage_rate"]))
    print("   corpus studies ever linked      : %d / %d (%.1f%%)" % (
        coverage["n_studies_ever_linked"], coverage["n_corpus_studies"],
        100 * coverage["corpus_utilisation_rate"]))
    print("   (exercise, study) edges         : %d" % coverage["n_edges"])

    disconnect = section_muscle_disconnect(catalog, corpus)
    print("\nB. per-muscle supply vs coverage (sorted by coverage)")
    print("   %-16s %8s %8s %10s %10s" % ("muscle", "exs", "covered", "supply", "delivered"))
    for muscle, row in sorted(disconnect["per_muscle"].items(), key=lambda kv: kv[1]["coverage_rate"]):
        delivered = ("%8.1f%%" % (100 * row["supply_delivered_rate"])
                     if row["supply_delivered_rate"] is not None else "     n/a")
        print("   %-16s %8d %7.1f%% %10d %s%s" % (
            muscle, row["n_exercises"], 100 * row["coverage_rate"],
            row["corpus_supply"], delivered,
            "" if row["engine_has_muscle_synonyms"] else "   <- no engine synonyms"))
    print("\n   gap-filling clusters: studies fetched -> ever linked")
    for cluster_id, row in sorted(disconnect["gap_clusters"].items()):
        print("   %-22s %3d -> %3d  (%.0f%% delivered)" % (
            cluster_id, row["studies_fetched"], row["studies_ever_linked"],
            100 * row["delivery_rate"]))

    alias = section_alias_mechanism(catalog)
    print("\nC. alias mechanism")
    print("   distinct aliases in catalog     : %d" % alias["n_distinct_aliases_in_catalog"])
    print("   distinct aliases that ever fire : %d (%.1f%%)" % (
        alias["n_distinct_aliases_that_ever_match"], 100 * alias["alias_firing_rate"]))
    print("   words per alias, matched vs all : %.2f vs %.2f" % (
        alias["matched_alias_word_count"]["mean"], alias["catalog_alias_word_count"]["mean"]))
    print("   matched-alias word histogram    : %s" % alias["matched_alias_word_count"]["histogram"])

    fanout = section_fanout(catalog)
    print("\nD. fan-out and citation-list collapse")
    print("   exercises per study             : mean %.1f  median %.0f  max %d" % (
        fanout["fanout_mean"], fanout["fanout_median"], fanout["fanout_max"]))
    print("   distinct citation lists         : %d across %d evidenced exercises" % (
        fanout["n_distinct_citation_lists"], fanout["n_evidenced_exercises"]))
    print("   largest identical citation group: %d exercises" % fanout["largest_identical_citation_group"])

    funnel = section_runtime_funnel(catalog)
    print("\nE. request-time funnel")
    for goal, row in funnel.items():
        print("   %-12s %d offline -> %d specific -> %d goal-ok  (%d exercises, %.1f%% of catalog)" % (
            goal, row["offline_links"], row["pass_specificity_gate"], row["pass_goal_gate"],
            row["exercises_with_a_surviving_citation"],
            100 * row["exercise_coverage_at_request_time"]))
        print("   %-12s passed via inferred-modality shortcut: %d (%.1f%%)" % (
            "", row["passed_via_modality_shortcut"], 100 * row["modality_shortcut_share"]))

    ranking = section_ranking(catalog)
    print("\nF. ranking behaviour")
    for goal, row in ranking.items():
        print("   %-12s top-5 evidenced %.1f%% vs rest %.1f%%  (enrichment %.1fx)" % (
            goal, 100 * row["top5_evidenced_rate"], 100 * row["rest_evidenced_rate"],
            row["evidence_enrichment"]))
        print("   %-12s mean share of a muscle tied at rank 1: %.1f%%" % (
            "", 100 * row["mean_rank1_tied_share"]))

    sample = section_judgment_sample(catalog, corpus)
    print("\nG. adjudication sample: %d pairs (%s)" % (
        len(sample), dict(collections.Counter(s["stratum"] for s in sample))))

    write_csv(
        "s3_muscle_disconnect",
        ["muscle", "n_exercises", "n_with_evidence", "coverage_rate", "corpus_supply",
         "supply_ever_linked", "supply_delivered_rate"],
        [[m, r["n_exercises"], r["n_exercises_with_evidence"], round(r["coverage_rate"], 4),
          r["corpus_supply"], r["corpus_supply_ever_linked"],
          round(r["supply_delivered_rate"], 4) if r["supply_delivered_rate"] is not None else ""]
         for m, r in sorted(disconnect["per_muscle"].items())],
    )
    path = write_results("s3_attribution_audit", {
        "environment": environment_snapshot(),
        "a_coverage": coverage,
        "b_muscle_disconnect": disconnect,
        "c_alias_mechanism": alias,
        "d_fanout": fanout,
        "e_runtime_funnel": funnel,
        "f_ranking": ranking,
    })
    write_results("s3_judgment_sample", {
        "environment": environment_snapshot(),
        "n_pairs": len(sample),
        "stratification": "terciles of matched-alias fan-out",
        "pairs": sample,
    })
    print("\nwrote %s" % path)


if __name__ == "__main__":
    main()
