# Stage-wise grounding audit

Evaluation harness for the CSE498R paper *Retrieval Is Not Grounding*. It measures the
capstone's evidence pipeline stage by stage, against ground truth the pipeline already
produces.

**This directory is additive.** Nothing outside `research/` is read-write; the engine's own
functions are imported and audited in place, so the harness measures the real system rather
than a reimplementation. `git status` shows no modification to `packages/`, `services/` or
`apps/` after a full run.

## Start here

- `TALK-BRIEF.md` — the 10-minute version: a primer on the concepts, a spoken spine, and
  the questions to expect. Start here if you are presenting.
- `BRIEFING.md` — the long reference: every number with its provenance, and a fuller Q&A
- `paper/pitch.md` — one-page pitch
- `paper/abstract.md` — paper abstract + CSE498R summary and outcomes
- `paper/draft.md` — full draft

## Modules

| Module | Stage | Needs |
|---|---|---|
| `s1_tier_audit.py` | study-design grading vs MEDLINE publication types | nothing |
| `s2_retrieval_eval.py` | retrieval quality × 5 embedding models × 4 query formulations | models (cached) |
| `s2b_threshold_roc.py` | distance-ceiling calibration per embedding space | models (cached) |
| `s2c_query_repair.py` | candidate query rewrites, chosen on a held-out split | models (cached) |
| `s3_attribution_audit.py` | coverage, alias mechanism, request-time funnel | nothing |
| `s3b_build_semantic_pairs.py` | builds the semantic-attachment comparison arm | models (cached) |
| `s3c_judge.py` | citation support at three specificity levels | Gemini API quota |
| `s3d_build_annotation.py` | generates the 40-item human annotation task | nothing |
| `s3e_agreement.py` | human vs model agreement (Cohen's κ) | completed annotations |
| `s4_conformance.py` | published claims vs code and data | nothing |
| `make_figures.py` | all six figures | results |

## Run

```bash
./.venv/bin/python -m research.s1_tier_audit
./.venv/bin/python -m research.s3_attribution_audit
./.venv/bin/python -m research.s4_conformance
./.venv/bin/python -m research.s2_retrieval_eval
./.venv/bin/python -m research.s2b_threshold_roc
./.venv/bin/python -m research.s2c_query_repair
./.venv/bin/python -m research.s3b_build_semantic_pairs
./.venv/bin/python -m research.s3c_judge
./.venv/bin/python -m research.s3d_build_annotation && open research/annotate/index.html
./.venv/bin/python -m research.s3e_agreement
./.venv/bin/python -m research.make_figures
```

`pip install -r research/requirements.txt` first (matplotlib is the only addition; the rest
ships with the engine). The embedding models download once, about 1.1 GB, into the
HuggingFace cache.

## Design notes

- **Exact search, not the production index.** Brute-force cosine over 1,264 chunks removes
  approximate-search error as a confound, is bit-reproducible, and avoids opening the
  committed Chroma store, which mutates on read.
- **Provenance labels are incomplete by construction**, so reported precision is a lower
  bound and recall is defined against the boolean-query result set. Conclusions rest on
  relative comparisons, where the shared label bias cancels.
- **The S2 baseline is owned by the harness**, not imported from the engine: a baseline
  that tracked the live function would move whenever the engine moved, collapsing the
  `production_template` and `production_template_fixed` conditions into each other.
- **`s4_conformance.py` parses published figures from their source files**, so it reports
  current state and works as a regression check rather than asserting against a snapshot.
- **Determinism.** S1, S3 and S4 are byte-identical across runs; S2 is identical given the
  same models and seed. Every result file records its package versions and the sampling seed.
- **`s3c_judge.py` caches every verdict**, so an interrupted or quota-limited run resumes.
  `JUDGE_CACHED_ONLY=1` regenerates the summary with no network access.
