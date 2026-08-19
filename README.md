# Axiom — Science-Backed AI Protocol Builder

A web app that generates a peer-reviewed weekly training protocol where **every exercise
suggestion is ranked and cited to the science behind it**. It pairs a polished Next.js
frontend with a Python engine that filters 1,324 exercises, retrieves matching PubMed
studies from a vector store, and uses an LLM to plan the weekly split.

```
┌─ apps/web         Next.js 16 + Tailwind v4 frontend (landing, builder, library, science)
│     └─ fetch ──▶ POST /api/protocol/generate ──┐
├─ services/engine  FastAPI ◀─────────────────────┘
│     ├─ app/              API layer (endpoints, mappers, lifespan warmup)
│     └─ protocol_engine/  the tested protocol engine + data pipeline
├─ packages/data    catalog + science corpus + Chroma vector store (shared JSON/binary)
```

## Prerequisites

- **Node.js 18+** and **npm**
- **Python 3.9+** with a virtualenv at `./.venv`
- A **Google Gemini API key** (the planner uses Gemini)

## Setup

```bash
# 1. Frontend + orchestrator deps (npm workspace)
npm install

# 2. Python engine deps (into the repo-root venv)
python3 -m venv .venv
./.venv/bin/pip install -r services/engine/requirements.txt

# 3. Configure secrets
cp services/engine/.env.example services/engine/.env
#   → edit services/engine/.env and set GEMINI_API_KEY
#   apps/web/.env.local already points at the local engine (NEXT_PUBLIC_ENGINE_URL)
```

## Run

```bash
npm run dev
```

- Web app → http://localhost:3000
- Engine API → http://localhost:8000 (docs at `/docs`)

The engine warms the embedding model + vector store on startup (~15–30s the first time).

> **Note on speed:** the default Gemini model (`gemma-4-26b-a4b-it`) is thorough but slow —
> a generation can take ~1–2 minutes on a free-tier key. Set `PROTOCOL_MODEL` in
> `services/engine/.env` to a faster model if your key has quota for it.

## Useful scripts

| Command | What it does |
|---|---|
| `npm run dev` | Run the web app + engine together |
| `npm run build` | Production build of the web app |
| `npm run test:engine` | Run the engine's Python test suite |

## API

| Endpoint | Purpose |
|---|---|
| `POST /api/protocol/generate` | Generate a cited weekly protocol |
| `GET /api/taxonomies` | Filter options for the builder |
| `GET /api/exercises` | Search/filter the 1,324-exercise catalog |
| `GET /api/exercises/{id}` | One exercise + full evidence |
| `GET /api/evidence/{pmid}` | Study detail from the corpus |
| `GET /api/health` | Liveness + warmup status |

## Data pipeline (offline)

The catalog, corpus, and vector store in `packages/data` are prebuilt and committed.
To regenerate them, the pipeline scripts live in `services/engine/protocol_engine/`
(`build_science_corpus.py`, `build_exercise_catalog.py`, `build_vector_store.py`,
`run_pipeline.py`).

### How exercises are ranked (and what the ranks mean)

Within each muscle + goal, exercises are ordered by an evidence-aware merit:
catalog score → count of direct PubMed studies → evidence confidence → goal-fit, with
the `exercise_id` as a deterministic, reproducible last resort. Better-evidenced
exercises win where evidence differs. When several exercises are indistinguishable on
every one of those signals, the rank is shown honestly as a tie (e.g. `#1/88 · tied×12`)
rather than implying a precise unique ordering.

Two intentional scope boundaries (documented, not bugs):

- **Evidence is movement-level, not per-variant.** A study that used a bench press is
  attributed to every bench-press variant, because abstracts rarely distinguish flat vs.
  incline vs. dumbbell. Variants of one movement therefore share that movement's evidence.
- **A muscle dominated by one movement can show several of its variants** among the top
  options (the tie flag makes this transparent). Picking between equally-evidenced variants
  is treated as an equipment/preference choice, not an evidence ranking.

## Deploy

- **Web** → Vercel (project root `apps/web`). Set `NEXT_PUBLIC_ENGINE_URL` to the engine's
  public URL. It is inlined at build time, so changing it needs a redeploy.
- **Engine** → container host (Railway / Fly.io / Render / Cloud Run):
  ```bash
  docker build -f services/engine/Dockerfile -t protocol-engine .
  docker run -p 8000:8000 -e GEMINI_API_KEY=... \
    -e ALLOWED_ORIGINS=https://your-vercel-domain.app protocol-engine
  ```
- **CORS is the usual deploy break.** The browser calls the engine directly, so the web
  app's origin must be in the engine's `ALLOWED_ORIGINS` — *exactly*, scheme and host, no
  trailing slash. Rename the Vercel domain and the engine starts answering preflights with
  `400 Disallowed CORS origin`, which the UI reports as "Couldn't reach the protocol
  engine". `ALLOWED_ORIGIN_REGEX` covers the Vercel preview URLs you can't enumerate.
  Check it from anywhere with:
  ```bash
  curl -i -X OPTIONS "$ENGINE_URL/api/protocol/generate" \
    -H "Origin: https://your-vercel-domain.app" \
    -H "Access-Control-Request-Method: POST"
  ```

---

_Evidence sourced from PubMed/NCBI · exercise data from the Free Exercise DB.
Axiom is an educational tool, not medical advice._
