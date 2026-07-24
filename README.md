# Agentic RAG Support Desk

A full-stack, enterprise-grade multi-agent customer support application powered by **LangGraph**, **FastAPI**, **React**, **Pinecone**, and **PostgreSQL/Supabase**.

React provides a modern customer chat interface and comprehensive admin dashboard; FastAPI exposes authenticated REST, Server-Sent Events (SSE) streaming, and real-time WebSocket APIs; LangGraph coordinates multi-agent routing, iterative vector retrieval, safety checks, and automated escalation.

---

## Key Capabilities

- **Streaming Customer Chat:** High-performance SSE chat streaming featuring guest sessions, user authentication, conversation history management, message feedback, and live agent execution progress tracking.
- **Clarification-Aware LangGraph Workflow:** Intelligent preparation phase that summarizes long conversation histories, rewrites user queries into optimized search terms, and automatically interrupts to request user clarification when queries are ambiguous.
- **Supervisor-Driven Multi-Agent Architecture:** Intent classification via `supervisor_agent`, deep retrieval execution via `knowledge_agent`, answer synthesis via `aggregator`, safety and hallucination evaluation via `safety_agent`, and automatic handoff summary generation via `human_escalation`.
- **Multi-Format Document Ingestion:** Asynchronous pipeline converting PDF, DOCX, PPTX, TXT, Markdown, CSV, XLSX, and XLS documents into unified Markdown using `MarkItDown` and `PyMuPDF4LLM`, backed by parent/child chunking strategies.
- **Tabular Data Processing:** Converts CSV, XLSX, and XLS spreadheets into self-contained `## Record N` Markdown blocks with explicit column-value pairs, ensuring metadata is retained across vector chunk boundaries.
- **Vector & Parent Storage:** Pinecone cloud vector store for child embeddings paired with PostgreSQL/Supabase `ParentChunk` storage (or local JSON file fallback) for full parent context reconstruction.
- **Enterprise Multi-Tenancy & Governance:** Opt-in tenant, department, and project isolation filters (`TenantContext`), optional Cohere/BGE reranking, and enterprise administration interfaces for prompt engineering, trace replays, and cost telemetry.
- **Full Observability Suite:** Complete tracking of system metrics, request latencies, retrieval runs, LLM token usage, cost breakdowns, and real-time WebSocket event broadcasting, integrated with optional Langfuse tracing.

---

## Technology Stack

| Layer | Technologies & Libraries |
| --- | --- |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Lucide Icons |
| **Backend & API** | FastAPI, Uvicorn, Pydantic v2, `sse-starlette`, WebSockets, PyJWT |
| **Agent Orchestration** | LangGraph, LangChain Core / Community, `langgraph-checkpoint-postgres` |
| **LLM Integrations** | Configurable OpenRouter, Google Gemini, NVIDIA AI Endpoints, OpenAI, or Ollama |
| **Retrieval & Embeddings** | Pinecone Vector Database (`langchain-pinecone`), FastEmbed (`BAAI/bge-small-en-v1.5`), `Qwen/Qwen3-Embedding-0.6B` |
| **Persistence & DB** | PostgreSQL / Supabase, Prisma Client Python, `psycopg3` / `psycopg-pool` |
| **Document Processing** | MarkItDown, PyMuPDF4LLM, custom parent-child text splitters |
| **Observability** | Native Metrics Collector, WebSockets, Ragas evaluation, optional Langfuse SDK |

---

## Repository Structure

```text
.
├── backend/                  # FastAPI Application & API Services
│   ├── api/                  # API endpoints and routers
│   │   ├── routers/          # Auth, Chat, Documents, Feedback, Analytics, Health, Enterprise
│   ├── middleware/           # Error handling and CORS middleware
│   ├── services/             # Analytics, Upload, Metrics, Chat, Auth services
│   ├── app.py                # FastAPI app initialization and lifespan manager
│   ├── bootstrap.py          # Environment loading and sys.path setup
│   └── main.py               # Application entry point (Uvicorn launcher)
├── frontend/                 # React 18 + Vite User & Admin Interface
│   ├── src/
│   │   ├── components/       # UI components (Chat, Documents, Analytics, Traces, Prompts)
│   │   ├── hooks/            # React hooks for API & WebSocket consumption
│   │   ├── pages/            # Application views (Customer Chat, Admin Dashboard)
│   │   └── lib/              # API clients, Supabase auth utilities, types
├── project/                  # Core RAG & LangGraph Implementation
│   ├── agents/               # Supervisor, Aggregator, Safety, Escalation agents
│   ├── config/               # Application settings, LLM & vector configurations
│   ├── core/                 # Document Manager, RAG System, Execution Logger, Observability
│   ├── db/                   # ParentChunk storage manager (Postgres / JSON)
│   ├── enterprise/           # Tenant context manager, reranking services
│   ├── rag_agent/            # LangGraph definition, nodes, edges, state, prompts, tools
│   ├── repositories/         # Prisma-backed data repositories
│   ├── vector/               # Pinecone vector store wrappers and index managers
│   └── schema.prisma         # Relational database schema definitions
├── knowledge_base/           # Retained original uploaded document files
├── markdown_docs/            # Converted Markdown sources used for reindexing
├── parent_store/             # Local JSON parent chunk fallback storage
├── docker-compose.yml        # Development container orchestration
├── Dockerfile                # Backend production container image
├── requirements.txt          # Python dependencies specification
├── README.md                 # Primary system documentation
└── ARCHITECTURE_ANALYSIS.md  # Deep technical architecture design analysis
```

---

## Prerequisites

- **Python:** 3.11 or higher (Python 3.11+ supported)
- **Node.js:** v20+ and `npm`
- **LLM API Key:** Valid key for your chosen provider (`OPENROUTER_API_KEY`, `GOOGLE_API_KEY`, `NVIDIA_API_KEY`, or `OPENAI_API_KEY`)
- **Pinecone Account:** API Key and Index name for vector storage
- **PostgreSQL / Supabase:** Database connection URI for durable thread checkpointing, application persistence, and analytics

---

## Environment Setup

### 1. Backend Configuration (`project/.env`)

Create `project/.env` in the repository root (or inside `project/` directory):

```env
# Selected LLM Provider (openrouter, google, nvidia, openai, ollama)
LLM_PROVIDER=google
GOOGLE_API_KEY=your_google_api_key_here

# Pinecone Retrieval Setup
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX=agentic-rag-index
PINECONE_ENVIRONMENT=us-east-1

# PostgreSQL / Supabase Database Connections
DATABASE_URL=postgresql://postgres.xxx:password@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Optional Enterprise Features
RERANKER_ENABLED=false
RERANKER_PROVIDER=bge
TENANCY_ENABLED=false
DEFAULT_TENANT_ID=default

# Optional Langfuse Telemetry
LANGFUSE_ENABLED=false
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_BASE_URL=http://localhost:3000
```

### 2. Frontend Configuration (`frontend/.env`)

Copy `frontend/.env.example` to `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8001
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### 3. Database Migration & Prisma Generation

Generate the Prisma client and sync database schema definitions. 

> [!NOTE]
> On Windows, ensure Python virtual environment binaries are on your PATH so Node's Prisma launcher can resolve `prisma-client-py`:

```powershell
# Add virtual environment to PATH (Windows PowerShell)
$env:PATH = "$(Get-Location)\.venv\Scripts;" + $env:PATH

# Generate Python Prisma Client & push schema to PostgreSQL
.venv\Scripts\prisma generate --schema=project\schema.prisma
.venv\Scripts\prisma db push --schema=project\schema.prisma
```

---

## Running Locally

### Backend Server

```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt

# Start backend application server
python -m backend.main
```
The FastAPI backend runs on **`http://localhost:8001`**. OpenAPI documentation is accessible at **`http://localhost:8001/docs`**.

### Frontend Client

```powershell
cd frontend
npm ci
npm run dev
```
The Vite development server runs on **`http://localhost:5173`** and proxies `/api` calls directly to `http://127.0.0.1:8001`.

---

## Running with Docker Compose

To launch both the backend API and frontend client in containerized mode:

```powershell
docker compose up --build
```
- API Endpoint: `http://localhost:8000`
- Vite Client: `http://localhost:5173`

---

## Core System Workflows

### 1. Interactive Support Chat Flow (`POST /api/chat`)

1. **Authentication & Scope:** The user issues a request with an optional session ID and tenant context (`tenant_id`, `department_id`, `project_id`).
2. **History Summarization:** `summarize_history` compresses older dialog turns into a concise running summary while retaining recent turns.
3. **Query Rewriting & Clarification:** `rewrite_query` generates optimized search queries. If the query is ambiguous, the graph triggers `request_clarification` and enters an `interrupt` state awaiting user input.
4. **Supervisor Routing:** `supervisor_agent` inspects the request intent and routes execution to the `knowledge_agent`.
5. **Knowledge Subgraph RAG Execution:** `knowledge_agent` runs an iterative RAG subgraph (`orchestrator` -> Pinecone vector retrieval -> context compression / fallback) to synthesize candidate answers directly grounded in indexed documents.
6. **Response Aggregation:** `aggregator` formats and merges candidate agent outputs.
7. **Safety & Confidence Routing:** `safety_agent` evaluates response safety and confidence. If confidence is `< 0.60`, safety fails, or the customer requests human help, the flow transitions to `human_escalation`.
8. **SSE Event Emission:** Server-Sent Events deliver real-time progress (`session`, `agent_status`, `clarification`, `tool_call`, `tool_result`, `token`, `sources`, `safety`, `final`, `done`, `error`) to the React client.

### 2. Document Processing & Ingestion (`POST /api/upload`)

```mermaid
flowchart LR
    File[Uploaded Document] --> Detect[Format Detection]
    Detect -->|PDF / DOCX / PPTX / TXT / MD| MarkItDown[MarkItDown Conversion]
    Detect -->|CSV / XLSX / XLS| Tabular[Record-per-Row Formatter]
    MarkItDown --> Markdown[Generated Markdown]
    Tabular --> Markdown
    Markdown --> Chunker[Parent-Child Chunker]
    Chunker --> ParentStore[(Postgres ParentChunk Table)]
    Chunker --> VectorStore[(Pinecone Vector Index)]
```

- **File Formats Supported:** `.pdf`, `.docx`, `.pptx`, `.txt`, `.md`, `.csv`, `.xlsx`, `.xls` (up to 25 MiB per file).
- **Tabular Conversion:** Rows are transformed into structured `## Record N` blocks with `- **Column**: Value` fields, retaining column context across child vector chunks.
- **Parent/Child Storage:** Parent chunks (~1000–2000 chars) store complete narrative context in PostgreSQL `ParentChunk` tables, while child chunks (~200–400 chars) are embedded into Pinecone.
- **Ingestion Guardrails:** Automatically enforces `MAX_CHILD_CHUNKS_PER_DOCUMENT` (default 20,000) to prevent CPU embedding hangs, and executes atomic parent deletion rollbacks if vector indexing encounters errors.

---

## API Summary

| Category | Endpoint | Method | Description |
| --- | --- | --- | --- |
| **Health** | `/api/live` | `GET` | Service Liveness & Health Status |
| **Auth** | `/api/auth/login` | `POST` | User Login / Registration |
| | `/api/auth/guest` | `POST` | Generate Anonymous Guest Credentials |
| | `/api/auth/profile` | `GET` | Retrieve Authenticated User Profile |
| **Chat** | `/api/chat` | `POST` | Initiate SSE Streaming Support Chat |
| | `/api/history/{session_id}` | `GET` | Retrieve Conversation History |
| | `/api/conversations` | `GET` | List User Conversations |
| **Documents** | `/api/upload` | `POST` | Upload Documents for Ingestion |
| | `/api/upload/{job_id}` | `GET` | Query Asynchronous Ingestion Job Status |
| | `/api/documents` | `GET` | List Ingested Documents & Searchable Status |
| | `/api/document/{source_name}` | `DELETE` | Remove Document & Vector Index Entries |
| | `/api/reindex` | `POST` | Reindex Corpus from Saved Markdown Files |
| **Analytics & Telemetry** | `/api/analytics/overview` | `GET` | Query High-Level Analytics Metrics |
| | `/api/analytics/ws` | `WS` | Real-Time Telemetry Event Stream |
| **Enterprise** | `/api/enterprise/traces` | `GET` | Query LangGraph Node Execution Traces |
| | `/api/enterprise/prompts` | `GET` / `POST` | Manage System Prompt Versions |
| | `/api/enterprise/costs` | `GET` | Query Token & Cost Breakdown |

---

## Testing & Verification

Run the test suite using `pytest` and `npm`:

```powershell
# Run backend pytest suite
pytest backend/tests

# Run project multi-agent verification tests
python project/test_local_smoke.py

# Run frontend build & unit tests
cd frontend
npm run build
npm test
```

---

## Operational Considerations

1. **Database Fallback:** If PostgreSQL connection fails at startup, thread checkpointing falls back to `MemorySaver` and parent chunks fall back to local JSON files under `parent_store/`.
2. **Supabase Connection Pooling:** On IPv4-only networks, use Supabase's transaction pooler host (`aws-0-ap-northeast-1.pooler.supabase.com:5432`) in `DATABASE_URL` to avoid IPv6 DNS resolution issues.
3. **Grounding & Escalation:** Answers are synthesized exclusively from indexed corpus documents. If information is missing, the system escalates directly to human support instead of generating ungrounded responses.

---

## Related Documentation

- For detailed design specifications, state graphs, and persistence models, see [ARCHITECTURE_ANALYSIS.md](file:///c:/Users/srita/Downloads/ganesh/Surge%20FAQ%20Bot/Agentic-RAG-main/Agentic-RAG-main/ARCHITECTURE_ANALYSIS.md).
