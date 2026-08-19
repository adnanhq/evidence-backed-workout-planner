"""Warm the HuggingFace cache for the S2 embedding arms. Safe to re-run."""
from __future__ import annotations

import time

MODELS = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "BAAI/bge-small-en-v1.5",
    "BAAI/bge-base-en-v1.5",
    "NeuML/pubmedbert-base-embeddings",
    "pritamdeka/S-PubMedBert-MS-MARCO",
]

if __name__ == "__main__":
    from sentence_transformers import SentenceTransformer

    for name in MODELS:
        start = time.time()
        try:
            model = SentenceTransformer(name)
            dim = model.get_sentence_embedding_dimension()
            params = sum(p.numel() for p in model.parameters())
            print("OK   %-45s dim=%-4d params=%.1fM  %.1fs"
                  % (name, dim, params / 1e6, time.time() - start), flush=True)
            del model
        except Exception as error:  # noqa: BLE001 - report and continue to the next arm
            print("FAIL %-45s %s" % (name, error), flush=True)
