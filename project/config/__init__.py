import os

# --- Directory Configuration ---
# We are one level deeper inside project/config, so base dir is three levels up
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

MARKDOWN_DIR = os.path.join(_BASE_DIR, "markdown_docs")
PARENT_STORE_PATH = os.path.join(_BASE_DIR, "parent_store")
QDRANT_DB_PATH = os.path.join(_BASE_DIR, "qdrant_db")
KNOWLEDGE_BASE_DIR = os.path.join(_BASE_DIR, "knowledge_base")  # Company support documents
STATE_DB_PATH = os.path.join(_BASE_DIR, "state_db.db")


# --- Qdrant Configuration ---
# Kept for migration utility backward compatibility
CHILD_COLLECTION = "document_child_chunks"
SPARSE_VECTOR_NAME = "sparse"

# --- Provider Configuration ---
# Options: "nvidia", "google", "ollama", "openrouter"
# Env-overridable so the provider can be switched without a code edit when one
# account hits its daily quota.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openrouter")

# --- Embedding Configuration ---
EMBEDDING_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "nvidia")
NVIDIA_EMBED_MODEL = os.environ.get("NVIDIA_EMBED_MODEL", "nvidia/nv-embedqa-e5-v5")
NVIDIA_EMBED_BASE_URL = "https://integrate.api.nvidia.com/v1"
EMBEDDING_DIMENSION = 1024  # matches agentic-rag-index Pinecone dimension
EMBEDDING_BATCH_SIZE = 100

# --- Model Configuration ---
# Kept for reference or backward compatibility
DENSE_MODEL = "Qwen/Qwen3-Embedding-0.6B"
SPARSE_MODEL = "Qdrant/bm25"
LLM_MODEL = "gemini-2.5-flash-lite"
JUDGE_MODEL = "ministral-3:3b-instruct-2512-q8_0"
LLM_TEMPERATURE = 0
LLM_SEED = 42

# --- Model Names per Provider ---
# llama-3.3-70b currently answers 503 on the NIM endpoint; the 8b instruct
# model responds in well under a second and supports tools + structured output.
NVIDIA_MODEL = os.environ.get("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")
GOOGLE_MODEL = "gemini-2.5-flash-lite"
OLLAMA_MODEL = "granite4.1:8b"
OPENROUTER_MODEL = "google/gemma-4-26b-a4b-it:free"

# Fallback OpenRouter / NVIDIA models if rate limits (HTTP 429) hit
OPENROUTER_FALLBACK_MODELS = [
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "google/gemma-4-31b-it:free",
]

OPENROUTER_REASONING_ENABLED = False



# --- Retrieval Configuration ---
RETRIEVAL_SCORE_THRESHOLD = 0.4
DEFAULT_RETRIEVAL_K = 7
CHILD_CHUNK_SEPARATOR = "\n\n<CHILD_CHUNK_BOUNDARY>\n\n"

# --- Agent Configuration ---
MAX_TOOL_CALLS = 8
MAX_ITERATIONS = 10
GRAPH_RECURSION_LIMIT = 50
MAIN_HISTORY_MESSAGES_TO_KEEP = 4
BASE_TOKEN_THRESHOLD = 2000
TOKEN_GROWTH_FACTOR = 0.9

# --- Terminal Execution Logging ---
EXECUTION_LOGGING_ENABLED = False
EXECUTION_LOG_MAX_CHARS = 1200
EXECUTION_LOG_USE_COLOR = True

# Enterprise defaults; Settings values remain environment configurable.
PROMPT_VERSIONING_ENABLED = True
SAFETY_MIN_CONFIDENCE = 0.70

# The supervisor's LLM call classifies intent for the admin view, but routing
# (route_from_supervisor) hardcodes the knowledge agent regardless of its
# answer. On a quota-limited key that call is ~15% of the per-question spend
# for no change in behaviour. Set to "true" to restore intent classification.
SUPERVISOR_LLM_ENABLED = os.environ.get("SUPERVISOR_LLM_ENABLED", "false").lower() == "true"

# --- Ingestion Limits ---
# High throughput cloud embeddings (NVIDIA API) process documents efficiently.
# Limit acts as safety ceiling for extremely large datasets.
MAX_CHILD_CHUNKS_PER_DOCUMENT = int(os.environ.get("MAX_CHILD_CHUNKS_PER_DOCUMENT", "100000"))


# --- Text Splitter Configuration ---
CHILD_CHUNK_SIZE = 500
CHILD_CHUNK_OVERLAP = 100
MIN_PARENT_SIZE = 2000
MAX_PARENT_SIZE = 4000
HEADERS_TO_SPLIT_ON = [
    ("#", "H1"),
    ("##", "H2"),
    ("###", "H3")
]

# --- Langfuse Observability ---
LANGFUSE_ENABLED = os.environ.get("LANGFUSE_ENABLED", "false").lower() == "true"
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
LANGFUSE_BASE_URL = os.environ.get("LANGFUSE_BASE_URL", "http://localhost:3000")
