# Retrieval Is Not Grounding
### Stage-Wise Evaluation of an Evidence-Backed Exercise Recommender
*CSE498R research proposal — with preliminary results already in hand*

---

## The one-sentence version

Our capstone app puts a PubMed citation beside every exercise it recommends. I traced
what has to be true for that citation to be trustworthy, found four places it can break,
and measured each one — three of them against ground truth that was already sitting in
our own data, at zero annotation cost.

## Why this is worth a paper

Retrieval-augmented systems over scientific literature are normally evaluated **at the
retriever**: precision, recall, nDCG on the search step. The implicit assumption is that a
better retriever yields better-grounded output.

We tested that assumption on a real deployed system and it does not hold. The retriever is
not where grounding fails. Every failure we found lives in the cheap glue code around it —
the study-type grader, the query template, the distance threshold, and the string matcher
that attaches papers to recommendations. A retriever-only evaluation would have reported
that the system was fine.

**The contribution is two-fold:**

1. **A reusable evaluation protocol.** Three of the four stages can be evaluated with no
   manual labelling at all, because literature-RAG pipelines already produce their own
   ground truth: the bibliographic index supplies study-design labels, and the boolean
   queries used to assemble the corpus supply relevance labels. Any team building a
   PubMed-backed system can run this in an afternoon.
2. **Findings that generalise.** The failure mechanisms are architectural, not specific to
   this app: keyword-cascade study grading, string-match attribution, a fixed distance
   threshold tied to one embedding model, and a confidence score that blends heuristics
   with evidence. Any system with those parts has these problems.

## The four stages, and where the ground truth comes from

| Stage | Mechanism | Ground truth | Labelling cost |
|---|---|---|---|
| **S1** Study grading | keyword cascade over title + abstract | MEDLINE publication types, already stored | **none** |
| **S2** Retrieval | dense vector search + distance ceiling | which boolean PubMed query fetched each study | **none** |
| **S3** Attribution | exercise names matched against study text | human + model adjudication of sampled pairs | 25 items |
| **S4** Presentation | confidence score, citations, appendix | the app's own published methodology page | **none** |

## Results already measured

**S1 — the study-design grader inflates, and can only inflate.**
It agrees with MEDLINE on 80.1% of 502 studies (κ = 0.719). Every one of the 100
disagreements grades the study *stronger* — 19.9% up, 0.0% down. This is structural, not
incidental: the grader is a first-match cascade searching publication types **or** the
abstract text, so widening the text it reads can only promote a tier, never demote one. It
labels 60 studies "meta-analysis"; MEDLINE supports 37. Restricting it to the title alone
removes more than half the inflation — a one-line change. The error propagates: 117 of 346
evidenced exercises shift confidence, 19 change confidence *level*, 38 display a different
top study.

**S2 — how the query is written matters ~6× more than which embedding model is used.**
Across five embedding models (with a size-matched control isolating "biomedical" from
"just bigger"), no model differs significantly from the shipped one (Wilcoxon p ≥ 0.06).
Query formulation spans 0.400 nDCG against 0.064 for model choice. The shipped model loses
**81% of its nDCG** between the raw query and the production query template. Notably,
domain-specific pretraining *hurt*: PubMedBERT scored worst; the biomedical model that
recovered was the one additionally trained for retrieval. **The discriminating factor is
retrieval training, not biomedical domain.**

**S2c — we acted on that finding and re-measured.**
Since formulation is the dominant lever, we treated it as an intervention. Five candidate
rewrites were tested; to avoid selecting a winner on the queries used to report its gain,
the 49 clusters were split and the winner chosen on one half, its effect read off the other.
Scoping the query to the target muscles, the goal, and the user's own notes scores
**0.215 against 0.091 on held-out queries — a 137% gain, p = 0.0088**, better on 12 of the
13 queries that moved. It improves *every* embedding model tested (+94% to +262%), and it
is not bought by retrieving less: the share of requests yielding any citation is unchanged
at 86%. Equipment tokens are neutral; candidate exercise names are actively harmful.

**S2b — the one hard filter on semantic retrieval is calibrated to a single model.**
The shipped 0.50 cosine ceiling admits 4.3% of the corpus under MiniLM. Under three of the
four other models it admits 95–100% and rejects *none* of our off-topic probes; under the
fourth it admits 1.5%. The best ceiling ranges from 0.20 to 0.53 across spaces. The code
documents a calibration that the repository cannot reproduce; we supply one that it can.

**S3 — the corpus holds the science; the name-matching step loses it.**
Only 346 of 1,324 exercises (26.1%) carry any citation, and only 145 of 502 studies (28.9%)
ever attach to one. Coverage ranges from 0% to 64% by muscle and does not follow supply:
the pipeline ran dedicated queries to fill the forearm gap, fetched 20 studies, and **not
one of the 37 forearm exercises cites any of them**. The mechanism explains it — only 57
of 1,970 catalog aliases ever match a study, and 49 of those 57 are exactly two words long.
Consequences: one study is cited for up to 47 exercises, and 36 exercises share a
byte-identical citation list.

**S3 — support collapses as the claim gets more specific.** *(pilot, n = 22)*
Of alias-matched citations, 59% involve the movement, 32% report a relevant outcome, and
14% used the actual variant. One failure category is a term that is a **clinical assessment
test, not an exercise** — "leg raise" matched an RCT on massage therapy for hamstring
flexibility.

**S4 — the published guardrail holds; the label around it does the heavy lifting.**
Of eleven published claims audited, six conformed, four diverged, one was qualified. All
four divergences have since been remediated and the conformance module now derives each
published figure from its source file, so it doubles as a regression check. The stated
guardrail is real: no zero-evidence exercise is ever labelled "high". But "moderate" is
applied to 1,006 exercises of which only **5.9%** have any linked study. And every set/rep
prescription a user reads is a constant or the planner model's own knowledge — the citation
beside it supports the exercise choice, never the dose.

## What we changed, and what we left alone

Four findings were acted on — all minimal, all covered by the existing test suite, all 73
engine tests passing unchanged: the query builder was scoped, the dormant
citation-containment check was wired into every generation, the API's evidence appendix was
aligned with the Markdown export, and two stale published counts were corrected.

One was deliberately left alone. Restricting the study-design grader to publication types
and titles would remove more than half the tier inflation, and S1 already measures that
counterfactual — but making it take effect requires regrading the corpus and rebuilding
both the catalog and the vector store, which would shift rankings the existing quality
tests assert on. We report the recommendation and its measured effect instead. Knowing
which findings are worth acting on and which are not is part of the result.

## What remains

Complete the adjudicated sample (the harness is built, cached and resumable; the free API
tier capped today's run at 22 of 169), collect the 40 human annotations already prepared as
a local task, report inter-rater agreement, and write up.

## Honest framing

This is not a list of bugs. Every mechanism measured is a documented design decision — the
movement-level attribution is stated in the project's own README as intentional. The paper
measures what those decisions cost. The system also does several things right, and we
report those: the ranking surfaces evidenced exercises 2.8× more often than chance, the
retriever returns an honestly empty result rather than padding with weak matches, and the
confidence cap does prevent unevidenced exercises from ever looking highly evidenced.
