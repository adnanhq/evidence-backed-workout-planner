# The 10-minute brief

Self-contained. Assumes you know nothing about ML terminology, and explains each idea at
the point the story needs it. Read Part 1 once to load the concepts, then Part 2 is what
you actually say out loud.

*(The long version with every number is `BRIEFING.md`. This is the version you talk from.)*

---

# Part 1 — The primer

## 1.1 What your capstone actually does, mechanically

Worth being precise about this, because the whole paper hangs on one detail of it.

**Built once, offline:**

1. **103 PubMed searches** run against the medical literature database — things like
   `"resistance training volume dose response hypertrophy meta-analysis"`. They pull back
   **502 studies**.
2. Each study's abstract is cut into a few pieces (~2.5 each) → **1,264 chunks**.
3. Each study is **graded by design quality** — meta-analysis is the strongest, then
   systematic review, then randomised controlled trial (RCT), down to "other". This grade
   is assigned by a *keyword rule*, not by a person: if the words "meta-analysis" appear,
   it's graded a meta-analysis.
4. Each of the **1,324 exercises** is linked to studies by **name matching**: if a study's
   abstract contains the phrase `"bench press"`, every bench-press exercise gets linked to
   it. That produces **1,915 exercise↔study links**.

**When a user makes a request:**

5. Python filters and ranks the catalog for their goal, muscles and equipment.
6. It builds **one search query** and searches the 1,264 chunks for related science.
7. **The AI model** receives the shortlisted exercises and the retrieved studies, and
   decides the weekly split and the sets/reps. **It is explicitly forbidden from citing
   anything.**
8. **Python attaches the citations afterwards** — deterministically, in code.

> **The one detail that matters most:** citations come from **two completely separate
> mechanisms**, and neither is the AI. One attaches studies **by name** (step 4). The
> other attaches them **by meaning** (step 6). The AI never picks a citation, which is why
> "the AI made up a fake study" is impossible here — and why the interesting question is a
> different one.

## 1.2 What an "embedding" is (needed for step 6)

A computer can't tell that "muscle growth" and "hypertrophy" mean the same thing. An
**embedding model** solves this: it converts a piece of text into a long list of numbers —
called a **vector** — arranged so that texts about similar topics get similar numbers.

Once every study chunk is a list of numbers, "find studies related to this request"
becomes "find the closest lists of numbers", which is instant.

**Cosine distance** is how you measure "close". **0 means nearly identical in meaning, 1
means unrelated.** Your engine has a hard rule: anything further than **0.50** gets thrown
away rather than cited. That single number matters later.

Your system uses an embedding model called **MiniLM** — small, fast, general-purpose. Not
trained on medical text specifically. That's one of the things we tested.

## 1.3 nDCG — how you score a search engine

If you search and get 10 results back, how good was that? You need a number.

**nDCG@10** ("normalised discounted cumulative gain at 10") is the standard one. It runs
**0 to 1**, where 1 is a perfect result list. Two ideas built into it:

- **Discounted** — a correct result at position 1 is worth more than the same result at
  position 10. Being right *early* counts more, because that's what people read.
- **Normalised** — the score is divided by the best score that was achievable for that
  particular question, so questions with lots of correct answers and questions with few
  are on the same scale.

**Say it as:** *"a 0-to-1 score for how good a ranked list of search results is, which
rewards putting the right things near the top."*

## 1.4 Cohen's kappa (κ) — the thing you asked about

**The problem it solves.** Suppose two people each grade 100 papers as either "RCT" or
"not RCT", and 90 of the papers really are RCTs. If both graders just lazily said "RCT"
every single time, they'd **agree 100% of the time** — while doing no actual work. Raw
agreement percentages are inflated by luck whenever one answer is common.

**Cohen's kappa fixes that.** It works out how much two graders would agree *purely by
chance*, and subtracts it out. What's left is agreement they actually earned.

- **κ = 1.0** → perfect agreement
- **κ = 0** → they agree no more than random guessing would produce
- **κ below 0** → they agree *less* than chance (they're systematically opposed)

The conventional reading, from a standard reference (Landis & Koch):

| κ | reading |
|---|---|
| 0.81 – 1.00 | almost perfect |
| **0.61 – 0.80** | **substantial** |
| 0.41 – 0.60 | moderate |
| 0.21 – 0.40 | fair |

**Ours is κ = 0.719**, which lands in "substantial". So our automatic study-grader isn't
junk — it's roughly as consistent with the official medical index as two reasonable people
would be with each other. But it's clearly not reliable enough to trust blindly, and the
*way* it disagrees turns out to be the interesting part.

**Say it as:** *"kappa is agreement between two graders after subtracting the agreement
you'd get by luck. 1 is perfect, 0 is chance. We got 0.72, which is 'substantial' —
decent, not trustworthy."*

## 1.5 "Significant", confidence intervals, and "held-out"

**p-value.** When you measure a difference between two things, some of it could just be
luck of which questions you happened to test. A p-value is the probability of seeing a
difference at least this big *if there were really no difference at all*. Small p = hard to
explain away as luck. Below **0.05** is the usual bar. **We report p = 0.0088**, which is
under 1 in 100.

**Confidence interval.** A range showing how much a number would wobble if you'd used a
different sample of questions. A wide interval means "don't lean on this number too hard".

**Held-out.** This one is about not fooling yourself. If you try five different fixes and
then report the score of whichever won, you're cheating — you *chose* the winner using the
same questions you're now bragging about. So we split our 49 test questions in half: we
picked the winner using one half, and reported its score on the **other** half, which had
no say in the choice. That's what makes the improvement believable rather than
self-congratulatory.

**Say it as:** *"we picked the fix on one set of questions and measured it on a different
set it had never seen."*

---

# Part 2 — What you actually say (about 6 minutes)

### Open — the question (30 sec)

> Our capstone puts a peer-reviewed PubMed citation next to every exercise it recommends.
> That's a strong claim to make to a user, so I wanted to test whether it holds up.
>
> The normal way to evaluate a system like this is to measure the search step — how good is
> the retrieval. I found that's the wrong place to look.

### The frame — four stages (1 min)

> For a citation to be trustworthy, four separate things all have to go right.
>
> One: the study has to be **graded correctly** — is it a strong meta-analysis or a weak
> observational study.
> Two: the system has to **retrieve** relevant science.
> Three: the right study has to actually get **attached** to the right exercise.
> Four: the interface has to **present** all of that honestly.
>
> Everyone measures stage two. I measured all four separately.

### The methodological trick — why this cost nothing (1 min)

> The reason nobody does this is that evaluating retrieval normally means paying experts to
> read hundreds of papers and label which ones are relevant. We couldn't do that.
>
> But it turned out our own pipeline had already stored the answers and thrown them away.
>
> First: PubMed already publishes each paper's *official* study type. So I could check our
> automatic grader against the authoritative source, on all 502 papers, with zero manual
> labelling.
>
> Second: when we built the corpus, each study recorded *which search query had pulled it
> in*. That's a free relevance label — and it comes from keyword search, a completely
> different method than the AI-based search we're testing. So it's a fair test, not a
> circular one.
>
> That's the reusable contribution: three of the four stages need no manual annotation at
> all, because these pipelines already produce their own ground truth.

### Finding 1 — the grader only ever inflates (1 min)

> Our study-grader agrees with the official PubMed classification 80% of the time. Kappa
> 0.72, which is "substantial" — so it's decent.
>
> But here's the thing. There were 100 disagreements, and **every single one graded the
> study as stronger evidence than it actually is. Not one graded it weaker.**
>
> And that's not bad luck — it's structural. The grader stops at the first keyword it
> matches, and it's checking strongest-category-first. It reads not just the official tags
> but the whole abstract. So if a paper merely *mentions* "meta-analysis" while discussing
> someone else's work, it gets promoted. Giving it more text to read can only ever promote,
> never demote.
>
> We call 60 papers meta-analyses; PubMed supports 37.

### Finding 2 — we optimised the wrong thing (1.5 min)

> Then I tested the search step, five different embedding models, including two trained
> specifically on biomedical text. I controlled for size, so the biomedical model and the
> general one had identical parameter counts — otherwise you can't tell whether a win came
> from the biology or just from being a bigger model.
>
> **None of them significantly beat the model we already use.** And the biomedical one was
> actually the *worst*. The thing that mattered wasn't medical training, it was whether the
> model had been trained for search specifically.
>
> What *did* matter — six times more — was **how the question was worded.** Our system was
> sending a search query that looked like this:
>
> *"hypertrophy resistance training protocol, target muscles: chest, sessions per week: 3,
> split template: auto, equipment available: barbell dumbbell, candidate exercises: Band
> Bench Press, Barbell Bench Press…"*
>
> About three quarters of that is scaffolding. "Sessions per week: 3" tells you nothing
> about which studies to fetch. That padding was costing us 81% of our search quality.

### Finding 3 — we fixed it and measured (1 min)

> So I tested five rewrites. And to avoid fooling myself, I split the test questions in
> half — chose the winner on one half, reported the result on the other half it had never
> seen.
>
> The winning query is just: **"chest hypertrophy resistance training"** plus whatever the
> user typed.
>
> On held-out questions that more than doubles retrieval quality — **plus 137%, p = 0.0088**.
> It improved *every* embedding model we tested, so it's a property of the query, not of one
> model. And it isn't cheating by retrieving less: the share of requests that produce a
> citation is unchanged.
>
> That's now in the codebase, and all 73 existing tests still pass.

### Finding 4 — the one that surprised me most (1 min)

> Last stage: attribution — how a study gets attached to a specific exercise. It's done by
> **name matching**. If a study's abstract says "bench press", every bench-press variant
> gets linked to it.
>
> Only 26% of our exercises have any citation at all. But the striking part is *why*.
>
> The pipeline had specifically noticed we had no forearm evidence, run dedicated searches,
> and successfully fetched 20 studies on grip and forearm training. **Not one of our 37
> forearm exercises cites any of them.**
>
> The reason: out of nearly 2,000 exercise name-aliases in our catalog, only **57** ever
> match anything — and 49 of those are exactly two words long. "Calf raise." "Biceps curl."
> "Bench press." If a movement doesn't happen to have a short, generic name, it gets nothing.
>
> And it fails in the other direction too. One study is cited for up to 47 different
> exercises. And the phrase "leg raise" matched a study about **massage therapy for
> hamstring flexibility** — because there, a leg raise is a clinical *test*, not an
> exercise. String matching can't tell the difference.

### Close — why it's a paper (30 sec)

> Two contributions. The **method** — a stage-by-stage audit that costs almost nothing to
> run, because these pipelines already store their own ground truth. Anyone building a
> literature-backed system can reuse it.
>
> And the **finding** — measuring the retriever, which is what the field does, would have
> told us this system was fine. Every real problem was somewhere else. Retrieval is not
> grounding.

---

# Part 3 — Six numbers to know cold

| | |
|---|---|
| Grader agreement with PubMed | **80.1%**, κ = 0.72 — and **19.9% inflate, 0.0% deflate** |
| Query wording vs model choice | wording matters **~6×** more |
| The fix, on held-out questions | **+137%**, p = 0.0088, helps every model |
| Exercises with any citation | **26.1%** (346 of 1,324) |
| Aliases that ever match | **57 of 1,970** — 49 are two words |
| Forearm exercises citing forearm studies | **0 of 37**, from 20 studies fetched |

---

# Part 4 — The questions you'll get

**"Your relevance labels come from your own search queries. Isn't that circular?"**
> The labels come from *keyword* search — a completely different method than the AI vector
> search we're testing, so reproducing them is a real task, not a tautology. And every
> conclusion is a comparison — this model versus that one, this wording versus that one —
> where all sides share the same labels, so any bias cancels out.

**"PubMed's own classifications aren't perfect either."**
> Agreed, which is why I separate *disagreement* from *error*. Sometimes our grader is
> right and PubMed's indexing is just incomplete. That's what 15 of the 40 human annotations
> are for. And the headline result doesn't depend on PubMed being right at all — the fact
> that disagreements only ever go one direction follows from how the code is written.

**"Is 49 test questions enough?"**
> It's enough that I *don't* claim any embedding model beats another — I report that as a
> null result with confidence intervals. The query effect is six times larger and holds up
> on held-out questions.

**"Aren't biomedical models supposed to be better?"**
> That's what I expected too, which is why I included a same-size general-purpose model as a
> control. The biomedical one lost at identical size. My reading is that being trained for
> *search* matters more than being trained on *medicine* — reported as one result on one
> corpus, not a general law.

**"Isn't this just finding bugs in your own project?"**
> Every mechanism I measured is a documented design decision — the name-based attribution is
> written up in our own README as an intentional trade-off. What this adds is a *number* for
> what that trade-off costs. And I report what the system gets right too: the ranking
> surfaces evidenced exercises 2.8× more often, it returns nothing rather than padding with
> weak citations, and one guardrail I tried hard to break held up perfectly.

**"You changed the query. How do I know that's not just retrieving less?"**
> I checked that specifically, because it's the obvious way to fake this result. The share
> of requests producing a citation is unchanged at 86%, and the average number of citations
> went 5.02 to 4.96. Same amount, more relevant.

**"So is your capstone broken?"**
> No. Retrieval works, the ranking works, and the guardrails hold. What I found is that the
> *cheap glue code* around the impressive part is where the weaknesses are — and I've
> already fixed four of them. The one I didn't fix, I didn't because making it take effect
> means rebuilding three data artefacts and would shift rankings our tests depend on, and I
> can already measure exactly what it would be worth. Knowing which findings are worth
> acting on is part of the result.

**If you get asked something you don't know:** say so, then say what you'd measure.
*"I don't know — but that's testable. I'd change X and re-run the harness, and I'd expect Y
if the mechanism is what we think."* That's a stronger answer than a guess, and the harness
makes it a one-command claim.
