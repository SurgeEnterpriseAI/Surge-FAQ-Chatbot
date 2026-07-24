import logging
from typing import List

import config
from config.settings import settings
from db.retry import retry_with_backoff
from openai import OpenAI

logger = logging.getLogger(__name__)


class NvidiaEmbeddings:
    """LangChain-compatible adapter for NVIDIA NIM hosted embedding models.

    Must specify input_type as "passage" for document indexing and "query" for
    search queries as required by asymmetric models like nv-embedqa-e5-v5.
    """

    def __init__(self):
        api_key = settings.NVIDIA_API_KEY
        if not api_key:
            raise ValueError(
                "NVIDIA_API_KEY is missing from environment/settings while "
                "EMBEDDING_PROVIDER is set to 'nvidia'."
            )
        self._client = OpenAI(
            base_url=config.NVIDIA_EMBED_BASE_URL,
            api_key=api_key,
        )

    def _embed(self, texts: List[str], input_type: str) -> List[List[float]]:
        if not texts:
            return []

        batch_size = getattr(config, "EMBEDDING_BATCH_SIZE", 100)
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            def call_api():
                res = self._client.embeddings.create(
                    model=config.NVIDIA_EMBED_MODEL,
                    input=batch,
                    extra_body={"input_type": input_type, "truncate": "END"},
                )
                return [item.embedding for item in res.data]

            batch_embeddings = retry_with_backoff(call_api)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts, "passage")

    def embed_query(self, text: str) -> List[float]:
        results = self._embed([text], "query")
        return results[0] if results else []


def get_embeddings():
    """Factory function returning configured Embeddings provider instance."""
    provider = str(getattr(config, "EMBEDDING_PROVIDER", "nvidia")).lower()
    if provider == "nvidia":
        return NvidiaEmbeddings()
    elif provider == "huggingface":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings

            return HuggingFaceEmbeddings(model_name=config.DENSE_MODEL)
        except ImportError as exc:
            raise RuntimeError(
                "langchain-huggingface package is required for HuggingFace embeddings"
            ) from exc
    else:
        logger.warning(
            "Unknown EMBEDDING_PROVIDER '%s'; defaulting to NvidiaEmbeddings", provider
        )
        return NvidiaEmbeddings()


def embedding_dimension() -> int:
    """Returns static embedding vector dimension without network probes."""
    return getattr(config, "EMBEDDING_DIMENSION", 1024)
