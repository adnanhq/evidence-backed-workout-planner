# CSE498R proposal form

## PROJECT TITLE

Retrieval Is Not Grounding: Stage-Wise Evaluation of an Evidence-Backed Exercise Recommender

## PROJECT SUMMARY

Systems citing scientific literature are usually evaluated only at retrieval, assuming
better retrieval yields better grounding. We test that on our prior capstone, which
attaches a PubMed citation to every exercise it recommends. We decompose the pipeline into
the four stages a citation passes through, study-design grading, semantic retrieval,
attribution to a specific exercise, and presentation, measuring each separately. Three need
no manual labelling, because the pipeline stores its own ground truth: the bibliographic
index labels study design, and the query that fetched each study is a relevance label.
Minimal fixes are then applied and re-measured on held-out queries.

## PROJECT OUTCOMES

Qualitative: a reusable, zero-annotation-cost protocol for auditing literature-grounded
recommenders; a stage-wise characterisation showing retrieval is not the binding
constraint; a taxonomy of attribution failures, including exercise names colliding with
clinical tests; a conformance audit against the system's published methodology; and a
paper. Quantitative: agreement and Cohen's kappa between the study grader and the
bibliographic index across 502 studies, with propagated effects on shown confidence;
retrieval metrics with confidence intervals and significance tests across five embedding
models and five query formulations; attribution coverage across 1,915 study-exercise links;
citation-support rates at three specificity levels; and a held-out validation of the
largest fix.
