from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from config.settings import settings


@dataclass
class RankedDocument:
    document: object
    vector_score: float | None
    rerank_score: float | None
    original_rank: int
    rank: int


class Reranker(Protocol):
    def rerank(self, query: str, candidates: list[tuple[object, float | None]]) -> list[RankedDocument]: ...


class DisabledReranker:
    def rerank(self, query, candidates):
        return [RankedDocument(doc, score, None, index, index) for index, (doc, score) in enumerate(candidates, 1)]


class BGEReranker:
    """Lazy BGE adapter; failure safely preserves the original retrieval order."""
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def rerank(self, query, candidates):
        if not candidates:
            return []
        try:
            if self._model is None:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
            scores = self._model.predict([(query, getattr(doc, "page_content", "")) for doc, _ in candidates])
            ranked = sorted(enumerate(zip(candidates, scores), 1), key=lambda item: float(item[1][1]), reverse=True)
            return [RankedDocument(doc, vector_score, float(score), original, rank)
                    for rank, (original, ((doc, vector_score), score)) in enumerate(ranked, 1)]
        except Exception:
            return DisabledReranker().rerank(query, candidates)


class CohereReranker:
    def rerank(self, query, candidates):
        if not settings.COHERE_API_KEY:
            return DisabledReranker().rerank(query, candidates)
        try:
            import cohere
            response = cohere.ClientV2(settings.COHERE_API_KEY).rerank(
                model=settings.RERANKER_COHERE_MODEL, query=query,
                documents=[getattr(doc, "page_content", "") for doc, _ in candidates], top_n=len(candidates),
            )
            result = []
            for rank, item in enumerate(response.results, 1):
                original = item.index + 1
                doc, vector_score = candidates[item.index]
                result.append(RankedDocument(doc, vector_score, float(item.relevance_score), original, rank))
            return result
        except Exception:
            return DisabledReranker().rerank(query, candidates)


def get_reranker() -> Reranker:
    if not settings.RERANKER_ENABLED:
        return DisabledReranker()
    if settings.RERANKER_PROVIDER == "cohere":
        return CohereReranker()
    return BGEReranker(settings.RERANKER_MODEL)


def rerank_with_timing(query: str, candidates: list[tuple[object, float | None]]) -> tuple[list[RankedDocument], float]:
    started = time.perf_counter()
    return get_reranker().rerank(query, candidates), (time.perf_counter() - started) * 1000
