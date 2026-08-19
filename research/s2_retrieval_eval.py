"""S2 - retrieval quality, and whether a better retriever produces better citations.

Relevance labels come free from corpus provenance: ``build_science_corpus`` records
in ``topic_clusters`` which boolean PubMed query pulled each study into the corpus.
A study is relevant to a query about cluster C exactly when C fetched it. The labels
therefore come from a different retrieval paradigm (boolean/MeSH keyword search)
than the one under test (dense vector search), and cost nothing.

Those labels are incomplete: a study fetched by one cluster's query may be genuinely
relevant to another's, and it will be scored as a miss. That biases precision
*downward* only, so every precision figure here is a lower bound. Recall is stated
precisely as recall against the boolean-query result set, not against all relevant
science.

Two things are measured, and the gap between them is the point of the paper:

  stage 1  standard IR metrics on the retriever's own output
  stage 2  the citation set that actually survives the production post-processing
           (distance ceiling, lexical re-rank, accept gate)

Exact brute-force cosine is used rather than the production HNSW index: it removes
approximate search as a confound, is bit-reproducible, and leaves the committed
Chroma store untouched.

    ./.venv/bin/python -m research.s2_retrieval_eval
"""
from __future__ import annotations

import collections
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np

from research.common import (
    RESEARCH_DIR,
    SEED,
    banner,
    bootstrap_ci,
    environment_snapshot,
    load_corpus,
    load_query_config,
    mean,
    write_csv,
    write_results,
)

CACHE_DIR = RESEARCH_DIR / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

# Four arms chosen so that a biomedical win cannot be confused with a bigger model:
# bge-base is the size-matched general-purpose control for the two PubMedBERT arms.
ARMS = [
    {"key": "baseline_minilm", "model": "sentence-transformers/all-MiniLM-L6-v2",
     "family": "general", "role": "production baseline"},
    {"key": "general_small", "model": "BAAI/bge-small-en-v1.5",
     "family": "general", "role": "dimension-matched general"},
    {"key": "general_base", "model": "BAAI/bge-base-en-v1.5",
     "family": "general", "role": "size control for the biomedical arms"},
    {"key": "biomed_base", "model": "NeuML/pubmedbert-base-embeddings",
     "family": "biomedical", "role": "domain-specific"},
    {"key": "biomed_retrieval", "model": "pritamdeka/S-PubMedBert-MS-MARCO",
     "family": "biomedical", "role": "domain-specific, retrieval-tuned"},
]

def audited_semantic_query(request: Any, candidates: list[dict[str, Any]]) -> str:
    """The full-field-list query formulation, held fixed as this study's baseline.

    Owned here rather than imported from the engine so the baseline is a constant of the
    experiment: a baseline that tracked the live function would move whenever the engine
    moved, and the ``production_template`` and ``production_template_fixed`` columns
    would collapse into each other. The engine's current formulation is measured
    alongside it, so both conditions are reported from the same run.
    """
    names = ", ".join(c["name"] for c in candidates[:5])
    parts = [
        "%s resistance training protocol" % request.goal,
        "target muscles: %s" % ", ".join(request.muscles),
        "sessions per week: %s" % request.sessions,
        "split template: %s" % request.split_template,
    ]
    if request.equipment:
        parts.append("equipment available: %s" % ", ".join(request.equipment))
    if request.notes:
        parts.append("user notes: %s" % request.notes)
    if names:
        parts.append("candidate exercises: %s" % names)
    return " | ".join(parts)


# Held constant across every production-template query so that the only thing
# varying is the template itself.
TEMPLATE_REQUEST = dict(
    goal="hypertrophy", muscles="chest", sessions=3, session_minutes=60,
    equipment="", experience="intermediate", avoid_joints="", notes="",
)
K_VALUES = (5, 10, 20, 50)
MAX_FINDING_DISTANCE = 0.50  # protocol_demo.py:36
FINDINGS_LIMIT = 6           # query_findings(limit=6)


# --- Queries and labels --------------------------------------------------------------

# Muscle-gap clusters name their muscle in the id; the catalog's own taxonomy
# supplies the rest. Clusters about training principles imply no muscle at all.
GAP_CLUSTER_MUSCLES = {
    "gap_core_abs": "abs",
    "gap_calves": "calves",
    "gap_forearms_grip": "forearms",
    "gap_hip_abductors": "hip_abductors",
    "gap_hip_adductors": "hip_adductors",
}


def cluster_muscles(cluster_id: str, topic: str) -> tuple[str, str]:
    """Best-effort muscle for a cluster, and where it came from.

    An exercise-specific cluster is named after a movement, so we look that
    movement up in the catalog by alias and take the muscle its exercises most
    often target. Principle clusters (frequency, rep ranges, deloads) imply no
    muscle; those queries keep the neutral default and are reported separately so
    the production-template arm can be read with and without them.
    """
    from research.common import load_catalog

    if cluster_id in GAP_CLUSTER_MUSCLES:
        return GAP_CLUSTER_MUSCLES[cluster_id], "gap_cluster_id"
    if cluster_id.startswith("exercise_"):
        movement = topic.split(":", 1)[-1].strip().lower() if ":" in topic else \
            cluster_id[len("exercise_"):].replace("_", " ")
        counts: collections.Counter = collections.Counter()
        for exercise in load_catalog()["exercises"]:
            if movement in {a.lower() for a in (exercise.get("aliases") or [])}:
                for muscle in exercise["muscles"]["primary"]:
                    counts[muscle] += 1
        if counts:
            return counts.most_common(1)[0][0], "catalog_alias_lookup"
    return TEMPLATE_REQUEST["muscles"], "default_no_muscle_implied"


def build_query_set() -> list[dict[str, Any]]:
    """One evaluation query per corpus-represented cluster, in four formulations."""
    from protocol_engine.protocol_demo import build_semantic_query, normalize_request

    corpus = load_corpus()
    clusters = load_query_config()
    present = collections.Counter()
    for document in corpus["documents"]:
        for cluster_id in document.get("topic_clusters") or []:
            present[cluster_id] += 1

    queries = []
    for cluster_id in sorted(present):
        config = clusters.get(cluster_id)
        if not config:
            continue  # a cluster in the corpus with no surviving config entry
        strings = config.get("queries") or []
        topic = config.get("topic", cluster_id.replace("_", " "))
        muscles, muscle_source = cluster_muscles(cluster_id, topic)
        request = normalize_request(
            **{**TEMPLATE_REQUEST, "muscles": muscles, "notes": topic}
        )
        queries.append({
            "cluster_id": cluster_id,
            "topic": topic,
            "n_relevant": present[cluster_id],
            "muscles": muscles,
            "muscle_source": muscle_source,
            "formulations": {
                # The boolean string the corpus builder actually sent to PubMed.
                "boolean": strings[0] if strings else topic,
                # The bare topic label: no boilerplate at all.
                "topic": topic,
                # The same topic phrased as a question: isolates question boilerplate.
                "question": "what does the research say about %s for resistance training?" % topic,
                # The production string as audited, with request fields held constant
                # so the difference from "topic" is attributable to the template.
                "production_template": audited_semantic_query(request, []),
                # The same request through the current engine, after the S2c repair.
                "production_template_fixed": build_semantic_query(request, []),
            },
            "boolean_alt": strings[-1] if strings else topic,
        })
    return queries


def relevance_by_document(corpus: dict) -> dict[str, set[str]]:
    """doc_id -> the clusters that fetched it. This is the label set."""
    return {
        document["doc_id"]: set(document.get("topic_clusters") or [])
        for document in corpus["documents"]
    }


# --- Encoding ------------------------------------------------------------------------

def cosine_distance(queries: np.ndarray, corpus: np.ndarray) -> np.ndarray:
    """Cosine distance for unit-norm inputs, matching Chroma's hnsw:space = cosine.

    NumPy on Apple Accelerate raises divide-by-zero/overflow status flags from this
    matmul even when every input is finite, so we assert the inputs and silence the
    flags rather than leaving unexplained warnings in the log.
    """
    assert np.isfinite(queries).all() and np.isfinite(corpus).all(), "non-finite embeddings"
    with np.errstate(all="ignore"):
        return 1.0 - (queries @ corpus.T)


def encode(arm: dict[str, Any], texts: list[str], tag: str) -> np.ndarray:
    """L2-normalised embeddings, cached on disk so reruns are instant and identical."""
    cache = CACHE_DIR / ("%s__%s.npy" % (arm["key"], tag))
    if cache.exists():
        return np.load(cache)
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(arm["model"])
    vectors = model.encode(
        texts, batch_size=64, convert_to_numpy=True,
        normalize_embeddings=True, show_progress_bar=False,
    ).astype(np.float32)
    np.save(cache, vectors)
    del model
    return vectors


# --- Metrics -------------------------------------------------------------------------

def dedupe_to_documents(order: list[int], chunk_doc_ids: list[str]) -> list[str]:
    """Collapse a chunk ranking to a document ranking, as dedupe_findings does."""
    seen, ranked = set(), []
    for index in order:
        doc_id = chunk_doc_ids[index]
        if doc_id not in seen:
            seen.add(doc_id)
            ranked.append(doc_id)
    return ranked


def score_ranking(ranked_docs: list[str], relevant: set[str]) -> dict[str, float]:
    """Binary-relevance IR metrics for one query's document ranking."""
    n_relevant = len(relevant)
    hits = [1.0 if doc_id in relevant else 0.0 for doc_id in ranked_docs]
    out: dict[str, float] = {}
    for k in K_VALUES:
        out["precision_at_%d" % k] = sum(hits[:k]) / k
        out["recall_at_%d" % k] = (sum(hits[:k]) / n_relevant) if n_relevant else float("nan")
    # R-precision handles wildly varying relevant-set sizes (2 to 121 here), which
    # precision@10 cannot: a cluster with 121 relevant docs caps recall@10 at 8%.
    out["r_precision"] = sum(hits[:n_relevant]) / n_relevant if n_relevant else float("nan")
    dcg = sum(hit / math.log2(rank + 2) for rank, hit in enumerate(hits[:10]))
    ideal = sum(1.0 / math.log2(rank + 2) for rank in range(min(10, n_relevant)))
    out["ndcg_at_10"] = dcg / ideal if ideal else float("nan")
    first = next((rank for rank, hit in enumerate(hits, start=1) if hit), None)
    out["mrr"] = 1.0 / first if first else 0.0
    return out


# --- Stage 2: the production post-processing -----------------------------------------

def production_citation_set(
    ranked_chunks: list[int],
    distances: np.ndarray,
    chunks: list[dict[str, Any]],
    request: Any,
    distance_ceiling: float,
) -> list[str]:
    """Replay the real post-retrieval pipeline and return the PMIDs it would cite.

    Mirrors query_findings (protocol_demo.py:2311-2434): trusted-only pass, hard
    distance ceiling, dedupe to one chunk per document, lexical re-rank, accept gate.
    """
    from protocol_engine.protocol_demo import (
        apply_ambiguity_penalty,
        get_target_terms,
        score_text_relevance,
    )

    target_terms = get_target_terms(request)
    findings, seen_docs = [], set()
    for index in ranked_chunks:
        if float(distances[index]) > distance_ceiling:
            continue
        chunk = chunks[index]
        if chunk.get("manual_review_required"):
            continue  # the first pass filters to manual_review_required == False
        if chunk["doc_id"] in seen_docs:
            continue
        seen_docs.add(chunk["doc_id"])
        text = chunk["text"]
        request_relevance = apply_ambiguity_penalty(
            text, request, score_text_relevance(text, target_terms)
        )
        # No candidate exercises are supplied, so candidate_relevance is 0 and the
        # accept gate reduces to request_relevance >= 2.
        findings.append({
            "pmid": chunk["pmid"],
            "request_relevance": request_relevance,
            "retrieval_weight": float(chunk.get("retrieval_weight", 0.0)),
            "distance": float(distances[index]),
        })
    findings.sort(
        key=lambda item: (item["request_relevance"], item["retrieval_weight"], -item["distance"]),
        reverse=True,
    )
    accepted = [f for f in findings if f["request_relevance"] >= 2]
    return [f["pmid"] for f in accepted[:FINDINGS_LIMIT]]


def jaccard(left: list[str], right: list[str]) -> float:
    a, b = set(left), set(right)
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b) if (a | b) else 1.0


# --- Main ----------------------------------------------------------------------------

def main() -> None:
    from protocol_engine.protocol_demo import normalize_request
    from scipy.stats import wilcoxon

    corpus = load_corpus()
    chunks = corpus["chunks"]
    chunk_texts = [c["text"] for c in chunks]
    chunk_doc_ids = [c["doc_id"] for c in chunks]
    labels = relevance_by_document(corpus)
    queries = build_query_set()
    formulations = ["boolean", "topic", "question", "production_template",
                    "production_template_fixed"]

    banner("S2 - retrieval quality, embedding ablation, query-formulation ablation")
    print("queries: %d clusters | corpus: %d chunks / %d documents"
          % (len(queries), len(chunks), len(corpus["documents"])))
    print("relevant-set size: min %d  median %d  max %d"
          % (min(q["n_relevant"] for q in queries),
             int(np.median([q["n_relevant"] for q in queries])),
             max(q["n_relevant"] for q in queries)))

    per_query: dict[str, dict[str, list[dict[str, float]]]] = {}
    stage2: dict[str, list[list[str]]] = {}
    stage2_rank_matched: dict[str, list[list[str]]] = {}
    distance_matrices: dict[str, np.ndarray] = {}
    pool_stats: dict[str, dict[str, float]] = {}
    pass_rates: dict[str, float] = {}
    encode_times: dict[str, float] = {}

    for arm in ARMS:
        start = time.time()
        try:
            corpus_vectors = encode(arm, chunk_texts, "corpus")
        except Exception as error:  # noqa: BLE001 - a missing arm must not sink the study
            print("\n!! skipping %s: %s" % (arm["key"], error))
            continue
        encode_times[arm["key"]] = time.time() - start
        per_query[arm["key"]] = {}

        for formulation in formulations:
            texts = [q["formulations"][formulation] for q in queries]
            query_vectors = encode(arm, texts, "q_%s" % formulation)
            # Cosine distance, matching Chroma's hnsw:space = cosine.
            distance_matrix = cosine_distance(query_vectors, corpus_vectors)
            scored = []
            for row, query in enumerate(queries):
                order = np.argsort(distance_matrix[row], kind="stable")
                ranked_docs = dedupe_to_documents(list(order), chunk_doc_ids)
                relevant = {d for d, clusters in labels.items()
                            if query["cluster_id"] in clusters}
                scored.append(score_ranking(ranked_docs, relevant))
            per_query[arm["key"]][formulation] = scored

        # Keep the production-template distances; stage 2 runs as a second pass so
        # each arm can be rank-matched against the baseline's pool size.
        query_vectors = encode(
            arm, [q["formulations"]["production_template"] for q in queries],
            "q_production_template",
        )
        distance_matrices[arm["key"]] = cosine_distance(query_vectors, corpus_vectors)
        print("  encoded %-18s %5.1fs  dim=%d" % (arm["key"], encode_times[arm["key"]],
                                                  corpus_vectors.shape[1]))

    # --- stage 2: replay the production post-processing --------------------------------
    baseline_key = ARMS[0]["key"]
    baseline_pool = [
        int((distance_matrices[baseline_key][row] <= MAX_FINDING_DISTANCE).sum())
        for row in range(len(queries))
    ]
    for arm_key, distance_matrix in distance_matrices.items():
        fixed, matched, pool_sizes = [], [], []
        for row, query in enumerate(queries):
            request = normalize_request(**{
                **TEMPLATE_REQUEST, "muscles": query["muscles"], "notes": query["topic"]
            })
            order = list(np.argsort(distance_matrix[row], kind="stable"))
            pool_sizes.append(int((distance_matrix[row] <= MAX_FINDING_DISTANCE).sum()))
            fixed.append(production_citation_set(
                order, distance_matrix[row], chunks, request, MAX_FINDING_DISTANCE))
            # Rank-matched: admit exactly as many chunks as the baseline admitted for
            # this query, so any remaining difference is ranking, not the threshold.
            take = max(1, min(len(chunks), baseline_pool[row]))
            ceiling = float(np.sort(distance_matrix[row])[take - 1])
            matched.append(production_citation_set(
                order, distance_matrix[row], chunks, request, ceiling))
        stage2[arm_key] = fixed
        stage2_rank_matched[arm_key] = matched
        pool_stats[arm_key] = {
            "mean_chunks_within_0.50": mean(pool_sizes),
            "median_chunks_within_0.50": float(np.median(pool_sizes)),
            "queries_with_empty_pool": sum(1 for n in pool_sizes if n == 0),
            "distance_p05": float(np.percentile(distance_matrix, 5)),
            "distance_p50": float(np.percentile(distance_matrix, 50)),
        }
        pass_rates[arm_key] = sum(1 for c in fixed if c) / len(queries)

    # --- stage 1 table ---------------------------------------------------------------
    print("\nSTAGE 1 - retriever output, nDCG@10 (95%% CI), n=%d queries" % len(queries))
    print("%-20s" % "arm" + "".join("%-22s" % f[:21] for f in formulations))
    stage1_summary: dict[str, Any] = {}
    for arm_key, by_formulation in per_query.items():
        cells, row_summary = [], {}
        for formulation in formulations:
            values = [s["ndcg_at_10"] for s in by_formulation[formulation]]
            low, high = bootstrap_ci(values)
            cells.append("%.3f [%.3f-%.3f]" % (mean(values), low, high))
            row_summary[formulation] = {
                metric: mean([s[metric] for s in by_formulation[formulation]])
                for metric in by_formulation[formulation][0]
            }
            row_summary[formulation]["ndcg_at_10_ci"] = [low, high]
        stage1_summary[arm_key] = row_summary
        print("%-20s" % arm_key + "".join("%-22s" % c for c in cells))

    print("\nSTAGE 1 - all metrics on the production-template formulation")
    metrics = ["precision_at_10", "r_precision", "ndcg_at_10", "mrr", "recall_at_50"]
    print("%-20s %s" % ("arm", "".join("%16s" % m for m in metrics)))
    for arm_key in per_query:
        print("%-20s %s" % (arm_key, "".join(
            "%16.3f" % stage1_summary[arm_key]["production_template"][m] for m in metrics)))

    # Paired significance against the production baseline, same queries in both arms.
    paired: dict[str, Any] = {}
    if baseline_key in per_query:
        base = [s["ndcg_at_10"] for s in per_query[baseline_key]["production_template"]]
        print("\nPAIRED vs %s (nDCG@10, production-template, Wilcoxon signed-rank)" % baseline_key)
        for arm_key in per_query:
            if arm_key == baseline_key:
                continue
            other = [s["ndcg_at_10"] for s in per_query[arm_key]["production_template"]]
            deltas = [b - a for a, b in zip(base, other)]
            try:
                statistic, p_value = wilcoxon(base, other)
            except ValueError:  # all deltas zero
                statistic, p_value = float("nan"), 1.0
            paired[arm_key] = {"mean_delta": mean(deltas), "wilcoxon_p": float(p_value),
                               "n_better": sum(1 for d in deltas if d > 0),
                               "n_worse": sum(1 for d in deltas if d < 0)}
            print("  %-20s delta=%+.3f  p=%.4f  better/worse = %d/%d"
                  % (arm_key, mean(deltas), p_value, paired[arm_key]["n_better"],
                     paired[arm_key]["n_worse"]))

    # --- stage 2 --------------------------------------------------------------------
    print("\nSTAGE 2 - the citation set that survives production post-processing")
    print("  a query is 'cited' if any finding clears distance<=%.2f and the accept gate"
          % MAX_FINDING_DISTANCE)
    stage2_summary: dict[str, Any] = {}
    print("  %-20s %9s %9s %11s %11s" % ("arm", "pool@0.50", "cites", "J(fixed)", "J(matched)"))
    for arm_key, cited in stage2.items():
        fixed_overlap = mean([jaccard(a, b) for a, b in zip(stage2[baseline_key], cited)])
        matched_overlap = mean([
            jaccard(a, b) for a, b in zip(stage2[baseline_key], stage2_rank_matched[arm_key])
        ])
        stage2_summary[arm_key] = {
            "queries_with_any_citation_rate": pass_rates[arm_key],
            "mean_citations_per_query": mean([len(c) for c in cited]),
            "jaccard_vs_baseline_fixed_threshold": fixed_overlap,
            "jaccard_vs_baseline_rank_matched": matched_overlap,
            **pool_stats[arm_key],
        }
        print("  %-20s %9.0f %9.2f %11.3f %11.3f"
              % (arm_key, pool_stats[arm_key]["mean_chunks_within_0.50"],
                 mean([len(c) for c in cited]), fixed_overlap, matched_overlap))
    print("  J(fixed) keeps the hard-coded 0.50 ceiling; J(matched) gives every arm the")
    print("  baseline's pool size, so the residual difference is ranking, not the threshold.")

    write_csv(
        "s2_stage1",
        ["arm", "formulation"] + metrics,
        [[arm_key, formulation] + [round(stage1_summary[arm_key][formulation][m], 4) for m in metrics]
         for arm_key in per_query for formulation in formulations],
    )
    path = write_results("s2_retrieval_eval", {
        "environment": environment_snapshot(),
        "design": {
            "n_queries": len(queries),
            "unit_of_analysis": "cluster (one query per corpus-represented cluster)",
            "search": "exact brute-force cosine, not the production HNSW index",
            "label_source": "corpus provenance (topic_clusters)",
            "label_caveat": "labels are incomplete, so precision is a lower bound; recall is "
                            "recall against the boolean-query result set",
            "arms": ARMS,
            "formulations": formulations,
            "template_request": TEMPLATE_REQUEST,
            "seed": SEED,
        },
        "queries": queries,
        "encode_seconds": {k: round(v, 1) for k, v in encode_times.items()},
        "stage1": stage1_summary,
        "stage1_paired_vs_baseline": paired,
        "stage2": stage2_summary,
        "stage2_cited_pmids": stage2,
        "stage2_cited_pmids_rank_matched": stage2_rank_matched,
    })
    print("\nwrote %s" % path)


if __name__ == "__main__":
    main()
