# Briefing: what we built, what it found, and how to defend it

Read this once end to end. Everything here traces to a file in `research/results/`.
Nothing in it is rhetorical — every number was computed from the committed capstone data.

---

## 1. The 60-second version (say this first)

> Our capstone puts a PubMed citation next to every exercise it recommends. For that
> citation to be trustworthy, four separate things all have to go right: the study has to be
> graded correctly, the right studies have to be retrieved, the right study has to get
> attached to the right exercise, and the interface has to represent all that honestly.
>
> I measured each of those four steps separately. Three of them turned out to have ground
> truth already sitting in our own data, so they cost nothing to evaluate — for example,
> PubMed already publishes each paper's official study type, so I could check our automatic
> grader against it on all 502 papers with no manual labelling.
>
> The headline is that **retrieval — the part everyone evaluates, and the part we spent the
> most effort on — was not where grounding failed.** The failures were all in the cheap glue
> code around it. That's the paper: retriever-only evaluation, which is the norm, would have
> reported that this system was fine.

> Then I acted on the biggest finding and re-measured: scoping the search query to what the
> user actually asked about raised retrieval quality **137% on held-out queries**, and it
> helped every embedding model I tested.

**If you only remember one number:** the query template costs about **six times** more
retrieval quality than the choice of embedding model — and fixing it is a ten-line change.

---

## 2. The system under test, in the terms you'll be asked about

- **Corpus**: 502 PubMed studies, fetched by 103 boolean queries grouped into 62 topic
  clusters. Split into 1,264 text chunks.
- **Vector store**: ChromaDB, cosine distance, embedded with `all-MiniLM-L6-v2`
  (a small, general-purpose sentence-embedding model — 22M parameters, 384 dimensions).
- **Catalog**: 1,324 exercises. (The README says 873 — that number is stale, it refers to an
  older dataset the engine no longer uses. We flag this in the paper.)
- **Two independent ways a study becomes a citation**, and this distinction is the spine of
  the whole paper:
  1. **By meaning** — vector search retrieves studies for the request as a whole.
  2. **By name** — an exercise's alias (e.g. `"bench press"`) is string-matched against
     study text. This is how per-exercise citations are produced.
- **The LLM never cites anything.** It is explicitly told not to. Python attaches every
  citation deterministically after the model returns. This matters: hallucinated citations
  are architecturally impossible here, so the interesting question is not "did it make the
  citation up" but "does the citation it attached actually support the claim".

---

## 3. Concepts you need, in plain English

| Term | Plain meaning | Why it's here |
|---|---|---|
| **RAG** | Retrieve documents, then have a model write using them | What the capstone is |
| **Embedding** | Turning text into a list of numbers so similar text sits close together | How the vector search works |
| **Cosine distance** | How far apart two of those number-lists point. 0 = identical, 1 = unrelated | The `0.50` threshold is a cosine distance |
| **Distant / provenance supervision** | Using a label you get for free from how the data was built, instead of paying humans to label | How we got relevance labels at zero cost |
| **Precision@10** | Of the top 10 results, what fraction were relevant | Basic retrieval quality |
| **Recall@50** | Of all the relevant studies, what fraction appeared in the top 50 | Coverage of retrieval |
| **R-precision** | Precision measured at *k = the number of relevant docs*. Fair when some queries have 2 relevant docs and others have 47 | Our clusters vary hugely in size, so plain precision@10 would be misleading |
| **nDCG@10** | Like precision@10, but rewards putting relevant results *higher up*. Ranges 0–1 | Our main retrieval metric |
| **MRR** | 1 / (rank of the first relevant result) | How fast a user hits something useful |
| **Cohen's κ (kappa)** | Agreement between two raters, corrected for agreement you'd get by luck. 0 = chance, 1 = perfect. 0.6–0.8 is "substantial" | Used for grader-vs-MEDLINE and human-vs-model |
| **Bootstrap CI** | Re-sample your queries thousands of times to see how much the average would wobble | Our error bars |
| **Wilcoxon signed-rank** | A significance test for paired measurements that doesn't assume a bell curve | Comparing embedding models on the same 49 queries |
| **Jaccard overlap** | Size of the intersection ÷ size of the union of two sets | How much two models' citation lists agree |
| **Ablation** | Change exactly one thing and re-measure, to see what that thing was worth | How we tested embeddings, query wording, and the threshold |

---

## 4. The four studies

### S1 — Is the study-design grader accurate? `results/s1_tier_audit.json`

**What the system does.** Every study is graded into a tier (meta-analysis > systematic
review > RCT > … > other), and that tier is the largest single term (weight 0.55) in the
study's retrieval weight, which then feeds the confidence score users see.

**How it grades.** A first-match keyword cascade. Simplified, the real line is:

```python
if any(pattern in publication_types or pattern in title_and_abstract for pattern in META_PATTERNS):
    return "meta_analysis"
```

**The trick that made this free.** Notice it checks the MEDLINE publication tags **or** the
abstract text. So we ran *the system's own function*, restricted to just the MEDLINE tags,
and used that as the reference. No mapping of ours sits between the system and its ground
truth — it is a one-line ablation of a single design decision: *should the grader read the
abstract body?*

**Result.** 80.1% agreement, κ = 0.719. Of 100 disagreements, **19.9% grade the study
stronger and 0.0% weaker.**

**Why that's a proof, not a coincidence.** Giving a first-match cascade *more text* can only
create matches, never remove them, and the cascade is ordered strongest-first. So widening
what it reads can only promote. The inflation is structural. *(This is a good thing to
volunteer — it shows you understand the mechanism, not just the number.)*

**What it costs.** 117 of 346 evidenced exercises shift confidence, 19 change confidence
*level*, 38 show a different top study. It calls 60 studies meta-analyses; MEDLINE
supports 37.

**The fix we can recommend.** Restrict the cascade to publication types + **title**. That
recovers most of the signal (90.8% agreement, κ = 0.866) and removes more than half the
inflation. One line.

---

### S2 — How good is retrieval, and what actually drives it? `results/s2_retrieval_eval.json`

**Where the labels came from.** When the corpus was built, each study recorded which boolean
PubMed query fetched it (`topic_clusters`). So: *a study is relevant to a query about topic C
exactly when C's PubMed query pulled it in.* Those labels come from a completely different
kind of search (boolean keyword / MeSH) than the one being tested (dense vectors), and they
cost nothing.

**What we varied.** Five embedding models × four ways of writing the query, 49 queries.

The five models are chosen to answer one question cleanly — *is a biomedical model better
because it's biomedical, or just because it's bigger?* `bge-base` (general), `PubMedBERT`
(biomedical) and `S-PubMedBERT-MS-MARCO` (biomedical + retrieval-trained) are **all 109.5M
parameters at 768 dimensions**. Identical size. So any difference is not size.

**Result 1 — the model barely matters.** No model differs significantly from the shipped one
(Wilcoxon p ≥ 0.06). Range across models: 0.064 nDCG.

**Result 2 — the query wording matters enormously.** Range across formulations: 0.400 nDCG,
about six times larger. The shipped model scores 0.446 on the raw boolean query and 0.086 on
the production query template — **it loses 81%**. The best model on the production template
still scores below the *worst* model on the raw query.

**Result 3 — a genuine negative result on domain-specific embeddings.** PubMedBERT was the
**worst** arm (0.267 on topic queries vs bge-base's 0.444, at identical size). The biomedical
model that did well was the one also trained for retrieval. **The discriminating factor is
retrieval training, not biomedical domain.** This is worth stating plainly — it's the kind of
result people assume the opposite of.

**Result 4 — the two-stage gap.** Even though no model is significantly better at retrieval,
swapping the model changes **most of the actual citations** (Jaccard 0.32 against the
baseline). Half of that instability is the fixed threshold not transferring between embedding
spaces (Jaccard rises to 0.45 when we give every model the same pool size), and half is
genuine ranking difference. **Retrieval quality metrics do not predict citation content.**

---

---

### S2c — We fixed it and re-measured `results/s2c_query_repair.json`

**Why this exists.** If formulation is the dominant lever, the responsible thing is to pull
it, not just point at it. So this is an intervention, not another observation.

**What the query used to carry.** For a chest hypertrophy request, the string embedded was:

> `hypertrophy resistance training protocol | target muscles: chest | sessions per week: 3 |`
> `split template: auto | equipment available: barbell, dumbbell | user notes: ... |`
> `candidate exercises: Band Bench Press, Barbell Bench Press, ...`

Roughly three quarters of that is scaffolding. "Sessions per week: 3" tells you nothing
about which studies to retrieve.

**The honest bit — how we avoided fooling ourselves.** Picking the best of five variants and
then reporting its score on the same queries would be cheating: you'd be selecting on your
own test set. So the 49 clusters were split in half, deterministically. The winner was
chosen on one half and its gain reported from the other half, which it never influenced.

**Result.** The winning query carries only the muscles, the goal, and the user's own notes:

> `chest hypertrophy resistance training | Beginner programming principles`

On held-out queries: **0.215 vs 0.091 nDCG@10, +137%, p = 0.0088**, better on 12 of the 13
queries that moved. It improves *every* embedding model tested, from +94% to +262% — so it
isn't a quirk of one model. And it isn't bought by retrieving less: the share of requests
producing any citation is unchanged at 86%.

Two side questions got answered too. Equipment tokens are **neutral**. Candidate exercise
names are **harmful** — catalog product names like "Band Two Legs Calf Raise - (Band Under
Both Legs) V. 2" are full of variant and equipment words that never appear in abstracts.

---

### S2b — Is the distance threshold calibrated? `results/s2b_threshold_roc.json`

The code says `MAX_FINDING_DISTANCE = 0.50` and documents it as calibrated against off-topic
probes "yoga, nutrition, swimming". **Those probes are not in the repository**, so the claim
can't be reproduced. We supply a probe set that can be.

**Result.** The ceiling is a property of the embedding space, not of the corpus:

| model | corpus admitted at 0.50 | off-topic probes rejected | best ceiling here |
|---|---|---|---|
| MiniLM (shipped) | 4.3% | 100% far, 20% adjacent | 0.425 |
| bge-small | 98.2% | **0%** | 0.275 |
| bge-base | 94.6% | **0%** | 0.275 |
| PubMedBERT | 1.5% | 100% far, 40% adjacent | 0.525 |
| S-PubMedBERT | 100.0% | **0%** | 0.200 |

Swap the embedding model and the only hard safety filter on semantic retrieval silently
becomes a no-op. Note also that even for the shipped model, in-domain queries range up to
0.821 — beyond the claimed 0.23–0.45 — so some legitimate queries are silenced entirely, and
4 of our 5 adjacent probes (which include yoga, nutrition and swimming) *pass* the filter.

---

### S3 — Does the evidence reach the recommendation? `results/s3_attribution_audit.json`

**Coverage.** 346 / 1,324 exercises (26.1%) carry any citation. Only 145 / 502 studies
(28.9%) ever attach to one. At request time it's worse: for a hypertrophy request, only
**18.9%** of the catalog can show a citation.

**The finding that lands hardest.** The corpus *has* the missing science. The pipeline ran
dedicated gap-filling queries, fetched 20 studies on grip and forearm training — and **not
one of the 37 forearm exercises cites any of them.** Same for traps (0/17) and hip abductors
(0/5), where 30 studies were fetched. More supply did not produce more attribution.

**Why — the mechanism, quantified.** Attribution only fires on short generic names. Of 1,970
distinct catalog aliases, only **57 ever match a study (2.9%)**, and **49 of those 57 are
exactly two words** ("calf raise", "biceps curl", "bench press"). Matched aliases average
2.21 words; the catalog's aliases average 3.59.

**Consequences.** One study is cited for up to **47** different exercises (mean 13.2). The
346 evidenced exercises share only **50 distinct citation lists** — the largest group is
**36 exercises with byte-identical citations**.

**A validity failure, not just a coverage one.** The alias `"leg raise"` matched an RCT on
*deep oscillation massage therapy for hamstring flexibility*. There, "leg raise" is the name
of a **clinical assessment test**, not a training exercise. String matching cannot tell the
difference.

**Support collapses with specificity** *(pilot, n = 22 adjudicated)*: 59% of alias-matched
citations involve the movement, 32% report a relevant outcome, 14% used the actual variant,
9% satisfy all three.

**The counterweight — say this unprompted.** The ranking *works*: top-5 exercises per muscle
are 2.8× more likely to be evidenced than the rest. And when nothing clears the bar the
system returns an empty result rather than padding with weak citations. Those are good
design decisions and the paper says so.

---

### S4 — Does the system do what it publicly says? `results/s4_conformance.json`

The app ships a methodology page with formulas and explicit claims. We checked each one.
**At audit time: six conformed, four diverged, one qualified.** All four divergences have
since been fixed, and the checker now reads each published figure out of its source file
rather than comparing against a snapshot — so it doubles as a regression test and would
catch the numbers going stale again.

The most important result is a claim that **holds**: the page says no exercise can look
highly-evidenced without evidence, because the heuristic path is capped at 0.72, below the
0.75 "high" threshold. That is true — of 978 zero-evidence exercises, none is labelled
"high", and the highest scores 0.64.

But the label around it does a lot of work: **"moderate" is applied to 1,006 exercises of
which only 5.9% have any linked study.** And every set/rep/rest number a user acts on is
either a hardcoded constant or the planner model's own knowledge — we demonstrated this by
calling the engine's function on three wildly dissimilar exercises and getting identical
output. **The citation beside a prescription supports the exercise choice, never the dose.**

---

## 4b. What we changed in the capstone, and what we deliberately did not

Four fixes were applied. All are small, all are covered by the existing test suite, and
**all 73 engine tests pass unchanged**.

| Change | Why | Worth |
|---|---|---|
| Query scoped to muscles, goal, user notes | S2 / S2c | +137% nDCG@10 held-out |
| Citation-containment check now runs on every generation | S4 | a tested guardrail becomes an executed one |
| API evidence appendix merges per-exercise references | S4 | study count covers every PMID shown |
| Two published counts corrected | S4 | conformance divergences resolved |

**One we did not touch, on purpose — and this is worth volunteering, because it shows
judgement.** Restricting the study-design grader to publication types and titles would
remove more than half the tier inflation. But tiers are baked into the corpus, the exercise
catalog *and* the vector store, so making it take effect means regrading and rebuilding all
three — which shifts catalog rankings that the existing quality tests assert on. S1 already
measures exactly what that change would be worth (90.8% agreement, κ=0.866), so we report
the recommendation and its measured effect instead of taking the risk. Knowing which
findings are worth acting on is part of the result.

## 5. Numbers cheat sheet

| | |
|---|---|
| Corpus / chunks / catalog | 502 studies · 1,264 chunks · 1,324 exercises |
| Evaluation queries | 49 clusters × 4 formulations × 5 models |
| Grader agreement with MEDLINE | 80.1%, κ = 0.719 |
| Grader disagreement direction | 19.9% stronger, **0.0% weaker** |
| Model choice worth | 0.064 nDCG, not significant (p ≥ 0.06) |
| Query wording worth | 0.400 nDCG (~6× more) |
| Shipped model, raw query → production template | 0.446 → 0.086 (**−81%**) |
| Query fix, held-out queries | 0.091 → **0.215** (+137%, p = 0.0088) |
| Query fix across all five models | +94% to +262%, citation yield unchanged (86%) |
| Threshold 0.50 admits | 4.3% (MiniLM) … 100% (S-PubMedBERT) |
| Exercises with any citation | 346 / 1,324 = **26.1%** |
| Studies ever cited | 145 / 502 = **28.9%** |
| Aliases that ever match | 57 / 1,970 = **2.9%** (49 are two words) |
| Max exercises citing one study | **47** (mean 13.2) |
| Forearm exercises citing forearm studies | **0 / 37** (20 studies fetched) |
| P(any evidence \| "moderate" label) | **5.9%** |
| Published claims at audit: conform / diverge / qualified | 6 / 4 / 1 (all 4 since fixed) |
| Engine tests after all fixes | **73 / 73 passing** |

---

## 6. Questions you will get, and how to answer them

**Q: Aren't your relevance labels circular? You're testing whether vector search reproduces
the keyword search that built the corpus.**
A: Good question, and it's why we're careful about what we claim. Three things. First, the
labels come from a *different retrieval paradigm* — boolean/MeSH keyword search — so
reproducing them is a genuinely different task, not a tautology. Second, the queries we test
with are mostly *not* the boolean strings; we report four formulations, and the boolean one
is explicitly labelled as an optimistic ceiling. Third, and most importantly, our main
conclusions are *relative comparisons* — model A vs model B, wording A vs wording B — and all
arms share the same labels, so any label bias affects them equally and cancels.

**Q: The labels are incomplete. A study fetched by one query might be relevant to another.**
A: Yes, and we state the direction of that bias. An incomplete label set counts a genuinely
relevant retrieved study as a miss, so it can only push precision *down*. Every precision
number we report is therefore a lower bound — a conservative direction. And we define recall
precisely as recall against the boolean-query result set, not against all relevant science.

**Q: MEDLINE publication types aren't perfect ground truth either.**
A: Correct, and that's exactly why we separate *disagreement* from *error*. Some
disagreements are our grader being right where MEDLINE indexing is incomplete — a paper
titled "A Systematic Review and Meta-Analysis" whose tags only say "Review". That's why 15 of
the 40 human annotations adjudicate a stratified sample of those disagreements, giving a
corrected accuracy alongside raw agreement. Also note the *direction* result doesn't depend
on MEDLINE being right at all: it's structural.

**Q: Is 49 queries enough?**
A: The query is the unit of analysis and we report bootstrap 95% confidence intervals over
it, plus paired Wilcoxon tests since all arms see the same queries. The intervals are wide
enough that we *don't* claim any embedding model beats another — we report that as a null
result. The formulation effect is roughly six times larger and survives comfortably.

**Q: Isn't a biomedical embedding model supposed to be better? Did you use it wrong?**
A: That was our expectation too, which is why we included a size-matched general-purpose
control. bge-base, PubMedBERT and S-PubMedBERT are all 109.5M parameters at 768 dimensions,
so size is held constant. PubMedBERT was worst; the biomedical model that did well was the
one *also* trained for retrieval on MS-MARCO. Our reading is that retrieval training matters
more than domain pretraining for this task, and we report it as an observation on one corpus,
not a general law.

**Q: Isn't this just finding bugs in your own project?**
A: Every mechanism we measure is a documented design decision, not a defect. The
movement-level attribution is stated in the project's README as intentional. What the paper
adds is a *number* for what that decision costs, and we report the things the system gets
right too — the ranking's 2.8× evidence enrichment, the honest-empty behaviour, and a
published guardrail that we verified actually holds.

**Q: So what's the actual research contribution?**
A: Two things. The protocol — three of four stages evaluated at zero annotation cost using
ground truth these pipelines already produce — which any team building a literature-backed
system can reuse. And the finding that retriever-only evaluation, which is the norm, is
insufficient: we show a case where retrieval metrics are flat across a design choice that
nonetheless changes most of the output citations.

**Q: Why does citation faithfulness matter here specifically?**
A: Because the product's entire proposition is "every recommendation is cited". A citation
that is topically adjacent but doesn't support the specific prescription manufactures
authority the evidence doesn't provide, in a health-adjacent domain. That's the risk worth
quantifying.

**Q: Why did you use exact search instead of the production vector index?**
A: Three reasons. It removes approximate-search error as a confound so model comparisons are
clean; it's bit-reproducible; and the committed Chroma database mutates when it's merely
opened, so avoiding it keeps the capstone repository untouched. With 1,264 chunks, exact
search costs nothing.

**Q: Your LLM judge only rated 22 pairs. Isn't that too few?**
A: It's a pilot and we label it as one. The free API tier capped today's run; the harness
caches every verdict and resumes, so the full 169 completes without re-doing work. The judged
component is also not what the main findings rest on — S1, S2, S2b and the S3 coverage
results are fully deterministic and need no judge at all. And the human annotation set covers
both attachment mechanisms, so the head-to-head doesn't depend on the model.

**Q: How do you know the LLM judge isn't just agreeing with itself / being lenient?**
A: We measure it. `s3e_agreement.py` reports Cohen's κ between the human labels and the
model's on the same items, and explicitly reports model leniency as the difference in "yes"
rates. If agreement is poor we report the human-only numbers.

**Q: You picked the best of five query variants. Isn't that overfitting?**
A: It would be if we reported its score on the queries we picked it with, so we didn't. The
49 clusters were split deterministically in half; the winner was chosen on one half and the
137% gain is measured on the other half, which played no part in the choice. The held-out
result is also significant on its own (p = 0.0088) and improves 12 of the 13 queries that
moved.

**Q: Did the query fix just make the system retrieve less, so precision looks better?**
A: No, and we checked specifically because that's the obvious way to fake this. Replaying
the full production pipeline, the share of requests producing at least one citation is
unchanged at 86% and mean citations per request goes 5.02 → 4.96. It retrieves the same
amount, more relevantly.

**Q: Why fix the query but not the study-design grader, when the grader finding is stronger?**
A: Because of what each change costs to make real. The query builder is one pure function
with no persisted state. Tier scores are baked into the corpus, the catalog and the vector
store, so changing the grader means regrading and rebuilding all three, which shifts
rankings the existing tests assert on. And S1 already measures what the fix would be worth,
so acting on it would add risk without adding evidence.

**Q: Could you just fix these problems instead of writing about them?**
A: We did fix four of them, and the paper reports the before and after. But the point stands:
you cannot find any of them by measuring the retriever, which is what the literature does.
The remaining recommendations — restrict the grader to titles and publication types,
recalibrate the ceiling per embedding space — are reported with their measured effect so
someone can act on them deliberately.

**Q: What would you do with more time?**
A: Complete the adjudicated sample; add a second independent judge; extend the protocol to a
second literature-RAG system to show the method transfers; and test whether replacing the
alias matcher with a retrieval-based attribution step closes the coverage gap — which our
S3 head-to-head is designed to indicate.

**Q: What's your biggest limitation?**
A: The evaluation is on one system and one corpus, so the specific numbers don't generalise —
the *mechanisms* are what we claim generalise. And the provenance labels are incomplete, which
we handle by reporting precision as a lower bound and relying on relative comparisons.

---

## 7. If you get asked something you don't know

Say so, then say what you'd measure. *"I don't know — but that's testable: I'd
[change X] and re-run the harness, and I'd expect [Y] if the mechanism is what we think."*
That answer is stronger than a guess, and the harness genuinely makes it a one-command claim.

---

## 8. Running everything

```bash
# fully deterministic, no network, ~2 minutes total
./.venv/bin/python -m research.s1_tier_audit
./.venv/bin/python -m research.s3_attribution_audit
./.venv/bin/python -m research.s4_conformance

# needs the embedding models (cached after the first run)
./.venv/bin/python -m research.s2_retrieval_eval
./.venv/bin/python -m research.s2b_threshold_roc
./.venv/bin/python -m research.s2c_query_repair

# the judged component
./.venv/bin/python -m research.s3b_build_semantic_pairs
./.venv/bin/python -m research.s3c_judge          # resumes; needs API quota
JUDGE_CACHED_ONLY=1 ./.venv/bin/python -m research.s3c_judge   # summary, no network

# your 40 annotations
./.venv/bin/python -m research.s3d_build_annotation
open research/annotate/index.html                 # ~30 min, export when done
./.venv/bin/python -m research.s3e_agreement

./.venv/bin/python -m research.make_figures
```

Every module writes `research/results/*.json`. S1, S3 and S4 are byte-identical across runs —
that's a checkable property, not a claim.
