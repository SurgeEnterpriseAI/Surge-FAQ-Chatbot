# Agentic RAG Support Desk

A support chatbot that answers questions using only your own documents.

You upload files (PDF, Word, PowerPoint, text, Markdown, CSV, Excel). The system turns them into text, splits them up, and stores them so they can be searched by meaning. When someone asks a question, a small team of AI helpers searches those documents, writes an answer, and checks it. If the answer cannot be trusted, the chat is passed to a human instead of guessing.

The bundled knowledge base in this repo is a medical FAQ set (MedQuAD), and the admin console is labelled "Medical FAQ Admin", but nothing in the code is tied to that subject — any set of documents works.

The app has three parts:

- A **React** website — a chat page for users and an admin console.
- A **FastAPI** server — logins, chat streaming, uploads, and analytics.
- A **LangGraph** workflow — the AI helpers that decide, search, write, and check.

---

## What It Can Do

- **Chat that types as it thinks.** The answer streams back piece by piece over SSE (Server-Sent Events). You also see each step of the workflow as it runs, and every search the AI made.
- **Asks you to explain when your question is unclear.** Before searching, the system shortens long chat histories and rewrites your question into better search terms. If the question is too vague, the workflow pauses and asks you what you mean, then carries on from where it stopped.
- **A team of AI helpers.** `supervisor_agent` records the intent, `knowledge_agent` searches, `aggregator` writes the answer, `safety_agent` runs five checks on it, and `human_escalation` writes a handover note for a real person.
- **Two-step search.** A first search finds short, focused snippets. If a snippet looks right but is too small to answer from, the AI pulls the bigger chunk it came from. That way the answer is written from full context, not fragments.
- **Reads many file types.** PDF, DOCX and PPTX go through `MarkItDown`. TXT and MD are read as-is. CSV and Excel get their own converter that keeps column names attached to every value.
- **Five safety checks in parallel.** Groundedness, prompt injection, PII, hallucination, and policy compliance. Two of them (injection and PII) use fast pattern matching before spending an AI call.
- **Hands over instead of guessing.** If the safety check fails, confidence drops below 0.60, the search errored, or the user asks for a person, the chat is escalated. The user gets a short handover message; the detailed ticket stays internal.
- **Admin console.** Upload and delete documents, rebuild the index, and view request volume, confidence, latency, and cost charts.
- **Runs when things are down.** If the database or Pinecone is unavailable, the system falls back to in-memory storage and local JSON files rather than crashing.

---

## What It Is Built With

| Part | Tools |
| --- | --- |
| **Website** | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router, Recharts, Framer Motion |
| **Server & API** | FastAPI, Uvicorn, Pydantic v2, `sse-starlette`, WebSockets, PyJWT |
| **AI workflow** | LangGraph 1.2, LangChain Core, `langgraph-checkpoint-postgres` |
| **AI models** | OpenRouter (default), Google Gemini, NVIDIA AI Endpoints, or Ollama |
| **Embeddings** | NVIDIA `nvidia/nv-embedqa-e5-v5` (1024 dimensions), with a HuggingFace option |
| **Search** | Pinecone serverless (cosine), optional BGE or Cohere re-ranking |
| **Databases** | PostgreSQL / Supabase via Prisma Client Python, `psycopg3` + `psycopg-pool` |
| **File reading** | MarkItDown, pandas (Excel), Python `csv` |
| **Monitoring** | Built-in metrics collector, WebSocket broadcast, optional Langfuse |

---

## Folder Layout

```text
.
├── backend/                  # The FastAPI server
│   ├── api/routers/          # health, auth, chat, documents, feedback,
│   │                         # analytics, analytics_ws, enterprise
│   ├── middleware/           # Error handlers
│   ├── schemas/              # Request and response shapes
│   ├── services/             # chat, upload, auth, analytics, conversation,
│   │                         # metrics collector
│   ├── tests/                # pytest suite
│   ├── app.py                # Builds the app, startup and shutdown steps
│   ├── bootstrap.py          # Loads .env, fixes import paths, Windows loop fix
│   ├── dependencies.py       # Shared FastAPI dependencies (auth, doc manager)
│   └── main.py               # Starts Uvicorn on port 8001
├── frontend/                 # React 18 + Vite website
│   └── src/
│       ├── components/       # chat, documents, feedback, layout, admin
│       ├── hooks/            # useChatStream, useAuth, useDocuments, useAnalytics
│       ├── pages/            # ChatPage, AdminPage, LoginPage, ProfilePage
│       └── lib/              # API client, SSE reader, Supabase, types
├── project/                  # The RAG and LangGraph brain
│   ├── agents/               # supervisor, aggregator, safety, escalation
│   ├── config/               # Tunable constants + env-backed settings
│   ├── core/                 # RAGSystem, DocumentManager, logging, observability
│   ├── db/                   # Parent chunk store, vector store manager, retry
│   ├── document_processing/  # File-to-Markdown conversion
│   ├── embeddings/           # NVIDIA embedding client
│   ├── enterprise/           # Tenant isolation, re-ranking
│   ├── loaders/              # MedQuAD one-row-per-QA loader
│   ├── rag_agent/            # The graph: nodes, edges, state, prompts, tools
│   ├── repositories/         # Database access through Prisma
│   ├── tools/                # Standalone tool helpers
│   ├── vector/               # Pinecone client and index creation
│   ├── document_chunker.py   # Parent/child splitting
│   └── schema.prisma         # 23 database tables
├── knowledge_base/           # Source documents you keep by hand
├── markdown_docs/            # Markdown used by the offline batch chunker
├── parent_store/             # JSON fallback when the database is off
├── docker-compose.yml        # Runs API + website in containers
├── Dockerfile                # Backend container image
└── requirements.txt          # Python packages
```

---

## What You Need First

- **Python** 3.11 or newer
- **Node.js** v20 or newer, with `npm`
- **An AI provider key** — `OPENROUTER_API_KEY` (default), or `GOOGLE_API_KEY`, or `NVIDIA_API_KEY`, or a local Ollama install
- **An NVIDIA key** (`NVIDIA_API_KEY`) for embeddings, unless you switch `EMBEDDING_PROVIDER` to `huggingface`
- **A Pinecone account** — the index is created for you if it does not exist
- **PostgreSQL or Supabase** — stores chats, documents, parent chunks, and lets a paused chat resume later

---

## Setup

### 1. Backend settings (`project/.env`)

The server reads `project/.env`. Create it there — not in the repo root.

```env
# Which AI provider to use: openrouter, google, nvidia, or ollama
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_key_here

# Embeddings (nvidia is the default; "huggingface" runs a local model instead)
EMBEDDING_PROVIDER=nvidia
NVIDIA_API_KEY=your_nvidia_key_here

# Pinecone
PINECONE_API_KEY=your_pinecone_key_here
PINECONE_INDEX=agentic-rag-index
PINECONE_ENVIRONMENT=us-east-1

# Database
DATABASE_URL=postgresql://postgres.xxx:password@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# IMPORTANT: must be true to actually use Pinecone and the Postgres parent store.
# Left false, the app runs on an in-memory keyword search and local JSON files.
CLOUD_BACKEND_ENABLED=true

# Re-ranking (on by default; set false to skip it)
RERANKER_ENABLED=true
RERANKER_PROVIDER=bge          # or "cohere" (then set COHERE_API_KEY)
RETRIEVAL_CANDIDATE_K=20       # how many to fetch before re-ranking
RETRIEVAL_RERANKED_K=5         # how many survive re-ranking

# Multi-tenant isolation (off by default)
TENANCY_ENABLED=false
DEFAULT_TENANT_ID=

# Optional Langfuse tracing
LANGFUSE_ENABLED=false
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_BASE_URL=http://localhost:3000
```

> **`CLOUD_BACKEND_ENABLED` is the switch that matters most.** It defaults to `false`, which is handy for offline testing but means no real vector search and no database-backed chunk storage. Set it to `true` for anything real.

### 2. Frontend settings (`frontend/.env`)

```env
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

The dev server forwards `/api` and `/ws` to `http://127.0.0.1:8001`, so no API URL is needed in development.

### 3. Set up the database tables

> [!NOTE]
> On Windows, put the virtual environment on your PATH first, or Node's Prisma launcher will not find `prisma-client-py`.

```powershell
$env:PATH = "$(Get-Location)\.venv\Scripts;" + $env:PATH

.venv\Scripts\prisma generate --schema=project\schema.prisma
.venv\Scripts\prisma db push --schema=project\schema.prisma
```

---

## Running It on Your Machine

### The backend

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m backend.main
```

The server listens on **`http://localhost:8001`**, with API docs at **`http://localhost:8001/docs`**.

Startup takes roughly 25–30 seconds (loading the RAG system and connecting to the database). If the RAG system fails to start, the server still comes up in degraded mode: chat and upload return 503, everything else works.

### The website

```powershell
cd frontend
npm ci
npm run dev
```

Opens on **`http://localhost:5173`**.

---

## Running It with Docker Compose

```powershell
docker compose up --build
```

- API: `http://localhost:8000` (reads a `.env` in the repo root, not `project/.env`)
- Website: `http://localhost:5173` (waits for the API health check to pass first)

---

## How the Main Flows Work

### 1. A chat message (`POST /api/chat`)

1. **Scope.** The request carries the message, an optional `session_id`, and optional `tenant_id`, `department_id`, and `project_id`.
2. **Resume or start.** If this session was paused waiting for a clarification, the reply is fed into the paused workflow and it continues. Otherwise a fresh run starts.
3. **Shorten the history.** `summarize_history` merges older turns into a running summary and keeps the last few messages as they are.
4. **Rewrite, or ask back.** `rewrite_query` produces clear standalone search questions. If the question is still unclear, the workflow stops at `request_clarification` and sends a `clarification` event.
5. **Route.** `supervisor_agent` records the intent and sends the work to `knowledge_agent`. (Routing is fixed to the knowledge agent, so the classification AI call is skipped by default — set `SUPERVISOR_LLM_ENABLED=true` to turn it back on.)
6. **Search.** For each rewritten question, an inner workflow searches Pinecone, optionally pulls bigger parent chunks, shrinks the collected text if it grows too large, and drafts an answer. It stops after 10 rounds or 8 searches, whichever comes first.
7. **Write.** `aggregator` merges the drafts into one reply.
8. **Check.** `safety_agent` runs five checks at once and takes the lowest confidence score.
9. **Finish or hand over.** Below 0.60 confidence, a failed safety check, a retrieval error, an empty answer, or a user asking for a person all send the chat to `human_escalation`.

Events sent to the browser along the way: `session`, `agent_status`, `clarification`, `tool_call`, `tool_result`, `token`, `sources`, `safety`, `final`, `done`, `error`.

### 2. Uploading a document (`POST /api/upload`)

```mermaid
flowchart LR
    File[Uploaded file] --> Temp[Copy to a temp folder]
    Temp --> Detect[Check the file type]
    Detect -->|PDF / DOCX / PPTX| MarkItDown[MarkItDown]
    Detect -->|TXT / MD| Direct[Read as-is]
    Detect -->|CSV / XLSX / XLS| Records[One record per row]
    MarkItDown --> Markdown[Markdown text]
    Direct --> Markdown
    Records --> Markdown
    Markdown --> Chunker[Split into parent and child chunks]
    Chunker --> ParentStore[(Postgres parent_chunks)]
    Chunker --> VectorStore[(Pinecone)]
    Chunker --> Cleanup[Delete the temp folder]
```

- **File types:** `.pdf`, `.docx`, `.pptx`, `.txt`, `.md`, `.csv`, `.xlsx`, `.xls`, up to 25 MiB each.
- **Nothing is left on disk.** The upload is copied to a temp folder, processed, and the folder is deleted. Your documents live in Postgres and Pinecone, not in a local folder.
- **Spreadsheets** become one `## Record N` block per row with `- **Column**: Value` lines. A normal Markdown table loses its header row when chunked, so a middle chunk would be bare values with no column names — one record per row avoids that.
- **MedQuAD and CSV files** take a shortcut: each question/answer row becomes exactly one parent and one child, with no further splitting.
- **Chunk sizes:** parents are 2,000–4,000 characters; children are 500 characters with 100 characters of overlap.
- **Limits:** a file producing more than `MAX_CHILD_CHUNKS_PER_DOCUMENT` chunks (100,000 by default) is rejected. MedQuAD and CSV files skip that check.
- **Undo on failure:** if embedding fails after the parent chunks were saved, those rows are deleted again and the document is marked failed.
- **Duplicates** are skipped by filename.

The upload runs in the background. Poll `GET /api/upload/{job_id}` for progress. Job state is written to `project/uploads/jobs_registry.json`, so a job caught by a restart shows up as `interrupted` rather than silently vanishing.

---

## API Endpoints

| Group | Endpoint | Method | What it does |
| --- | --- | --- | --- |
| **Health** | `/api/live` | `GET` | Is the process alive (no external checks) |
| | `/api/health` | `GET` | Graph, database, and vector store status |
| | `/api/ready` | `GET` | Same, plus a single ready/not-ready answer |
| **Auth** | `/api/auth/login` | `POST` | Log in |
| | `/api/auth/guest` | `POST` | Get anonymous guest access |
| | `/api/auth/logout` | `POST` | Log out |
| | `/api/auth/profile` | `GET` | Current user's profile |
| **Chat** | `/api/chat` | `POST` | Streaming chat (SSE) |
| | `/api/history/{session_id}` | `GET` | One conversation, owner only |
| | `/api/conversations` | `GET` | List your conversations |
| | `/api/conversations/{session_id}` | `DELETE` | Delete one, owner only |
| **Feedback** | `/api/feedback` | `POST` | Rate an answer |
| | `/api/escalate` | `POST` | Ask for a human |
| **Documents** | `/api/upload` | `POST` | Upload files |
| | `/api/upload/{job_id}` | `GET` | Upload progress |
| | `/api/documents` | `GET` | List documents |
| | `/api/document/{source_name}` | `DELETE` | Delete a document and its vectors |
| | `/api/reindex` | `POST` | Rebuild the vector index |
| **Analytics** (admin) | `/api/analytics/ai-performance` | `GET` | Requests, confidence, trends |
| | `/api/analytics/agent-performance` | `GET` | Per-agent numbers |
| | `/api/analytics/business-metrics` | `GET` | Business-level numbers |
| | `/api/analytics/knowledge-base` | `GET` | Document and chunk counts |
| | `/api/analytics/system` | `GET` | Latency and memory |
| | `/api/analytics/users` | `GET` | Active users |
| | `/api/analytics/security` | `GET` | Safety and injection events |
| | `/api/analytics/predictions` | `GET` | Cost and forecast |
| | `/api/analytics/admin/reindex` | `POST` | Rebuild the index |
| | `/api/analytics/admin/clear-cache` | `POST` | Clear caches |
| | `/api/analytics/admin/restart-services` | `POST` | Restart the pool |
| | `/api/analytics/admin/logs` | `GET` | Recent log lines |
| | `/api/analytics/export/csv` | `GET` | Export as CSV |
| | `/api/analytics/export/pdf-data` | `GET` | Export data for a PDF |
| **Enterprise** (admin) | `/api/enterprise/traces` | `GET` | Past workflow runs |
| | `/api/enterprise/traces/{thread_id}` | `GET` | One run, step by step |
| | `/api/enterprise/prompts` | `GET` / `POST` | View and save prompt versions |
| | `/api/enterprise/costs` | `GET` | Token use and cost |
| **Live events** | `/ws/analytics/events` | `WS` | Broadcast of safety, escalation, and request events |

The enterprise endpoints and the WebSocket work, but the current React app does not call them — they are for admin tooling and scripts.

---

## Testing

```powershell
# Backend tests
pytest backend/tests

# A quick end-to-end check of the workflow
python project/test_local_smoke.py

# Frontend build and tests
cd frontend
npm run build
npm test
```

---

## Things to Keep in Mind

1. **`CLOUD_BACKEND_ENABLED=false` silently changes the engine.** Search becomes in-memory word overlap and parent chunks go to `parent_store/*.json`. Fine for a smoke test, wrong for real answers.
2. **If Postgres is unreachable**, the workflow keeps its state in memory instead, so a paused chat cannot be resumed after a restart. Watch the first startup line: `Connected to Postgres checkpointer.` means it worked.
3. **One `DATABASE_URL` serves two clients.** Prisma accepts extras like `pgbouncer=true` and `prepared_statements=false`; psycopg refuses to connect with them. They are stripped automatically before psycopg sees the URL, so you can keep the URL Supabase gives you. Real libpq settings such as `sslmode` are left untouched.
4. **On IPv4-only networks**, use a Supabase pooler host (`...pooler.supabase.com`), otherwise IPv6 name lookups fail. Port 6543 is the transaction pooler, 5432 the session pooler; both work.
5. **On Windows the server needs a selector event loop.** `backend.main` passes one to uvicorn, because psycopg cannot run on the ProactorEventLoop uvicorn would otherwise pick. Start the server with `python -m backend.main` rather than a bare `uvicorn backend.app:app`, or Postgres persistence will fall back to memory.
6. **Deleting a document needs a Pinecone tier that supports delete-by-filter.** If yours does not, the API returns 501 and tells you to run `POST /api/reindex`.
7. **Reindex rebuilds from the database, not from files.** It clears the Pinecone namespace and re-embeds from the stored parent chunks, so the parent store must be intact.
8. **Admin access** is granted to the user id `mock-admin-id` or the email `admin@example.com`, or to a user row with the admin flag set.
9. **Answers come only from your documents.** When they are not enough, the chat is handed to a human.
10. **A leftover server no longer blocks startup.** Closing the terminal without pressing Ctrl+C leaves the previous run alive and still holding port 8001, which used to fail the next start with `WinError 10048`. Startup now spots that orphan, stops it, and takes the port — you will see `Port 8001 is held by an earlier run of this server (PID ...); stopping it.` It only ever stops a Python process running this same app; anything else on the port is reported and left alone. Set `API_PORT_RECLAIM=0` to disable, or `API_PORT` to use a different port.

---

## More Reading

For the deeper design — the graphs, the events, the storage rules, and the known limits — see [ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md).
