# Agentic RAG System - Project Core Developer Documentation

This directory contains the core LangGraph multi-agent orchestration, repository databases layer, and vector index configurations.

For the main project setup, installations, and backend/frontend application execution guides, please refer to the root [README.md](../README.md).

---

## 🏗️ Core Architecture Overview

The core conversational logic is a multi-agent StateGraph orchestration defined in [project/rag_agent/graph.py](file:///c:/Users/srita/Downloads/ganesh/Agentic RAG/project/rag_agent/graph.py). 

### 1. LangGraph Multi-Agent Flow
1. **Pre-processing**: 
   * `summarize_history` extracts running context from previous messages.
   * `rewrite_query` generates semantic search questions. If the user intent is vague, the graph interrupts (`interrupt_before=["request_clarification"]`) to seek user clarification.
2. **Routing Supervisor**:
   * The `supervisor_agent` inspects the clarified, rewritten queries and issues a parallel fan-out list of target agents: `BillingAgent`, `ShippingAgent`, `TechnicalAgent`, and/or `KnowledgeAgent`.
3. **Execution Branches (Parallel)**:
   * **Billing Agent**: Evaluates refunds and invoices.
   * **Shipping Agent**: Checks tracking status and shipping estimations.
   * **Technical Agent**: Walkthrough device diagnostic steps.
   * **Knowledge Agent**: Executes search queries on Pinecone Cloud vector namespaces, fetching corresponding contextual content from the `parent_chunks` Supabase table.
4. **Answer Aggregator**:
   * Combines execution results from parallel runs into a single synthesized draft response.
5. **Safety Guardrail Node**:
   * The `safety_agent` evaluates the generated answer for compliance, hallucinations, and prompt injections.
6. **Output routing**:
   * If approved and confidence is high, the flow ends, returning the response.
   * If the confidence score is `< 0.60`, safety reports an issue, a tool fails, or the user requested human intervention, the flow routes to `human_escalation` to record a support ticket.

### 2. State & Databases Checkpointing
* **State Checkpoints**: LangGraph states are saved after every node transition using `langgraph_checkpoint_postgres.PostgresSaver`. This saves checkpoints to the Supabase PostgreSQL database under the `sessions` and checkpointer tables.
* **ORM & Database Clients**: The auto-generated **Prisma Client Python** executes SQL operations mapped in [project/schema.prisma](file:///c:/Users/srita/Downloads/ganesh/Agentic RAG/project/schema.prisma).

---

## ⚙️ Core Configuration Options

All primary agent parameters live in [project/config/__init__.py](file:///c:/Users/srita/Downloads/ganesh/Agentic RAG/project/config/__init__.py).

Key configurable attributes:

| Configuration Parameter | Purpose / Detail |
|---|---|
| `LLM_PROVIDER` | Active model provider. Options: `"google"`, `"nvidia"`, `"ollama"`, or `"openrouter"`. |
| `RETRIEVAL_SCORE_THRESHOLD` | Similarity search cut-off score (default `0.4`). Lower values increase recall; higher values prioritize precision. |
| `DEFAULT_RETRIEVAL_K` | Number of child chunks fetched per query (default `7`). |
| `MAX_TOOL_CALLS` | Hard limit on the number of cumulative tool executions permitted per query run (default `8`). |
| `MAX_ITERATIONS` | Maximum reasoning iterations allowed inside the Agent Subgraph (default `10`). |
| `MAIN_HISTORY_MESSAGES_TO_KEEP` | Number of conversation messages preserved in context memory (default `4`). |
| `BASE_TOKEN_THRESHOLD` | Message token capacity limit before automatic memory summaries are triggered (default `2000`). |

---

## 🛠️ Common Customizations

### 1. Switching LLM Providers
The application boots the model selected by `LLM_PROVIDER` inside [project/core/rag_system.py](file:///c:/Users/srita/Downloads/ganesh/Agentic RAG/project/core/rag_system.py).

* **OpenRouter (Default)**: Set `LLM_PROVIDER = "openrouter"` in `config/__init__.py`. Ensure `OPENROUTER_API_KEY` is set in your `.env`.
* **Google Gemini**: Set `LLM_PROVIDER = "google"` in `config/__init__.py`. Ensure `GOOGLE_API_KEY` is set in your `.env`.
* **NVIDIA NeMo**: Set `LLM_PROVIDER = "nvidia"` in `config/__init__.py`. Ensure `NVIDIA_API_KEY` is set in your `.env`.
* **Ollama (Local)**: Set `LLM_PROVIDER = "ollama"` in `config/__init__.py`. Ensure Ollama is running locally on port `11434`.

### 2. Customizing Chunks & Splitters
To modify how PDFs are indexed, configure the parameters in `config/__init__.py`:
* `CHILD_CHUNK_SIZE` (default `500` characters): Chunk size used to construct Pinecone vector embeddings.
* `CHILD_CHUNK_OVERLAP` (default `100` characters): Overlap budget between consecutive chunks.
* `MIN_PARENT_SIZE` (default `2000` characters) & `MAX_PARENT_SIZE` (default `4000` characters): Size bounds for the context windows stored in the database.

---

## 🔍 Observability

Traces are piped directly to your **Langfuse** dashboard if enabled in `.env`:
```env
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```
Traced items include:
* Main graph steps (`summarize_history`, `rewrite_query`, `request_clarification`, `aggregate_answers`).
* Parallel node execution via `Send()`.
* Tools call arguments and response payloads.

---

## ❌ Troubleshooting

| Error | Common Cause | Resolution |
|---|---|---|
| Prisma `P1001` / Address resolution timeout | Direct connection is blocked on IPv4 networks. | Configure `DATABASE_URL` to point to the Supabase connection pooler on port `5432`. |
| `[Errno 11001] getaddrinfo failed` | Network connectivity or hostname DNS resolution error. | Check your Internet connection and confirm settings in `project/.env`. |
| `api_key not found` | Environment variables not loaded correctly. | Verify `.env` exists in the `project/` directory and contains valid keys. |
| Graph recursion limits hit | Graph steps exceeded 50. | Adjust `GRAPH_RECURSION_LIMIT` inside `config/__init__.py`. |
