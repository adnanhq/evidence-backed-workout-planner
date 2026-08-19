"""S1 — how accurate is the study-design grader, and what does its error cost?

The engine grades every study into an evidence tier with a keyword cascade that
searches the MEDLINE publication-type tags *and* the title and abstract text
(``build_science_corpus.classify_evidence_tier``):

    if any(pattern in joined_types or pattern in text for pattern in META_PATTERNS): ...

So the design decision under test is a single clause: should the grader read the
abstract body? We answer it by running the engine's own classifier under three
progressively wider views of each document, which keeps the precedence order and
the pattern lists identical and isolates that one clause:

    pt_only   publication types only   -- the authoritative bibliographic index
    pt_title  + the title             -- a defensible middle ground
    pt_full   + the abstract body     -- what the system actually ships

``pt_only`` is the reference condition. Because it is the same function, no
mapping of ours stands between the system and its ground truth. A hand-built
mapping is also evaluated as a sensitivity check.

The tier score carries a 0.55 coefficient in ``retrieval_weight`` and feeds
exercise ``confidence_score``, so we propagate every disagreement forward to the
numbers a user actually sees.

    ./.venv/bin/python -m research.s1_tier_audit
"""
from __future__ import annotations

import collections
import random
from typing import Any

from sklearn.metrics import cohen_kappa_score

from research.common import (
    SEED,
    banner,
    environment_snapshot,
    load_catalog,
    load_corpus,
    mean,
    write_csv,
    write_results,
)

# Strongest first. This is the cascade order in classify_evidence_tier, so index
# order is evidence strength and lets us talk about "stronger" and "weaker".
TIERS = [
    "meta_analysis",
    "systematic_review",
    "rct",
    "controlled_trial",
    "observational",
    "narrative_review",
    "other",
]
TIER_RANK = {tier: index for index, tier in enumerate(TIERS)}

CONDITIONS = ("pt_only", "pt_title", "pt_full")


def classify_under(document: dict[str, Any], condition: str) -> tuple[str, float]:
    """Grade one document with the engine's classifier under a restricted view."""
    from protocol_engine.build_science_corpus import classify_evidence_tier

    publication_types = document.get("publication_types") or []
    if condition == "pt_only":
        return classify_evidence_tier(publication_types, "", "")
    if condition == "pt_title":
        return classify_evidence_tier(publication_types, document.get("title", ""), "")
    if condition == "pt_full":
        return classify_evidence_tier(
            publication_types, document.get("title", ""), document.get("abstract", "")
        )
    raise ValueError("unknown condition: %s" % condition)


def hand_mapped_tier(publication_types: list[str]) -> str:
    """Sensitivity check: an independent reading of MEDLINE tags, not the engine's.

    Written before the engine-restricted reference existed, and kept so the
    headline conclusion can be shown to survive a different mapping.
    """
    joined = " | ".join(publication_types).lower()
    if "meta-analysis" in joined:
        return "meta_analysis"
    if "systematic review" in joined or "scoping review" in joined:
        return "systematic_review"
    if "randomized controlled trial" in joined:
        return "rct"
    if "clinical trial" in joined or "comparative study" in joined:
        return "controlled_trial"
    if any(term in joined for term in ("observational study", "cohort", "cross-sectional", "case reports")):
        return "observational"
    if "review" in joined:
        return "narrative_review"
    return "other"


def confusion(pairs: list[tuple[str, str]]) -> dict[str, dict[str, int]]:
    counts = collections.Counter(pairs)
    return {
        predicted: {actual: counts[(predicted, actual)] for actual in TIERS}
        for predicted in TIERS
    }


def per_class_scores(pairs: list[tuple[str, str]]) -> dict[str, dict[str, float]]:
    """Precision/recall/F1 per tier, treating the reference condition as truth."""
    scores = {}
    for tier in TIERS:
        true_positive = sum(1 for p, a in pairs if p == tier and a == tier)
        predicted = sum(1 for p, _ in pairs if p == tier)
        actual = sum(1 for _, a in pairs if a == tier)
        precision = true_positive / predicted if predicted else float("nan")
        recall = true_positive / actual if actual else float("nan")
        if precision == precision and recall == recall and (precision + recall) > 0:
            f1 = 2 * precision * recall / (precision + recall)
        else:
            f1 = float("nan")
        scores[tier] = {
            "predicted_count": predicted,
            "reference_count": actual,
            "true_positive": true_positive,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    return scores


def agreement_block(pairs: list[tuple[str, str]], label: str) -> dict[str, Any]:
    """Agreement, kappa, and the direction of disagreement for one comparison."""
    from protocol_engine.build_science_corpus import EVIDENCE_TIER_SCORES

    total = len(pairs)
    exact = sum(1 for p, a in pairs if p == a)
    stronger = sum(1 for p, a in pairs if TIER_RANK[p] < TIER_RANK[a])
    weaker = sum(1 for p, a in pairs if TIER_RANK[p] > TIER_RANK[a])
    deltas = [EVIDENCE_TIER_SCORES[p] - EVIDENCE_TIER_SCORES[a] for p, a in pairs]
    return {
        "comparison": label,
        "n": total,
        "exact_agreement": exact / total,
        "exact_agreement_count": exact,
        "cohen_kappa": cohen_kappa_score([p for p, _ in pairs], [a for _, a in pairs]),
        "cohen_kappa_linear_weighted": cohen_kappa_score(
            [TIER_RANK[p] for p, _ in pairs],
            [TIER_RANK[a] for _, a in pairs],
            weights="linear",
        ),
        "graded_stronger": stronger,
        "graded_stronger_rate": stronger / total,
        "graded_weaker": weaker,
        "graded_weaker_rate": weaker / total,
        "inflation_asymmetry_ratio": (stronger / weaker) if weaker else None,
        "one_directional": weaker == 0,
        "mean_tier_score_delta": mean(deltas),
        "mean_retrieval_weight_delta": 0.55 * mean(deltas),
    }


def propagate_to_confidence(
    documents: list[dict[str, Any]], corrected_tier: dict[str, str]
) -> dict[str, Any]:
    """Re-derive exercise confidence with corrected tiers, using the catalog formula.

    ``build_exercise_catalog.compute_evidence_confidence``:
        clamp(0.35*max_quality + 0.35*avg_retrieval_weight + 0.20 + min(0.2, 0.04n))
    Both inputs depend on the tier, so a misgraded study moves a user-visible number.
    """
    from protocol_engine.build_science_corpus import EVIDENCE_TIER_SCORES
    from protocol_engine.pipeline_common import clamp

    by_pmid = {document["pmid"]: document for document in documents}

    def weight_for(document: dict[str, Any], tier: str) -> float:
        return (
            EVIDENCE_TIER_SCORES[tier] * 0.55
            + float(document.get("recency_score", 0.0)) * 0.25
            + float(document.get("relevance_score", 0.0)) * 0.20
        )

    def confidence(quality: list[float], weights: list[float]) -> float:
        return clamp(
            0.35 * max(quality)
            + 0.35 * (sum(weights) / len(weights))
            + 0.20
            + min(0.2, len(quality) * 0.04)
        )

    shifted, deltas, level_changes, reorderings = 0, [], 0, 0
    LEVELS = lambda score: "high" if score >= 0.75 else ("moderate" if score >= 0.55 else "low")  # noqa: E731

    for exercise in load_catalog()["exercises"]:
        studies = exercise["evidence"].get("studies") or []
        pmids = [study["pmid"] for study in studies if study["pmid"] in by_pmid]
        if not pmids:
            continue
        shipped_tiers = [by_pmid[pmid]["evidence_tier"] for pmid in pmids]
        fixed_tiers = [corrected_tier[pmid] for pmid in pmids]

        shipped = confidence(
            [EVIDENCE_TIER_SCORES[t] for t in shipped_tiers],
            [weight_for(by_pmid[p], t) for p, t in zip(pmids, shipped_tiers)],
        )
        fixed = confidence(
            [EVIDENCE_TIER_SCORES[t] for t in fixed_tiers],
            [weight_for(by_pmid[p], t) for p, t in zip(pmids, fixed_tiers)],
        )
        deltas.append(shipped - fixed)
        if abs(shipped - fixed) >= 0.005:
            shifted += 1
        if LEVELS(shipped) != LEVELS(fixed):
            level_changes += 1

        # Studies are shown ordered by (quality_score, retrieval_weight, year); a
        # tier correction can change which study is presented first.
        def order(tiers: list[str]) -> list[str]:
            return [
                pmid
                for pmid, _ in sorted(
                    zip(pmids, tiers),
                    key=lambda item: (
                        EVIDENCE_TIER_SCORES[item[1]],
                        weight_for(by_pmid[item[0]], item[1]),
                        by_pmid[item[0]].get("publication_year", 0),
                    ),
                    reverse=True,
                )
            ]

        if order(shipped_tiers)[:1] != order(fixed_tiers)[:1]:
            reorderings += 1

    return {
        "exercises_with_linked_studies": len(deltas),
        "exercises_whose_confidence_moves": shifted,
        "exercises_whose_confidence_level_changes": level_changes,
        "exercises_whose_top_study_changes": reorderings,
        "mean_confidence_inflation": mean(deltas),
        "max_confidence_inflation": max(deltas) if deltas else 0.0,
    }


def main() -> None:
    corpus = load_corpus()
    documents = corpus["documents"]

    graded = {
        condition: {d["pmid"]: classify_under(d, condition)[0] for d in documents}
        for condition in CONDITIONS
    }

    banner("S1 - study-design grading: does reading the abstract body help or hurt?")

    # Sanity gate: the shipped corpus must reproduce under pt_full, otherwise the
    # committed data and the current classifier have drifted apart and nothing
    # downstream is meaningful.
    shipped = {d["pmid"]: d["evidence_tier"] for d in documents}
    mismatched = [p for p in shipped if shipped[p] != graded["pt_full"][p]]
    print("reproduces committed corpus under pt_full: %s (%d mismatches)"
          % (not mismatched, len(mismatched)))

    comparisons = {}
    for condition in ("pt_full", "pt_title"):
        pairs = [(graded[condition][p], graded["pt_only"][p]) for p in shipped]
        comparisons[condition] = agreement_block(pairs, "%s vs pt_only" % condition)
        comparisons[condition]["confusion"] = confusion(pairs)
        comparisons[condition]["per_class"] = per_class_scores(pairs)

    # Abstract-body reading in isolation: everything pt_full does that pt_title does not.
    body_pairs = [(graded["pt_full"][p], graded["pt_title"][p]) for p in shipped]
    comparisons["abstract_body_effect"] = agreement_block(
        body_pairs, "pt_full vs pt_title (abstract body alone)"
    )

    sensitivity = agreement_block(
        [(graded["pt_full"][p], hand_mapped_tier(d.get("publication_types") or []))
         for p, d in ((doc["pmid"], doc) for doc in documents)],
        "pt_full vs independent hand mapping",
    )

    for key in ("pt_full", "pt_title", "abstract_body_effect"):
        block = comparisons[key]
        print("\n%-42s agreement=%5.1f%%  kappa=%.3f (lin %.3f)"
              % (block["comparison"], 100 * block["exact_agreement"],
                 block["cohen_kappa"], block["cohen_kappa_linear_weighted"]))
        ratio = ("%.1f:1" % block["inflation_asymmetry_ratio"]) if block["inflation_asymmetry_ratio"] else "one-directional"
        print("%-42s stronger=%4.1f%%  weaker=%4.1f%%  %s  mean weight delta=%+.4f"
              % ("", 100 * block["graded_stronger_rate"], 100 * block["graded_weaker_rate"],
                 ratio, block["mean_retrieval_weight_delta"]))

    print("\nsensitivity (independent mapping): agreement=%.1f%%  kappa=%.3f  stronger:weaker=%.1f:1"
          % (100 * sensitivity["exact_agreement"], sensitivity["cohen_kappa"],
             sensitivity["inflation_asymmetry_ratio"] or float("nan")))

    print("\nconfusion, pt_full (rows) vs pt_only (cols):")
    matrix = comparisons["pt_full"]["confusion"]
    print("%-19s" % "" + "".join("%10s" % t[:9] for t in TIERS))
    for tier in TIERS:
        print("%-19s" % tier + "".join("%10d" % matrix[tier][t] for t in TIERS))

    propagation = propagate_to_confidence(documents, graded["pt_only"])
    print("\npropagated to the user-visible confidence score:")
    for key, value in propagation.items():
        print("  %-42s %s" % (key, ("%.4f" % value) if isinstance(value, float) else value))

    # Over-graded top tier: the sharpest single statement in this study.
    overgraded_meta = [
        d for d in documents
        if graded["pt_full"][d["pmid"]] == "meta_analysis"
        and graded["pt_only"][d["pmid"]] != "meta_analysis"
    ]
    total_meta = sum(1 for d in documents if graded["pt_full"][d["pmid"]] == "meta_analysis")
    print("\ntop tier: %d of %d 'meta_analysis' gradings are not supported by MEDLINE tags"
          % (len(overgraded_meta), total_meta))

    # Stratified disagreement sample for human adjudication: disagreement is not
    # automatically error, and only a person can separate the two.
    rng = random.Random(SEED)
    disagreements = [
        {
            "pmid": d["pmid"],
            "title": d["title"],
            "journal": d.get("journal", ""),
            "publication_year": d.get("publication_year"),
            "publication_types": d.get("publication_types") or [],
            "abstract": d.get("abstract", ""),
            "tier_pt_full": graded["pt_full"][d["pmid"]],
            "tier_pt_only": graded["pt_only"][d["pmid"]],
            "promotion": "%s -> %s" % (
                graded["pt_only"][d["pmid"]], graded["pt_full"][d["pmid"]]
            ),
            "url": "https://pubmed.ncbi.nlm.nih.gov/%s/" % d["pmid"],
        }
        for d in documents
        if graded["pt_full"][d["pmid"]] != graded["pt_only"][d["pmid"]]
    ]
    # Every disagreement is a promotion (see one_directional above), so stratify
    # by which promotion happened and sample proportionally, at least one each.
    by_pair = collections.defaultdict(list)
    for item in disagreements:
        by_pair[(item["tier_pt_only"], item["tier_pt_full"])].append(item)
    target, sample = 15, []  # type: list[dict[str, Any]]
    for pair in sorted(by_pair, key=lambda k: (-len(by_pair[k]), k)):
        pool = sorted(by_pair[pair], key=lambda item: item["pmid"])
        rng.shuffle(pool)
        take = max(1, round(target * len(pool) / len(disagreements)))
        sample.extend(pool[:take])
    sample = sample[:target]
    print("disagreements: %d total; sampled %d for human adjudication"
          % (len(disagreements), len(sample)))

    write_csv(
        "s1_confusion",
        ["pt_full_tier"] + TIERS,
        [[tier] + [matrix[tier][t] for t in TIERS] for tier in TIERS],
    )
    path = write_results(
        "s1_tier_audit",
        {
            "environment": environment_snapshot(),
            "n_documents": len(documents),
            "reproduces_committed_corpus": not mismatched,
            "committed_corpus_mismatches": mismatched,
            "tier_distribution": {
                condition: dict(collections.Counter(graded[condition].values()))
                for condition in CONDITIONS
            },
            "comparisons": comparisons,
            "sensitivity_independent_mapping": sensitivity,
            "propagation_to_confidence": propagation,
            "overgraded_top_tier": {
                "n_overgraded": len(overgraded_meta),
                "n_graded_meta_analysis": total_meta,
                "examples": [
                    {
                        "pmid": d["pmid"],
                        "title": d["title"],
                        "publication_types": d.get("publication_types") or [],
                    }
                    for d in sorted(overgraded_meta, key=lambda d: d["pmid"])[:10]
                ],
            },
            "disagreement_sample": sample,
            "n_disagreements": len(disagreements),
        },
    )
    print("\nwrote %s" % path)


if __name__ == "__main__":
    main()
