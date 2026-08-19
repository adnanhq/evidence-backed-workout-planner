# Abstract & proposal text

**Title:** Retrieval Is Not Grounding: Stage-Wise Evaluation of an Evidence-Backed
Exercise Recommender

---

## Paper abstract (~200 words)

Systems that cite scientific literature are conventionally evaluated at the retriever, on
the assumption that better retrieval yields better-grounded output. We test that assumption
on a deployed exercise-recommendation system that attaches a PubMed citation to every
exercise it recommends, and find it does not hold: the retriever is not where grounding
fails. We introduce a stage-wise audit of the chain from bibliographic record to on-screen
citation, and show that three of its four stages can be evaluated at zero annotation cost
using ground truth these pipelines already produce — the bibliographic index supplies
study-design labels, and the boolean queries that assembled the corpus supply relevance
labels. Across 502 studies and 1,324 exercises the audit finds a study-design grader that
inflates evidence tiers in one direction only (80.1% agreement, κ=0.719; 19.9% graded
stronger, 0.0% weaker); a query template costing six times more retrieval quality than the
choice of embedding model, where domain-specific pretraining did not help; a distance
threshold valid for one embedding space; and name-matching attribution that leaves 74% of
the catalog uncited while the corpus holds the missing evidence. Acting on the largest
finding raises held-out retrieval quality by 137% (p = 0.0088) across every model tested,
without retrieving less.

---

## CSE498R — Project Summary (~195 words)

This project evaluates how trustworthy the evidence links are in an existing
retrieval-augmented exercise-recommendation system, the team's prior capstone. The system
builds a corpus of peer-reviewed PubMed studies, embeds it in a vector store, grades each
study by design and recency, and presents citations alongside 1,324 catalogued exercises.
Rather than assume retrieval determines citation quality, we decompose the pipeline into the
four stages a citation must pass through — study-design grading, semantic retrieval,
attribution of a study to a specific exercise, and presentation — and measure each
separately. The central methodological contribution is that three of those stages need no
manual annotation, because the pipeline already stores its own ground truth: MEDLINE
publication types independently label study design, and the boolean query that fetched each
study serves as a relevance label produced by a different retrieval paradigm than the one
under test. We complement this with a small human-annotated sample validating an automated
adjudicator, and with controlled ablations over embedding models, query formulation and the
distance threshold. Where a finding admits a minimal, verifiable change we apply it and
re-measure on held-out queries, so the strongest recommendations are validated rather than
inferred. The result characterises where grounding breaks, why retriever-only evaluation
misses it, and what closing the largest gap is worth.

---

## CSE498R — Project Outcomes (~195 words)

Qualitative outcomes: (1) a reusable, zero-annotation-cost evaluation protocol for
literature-grounded recommenders, with an open harness that runs against committed data and
reproduces byte-identically; (2) a stage-wise failure characterisation showing that the
retrieval stage is not the binding constraint, and that three architectural mechanisms —
keyword-cascade study grading, a fixed distance threshold tied to one embedding space, and
string-match attribution — account for the observed grounding failures; (3) a failure
taxonomy for citation attribution, including cases where an exercise name collides with the
name of a clinical assessment test; (4) a conformance audit of the system against its own
published methodology, together with the remediation it prompted and a regression check
that keeps it honest; (5) a written research paper suitable for an undergraduate venue.
Quantitative outcomes: agreement and Cohen's kappa between the automated study-design grader
and MEDLINE indexing over 502 studies, with the propagated effect on user-visible confidence
scores; standard retrieval metrics (precision@k, R-precision, nDCG@10, MRR, recall@50) with
bootstrap intervals and paired significance tests across five embedding models and five
query formulations; a reproducible distance-threshold calibration per embedding space;
attribution coverage and citation fan-out across 1,915 study–exercise links;
citation-support rates at three levels of claim specificity with human–model agreement; and
a held-out validation of the highest-value change the audit identified.
