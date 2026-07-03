"""
build_vector_store.py

Embeds the science corpus chunks into a local ChromaDB vector store.

Each chunk is stored with its pre-computed metadata (evidence_tier,
quality_score, retrieval_weight, etc.) so that retrieval can filter
or rerank based on evidence quality without touching a separate database.

Run:
    python scripts/build_vector_store.py
"""

import json
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# Resolve all paths through settings so this writes to the location the engine
# actually reads (packages/data/processed), regardless of CWD. The previous
# hardcoded "../data/processed" was a stale leftover from the old scripts/ layout
# and pointed at services/engine/data/processed, which the engine never loads.
try:
    from . import settings
except ImportError:  # pragma: no cover
    import settings

CORPUS_PATH = str(settings.SCIENCE_PATH)
VECTOR_STORE_PATH = str(settings.VECTOR_STORE_PATH)
COLLECTION_NAME = settings.VECTOR_COLLECTION_NAME
EMBEDDING_MODEL = settings.EMBEDDING_MODEL


def load_chunks(corpus_path: str) -> list[dict]:
    with open(corpus_path) as f:
        data = json.load(f)
    return data["chunks"]


def build_vector_store(chunks: list[dict]) -> None:
    embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

    client = chromadb.PersistentClient(path=VECTOR_STORE_PATH)

    # Delete existing collection if rebuilding from scratch
    existing = [c.name for c in client.list_collections()]
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing collection '{COLLECTION_NAME}'")

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        ids.append(chunk["chunk_id"])
        documents.append(chunk["text"])
        metadatas.append({
            "doc_id": chunk["doc_id"],
            "pmid": chunk["pmid"],
            "evidence_tier": chunk["evidence_tier"],
            "quality_score": chunk["quality_score"],
            "retrieval_weight": chunk["retrieval_weight"],
            "publication_year": chunk["publication_year"],
            "manual_review_required": chunk["manual_review_required"],
            # ChromaDB metadata values must be scalar; join list to string
            "topic_clusters": ",".join(chunk.get("topic_clusters", [])),
        })

    # Add in batches to avoid memory spikes on larger corpora
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        collection.add(
            ids=ids[i:i + batch_size],
            documents=documents[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size],
        )
        print(f"  Embedded chunks {i + 1}–{min(i + batch_size, len(ids))} / {len(ids)}")

    print(f"\nVector store built: {collection.count()} chunks in '{COLLECTION_NAME}'")
    print(f"Persisted to: {VECTOR_STORE_PATH}")


def smoke_test(query: str = "training volume for muscle hypertrophy") -> None:
    """Quick sanity check: run one query and print the top 3 results."""
    embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=VECTOR_STORE_PATH)
    collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)

    results = collection.query(
        query_texts=[query],
        n_results=3,
        include=["documents", "metadatas", "distances"],
    )

    print(f"\nSmoke test — query: '{query}'\n")
    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        print(f"Result {i + 1}")
        print(f"  PMID:           {meta['pmid']}")
        print(f"  Evidence tier:  {meta['evidence_tier']}")
        print(f"  Quality score:  {meta['quality_score']}")
        print(f"  Cosine dist:    {dist:.4f}")
        print(f"  Text snippet:   {doc[:200]}...")
        print()


if __name__ == "__main__":
    print("Loading science corpus...")
    chunks = load_chunks(CORPUS_PATH)
    print(f"Loaded {len(chunks)} chunks\n")

    print("Building vector store...")
    build_vector_store(chunks)

    smoke_test()
