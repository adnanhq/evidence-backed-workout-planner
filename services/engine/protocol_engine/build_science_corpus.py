from __future__ import annotations

import argparse
import os
import re
import socket
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from .pipeline_common import (
        clamp,
        chunk_text,
        mean,
        normalize_text,
        now_utc_iso,
        parse_year,
        read_json,
        write_json,
    )
except ImportError:  # pragma: no cover
    from pipeline_common import (
        clamp,
        chunk_text,
        mean,
        normalize_text,
        now_utc_iso,
        parse_year,
        read_json,
        write_json,
    )

try:
    from Bio import Entrez, Medline
except ImportError:  # pragma: no cover
    Entrez = None
    Medline = None


EVIDENCE_TIER_SCORES = {
    "meta_analysis": 1.0,
    "systematic_review": 0.92,
    "rct": 0.85,
    "controlled_trial": 0.75,
    "observational": 0.6,
    "narrative_review": 0.5,
    "other": 0.4,
}

META_PATTERNS = ("meta-analysis", "meta analysis")
SYSTEMATIC_PATTERNS = ("systematic review",)
RCT_PATTERNS = (
    "randomized controlled trial",
    "randomised controlled trial",
    "randomized trial",
    "randomised trial",
    "randomly allocated",
    "randomly assigned",
)
CONTROLLED_PATTERNS = (
    "controlled clinical trial",
    "clinical trial",
    "training intervention",
    "intervention study",
    "pre- and post-training",
)
OBSERVATIONAL_PATTERNS = (
    "cohort",
    "cross-sectional",
    "case-control",
    "observational",
)
NARRATIVE_REVIEW_PATTERNS = ("review",)

EMG_PATTERNS = ("electromyography", "emg")
IMAGING_PATTERNS = (
    "mri",
    "magnetic resonance imaging",
    "ultrasound",
    "muscle thickness",
    "cross-sectional area",
    "dexa",
)
PERFORMANCE_PATTERNS = (
    "1rm",
    "one repetition maximum",
    "strength",
    "power output",
    "force production",
)
HYPERTROPHY_PATTERNS = ("hypertrophy", "muscle growth")

N_EQUALS_PATTERN = re.compile(r"\b[nN]\s*=\s*(\d{1,4})\b")
PARTICIPANT_PATTERN = re.compile(
    r"\b(\d{1,4})\s+(?:[a-z-]+\s+){0,3}"
    r"(participants|subjects|men|women|adults|athletes|individuals|males|females)\b",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an evidence-weighted PubMed corpus for resistance training RAG retrieval."
        )
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Contact email required by NCBI Entrez. Falls back to ENTREZ_EMAIL env var.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional NCBI API key. Falls back to NCBI_API_KEY env var.",
    )
    parser.add_argument(
        "--tool-name",
        default="cse499-fitness-rag-pipeline",
        help="Tool identifier sent to Entrez.",
    )
    parser.add_argument(
        "--query-config",
        default="config/pubmed_queries.json",
        help="Path to topic cluster query config JSON.",
    )
    parser.add_argument(
        "--extra-query-config",
        default=None,
        help=(
            "Optional second cluster config (e.g. generated exercise-pattern queries) "
            "whose clusters are merged with --query-config. Clusters may set a per-cluster "
            "'retmax' to override the global default."
        ),
    )
    parser.add_argument(
        "--retmax-per-query",
        type=int,
        default=None,
        help="Override top N results pulled per query.",
    )
    parser.add_argument(
        "--from-year",
        type=int,
        default=2018,
        help="Minimum publication year to keep in corpus.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=900,
        help="Maximum characters per chunk.",
    )
    parser.add_argument(
        "--request-sleep-seconds",
        type=float,
        default=0.34,
        help="Delay between Entrez requests to respect rate limits.",
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=45.0,
        help="Global socket timeout for Entrez requests.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Retries per Entrez request when transient failures occur.",
    )
    parser.add_argument(
        "--max-documents",
        type=int,
        default=0,
        help="Optional cap after ranking. 0 means no cap.",
    )
    parser.add_argument(
        "--low-topic-relevance-threshold",
        type=float,
        default=0.12,
        help="Topic relevance cutoff used to identify potentially off-topic records.",
    )
    parser.add_argument(
        "--low-topic-review-max-weight",
        type=float,
        default=0.65,
        help="Only low-topic records with retrieval_weight below this are queued for review.",
    )
    parser.add_argument(
        "--lower-tier-review-max-weight",
        type=float,
        default=0.55,
        help="Only lower-evidence-tier records below this weight are queued for review.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/science_corpus.json",
        help="Output path for the final corpus JSON.",
    )
    parser.add_argument(
        "--manual-review-output",
        default="data/processed/science_manual_review_queue.json",
        help="Output path for manual review queue JSON.",
    )
    return parser.parse_args()


def classify_evidence_tier(
    publication_types: list[str],
    title: str,
    abstract: str,
) -> tuple[str, float]:
    joined_types = " ".join(publication_types).lower()
    text = f"{title} {abstract}".lower()

    if any(pattern in joined_types or pattern in text for pattern in META_PATTERNS):
        return "meta_analysis", EVIDENCE_TIER_SCORES["meta_analysis"]
    if any(pattern in joined_types or pattern in text for pattern in SYSTEMATIC_PATTERNS):
        return "systematic_review", EVIDENCE_TIER_SCORES["systematic_review"]
    if any(pattern in joined_types or pattern in text for pattern in RCT_PATTERNS):
        return "rct", EVIDENCE_TIER_SCORES["rct"]
    if any(pattern in joined_types or pattern in text for pattern in CONTROLLED_PATTERNS):
        return "controlled_trial", EVIDENCE_TIER_SCORES["controlled_trial"]
    if any(pattern in joined_types or pattern in text for pattern in OBSERVATIONAL_PATTERNS):
        return "observational", EVIDENCE_TIER_SCORES["observational"]
    if any(pattern in joined_types or pattern in text for pattern in NARRATIVE_REVIEW_PATTERNS):
        return "narrative_review", EVIDENCE_TIER_SCORES["narrative_review"]
    return "other", EVIDENCE_TIER_SCORES["other"]


def infer_measurement_modalities(title: str, abstract: str) -> list[str]:
    text = f"{title} {abstract}".lower()
    modalities: list[str] = []
    if any(marker in text for marker in EMG_PATTERNS):
        modalities.append("EMG")
    if any(marker in text for marker in IMAGING_PATTERNS):
        modalities.append("Imaging")
    if any(marker in text for marker in PERFORMANCE_PATTERNS):
        modalities.append("Performance")
    if any(marker in text for marker in HYPERTROPHY_PATTERNS):
        modalities.append("Hypertrophy")
    if not modalities:
        modalities.append("Unspecified")
    return modalities


def estimate_participant_count(abstract: str) -> int | None:
    if not abstract:
        return None
    n_equals = N_EQUALS_PATTERN.findall(abstract)
    if n_equals:
        return int(n_equals[0])
    matches = PARTICIPANT_PATTERN.findall(abstract)
    if matches:
        return int(matches[0][0])
    return None


def relevance_score(text: str, keywords: list[str]) -> float:
    if not text or not keywords:
        return 0.0
    normalized = normalize_text(text)
    matched = 0
    for keyword in keywords:
        term = normalize_text(keyword)
        if term and term in normalized:
            matched += 1
    return matched / len(keywords)


def build_query(raw_query: str, from_year: int) -> str:
    return f"({raw_query}) AND ({from_year}:3000[pdat])"


def search_pmids(query: str, retmax: int, sleep_seconds: float) -> list[str]:
    return search_pmids_with_retries(
        query=query,
        retmax=retmax,
        sleep_seconds=sleep_seconds,
        max_retries=3,
    )


def search_pmids_with_retries(
    query: str,
    retmax: int,
    sleep_seconds: float,
    max_retries: int,
) -> list[str]:
    for attempt in range(1, max_retries + 1):
        try:
            handle = Entrez.esearch(db="pubmed", term=query, retmax=retmax, sort="relevance")
            response = Entrez.read(handle)
            handle.close()
            time.sleep(sleep_seconds)
            return list(response.get("IdList", []))
        except Exception as exc:  # pragma: no cover
            if attempt >= max_retries:
                raise RuntimeError(f"PubMed search failed after {max_retries} attempts: {exc}") from exc
            backoff = sleep_seconds * attempt
            print(f"[warn] search retry {attempt}/{max_retries} for query: {query[:80]}...", flush=True)
            time.sleep(backoff)
    return []


def fetch_medline_records(
    pmids: list[str],
    sleep_seconds: float,
    max_retries: int,
    batch_size: int = 150,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for start in range(0, len(pmids), batch_size):
        batch = pmids[start : start + batch_size]
        if not batch:
            continue
        parsed = []
        for attempt in range(1, max_retries + 1):
            try:
                handle = Entrez.efetch(
                    db="pubmed",
                    id=",".join(batch),
                    rettype="medline",
                    retmode="text",
                )
                parsed = list(Medline.parse(handle))
                handle.close()
                break
            except Exception as exc:  # pragma: no cover
                if attempt >= max_retries:
                    raise RuntimeError(
                        f"PubMed efetch failed after {max_retries} attempts at batch index {start}: {exc}"
                    ) from exc
                backoff = sleep_seconds * attempt
                print(
                    f"[warn] efetch retry {attempt}/{max_retries} for batch starting at {start}",
                    flush=True,
                )
                time.sleep(backoff)
        records.extend(parsed)
        print(
            f"[fetch] batch={(start // batch_size) + 1} records={len(parsed)} total={len(records)}",
            flush=True,
        )
        time.sleep(sleep_seconds)
    return records


def coerce_to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def extract_doi(aid_values: list[str]) -> str | None:
    for aid in aid_values:
        lower = aid.lower()
        if "[doi]" in lower:
            return aid.split(" ")[0].strip()
    return None


def main() -> None:
    args = parse_args()

    if Entrez is None or Medline is None:
        raise SystemExit(
            "Biopython is required for full PubMed scraping. Install with `python3 -m pip install -r requirements.txt`, "
            "or use `python3 scripts/fetch_pubmed_seed_records.py` to fetch vetted seed PMIDs."
        )

    email = args.email or os.environ.get("ENTREZ_EMAIL")
    if not email:
        raise SystemExit(
            "Missing Entrez email. Pass --email or set ENTREZ_EMAIL in your environment."
        )
    api_key = args.api_key or os.environ.get("NCBI_API_KEY")

    Entrez.email = email
    Entrez.tool = args.tool_name
    if api_key:
        Entrez.api_key = api_key
    socket.setdefaulttimeout(args.request_timeout_seconds)

    config = read_json(args.query_config)
    clusters: list[dict[str, Any]] = list(config.get("clusters", []))
    if not clusters:
        raise SystemExit(f"No clusters found in {args.query_config}")
    if args.extra_query_config:
        extra_clusters = read_json(args.extra_query_config).get("clusters", [])
        clusters.extend(extra_clusters)
        print(
            f"[config] merged {len(extra_clusters)} extra clusters from {args.extra_query_config}",
            flush=True,
        )
    retmax = args.retmax_per_query or int(config.get("default_retmax", 30))

    pmid_to_clusters: dict[str, set[str]] = defaultdict(set)
    pmid_to_queries: dict[str, set[str]] = defaultdict(set)
    cluster_keywords: dict[str, list[str]] = {}
    search_stats: list[dict[str, Any]] = []

    total_queries = sum(len(cluster.get("queries", [])) for cluster in clusters)
    query_counter = 0
    seeded_pmids = 0
    for cluster in clusters:
        cluster_id = cluster["id"]
        cluster_retmax = int(cluster.get("retmax", retmax))
        cluster_keywords[cluster_id] = cluster.get("keywords", [])
        cluster_seed_pmids = [
            str(pmid).strip()
            for pmid in cluster.get("seed_pmids", [])
            if str(pmid).strip()
        ]
        for pmid in cluster_seed_pmids:
            pmid_to_clusters[pmid].add(cluster_id)
            pmid_to_queries[pmid].add(f"seed PMID {pmid}")
        if cluster_seed_pmids:
            seeded_pmids += len(cluster_seed_pmids)
            search_stats.append(
                {
                    "cluster_id": cluster_id,
                    "query": "seed_pmids",
                    "retmax": len(cluster_seed_pmids),
                    "hit_count": len(cluster_seed_pmids),
                }
            )
        for raw_query in cluster.get("queries", []):
            query_counter += 1
            query = build_query(raw_query, args.from_year)
            pmids = search_pmids_with_retries(
                query=query,
                retmax=cluster_retmax,
                sleep_seconds=args.request_sleep_seconds,
                max_retries=args.max_retries,
            )
            for pmid in pmids:
                pmid_to_clusters[pmid].add(cluster_id)
                pmid_to_queries[pmid].add(raw_query)
            print(
                f"[search] {query_counter}/{total_queries} cluster={cluster_id} hits={len(pmids)}",
                flush=True,
            )
            search_stats.append(
                {
                    "cluster_id": cluster_id,
                    "query": raw_query,
                    "retmax": cluster_retmax,
                    "hit_count": len(pmids),
                }
            )

    unique_pmids = sorted(pmid_to_clusters.keys())
    medline_records = fetch_medline_records(
        unique_pmids,
        sleep_seconds=args.request_sleep_seconds,
        max_retries=args.max_retries,
    )

    current_year = datetime.utcnow().year
    docs: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    manual_review_queue: list[dict[str, Any]] = []
    excluded_count = 0
    skipped_no_pmid = 0

    for record in medline_records:
        pmid = str(record.get("PMID", "")).strip()
        if not pmid:
            skipped_no_pmid += 1
            continue
        title = str(record.get("TI", "")).strip()
        abstract = str(record.get("AB", "")).strip()
        year = parse_year(str(record.get("DP", "")).strip())
        if year is None or year < args.from_year:
            excluded_count += 1
            continue

        publication_types = coerce_to_list(record.get("PT"))
        authors = coerce_to_list(record.get("FAU"))
        aid_values = coerce_to_list(record.get("AID"))
        doi = extract_doi(aid_values)

        tier, tier_score = classify_evidence_tier(
            publication_types=publication_types,
            title=title,
            abstract=abstract,
        )
        topic_clusters = sorted(pmid_to_clusters.get(pmid, set()))
        matched_queries = sorted(pmid_to_queries.get(pmid, set()))
        relevance_values = [
            relevance_score(f"{title} {abstract}", cluster_keywords.get(cluster_id, []))
            for cluster_id in topic_clusters
        ]
        relevance = max(relevance_values) if relevance_values else 0.0
        recency_score = clamp(1.0 - ((current_year - year) / 10.0), 0.0, 1.0)
        retrieval_weight = (
            (tier_score * 0.55) + (recency_score * 0.25) + (relevance * 0.20)
        )

        manual_review_reasons: list[str] = []
        data_quality_notes: list[str] = []
        if not abstract:
            manual_review_reasons.append("missing_abstract")
        if tier in {"other", "narrative_review"} and retrieval_weight < args.lower_tier_review_max_weight:
            manual_review_reasons.append("lower_evidence_tier_low_weight")
        if (
            relevance < args.low_topic_relevance_threshold
            and retrieval_weight < args.low_topic_review_max_weight
        ):
            manual_review_reasons.append("low_topic_relevance_low_weight")

        modalities = infer_measurement_modalities(title=title, abstract=abstract)
        participant_count = estimate_participant_count(abstract)
        if participant_count is None and tier in {"rct", "controlled_trial"}:
            data_quality_notes.append("participant_count_not_found")

        doc_id = f"pmid-{pmid}"
        chunk_source = abstract or title
        chunk_texts = chunk_text(chunk_source, max_chars=args.chunk_size, min_chars=230)
        if not chunk_texts:
            chunk_texts = [title] if title else []
            manual_review_reasons.append("no_chunkable_text")

        doc_chunk_ids: list[str] = []
        topic_keywords = []
        for cluster_id in topic_clusters:
            topic_keywords.extend(cluster_keywords.get(cluster_id, []))

        for index, passage in enumerate(chunk_texts, start=1):
            chunk_id = f"{doc_id}-chunk-{index:03d}"
            doc_chunk_ids.append(chunk_id)
            chunk_relevance = relevance_score(passage, topic_keywords) if topic_keywords else relevance
            chunk_weight = clamp((retrieval_weight * 0.85) + (chunk_relevance * 0.15), 0.0, 1.0)
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "pmid": pmid,
                    "text": passage,
                    "topic_clusters": topic_clusters,
                    "publication_year": year,
                    "evidence_tier": tier,
                    "quality_score": round(tier_score, 4),
                    "retrieval_weight": round(chunk_weight, 4),
                    "manual_review_required": bool(manual_review_reasons),
                }
            )

        doc = {
            "doc_id": doc_id,
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "journal": str(record.get("JT", "") or record.get("TA", "")).strip(),
            "publication_year": year,
            "publication_types": publication_types,
            "authors": authors,
            "doi": doi,
            "topic_clusters": topic_clusters,
            "query_matches": matched_queries,
            "evidence_tier": tier,
            "measurement_modalities_detected": modalities,
            "participant_count_estimate": participant_count,
            "quality_score": round(tier_score, 4),
            "recency_score": round(recency_score, 4),
            "relevance_score": round(relevance, 4),
            "retrieval_weight": round(clamp(retrieval_weight, 0.0, 1.0), 4),
            "manual_review_required": bool(manual_review_reasons),
            "manual_review_reasons": sorted(set(manual_review_reasons)),
            "data_quality_notes": sorted(set(data_quality_notes)),
            "chunk_ids": doc_chunk_ids,
            "source": {
                "provider": "PubMed",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            },
        }
        docs.append(doc)

        if doc["manual_review_required"]:
            manual_review_queue.append(
                {
                    "doc_id": doc_id,
                    "pmid": pmid,
                    "title": title,
                    "publication_year": year,
                    "evidence_tier": tier,
                    "retrieval_weight": doc["retrieval_weight"],
                    "manual_review_reasons": doc["manual_review_reasons"],
                    "data_quality_notes": doc["data_quality_notes"],
                    "url": doc["source"]["url"],
                }
            )

    docs.sort(
        key=lambda item: (
            item["retrieval_weight"],
            item["quality_score"],
            item["publication_year"],
        ),
        reverse=True,
    )
    if args.max_documents > 0:
        allowed_doc_ids = {doc["doc_id"] for doc in docs[: args.max_documents]}
        docs = docs[: args.max_documents]
        chunks = [chunk for chunk in chunks if chunk["doc_id"] in allowed_doc_ids]
        manual_review_queue = [
            item for item in manual_review_queue if item["doc_id"] in allowed_doc_ids
        ]

    chunks.sort(key=lambda item: item["retrieval_weight"], reverse=True)

    pmid_to_doc_id = {doc["pmid"]: doc["doc_id"] for doc in docs}
    summary = {
        "generated_at_utc": now_utc_iso(),
        "query_config_path": str(Path(args.query_config).resolve()),
        "manual_review_policy": {
            "version": "2026-02-25-v2",
            "low_topic_relevance_threshold": args.low_topic_relevance_threshold,
            "low_topic_review_max_weight": args.low_topic_review_max_weight,
            "lower_tier_review_max_weight": args.lower_tier_review_max_weight,
            "participant_count_note_is_non_blocking": True,
        },
        "from_year": args.from_year,
        "retmax_per_query": retmax,
        "total_queries": len(search_stats),
        "seeded_pmids": seeded_pmids,
        "requested_unique_pmids": len(unique_pmids),
        "fetched_records": len(medline_records),
        "included_documents": len(docs),
        "included_chunks": len(chunks),
        "manual_review_documents": len(manual_review_queue),
        "documents_with_data_quality_notes": sum(1 for doc in docs if doc["data_quality_notes"]),
        "excluded_for_year_filter": excluded_count,
        "skipped_without_pmid": skipped_no_pmid,
        "avg_doc_retrieval_weight": round(mean(doc["retrieval_weight"] for doc in docs), 4),
    }

    corpus_payload = {
        "metadata": summary,
        "search_stats": search_stats,
        "documents": docs,
        "chunks": chunks,
        "pmid_to_doc_id": pmid_to_doc_id,
    }
    write_json(args.output, corpus_payload)

    manual_review_payload = {
        "metadata": {
            "generated_at_utc": now_utc_iso(),
            "document_count": len(manual_review_queue),
            "source_corpus_path": str(Path(args.output).resolve()),
        },
        "documents": manual_review_queue,
    }
    write_json(args.manual_review_output, manual_review_payload)

    print(
        (
            f"Corpus written: {args.output} | documents={len(docs)} chunks={len(chunks)} "
            f"manual_review={len(manual_review_queue)}"
        )
    )


if __name__ == "__main__":
    main()
