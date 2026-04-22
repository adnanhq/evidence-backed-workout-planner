## Week 1 Summary: Dataset Pipeline for Science-Based Fitness Protocol Builder

### The Product and Why We Need Custom Data

Our product is an AI-powered training protocol generator that recommends hypertrophy and strength programs grounded in modern exercise science, rather than decade-old gym templates. The core architecture uses a RAG pipeline to retrieve relevant scientific evidence based on user input, feed it to an open-source LLM, and generate a structured, personalized protocol.

We initially investigated whether existing datasets could serve this purpose, but we found that they could not. Public exercise databases, such as Kaggle CSVs or wger, list exercise mechanics but contain zero scientific rationale. They lack study citations, evidence quality ratings, and a basis for preferring one exercise over another. Since our selling point is evidence-based recommendations, we decided to build the dataset ourselves.

### Why We Settled on Two Datasets

We chose to develop two separate datasets because they serve different purposes and are utilized in distinct ways at inference time.

The **exercise catalog** consists of structured metadata. It answers questions about what exercises exist, the muscles they work, required equipment, the stress they place on joints, and how well-evidenced are they. We query this like a database using exact field matching before any AI reasoning occurs. If a user has a knee injury and only possesses dumbbells, we filter out high knee-stress and non-dumbbell exercises immediately at the metadata level. This allows the system to function reliably and deterministically without forcing the LLM to calculate these constraints manually.

The **science corpus** is composed of unstructured text, specifically abstracts from PubMed research papers divided into passages. Scientific findings are often nuanced prose that cannot be easily reduced to table cells. For instance, the finding that "training at long muscle lengths produces greater hypertrophy" needs to exist as a retrievable text passage with semantic meaning. This data goes into our vector database and is retrieved by semantic similarity to the user's query.

These datasets work together during inference. The catalog handles hard constraints and pre-filtering, while the science corpus provides reasoning and justification. We then use the LLM to synthesize both into a cohesive protocol. We believe merging them would compromise the system, as we would lose either structured filterability or semantic richness.

---

### Dataset 1: Exercise Catalog

**Base data:** We used the free-exercise-db GitHub repository as our foundation. This provided 800+ exercises in JSON format with basic fields like name, muscles, equipment, and difficulty already populated, which saved us from manually cataloging hundreds of movements.

**What our build script does:**

* **Normalization:** We first normalize the raw data into a consistent vocabulary. For example, "body only" becomes "bodyweight" and muscle names are standardized. This ensures our downstream filter logic works reliably.
* **Goal Profiles:** We score each exercise for hypertrophy and strength suitability based on category, mechanic, and force type. Isolation exercises receive a hypertrophy bonus because single-muscle work is more hypertrophy-specific, while compound movements get a strength bonus. These are established programming principles we've integrated into the logic.
* **Joint Stress Profiling:** We derive a stress score per joint by combining muscle involvement data with keyword patterns in exercise names. For example, "squat" or "lunge" always adds knee stress regardless of muscle tags. This dual-source approach allows for reliable injury filtering.
* **Evidence Linking:** We search the science corpus for papers mentioning each exercise. If matches are found, those studies' quality scores are linked, giving the exercise a higher confidence score. Exercises without direct study support are flagged as lower confidence but remain in the system based on "expert consensus."
* **Muscle Group Rankings:** We pre-compute rankings for hypertrophy and strength within each muscle group. This allows the LLM to read a conclusion, such as "incline curl ranks #1 for bicep long head," rather than re-deriving it during every session.
* **Manual Review Flagging:** Any exercises with confidence below 0.50 are marked for human review and sent to a separate queue.

---

### Dataset 2: Science Corpus

**Data source:** We utilize PubMed's official Entrez E-utilities API. We use Biopython’s Entrez module to retrieve MEDLINE format text including titles, abstracts, and metadata. We focus on abstracts because they contain the actionable findings—methods, results, and conclusions—and ensure consistent coverage regardless of paywalls.

**What our build script does:**

* **Topic Clusters:** We defined 11 clusters covering areas like training frequency, volume landmarks, and injury modifications. We use 34 specific search queries to gather relevant data.
* **Evidence Tier Classification:** We classify each paper (e.g., meta-analysis, RCT, or observational) by checking PubMed’s publication type field and scanning for keywords. This hierarchy mirrors the evidence-based medicine framework used by scientists.

* **Chunking:** We use sentence-aware chunking to group abstracts into passages between 250 and 900 characters. By splitting at sentence boundaries rather than character counts, we avoid corrupting the meaning of the text.
* **Current Size:** Our current corpus includes 220 documents and 564 chunks.

---

### The Weights and Scores: Our Rationale

Every numeric score we use was a deliberate design decision. Our evidence tier scores directly mirror the established hierarchy of research. Meta-analyses sit at the top ($1.0$) because they synthesize many studies, while observational studies score lower ($0.6$) because they show correlation rather than causation.

**Our Retrieval Weight Formula:**


$$retrieval\_weight = (tier\_score \times 0.55) + (recency\_score \times 0.25) + (relevance \times 0.20)$$

We give evidence quality the dominant weight because a high-quality older study is generally more trustworthy than a low-quality recent one. Recency is weighted at $0.25$ to ensure modern science surfaces when quality is comparable. Our recency score decays linearly over a 10-year window, reflecting how quickly exercise science evolves.

---

### Manual Review: Our Quality Control

We do not use an automated review system; instead, we utilize a flag and queue system. The pipeline marks entries for manual review if they meet certain "weak evidence" conditions.

Currently, 60 out of 220 documents are in our manual review queue. Our task is to look through these entries and decide whether to keep them, remove them, or fix the metadata. This human checkpoint ensures that noise from the automated pipeline does not degrade our recommendation quality.

### Where We Are and What's Next

Our deliverables for this week:

* **Science corpus:** 220 documents and 564 chunks are fully scored.
* **Exercise catalog:** Enriched with joint stress, goal profiles, and rankings.
* **Outputs:** Clean JSON files are ready for ingestion.
* **Queues:** Manual review files have been generated.

**Our next task** is the manual review of the 60 flagged science documents. Following that, Week 2 will focus on building the RAG pipeline, setting up the database, and integrating with a local LLM via Ollama or via API calls to synthesize this context into structured protocol outputs.