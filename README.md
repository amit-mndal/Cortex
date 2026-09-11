# Cortex — Multi-Agent Research & Analysis Platform

A **Supervisor** agent classifies every question and routes it to one of
three specialists. Every run is **asynchronous**: the API queues the job on
a Celery worker and returns immediately, while the frontend watches live
progress over a Server-Sent Events stream — no blank loading spinner.

Every RAG answer is also **automatically scored** for faithfulness (is it
actually grounded in the retrieved documents, or did it hallucinate?) and
relevance, persisted to a local database. And before running the full
pipeline, a **semantic cache** checks whether a very similar question was
already answered recently — if so, the cached answer returns instantly,
skipping the agent entirely.

- **Document agent** — hybrid RAG (vector + keyword search) with a
  self-correcting retrieval loop (Corrective-RAG): grades its own results
  and rewrites the query if the first pass wasn't good enough
- **Web-search agent** — free live web search (DuckDuckGo, no API key)
  for questions your documents can't answer
- **Data-analysis agent** — writes and safely executes pandas code
  against an uploaded CSV, in a sandboxed subprocess with a timeout

Each specialist is its own LangGraph subgraph; the Supervisor is the
top-level graph that routes between them. Every node publishes a progress
event over Redis pub/sub as it runs, which is how the live-streaming UI works.

## Stack
Backend: FastAPI · LangChain · LangGraph · ChromaDB · sentence-transformers · Groq (free LLM) · DuckDuckGo Search · pandas · Celery · Redis · SQLAlchemy/SQLite
Frontend: React · Vite · Tailwind (SSE streaming)

---

## 1. Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for Redis) — or a locally installed Redis server
- A free Groq API key (see below)

## 2. Get your free API key (takes 2 minutes, no card required)

1. Go to https://console.groq.com/keys
2. Sign up / log in
3. Click "Create API Key", copy it

Groq's free tier gives generous daily limits on Llama 3.3 70B — more than
enough for a portfolio project and demos.

## 3. Start Redis

From the project root (where `docker-compose.yml` lives):

```bash
docker compose up -d
```

This starts Redis on `localhost:6379` — used as both the Celery message
broker and the pub/sub channel for live progress streaming. No config
needed, no signup, completely free.

(No Docker? Install Redis directly: `sudo apt install redis-server` on
Linux, `brew install redis` on Mac, then `redis-server` to start it.)

## 4. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

python -m pip install --upgrade pip

# Install PyTorch FIRST, from PyTorch's own index - this guarantees a
# correct, matching CPU wheel for your OS/Python version. Installing it
# indirectly (as a side-effect of `pip install -r requirements.txt`) is
# the most common cause of the "works on my machine" crash on Windows.
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Now install everything else - pip sees torch is already satisfied
pip install -r requirements.txt

cp .env.example .env
# open .env and paste your GROQ_API_KEY

# Sanity check BEFORE starting the server - if this line prints "all good"
# with no errors above it, you're clear to continue.
python -c "import numpy, torch; from sentence_transformers import SentenceTransformer; print('all good')"

uvicorn app.main:app --reload --port 8000
```

Backend is now running at http://localhost:8000
Check http://localhost:8000/health → should return `{"status":"ok"}`

First run will download the embedding model (~90MB) automatically — one-time.

## 5. Start the Celery worker

Open a **third terminal** (Redis in one, backend in another, worker here):

```bash
cd backend
source venv/bin/activate        # Windows: venv\Scripts\activate
celery -A app.workers.tasks worker --loglevel=info --pool=solo
```

`--pool=solo` is needed on Windows; on Mac/Linux you can drop it and get
real parallelism with `--pool=prefork --concurrency=4` instead.

This worker is what actually runs the agent graphs. Without it running,
`/ask-async` will queue jobs that never execute — if a question hangs
forever with no progress messages, this is the first thing to check.

## 6. Frontend setup

Open a **fourth terminal**:

```bash
cd frontend
npm install
npm run dev
```

Frontend is now running at http://localhost:5173

## 7. Try it

1. Open http://localhost:5173
2. Click "+ Add document" — upload any PDF or .txt file
3. Ask a question about it in the chat box
4. Watch the answer come back with numbered source citations

If the agent's first retrieval isn't relevant enough, you'll see
`refined search × 1` above the answer — that's the self-correction loop
in action.

---

## Project structure

```
cortex/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entrypoint
│   │   ├── api/
│   │   │   ├── chat.py          # POST /api/ask
│   │   │   ├── documents.py     # POST /api/upload
│   │   │   └── schemas.py
│   │   ├── agents/
│   │   │   ├── supervisor.py    # routes questions to the right specialist
│   │   │   ├── rag_agent.py     # document Q&A with self-correction loop
│   │   │   ├── web_agent.py     # live web search agent
│   │   │   └── data_agent.py    # CSV analysis via sandboxed pandas code
│   │   ├── eval/
│   │   │   └── evaluator.py     # LLM-as-judge faithfulness/relevance scoring
│   │   ├── cache/
│   │   │   └── semantic_cache.py # embedding-similarity response cache
│   │   ├── db/
│   │   │   ├── models.py        # EvalScore table
│   │   │   └── session.py       # SQLite engine
│   │   ├── workers/
│   │   │   ├── celery_app.py    # Celery config (broker = Redis)
│   │   │   └── tasks.py         # background job: cache check → agent → eval
│   │   ├── tools/
│   │   │   ├── web_search_tool.py
│   │   │   └── code_sandbox.py  # isolated subprocess execution
│   │   ├── retrieval/
│   │   │   ├── embeddings.py    # local embedding model
│   │   │   ├── vector_store.py  # ChromaDB
│   │   │   ├── hybrid_search.py # BM25 + vector fusion
│   │   │   └── ingest.py        # PDF/text chunking
│   │   └── core/
│   │       ├── config.py
│   │       └── progress.py      # Redis pub/sub for live progress events
│   ├── requirements.txt
│   └── .env.example
│
├── docker-compose.yml            # Redis (broker + pub/sub)
│
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── components/
    │   │   ├── DocumentPanel.jsx
    │   │   └── Message.jsx
    │   └── index.css
    ├── tailwind.config.js
    └── package.json
```

---

## How a question actually flows through the system now

```
1. Browser: POST /api/ask-async {question}
        ↓
2. FastAPI creates a job_id, hands it to Celery via Redis, returns job_id immediately
        ↓
3. Browser opens: GET /api/stream/{job_id}   (Server-Sent Events)
        ↓
4. Celery worker (separate process) runs the Supervisor graph.
   Every node it visits publishes a progress message to Redis:
   "Deciding which agent..." → "Routed to: rag agent" → "Searching documents..."
   → "Checking relevance..." → "Writing the answer..."
        ↓
5. FastAPI's /stream endpoint relays each message to the browser over SSE
   as it happens - this is what you see live in the UI
        ↓
6. When the worker finishes, it writes the final answer to Redis and
   publishes an "end" event → the stream sends the full result and closes
```

This is the difference between a toy demo and something that behaves like
a real product: the API responds in milliseconds (job queued), and the
person watches the agent actually think in real time instead of staring
at a spinner for 20-40 seconds.

## Agent routing (same as Phase 2, now streamed live)

```
question
   │
   ▼
[Supervisor: classify] ── LLM picks one of: rag / web / data / chat
   │
   ├── rag ──► retrieve (hybrid vector+BM25) ─► grade ─┬─ relevant ─► generate (cited answer)
   │                                                     └─ not relevant ─► rewrite query ─► retry (max 2×)
   │
   ├── web ──► DuckDuckGo search ─► synthesize answer with source links
   │
   ├── data ─► load latest CSV ─► LLM writes pandas code ─► run in sandboxed
   │           subprocess (15s timeout) ─► explain result in plain language
   │
   └── chat ─► direct LLM response, no tools
```

`supervisor.py` is the top-level LangGraph `StateGraph`; `rag_agent.py` is
itself a subgraph with its own retry loop. Upload a PDF and ask about it →
routes to `rag`. Upload a CSV and ask "what's the average X" → routes to
`data`. Ask about something current ("who won yesterday's match") → routes
to `web`. The frontend shows which agent handled each answer.

### Trying each agent

- **Document agent**: upload a PDF, ask "What does this document say about X?"
- **Data agent**: upload a CSV, ask "What's the average of column Y?" or
  "How many rows have Z greater than 100?"
- **Web agent**: ask something time-sensitive the documents wouldn't contain
- **Chat**: ask something conversational like "explain recursion simply"

---

## Deploying to production (free)

This puts a real public link on your resume instead of "runs on localhost."
Three free services, ~15 minutes total.

### 1. Push to GitHub
```bash
cd cortex
git add .
git commit -m "Cortex: multi-agent RAG platform"
git remote add origin https://github.com/<your-username>/cortex.git
git push -u origin main
```

### 2. Free managed Redis (Upstash)
1. Go to https://upstash.com → sign up free
2. Create a Redis database (any region close to where you'll deploy Render)
3. Copy the **`REDIS_URL`** (starts with `rediss://`) from the dashboard —
   you'll paste this into Render in the next step

### 3. Free persistent database for eval history (Supabase)
1. Go to https://supabase.com → sign up free → New Project
2. Once created, go to **Project Settings → Database → Connection string**
   and copy the **URI** (starts with `postgresql://`)
3. Replace `[YOUR-PASSWORD]` in that string with your actual database
   password (set when you created the project)
4. Keep this string handy — you'll paste it as `DATABASE_URL` in Render below

### 4. Deploy backend + worker (Render)
1. Go to https://render.com → sign up free → New → **Blueprint**
2. Connect your GitHub repo — Render auto-detects `render.yaml` and creates
   **two services**: `cortex-api` (web) and `cortex-worker` (background)
3. For each service, set these environment variables in the Render dashboard:
   - `GROQ_API_KEY` → your key from console.groq.com
   - `REDIS_URL` → the Upstash URL from step 2
   - `DATABASE_URL` → the Supabase Postgres URL from step 3 (this is what
     makes your evaluation history survive redeploys — see caveat below)
   - `FRONTEND_ORIGIN` → leave as `http://localhost:5173` for now, you'll
     update it after step 5
4. Deploy. Once live, copy the `cortex-api` service URL
   (e.g. `https://cortex-api.onrender.com`)

### 5. Deploy frontend (Vercel)
1. Go to https://vercel.com → sign up free → New Project → import your repo
2. Set **Root Directory** to `frontend`
3. Add environment variable: `VITE_API_BASE` =
   `https://cortex-api.onrender.com/api` (your actual Render URL + `/api`)
4. Deploy. Copy the resulting Vercel URL
   (e.g. `https://cortex.vercel.app`)

### 6. Close the loop
Go back to Render → both services → update `FRONTEND_ORIGIN` to your Vercel
URL (e.g. `https://cortex.vercel.app`) → redeploy both. This is what lets
the deployed frontend actually call the deployed backend (CORS).

### ⚠️ Remaining honest caveat: vector store + uploads are still ephemeral
With `DATABASE_URL` pointed at Supabase, your **evaluation history now
survives redeploys** — that part is genuinely persistent. What's still
ephemeral on Render's free tier: the ChromaDB document index and any
uploaded CSVs, since those live on local disk. Every redeploy wipes them
(re-upload your demo PDF/CSV after a redeploy). To close this last gap:
- **Vector store**: migrate ChromaDB to a hosted option (Chroma Cloud free
  tier, or Qdrant Cloud free tier)
- **Uploads**: store to S3-compatible storage (Cloudflare R2 has a free
  tier) instead of local disk

Being able to explain *why* this matters and *how* you'd fix it is
genuinely a stronger interview answer than never having hit the problem.

## What's genuinely left (optional polish)

- **Vector store persistence**: migrate ChromaDB to a hosted option (Chroma
  Cloud or Qdrant Cloud free tier) so uploaded documents also survive
  redeploys, not just eval history
- **Swap in real RAGAS**: `pip install ragas`, replace `evaluator.py`'s two
  judge prompts with `ragas.evaluate(...)` using the same
  (question, answer, contexts) inputs — same interface, drop-in
- **Observability dashboard**: a small React page reading `/api/evals`
  and `/api/evals/summary` to chart quality trends over time

At this point the core platform — multi-agent RAG, async/streaming,
evaluation, semantic caching, deployment, and persistent eval storage —
is complete. Everything above is genuine nice-to-have, not a missing
core feature.

## Evaluation & caching in detail

**Why "LLM-as-judge" instead of the `ragas` package directly:** `ragas`
implements this same pattern internally (an LLM scores faithfulness/
relevance against retrieved context) but pulls in a fairly heavy, fast-moving
dependency chain. `app/eval/evaluator.py` implements the identical concept
directly with two focused prompts, so it's transparent, easy to debug, and
has zero extra dependencies beyond what's already installed. The interface
(question, answer, contexts → 0-1 scores) is exactly what `ragas.evaluate()`
expects, so swapping in the real package later is a same-file change, not
a redesign — see "What to build next" below.

**Cache flow:** every question's embedding is checked against a
`semantic_cache` ChromaDB collection (separate from your document index)
before the agent runs. A cosine similarity above 0.93 counts as a hit and
returns the previous answer in milliseconds. Every new answer gets stored
back into the cache after it's generated, so repeated or slightly-reworded
questions get progressively faster.

**Try it:** ask the same question twice — the second time, watch the
progress stream jump straight to "Found a similar question answered
recently" instead of going through the full retrieve → grade → generate loop.

**View evaluation history:**
```bash
curl http://localhost:8000/api/evals/summary
curl http://localhost:8000/api/evals
```

## Troubleshooting

- **`GROQ_API_KEY` error on startup** → make sure `.env` exists in `backend/`
  (copied from `.env.example`) and has your real key, not the placeholder.
- **CORS error in browser console** → confirm backend is on port 8000 and
  frontend on 5173 (matches `FRONTEND_ORIGIN` in `.env`).
- **Upload succeeds but answers say "no relevant information"** → the PDF
  might be a scanned image (no extractable text). Try a text-based PDF first.
- **First upload/question is slow** → the embedding model downloads once on
  first use; subsequent runs are fast.
- **Data agent says "No CSV has been uploaded yet"** → upload a `.csv` file
  first; it's routed separately from PDFs (not chunked/embedded).
- **Web agent returns nothing** → DuckDuckGo occasionally rate-limits rapid
  repeated requests; wait a few seconds and retry.
- **Wrong agent handled my question** → the Supervisor's classification is a
  single LLM call and won't be perfect 100% of the time; rephrasing the
  question (e.g. starting a doc question with "According to the document…")
  helps it route correctly.
- **Question hangs forever with no progress messages** → the Celery worker
  isn't running. Check the terminal you started it in for errors, and make
  sure Redis is up (`docker compose ps`).
- **"Connection refused" to Redis** → run `docker compose up -d` from the
  project root first, before starting the backend or worker.
- **SSE stream connects but nothing streams** → check the browser console;
  some ad-blockers/extensions interfere with EventSource connections to
  localhost. Try in an incognito window if stuck.
- **`no such table: eval_scores`** → the SQLite DB is created automatically
  on first backend startup (`init_db()` in `main.py`); make sure you've
  started the backend at least once, from the `backend/` directory (so the
  relative `./data/cortex.db` path resolves correctly).
- **Same question doesn't hit the cache** → the cache uses semantic
  similarity (threshold 0.93), not exact match — very differently-worded
  questions about the same topic may legitimately miss. Lower
  `SIMILARITY_THRESHOLD` in `semantic_cache.py` to make it more lenient.
- **Eval scores seem off/inconsistent** → this is expected; a single LLM
  judge call is a rough signal, not ground truth. This is exactly why real
  RAGAS setups usually average over multiple runs or models — a good thing
  to mention if asked about it in an interview.
- **Deployed frontend can't reach the backend (CORS error)** → double-check
  `FRONTEND_ORIGIN` on both Render services exactly matches your Vercel URL,
  including `https://` and no trailing slash, then redeploy.
- **Render free tier "spins down" after inactivity** → free web services
  sleep after 15 minutes idle and take ~30-50s to wake on the next request.
  This is normal for free tiers; mention it if a demo feels slow to start.
- **Worker deployed but jobs never complete in production** → confirm both
  Render services (`cortex-api` and `cortex-worker`) show the same
  `REDIS_URL` in their environment tabs — a mismatch here is the most
  common cause of "queued forever" in production.
- **`psycopg2` connection errors to Supabase** → double check you replaced
  `[YOUR-PASSWORD]` in the connection string with your actual database
  password, and that the URL starts with `postgresql://` not `postgres://`
  (SQLAlchemy needs the former; Supabase sometimes shows the latter —
  just rename the prefix if so).
