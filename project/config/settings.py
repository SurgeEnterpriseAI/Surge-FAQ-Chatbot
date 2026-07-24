import os
from pathlib import Path
from dotenv import load_dotenv

# Load env file from the project directory (this file lives in project/config/)
_BASE_DIR = Path(__file__).resolve().parent.parent
_env_loaded = False


def _ensure_env():
    global _env_loaded
    if not _env_loaded:
        load_dotenv(_BASE_DIR / ".env", override=True)
        _env_loaded = True


class _Settings:
    """Lazy settings — each attribute is resolved from os.environ at access time
    so that load_dotenv() calls made by bootstrap always take effect regardless
    of import order."""

    _DEFAULTS = {
        "OPENAI_API_KEY": "",
        "GOOGLE_API_KEY": "",
        "NVIDIA_API_KEY": "",
        "OPENROUTER_API_KEY": "",
        "PINECONE_API_KEY": "",
        "PINECONE_INDEX": "agentic-rag-index",
        "PINECONE_ENVIRONMENT": "us-east-1",
        "SUPABASE_URL": "",
        "SUPABASE_KEY": "",
        "DATABASE_URL": "",
        "REQUEST_TIMEOUT": "30",
        "MAX_RETRIES": "3",
        "CLOUD_BACKEND_ENABLED": "false",
        "ENTERPRISE_FEATURES_ENABLED": "true",
        "RERANKER_ENABLED": "true",
        "RERANKER_PROVIDER": "bge",
        "RERANKER_MODEL": "BAAI/bge-reranker-base",
        "RERANKER_COHERE_MODEL": "rerank-v3.5",
        "COHERE_API_KEY": "",
        "RETRIEVAL_CANDIDATE_K": "20",
        "RETRIEVAL_RERANKED_K": "5",
        "TENANCY_ENABLED": "false",
        "TENANT_NAMESPACE_TEMPLATE": "{base}",
        "DEFAULT_TENANT_ID": "",
        "OBSERVABILITY_REDACT_PII": "true",
        "GRACEFUL_SHUTDOWN_SECONDS": "20",
        "EVALUATION_JUDGE_ENABLED": "false",
        "MODEL_INPUT_COST_PER_MILLION": "0",
        "MODEL_OUTPUT_COST_PER_MILLION": "0",
    }

    # Boolean keys — returned as bool instead of str
    _BOOL_KEYS = {
        "CLOUD_BACKEND_ENABLED",
        "ENTERPRISE_FEATURES_ENABLED",
        "RERANKER_ENABLED",
        "TENANCY_ENABLED",
        "OBSERVABILITY_REDACT_PII",
        "EVALUATION_JUDGE_ENABLED",
    }

    # Integer keys
    _INT_KEYS = {
        "REQUEST_TIMEOUT",
        "MAX_RETRIES",
        "RETRIEVAL_CANDIDATE_K",
        "RETRIEVAL_RERANKED_K",
        "GRACEFUL_SHUTDOWN_SECONDS",
    }

    # Float keys
    _FLOAT_KEYS = {
        "MODEL_INPUT_COST_PER_MILLION",
        "MODEL_OUTPUT_COST_PER_MILLION",
    }

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        _ensure_env()
        default = self._DEFAULTS.get(name, "")
        raw = os.environ.get(name, default)
        if name in self._BOOL_KEYS:
            return raw.lower() == "true"
        if name in self._INT_KEYS:
            return int(raw)
        if name in self._FLOAT_KEYS:
            return float(raw)
        return raw

    def validate(self):
        missing = []
        if not self.PINECONE_API_KEY:
            missing.append("PINECONE_API_KEY")
        if not self.DATABASE_URL:
            missing.append("DATABASE_URL")

        if missing:
            print(f"WARNING: Missing core configuration in environment variables: {', '.join(missing)}")
            return False
        return True


settings = _Settings()

