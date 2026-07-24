import time

from langchain_core.tools import tool
import config
from db.parent_store_manager import ParentStoreManager
from config.settings import settings
from core.execution_logger import log_error, log_tool_end, log_tool_start
from enterprise.reranking import rerank_with_timing
from enterprise.tenant import current_tenant


def _record_vector_latency(duration_ms: float) -> None:
    """Report measured search latency for system metrics, if the API is loaded."""
    try:
        from backend.services.metrics_collector import latency_tracker

        latency_tracker.record("vector", duration_ms)
    except Exception:
        # project/ is usable without the FastAPI layer (notebooks, scripts).
        pass


class ToolFactory:
    
    def __init__(self, collection):
        self.collection = collection
        self.parent_store_manager = ParentStoreManager()
    
    def _search_child_chunks(self, query: str, limit: int = config.DEFAULT_RETRIEVAL_K) -> str:
        """Search document excerpts for evidence related to the user question.

        Use this as the first retrieval step. Results include parent IDs, file
        names, and short child-chunk excerpts. If excerpts are relevant but too
        fragmented to answer confidently, call retrieve_parent_chunks with the
        returned parent_id.
        
        Args:
            query: Focused search query with concrete keywords from the question.
            limit: Maximum number of child chunks to return.
        """
        tenant = current_tenant()
        candidate_limit = max(limit, settings.RETRIEVAL_CANDIDATE_K) if settings.RERANKER_ENABLED else limit
        log_tool_start("search_child_chunks", {"query": query, "limit": limit, "candidate_limit": candidate_limit,
                                                 "tenant_filter": tenant.metadata_filter()})
        try:
            search_started = time.perf_counter()
            search = getattr(self.collection, "similarity_search_with_score", None)
            if search:
                candidates = search(query, k=candidate_limit, score_threshold=config.RETRIEVAL_SCORE_THRESHOLD,
                                    filter=tenant.metadata_filter() or None)
            else:
                candidates = [(doc, None) for doc in self.collection.similarity_search(
                    query, k=candidate_limit, score_threshold=config.RETRIEVAL_SCORE_THRESHOLD,
                    filter=tenant.metadata_filter() or None)]
            _record_vector_latency((time.perf_counter() - search_started) * 1000)
            reranked, latency_ms = rerank_with_timing(query, candidates)
            reranked = reranked[:limit if not settings.RERANKER_ENABLED else min(limit, settings.RETRIEVAL_RERANKED_K)]
            results = [item.document for item in reranked]
            if not results:
                output = "NO_RELEVANT_CHUNKS"
                log_tool_end("search_child_chunks", output)
                return output

            output = config.CHILD_CHUNK_SEPARATOR.join([
                f"Parent ID: {doc.metadata.get('parent_id', '')}\n"
                f"File Name: {doc.metadata.get('source', '')}\n"
                f"Content: {doc.page_content.strip()}"
                for doc in results
            ])
            log_tool_end("search_child_chunks", {"output": output, "reranking_latency_ms": round(latency_ms, 2),
                "documents": [{"parent_id": item.document.metadata.get("parent_id"), "source": item.document.metadata.get("source"),
                                "vector_score": item.vector_score, "rerank_score": item.rerank_score,
                                "original_rank": item.original_rank, "rank": item.rank} for item in reranked]})
            return output

        except Exception as e:
            log_error("search_child_chunks", e)
            output = f"RETRIEVAL_ERROR: {str(e)}"
            log_tool_end("search_child_chunks", output)
            return output
    
    def _retrieve_parent_chunks(self, parent_id: str) -> str:
        """Retrieve the full parent chunk for a relevant child search result.

        Use this only after search_child_chunks returns a relevant parent_id and
        the child excerpt needs more surrounding context. Do not call this for
        parent IDs already available in compressed context.
    
        Args:
            parent_id: Parent chunk ID returned by search_child_chunks.
        """
        log_tool_start("retrieve_parent_chunks", {"parent_id": parent_id})
        try:
            parent = self.parent_store_manager.load_content(parent_id)
            if not parent:
                output = "NO_PARENT_DOCUMENT"
                log_tool_end("retrieve_parent_chunks", output)
                return output

            output = (
                f"Parent ID: {parent.get('parent_id', 'n/a')}\n"
                f"File Name: {parent.get('metadata', {}).get('source', 'unknown')}\n"
                f"Content: {parent.get('content', '').strip()}"
            )
            log_tool_end("retrieve_parent_chunks", output)
            return output

        except Exception as e:
            log_error("retrieve_parent_chunks", e)
            output = f"PARENT_RETRIEVAL_ERROR: {str(e)}"
            log_tool_end("retrieve_parent_chunks", output)
            return output
    
    def create_tools(self) -> list:
        """Create and return the list of tools."""
        search_tool = tool("search_child_chunks")(self._search_child_chunks)
        retrieve_tool = tool("retrieve_parent_chunks")(self._retrieve_parent_chunks)
        
        return [search_tool, retrieve_tool]
