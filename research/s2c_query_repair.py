"""S2c - repairing the semantic query, measured rather than guessed.

S2 identified query formulation as the dominant lever on retrieval quality: it spans
roughly six times more nDCG than the choice of embedding model. This module tests
candidate rewrites of ``build_semantic_query`` against the same provenance labels and
picks a winner, so the change we recommend is an empirical result rather than an
opinion.

Two differences from the S2 production-template arm, both deliberate. There, request
fields were held constant and no candidate exercises were supplied, which isolated the
template itself. Here every query is built the way a live request would build it —
correct muscle, real candidate exercise names from ``filter_and_score_exercises`` — so
the baseline is the realistic one and any improvement is measured against what the
system actually sends.

    ./.venv/bin/python -m research.s2c_query_repair
"""
from __future__ import annotations

from typing import Any, Callable

import numpy as np
from scipy.stats import wilcoxon

from research.common import (
    banner,
    bootstrap_ci,
    environment_snapshot,
    load_catalog,
    load_corpus,
    mean,
    write_csv,
    write_results,
)
from research.s2_retrieval_eval import (
    ARMS,
    audited_semantic_query,
    build_query_set,
    cosine_distance,
    dedupe_to_documents,
    encode,
    relevance_by_document,
    score_ranking,
)

BASELINE_ARM = ARMS[0]  # the shipped embedding model; the fix must work for it


# --- Candidate formulations ----------------------------------------------------------
# Each takes the same (request, candidates) as the real function and returns a query
# string. `current` is a verbatim copy of the shipped implementation.

q_current = audited_semantic_query  # the shipped template as audited, frozen in S2


def q_drop_scheduling(request: Any, candidates: list[dict[str, Any]]) -> str:
    """Sessions per week and split template describe layout, not subject matter."""
    names = ", ".join(c["name"] for c in candidates[:5])
    parts = [
        "%s resistance training protocol" % request.goal,
        "target muscles: %s" % ", ".join(request.muscles),
    ]
    if request.equipment:
        parts.append("equipment available: %s" % ", ".join(request.equipment))
    if request.notes:
        parts.append("user notes: %s" % request.notes)
    if names:
        parts.append("candidate exercises: %s" % names)
    return " | ".join(parts)


def q_drop_scheduling_and_equipment(request: Any, candidates: list[dict[str, Any]]) -> str:
    names = ", ".join(c["name"] for c in candidates[:5])
    parts = [
        "%s resistance training protocol" % request.goal,
        "target muscles: %s" % ", ".join(request.muscles),
    ]
    if request.notes:
        parts.append("user notes: %s" % request.notes)
    if names:
        parts.append("candidate exercises: %s" % names)
    return " | ".join(parts)


def q_lead_with_need(request: Any, candidates: list[dict[str, Any]]) -> str:
    """Subject matter first, as a phrase rather than a labelled field list."""
    names = ", ".join(c["name"] for c in candidates[:5])
    parts = ["%s %s resistance training" % (", ".join(request.muscles), request.goal)]
    if request.notes:
        parts.append(request.notes)
    if names:
        parts.append(names)
    return " | ".join(parts)


def q_minimal(request: Any, candidates: list[dict[str, Any]]) -> str:
    """The user's need alone, with no candidate names and no scaffolding."""
    parts = ["%s %s resistance training" % (", ".join(request.muscles), request.goal)]
    if request.notes:
        parts.append(request.notes)
    return " | ".join(parts)


def q_minimal_with_equipment(request: Any, candidates: list[dict[str, Any]]) -> str:
    """As q_minimal, but keeps equipment - tested separately because abstracts do
    sometimes contrast machine, free-weight and band training."""
    parts = ["%s %s resistance training" % (", ".join(request.muscles), request.goal)]
    if request.notes:
        parts.append(request.notes)
    if request.equipment:
        parts.append(", ".join(request.equipment))
    return " | ".join(parts)


VARIANTS: dict[str, Callable[..., str]] = {
    "current": q_current,
    "drop_scheduling": q_drop_scheduling,
    "drop_scheduling_and_equipment": q_drop_scheduling_and_equipment,
    "lead_with_need": q_lead_with_need,
    "minimal": q_minimal,
    "minimal_with_equipment": q_minimal_with_equipment,
}

# Selecting a winner and reporting its gain on the same queries would overfit, so the
# clusters are split once, deterministically: the winner is chosen on `dev` and the
# headline gain is read off `heldout`.
def split_clusters(queries: list[dict[str, Any]]) -> tuple[list[int], list[int]]:
    ordered = sorted(range(len(queries)), key=lambda i: queries[i]["cluster_id"])
    dev = [i for n, i in enumerate(ordered) if n % 2 == 0]
    heldout = [i for n, i in enumerate(ordered) if n % 2 == 1]
    return dev, heldout


def main() -> None:
    from protocol_engine.protocol_demo import (
        build_semantic_query,
        filter_and_score_exercises,
        normalize_request,
    )

    corpus, catalog = load_corpus(), load_catalog()
    chunks = corpus["chunks"]
    chunk_doc_ids = [c["doc_id"] for c in chunks]
    labels = relevance_by_document(corpus)
    queries = build_query_set()

    banner("S2c - repairing the semantic query")
    print("model: %s (the shipped one) | %d cluster queries, built as a live request would"
          % (BASELINE_ARM["model"], len(queries)))

    # Reconstruct each cluster's request and its real candidate shortlist once.
    contexts = []
    for index, query in enumerate(queries):
        # Alternate equipment on and off: a live request usually specifies some, and
        # without it two of the variants would collapse into the same string.
        equipment = "barbell,dumbbell" if index % 2 == 0 else ""
        request = normalize_request(
            goal="hypertrophy", muscles=query["muscles"], sessions=3, session_minutes=60,
            equipment=equipment, experience="intermediate", avoid_joints="", notes=query["topic"],
        )
        candidates = filter_and_score_exercises(request, catalog["exercises"])
        contexts.append((query, request, candidates))

    # Guard: q_current must be a faithful copy of the shipped function, or the whole
    # comparison is against a strawman.
    repaired = [
        q["cluster_id"] for q, r, c in contexts
        if build_semantic_query(r, c) == q_current(r, c)
    ]
    winner_live = [
        q["cluster_id"] for q, r, c in contexts
        if build_semantic_query(r, c) != q_minimal(r, c)
    ]
    print("engine still on the audited template: %s | engine matches q_minimal: %s"
          % (len(repaired) == len(contexts), not winner_live))

    corpus_vectors = encode(BASELINE_ARM, [c["text"] for c in chunks], "corpus")
    results: dict[str, Any] = {}
    per_query_ndcg: dict[str, list[float]] = {}

    for name, builder in VARIANTS.items():
        texts = [builder(request, candidates) for _, request, candidates in contexts]
        vectors = encode(BASELINE_ARM, texts, "repair_%s" % name)
        distances = cosine_distance(vectors, corpus_vectors)
        scored = []
        for row, (query, _, _) in enumerate(contexts):
            order = np.argsort(distances[row], kind="stable")
            ranked = dedupe_to_documents(list(order), chunk_doc_ids)
            relevant = {d for d, cl in labels.items() if query["cluster_id"] in cl}
            scored.append(score_ranking(ranked, relevant))
        per_query_ndcg[name] = [s["ndcg_at_10"] for s in scored]
        low, high = bootstrap_ci(per_query_ndcg[name])
        results[name] = {
            "example_query": texts[0],
            "mean_query_chars": mean([len(t) for t in texts]),
            "ndcg_at_10": mean(per_query_ndcg[name]),
            "ndcg_at_10_ci": [low, high],
            **{m: mean([s[m] for s in scored])
               for m in ("precision_at_10", "r_precision", "mrr", "recall_at_50")},
        }

    dev, heldout = split_clusters(queries)
    base = per_query_ndcg["current"]

    def on(split: list[int], name: str) -> float:
        return mean([per_query_ndcg[name][i] for i in split])

    def paired(split: list[int], name: str) -> dict[str, Any]:
        a = [base[i] for i in split]
        b = [per_query_ndcg[name][i] for i in split]
        try:
            _, p_value = wilcoxon(a, b)
        except ValueError:
            p_value = 1.0
        return {
            "ndcg_at_10": mean(b),
            "delta_vs_current": mean(b) - mean(a),
            "relative_gain": (mean(b) / mean(a) - 1.0) if mean(a) else float("nan"),
            "wilcoxon_p": float(p_value),
            "n_better": sum(1 for x, y in zip(a, b) if y > x),
            "n_worse": sum(1 for x, y in zip(a, b) if y < x),
        }

    print("\n%-32s %8s %-18s %9s %9s %8s" % (
        "variant", "nDCG@10", "95% CI", "P@10", "R-prec", "chars"))
    for name, row in results.items():
        print("%-32s %8.3f [%.3f-%.3f]  %9.3f %9.3f %8.0f" % (
            name, row["ndcg_at_10"], row["ndcg_at_10_ci"][0], row["ndcg_at_10_ci"][1],
            row["precision_at_10"], row["r_precision"], row["mean_query_chars"]))
        row["dev"] = paired(dev, name)
        row["heldout"] = paired(heldout, name)
        results[name]["delta_vs_current"] = mean(
            [per_query_ndcg[name][i] - base[i] for i in range(len(base))])
        results[name]["relative_gain"] = mean(per_query_ndcg[name]) / mean(base) - 1.0

    print("\nselection split: dev n=%d, held-out n=%d (deterministic, by cluster id)"
          % (len(dev), len(heldout)))
    print("%-32s %12s %12s %12s" % ("variant", "dev nDCG", "held-out", "held-out p"))
    for name in VARIANTS:
        print("%-32s %12.3f %12.3f %12.4f" % (
            name, on(dev, name), on(heldout, name), results[name]["heldout"]["wilcoxon_p"]))

    # Chosen on dev only. Ties broken toward the shorter query.
    winner = max(
        (n for n in VARIANTS if n != "current"),
        key=lambda n: (round(on(dev, n), 4), -results[n]["mean_query_chars"]),
    )
    held = results[winner]["heldout"]
    print("\nchosen on dev: %s" % winner)
    print("held-out result: %.3f vs %.3f (%+.0f%%), p=%.4f, better/worse = %d/%d" % (
        held["ndcg_at_10"], on(heldout, "current"), 100 * held["relative_gain"],
        held["wilcoxon_p"], held["n_better"], held["n_worse"]))
    print("\nexample query, shipped:\n  %s" % results["current"]["example_query"][:200])
    print("example query, %s:\n  %s" % (winner, results[winner]["example_query"][:200]))

    write_csv(
        "s2c_query_repair",
        ["variant", "ndcg_at_10", "ci_low", "ci_high", "precision_at_10", "r_precision",
         "mrr", "recall_at_50", "mean_query_chars", "delta_vs_current", "wilcoxon_p"],
        [[n, round(r["ndcg_at_10"], 4), round(r["ndcg_at_10_ci"][0], 4),
          round(r["ndcg_at_10_ci"][1], 4), round(r["precision_at_10"], 4),
          round(r["r_precision"], 4), round(r["mrr"], 4), round(r["recall_at_50"], 4),
          round(r["mean_query_chars"], 1), round(r.get("delta_vs_current", 0.0), 4),
          round(r.get("wilcoxon_p", 1.0), 4)] for n, r in results.items()],
    )
    write_results("s2c_query_repair", {
        "environment": environment_snapshot(),
        "embedding_model": BASELINE_ARM["model"],
        "n_queries": len(queries),
        "selection_protocol": "variant chosen on the dev half only; the headline gain is "
                              "read off the held-out half, so the reported improvement is "
                              "not selected on the queries it is reported from",
        "dev_indices": dev,
        "heldout_indices": heldout,
        "baseline_is_the_frozen_audited_template": True,
        "engine_now_uses_the_winner": not winner_live,
        "variants": results,
        "winner": winner,
    })
    print("\nwrote results/s2c_query_repair.json")


if __name__ == "__main__":
    main()
