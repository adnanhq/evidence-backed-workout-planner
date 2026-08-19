"""S2b - is the distance ceiling calibrated, and does it survive a model swap?

``protocol_demo.py:32-36`` documents MAX_FINDING_DISTANCE = 0.50 as calibrated:

    legitimate builder queries score 0.23-0.45 against this corpus; off-topic
    probes (yoga, nutrition, swimming) score >= 0.51

but ``calibrate_retrieval.py`` ships six in-domain requests and no off-topic probes,
so that claim cannot be reproduced from the repository. This module supplies the
missing probe set and reports the calibration for every embedding arm, because a
cosine ceiling is a property of the embedding space, not of the corpus.

    ./.venv/bin/python -m research.s2b_threshold_roc
"""
from __future__ import annotations

from typing import Any

import numpy as np

from research.common import banner, environment_snapshot, load_corpus, mean, write_csv, write_results
from research.s2_retrieval_eval import ARMS, cosine_distance, encode, build_query_set

# Named in the code comment, plus harder adjacent cases. "Adjacent" probes are the
# real test: a ceiling that only rejects dentistry is not doing any work.
OFF_TOPIC_PROBES = {
    "far": [
        "dental caries prevention in children",
        "urban air pollution and childhood asthma",
        "convolutional neural networks for image classification",
        "monetary policy and inflation expectations",
    ],
    "adjacent": [
        "yoga practice for flexibility and stress",
        "sports nutrition protein timing for recovery",
        "competitive swimming stroke technique",
        "marathon endurance running training plan",
        "sleep quality and daytime fatigue",
    ],
}
THRESHOLDS = [round(0.20 + 0.025 * i, 3) for i in range(25)]  # 0.200 .. 0.800
SHIPPED_CEILING = 0.50


def auc(positive: list[float], negative: list[float]) -> float:
    """P(a random off-topic query is farther than a random in-domain one).

    1.0 means some threshold separates them perfectly; 0.5 means none does.
    """
    wins = sum(
        1.0 if n > p else 0.5 if n == p else 0.0
        for p in positive for n in negative
    )
    return wins / (len(positive) * len(negative))


def main() -> None:
    corpus = load_corpus()
    chunks = corpus["chunks"]
    chunk_texts = [c["text"] for c in chunks]
    chunk_doc_ids = [c["doc_id"] for c in chunks]
    labels = {d["doc_id"]: set(d.get("topic_clusters") or []) for d in corpus["documents"]}
    queries = build_query_set()
    probe_texts = OFF_TOPIC_PROBES["far"] + OFF_TOPIC_PROBES["adjacent"]
    probe_kind = ["far"] * len(OFF_TOPIC_PROBES["far"]) + ["adjacent"] * len(OFF_TOPIC_PROBES["adjacent"])

    banner("S2b - distance-ceiling calibration across embedding spaces")
    print("in-domain queries: %d (topic formulation)  off-topic probes: %d"
          % (len(queries), len(probe_texts)))

    results: dict[str, Any] = {}
    sweep_rows = []
    for arm in ARMS:
        try:
            corpus_vectors = encode(arm, chunk_texts, "corpus")
        except Exception as error:  # noqa: BLE001
            print("!! skipping %s: %s" % (arm["key"], error))
            continue
        in_domain = cosine_distance(
            encode(arm, [q["formulations"]["topic"] for q in queries], "q_topic"),
            corpus_vectors,
        )
        off_topic = cosine_distance(
            encode(arm, probe_texts, "q_offtopic"), corpus_vectors
        )
        # A query survives on its nearest chunk: if that clears the ceiling it cites.
        nearest_in = in_domain.min(axis=1).tolist()
        nearest_off = off_topic.min(axis=1).tolist()

        sweep = []
        for threshold in THRESHOLDS:
            admitted_precision, admitted_recall, admitted_fraction = [], [], []
            for row, query in enumerate(queries):
                relevant = {d for d, clusters in labels.items() if query["cluster_id"] in clusters}
                mask = in_domain[row] <= threshold
                admitted_fraction.append(float(mask.mean()))
                docs = {chunk_doc_ids[i] for i in np.flatnonzero(mask)}
                if docs:
                    admitted_precision.append(len(docs & relevant) / len(docs))
                admitted_recall.append(len(docs & relevant) / len(relevant) if relevant else float("nan"))
            rejected_far = sum(
                1 for d, k in zip(nearest_off, probe_kind) if k == "far" and d > threshold
            ) / len(OFF_TOPIC_PROBES["far"])
            rejected_adjacent = sum(
                1 for d, k in zip(nearest_off, probe_kind) if k == "adjacent" and d > threshold
            ) / len(OFF_TOPIC_PROBES["adjacent"])
            row_out = {
                "threshold": threshold,
                "mean_corpus_fraction_admitted": mean(admitted_fraction),
                "mean_precision_of_admitted_set": mean(admitted_precision) if admitted_precision else float("nan"),
                "mean_recall_of_admitted_set": mean([r for r in admitted_recall if r == r]),
                "off_topic_far_rejected": rejected_far,
                "off_topic_adjacent_rejected": rejected_adjacent,
                "in_domain_queries_silenced": sum(1 for d in nearest_in if d > threshold) / len(nearest_in),
            }
            sweep.append(row_out)
            sweep_rows.append([arm["key"]] + [round(row_out[k], 4) for k in
                                              ("threshold", "mean_corpus_fraction_admitted",
                                               "mean_precision_of_admitted_set",
                                               "mean_recall_of_admitted_set",
                                               "off_topic_far_rejected",
                                               "off_topic_adjacent_rejected",
                                               "in_domain_queries_silenced")])

        separability = auc(nearest_in, nearest_off)
        # The ceiling that best separates in-domain from off-topic in THIS space.
        best = max(
            THRESHOLDS,
            key=lambda t: (sum(1 for d in nearest_in if d <= t) / len(nearest_in))
            + (sum(1 for d in nearest_off if d > t) / len(nearest_off)),
        )
        at_shipped = next(r for r in sweep if r["threshold"] == SHIPPED_CEILING)
        results[arm["key"]] = {
            "model": arm["model"],
            "family": arm["family"],
            "nearest_distance_in_domain": {
                "min": min(nearest_in), "p50": float(np.median(nearest_in)), "max": max(nearest_in)
            },
            "nearest_distance_off_topic": {
                "min": min(nearest_off), "p50": float(np.median(nearest_off)), "max": max(nearest_off)
            },
            "separability_auc": separability,
            "best_separating_ceiling_in_this_space": best,
            "at_shipped_ceiling_0.50": at_shipped,
            "sweep": sweep,
        }
        print("\n%-20s in-domain nearest %.3f-%.3f (median %.3f) | off-topic %.3f-%.3f (median %.3f)"
              % (arm["key"],
                 min(nearest_in), max(nearest_in), float(np.median(nearest_in)),
                 min(nearest_off), max(nearest_off), float(np.median(nearest_off))))
        print("%-20s separability AUC=%.3f | best ceiling here=%.3f | shipped 0.50 admits %.1f%% of the corpus"
              % ("", separability, best, 100 * at_shipped["mean_corpus_fraction_admitted"]))
        print("%-20s at 0.50: rejects %.0f%% of far probes, %.0f%% of adjacent probes"
              % ("", 100 * at_shipped["off_topic_far_rejected"],
                 100 * at_shipped["off_topic_adjacent_rejected"]))

    write_csv(
        "s2b_threshold_sweep",
        ["arm", "threshold", "corpus_fraction_admitted", "precision_of_admitted",
         "recall_of_admitted", "far_probes_rejected", "adjacent_probes_rejected",
         "in_domain_queries_silenced"],
        sweep_rows,
    )
    path = write_results("s2b_threshold_roc", {
        "environment": environment_snapshot(),
        "shipped_ceiling": SHIPPED_CEILING,
        "off_topic_probes": OFF_TOPIC_PROBES,
        "documented_claim": "legitimate builder queries score 0.23-0.45; off-topic probes "
                            "(yoga, nutrition, swimming) score >= 0.51 (protocol_demo.py:32-36)",
        "arms": results,
    })
    print("\nwrote %s" % path)


if __name__ == "__main__":
    main()
