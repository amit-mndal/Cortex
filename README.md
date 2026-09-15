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


<img width="1813" height="887" alt="image" src="https://github.com/user-attachments/assets/ea0488a5-4ef4-4c96-8c01-860e4e496fa4" />


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
- A free Groq API key 

## 2. Get your free API key 

## 3. Start Redis

From the project root (where `docker-compose.yml` lives):

```bash
docker compose up -d
```

This starts Redis on `localhost:6379` — used as both the Celery message
broker and the pub/sub channel for live progress streaming. No config
needed, no signup, completely free.


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
