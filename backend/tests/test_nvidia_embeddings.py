from unittest.mock import MagicMock, patch
import pytest

from embeddings.embedding_service import NvidiaEmbeddings, embedding_dimension, get_embeddings


def test_nvidia_embeddings_missing_key():
    with patch("config.settings.settings.NVIDIA_API_KEY", ""):
        with pytest.raises(ValueError, match="NVIDIA_API_KEY is missing"):
            NvidiaEmbeddings()


def test_nvidia_embeddings_batching_and_types():
    mock_client = MagicMock()
    
    def fake_create(model, input, extra_body):
        mock_response = MagicMock()
        mock_items = []
        for text in input:
            item = MagicMock()
            item.embedding = [0.1] * 1024
            mock_items.append(item)
        mock_response.data = mock_items
        return mock_response

    mock_client.embeddings.create.side_effect = fake_create

    with patch("config.settings.settings.NVIDIA_API_KEY", "fake_key"), patch(
        "embeddings.embedding_service.OpenAI", return_value=mock_client
    ):
        embedder = NvidiaEmbeddings()

        # Test document embedding (passage)
        docs = [f"Doc {i}" for i in range(150)]
        res_docs = embedder.embed_documents(docs)

        assert len(res_docs) == 150
        assert len(res_docs[0]) == 1024
        # Verify 2 calls for 150 docs with batch size 100
        assert mock_client.embeddings.create.call_count == 2
        
        first_call = mock_client.embeddings.create.call_args_list[0]
        assert first_call.kwargs["extra_body"]["input_type"] == "passage"
        assert first_call.kwargs["extra_body"]["truncate"] == "END"

        # Reset call count and test query embedding (query)
        mock_client.embeddings.create.reset_mock()
        res_query = embedder.embed_query("Sample question?")

        assert len(res_query) == 1024
        assert mock_client.embeddings.create.call_count == 1
        query_call = mock_client.embeddings.create.call_args_list[0]
        assert query_call.kwargs["extra_body"]["input_type"] == "query"
        assert query_call.kwargs["extra_body"]["truncate"] == "END"


def test_embedding_dimension_static():
    assert embedding_dimension() == 1024
