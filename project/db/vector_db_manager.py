import logging
import math
import re
import uuid
from collections import Counter

import config
from config.settings import settings
from db.retry import retry_with_backoff
from embeddings.embedding_service import embedding_dimension, get_embeddings
from vector.pinecone_manager import PineconeManager

try:
    from langchain_core.documents import Document
except ImportError:
    Document = None

logger = logging.getLogger(__name__)


class LocalVectorStore:
    """Offline subset of the vector-store API used by the app."""

    def __init__(self):
        self._documents = []

    @staticmethod
    def _tokens(text: str) -> Counter:
        return Counter(re.findall(r"[a-z0-9]+", str(text).lower()))

    @classmethod
    def _score(cls, query: str, content: str) -> float:
        query_tokens = cls._tokens(query)
        content_tokens = cls._tokens(content)
        if not query_tokens or not content_tokens:
            return 0.0
        overlap = sum(min(count, content_tokens[token]) for token, count in query_tokens.items())
        return overlap / math.sqrt(sum(query_tokens.values()) * sum(content_tokens.values()))

    def add_documents(self, documents, progress_callback=None, **kwargs):
        self._documents.extend(documents)
        if progress_callback:
            progress_callback(len(documents))
        return [doc.metadata.get("parent_id", str(i)) for i, doc in enumerate(documents)]

    def similarity_search(self, query, k=4, score_threshold=None, **kwargs):
        threshold = 0 if score_threshold is None else min(float(score_threshold), 0.05)
        scored = [
            (self._score(query, doc.page_content), doc)
            for doc in self._documents
        ]
        return [
            doc
            for score, doc in sorted(scored, key=lambda item: item[0], reverse=True)
            if score > threshold
        ][:k]

    def similarity_search_with_score(self, query, k=4, score_threshold=None, **kwargs):
        threshold = 0 if score_threshold is None else min(float(score_threshold), 0.05)
        scored = [(self._score(query, doc.page_content), doc) for doc in self._documents]
        return [
            (doc, score)
            for score, doc in sorted(scored, key=lambda item: item[0], reverse=True)
            if score > threshold
        ][:k]


class PineconeVectorStore:
    """Small LangChain-compatible adapter built on the supported Pinecone SDK."""

    _CONTENT_KEY = "page_content"

    def __init__(self, index, embedding, namespace: str):
        self.index = index
        self.embedding = embedding
        self.namespace = namespace

    @staticmethod
    def _metadata(metadata):
        """Keep only values accepted by Pinecone metadata storage."""
        clean = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                clean[key] = value
            elif isinstance(value, (list, tuple)) and all(isinstance(v, str) for v in value):
                clean[key] = list(value)
            else:
                clean[key] = str(value)
        return clean

    @staticmethod
    def _matches(response):
        return response.get("matches", []) if isinstance(response, dict) else response.matches

    def add_documents(self, documents, batch_size=None, progress_callback=None):
        if not documents:
            return []

        effective_batch_size = batch_size or getattr(config, "EMBEDDING_BATCH_SIZE", 100)
        ids = []

        for i in range(0, len(documents), effective_batch_size):
            batch_docs = documents[i : i + effective_batch_size]
            texts = [doc.page_content for doc in batch_docs]

            vectors = retry_with_backoff(lambda: self.embedding.embed_documents(texts))
            records = []
            for doc, vector in zip(batch_docs, vectors):
                # Never fall back to parent_id: sibling children share it and
                # would silently overwrite each other on upsert.
                vector_id = doc.metadata.get("id")
                if not vector_id:
                    vector_id = str(uuid.uuid4())
                    logger.warning(
                        "Child chunk from %s has no 'id' metadata; assigned %s",
                        doc.metadata.get("source", "unknown"),
                        vector_id,
                    )
                metadata = self._metadata(doc.metadata)
                metadata[self._CONTENT_KEY] = doc.page_content
                records.append({"id": vector_id, "values": vector, "metadata": metadata})
                ids.append(vector_id)

            for start in range(0, len(records), 100):
                chunk = records[start : start + 100]
                retry_with_backoff(
                    lambda: self.index.upsert(vectors=chunk, namespace=self.namespace)
                )

            if progress_callback:
                progress_callback(min(i + len(batch_docs), len(documents)))

        return ids

    def similarity_search(self, query, k=4, score_threshold=None, **kwargs):
        vector = self.embedding.embed_query(query)
        response = retry_with_backoff(
            lambda: self.index.query(
                vector=vector,
                top_k=k,
                include_metadata=True,
                namespace=self.namespace,
                filter=kwargs.get("filter"),
            )
        )
        documents = []
        for match in self._matches(response):
            score = match.get("score", 0) if isinstance(match, dict) else match.score
            if score_threshold is not None and score < score_threshold:
                continue
            metadata = dict(
                match.get("metadata", {}) if isinstance(match, dict) else match.metadata or {}
            )
            content = metadata.pop(self._CONTENT_KEY, "")
            if Document is not None:
                documents.append(Document(page_content=content, metadata=metadata))
        return documents

    def similarity_search_with_score(self, query, k=4, score_threshold=None, **kwargs):
        vector = self.embedding.embed_query(query)
        response = retry_with_backoff(
            lambda: self.index.query(
                vector=vector,
                top_k=k,
                include_metadata=True,
                namespace=self.namespace,
                filter=kwargs.get("filter"),
            )
        )
        results = []
        for match in self._matches(response):
            score = match.get("score", 0) if isinstance(match, dict) else match.score
            if score_threshold is not None and score < score_threshold:
                continue
            metadata = dict(
                match.get("metadata", {}) if isinstance(match, dict) else match.metadata or {}
            )
            content = metadata.pop(self._CONTENT_KEY, "")
            if Document is not None:
                results.append((Document(page_content=content, metadata=metadata), float(score)))
        return results

    def delete(self, ids=None, filter=None, **kwargs):
        return retry_with_backoff(
            lambda: self.index.delete(
                ids=ids, filter=filter, namespace=self.namespace, **kwargs
            )
        )


class VectorDbManager:
    _local_collections = {}

    def __init__(self):
        self.pinecone_manager = PineconeManager()
        self.__dense_embeddings = None
        if not self._use_local_fallback():
            self.__dense_embeddings = get_embeddings()

    def _use_local_fallback(self):
        return not getattr(settings, "CLOUD_BACKEND_ENABLED", False)

    def _local_collection(self, collection_name):
        if collection_name not in self._local_collections:
            self._local_collections[collection_name] = LocalVectorStore()
        return self._local_collections[collection_name]

    def _dense_vector_size(self):
        return embedding_dimension()

    def create_collection(self, collection_name):
        """Create or verify the Pinecone index/namespace."""
        if self._use_local_fallback():
            self._local_collection(collection_name)
            logger.warning("Using local in-memory vector store for collection: %s", collection_name)
            return

        expected_size = self._dense_vector_size()
        try:
            retry_with_backoff(
                lambda: self.pinecone_manager.get_index(dimension=expected_size)
            )
            logger.info("Pinecone index verified for collection: %s", collection_name)
        except Exception as e:
            logger.error("Pinecone unavailable in strict cloud mode: %s", e)
            raise

    def delete_collection(self, collection_name):
        """Clear vectors within a specific namespace."""
        if self._use_local_fallback():
            self._local_collections[collection_name] = LocalVectorStore()
            return

        try:
            index = retry_with_backoff(
                lambda: self.pinecone_manager.get_index(dimension=self._dense_vector_size())
            )
            retry_with_backoff(
                lambda: index.delete(delete_all=True, namespace=collection_name)
            )
            logger.info("Cleared all vectors in Pinecone namespace: %s", collection_name)
        except Exception as e:
            logger.error("Could not clear Pinecone namespace '%s' in strict cloud mode: %s", collection_name, e)
            raise

    def get_collection(self, collection_name):
        """Return a PineconeVectorStore instance bound to the collection/namespace."""
        if self._use_local_fallback():
            return self._local_collection(collection_name)

        try:
            index = retry_with_backoff(
                lambda: self.pinecone_manager.get_index(dimension=self._dense_vector_size())
            )
            return PineconeVectorStore(
                index=index,
                embedding=self.__dense_embeddings,
                namespace=collection_name,
            )
        except Exception as e:
            logger.error("Unable to initialize Pinecone vector store '%s' in strict cloud mode: %s", collection_name, e)
            raise
