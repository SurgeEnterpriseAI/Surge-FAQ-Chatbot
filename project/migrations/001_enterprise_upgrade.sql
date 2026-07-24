-- Additive migration: existing tables and API data remain intact.
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS trace_id text;
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS duration_ms double precision;
CREATE INDEX IF NOT EXISTS agent_logs_trace_id_idx ON agent_logs(trace_id);
CREATE TABLE IF NOT EXISTS prompt_versions (id text primary key, key text not null, version integer not null, content text not null, active boolean not null default false, metadata jsonb, created_at timestamptz not null default now(), unique(key, version));
CREATE TABLE IF NOT EXISTS conversation_traces (id text primary key, chat_id text, thread_id text not null, tenant_id text, status text not null default 'running', started_at timestamptz not null default now(), ended_at timestamptz, metadata jsonb);
CREATE INDEX IF NOT EXISTS conversation_traces_thread_id_idx ON conversation_traces(thread_id);
CREATE TABLE IF NOT EXISTS retrieval_runs (id text primary key, trace_id text, query text not null, namespace text not null, filters jsonb, provider text, latency_ms double precision, created_at timestamptz not null default now());
CREATE TABLE IF NOT EXISTS retrieval_results (id text primary key, retrieval_run_id text not null, document_id text, parent_id text, vector_score double precision, rerank_score double precision, original_rank integer, rank integer, metadata jsonb);
CREATE TABLE IF NOT EXISTS cost_usage (id text primary key, trace_id text, agent_name text, provider text, model text, input_tokens integer not null default 0, output_tokens integer not null default 0, cost_usd double precision not null default 0, created_at timestamptz not null default now());
CREATE TABLE IF NOT EXISTS evaluation_datasets (id text primary key, name text unique not null, description text, created_at timestamptz not null default now());
CREATE TABLE IF NOT EXISTS evaluation_runs (id text primary key, dataset_id text not null, status text not null default 'pending', metrics jsonb, baseline jsonb, created_at timestamptz not null default now());
