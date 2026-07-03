from __future__ import annotations

import argparse
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from .build_science_corpus import (
        EVIDENCE_TIER_SCORES,
        classify_evidence_tier,
        estimate_participant_count,
        infer_measurement_modalities,
        relevance_score,
    )
    from .pipeline_common import clamp, chunk_text, mean, now_utc_iso, parse_year, read_json, write_json
except ImportError:  # pragma: no cover
    from build_science_corpus import (
        EVIDENCE_TIER_SCORES,
        classify_evidence_tier,
        estimate_participant_count,
        infer_measurement_modalities,
        relevance_score,
    )
    from pipeline_common import clamp, chunk_text, mean, now_utc_iso, parse_year, read_json, write_json


EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch vetted PubMed seed PMIDs into the existing science corpus."
    )
    parser.add_argument(
        "--query-config",
        default="config/pubmed_queries.json",
        help="Query config containing cluster seed_pmids.",
    )
    parser.add_argument(
        "--science-corpus",
        default="data/processed/science_corpus.json",
        help="Existing science corpus to update.",
    )
    parser.add_argument(
        "--manual-review-output",
        default="data/processed/science_manual_review_queue.json",
        help="Manual review queue to regenerate from the updated corpus.",
    )
    parser.add_argument(
        "--from-year",
        type=int,
        default=2018,
        help="Minimum publication year to keep.",
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
        help="Delay between PubMed requests.",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Optional contact email included in NCBI E-utilities requests.",
    )
    return parser.parse_args()


def collect_seed_maps(config: dict[str, Any]) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, list[str]]]:
    pmid_to_clusters: dict[str, set[str]] = defaultdict(set)
    pmid_to_queries: dict[str, set[str]] = defaultdict(set)
    cluster_keywords: dict[str, list[str]] = {}

    for cluster in config.get("clusters", []):
        cluster_id = cluster["id"]
        cluster_keywords[cluster_id] = cluster.get("keywords", [])
        for pmid in cluster.get("seed_pmids", []):
            normalized_pmid = str(pmid).strip()
            if not normalized_pmid:
                continue
            pmid_to_clusters[normalized_pmid].add(cluster_id)
            pmid_to_queries[normalized_pmid].add(f"seed PMID {normalized_pmid}")

    return pmid_to_clusters, pmid_to_queries, cluster_keywords


def node_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def article_year(article: ET.Element) -> int | None:
    year = article.findtext(".//PubDate/Year")
    if year:
        return parse_year(year)
    medline_date = article.findtext(".//PubDate/MedlineDate")
    return parse_year(medline_date)


def article_doi(article: ET.Element) -> str | None:
    for article_id in article.findall(".//ArticleId"):
        if article_id.attrib.get("IdType") == "doi" and article_id.text:
            return article_id.text.strip()
    return None


def parse_pubmed_xml(raw_xml: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(raw_xml)
    records = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID")
        if not pmid:
            continue
        abstract_parts = [
            node_text(abstract_node)
            for abstract_node in article.findall(".//Abstract/AbstractText")
        ]
        records.append(
            {
                "pmid": pmid.strip(),
                "title": node_text(article.find(".//ArticleTitle")),
                "abstract": " ".join(part for part in abstract_parts if part),
                "journal": node_text(article.find(".//Journal/Title")),
                "publication_year": article_year(article),
                "publication_types": [
                    node_text(publication_type)
                    for publication_type in article.findall(".//PublicationType")
                    if node_text(publication_type)
                ],
                "authors": [
                    node_text(author)
                    for author in article.findall(".//AuthorList/Author")
                    if node_text(author)
                ],
                "doi": article_doi(article),
            }
        )
    return records


def fetch_records(pmids: list[str], email: str | None, sleep_seconds: float) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for start in range(0, len(pmids), 50):
        batch = pmids[start : start + 50]
        params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "retmode": "xml",
            "tool": "cse499-seed-fetch",
        }
        if email:
            params["email"] = email
        url = f"{EUTILS_BASE}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=60) as response:
            records.extend(parse_pubmed_xml(response.read()))
        time.sleep(sleep_seconds)
    return records


def build_document(
    record: dict[str, Any],
    pmid_to_clusters: dict[str, set[str]],
    pmid_to_queries: dict[str, set[str]],
    cluster_keywords: dict[str, list[str]],
    from_year: int,
    chunk_size: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any] | None] | None:
    pmid = str(record.get("pmid", "")).strip()
    year = record.get("publication_year")
    if not pmid or year is None or int(year) < from_year:
        return None

    title = record.get("title", "")
    abstract = record.get("abstract", "")
    tier, tier_score = classify_evidence_tier(
        publication_types=record.get("publication_types", []),
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
    current_year = datetime.utcnow().year
    recency_score = clamp(1.0 - ((current_year - int(year)) / 10.0), 0.0, 1.0)
    retrieval_weight = (tier_score * 0.55) + (recency_score * 0.25) + (relevance * 0.20)

    manual_review_reasons: list[str] = []
    data_quality_notes: list[str] = []
    if not abstract:
        manual_review_reasons.append("missing_abstract")
    if tier in {"other", "narrative_review"} and retrieval_weight < 0.55:
        manual_review_reasons.append("lower_evidence_tier_low_weight")
    if relevance < 0.12 and retrieval_weight < 0.65:
        manual_review_reasons.append("low_topic_relevance_low_weight")

    modalities = infer_measurement_modalities(title=title, abstract=abstract)
    participant_count = estimate_participant_count(abstract)
    if participant_count is None and tier in {"rct", "controlled_trial"}:
        data_quality_notes.append("participant_count_not_found")

    doc_id = f"pmid-{pmid}"
    chunk_source = abstract or title
    passages = chunk_text(chunk_source, max_chars=chunk_size, min_chars=230)
    if not passages:
        passages = [title] if title else []
        manual_review_reasons.append("no_chunkable_text")

    topic_keywords = []
    for cluster_id in topic_clusters:
        topic_keywords.extend(cluster_keywords.get(cluster_id, []))

    chunks = []
    chunk_ids = []
    for index, passage in enumerate(passages, start=1):
        chunk_id = f"{doc_id}-chunk-{index:03d}"
        chunk_ids.append(chunk_id)
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

    document = {
        "doc_id": doc_id,
        "pmid": pmid,
        "title": title,
        "abstract": abstract,
        "journal": record.get("journal", ""),
        "publication_year": year,
        "publication_types": record.get("publication_types", []),
        "authors": record.get("authors", []),
        "doi": record.get("doi"),
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
        "chunk_ids": chunk_ids,
        "source": {
            "provider": "PubMed",
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        },
    }

    review_item = None
    if document["manual_review_required"]:
        review_item = {
            "doc_id": doc_id,
            "pmid": pmid,
            "title": title,
            "publication_year": year,
            "evidence_tier": tier,
            "retrieval_weight": document["retrieval_weight"],
            "manual_review_reasons": document["manual_review_reasons"],
            "data_quality_notes": document["data_quality_notes"],
            "url": document["source"]["url"],
        }

    return document, chunks, review_item


def main() -> None:
    args = parse_args()
    config = read_json(args.query_config)
    corpus = read_json(args.science_corpus)

    pmid_to_clusters, pmid_to_queries, cluster_keywords = collect_seed_maps(config)
    seed_pmids = sorted(pmid_to_clusters)
    if not seed_pmids:
        raise SystemExit("No seed_pmids found in query config.")

    records = fetch_records(seed_pmids, email=args.email, sleep_seconds=args.request_sleep_seconds)
    parsed_pmids = {record["pmid"] for record in records}
    missing_pmids = [pmid for pmid in seed_pmids if pmid not in parsed_pmids]
    if missing_pmids:
        print(f"[warn] PubMed did not return seed PMIDs: {', '.join(missing_pmids)}")

    seed_doc_ids = {f"pmid-{pmid}" for pmid in seed_pmids}
    documents = [
        doc for doc in corpus.get("documents", []) if doc.get("doc_id") not in seed_doc_ids
    ]
    chunks = [
        chunk for chunk in corpus.get("chunks", []) if chunk.get("doc_id") not in seed_doc_ids
    ]

    added_documents = []
    added_review_items = []
    for record in records:
        built = build_document(
            record=record,
            pmid_to_clusters=pmid_to_clusters,
            pmid_to_queries=pmid_to_queries,
            cluster_keywords=cluster_keywords,
            from_year=args.from_year,
            chunk_size=args.chunk_size,
        )
        if built is None:
            continue
        document, doc_chunks, review_item = built
        documents.append(document)
        chunks.extend(doc_chunks)
        added_documents.append(document)
        if review_item:
            added_review_items.append(review_item)

    documents.sort(
        key=lambda item: (
            item["retrieval_weight"],
            item["quality_score"],
            item["publication_year"],
        ),
        reverse=True,
    )
    chunks.sort(key=lambda item: item["retrieval_weight"], reverse=True)

    corpus["documents"] = documents
    corpus["chunks"] = chunks
    corpus["pmid_to_doc_id"] = {doc["pmid"]: doc["doc_id"] for doc in documents}
    corpus.setdefault("metadata", {})
    corpus["metadata"].update(
        {
            "generated_at_utc": now_utc_iso(),
            "included_documents": len(documents),
            "included_chunks": len(chunks),
            "manual_review_documents": sum(1 for doc in documents if doc["manual_review_required"]),
            "documents_with_data_quality_notes": sum(1 for doc in documents if doc["data_quality_notes"]),
            "avg_doc_retrieval_weight": round(mean(doc["retrieval_weight"] for doc in documents), 4),
            "seeded_pmids": len(seed_pmids),
            "seed_fetch_added_or_refreshed": len(added_documents),
        }
    )

    write_json(args.science_corpus, corpus)

    manual_review_items = [
        {
            "doc_id": doc["doc_id"],
            "pmid": doc["pmid"],
            "title": doc["title"],
            "publication_year": doc["publication_year"],
            "evidence_tier": doc["evidence_tier"],
            "retrieval_weight": doc["retrieval_weight"],
            "manual_review_reasons": doc["manual_review_reasons"],
            "data_quality_notes": doc["data_quality_notes"],
            "url": doc["source"]["url"],
        }
        for doc in documents
        if doc["manual_review_required"]
    ]
    write_json(
        args.manual_review_output,
        {
            "metadata": {
                "generated_at_utc": now_utc_iso(),
                "document_count": len(manual_review_items),
                "source_corpus_path": str(Path(args.science_corpus).resolve()),
            },
            "documents": manual_review_items,
        },
    )

    print(
        "Seed fetch complete: "
        f"seed_pmids={len(seed_pmids)} added_or_refreshed={len(added_documents)} "
        f"documents={len(documents)} chunks={len(chunks)} manual_review={len(manual_review_items)}"
    )


if __name__ == "__main__":
    main()
