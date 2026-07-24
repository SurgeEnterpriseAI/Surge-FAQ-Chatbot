"""Lightweight API tests: the LangGraph graph and the LLM are always faked —
no model call, no Pinecone, no Supabase."""
from backend.bootstrap import bootstrap

bootstrap()

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk

from backend.app import create_app
from backend.dependencies import get_current_user, get_doc_manager, get_rag_system

TEST_USER = {"user_id": "guest-testtest", "email": "guest-testtest@guest.local", "is_guest": True}


class FakeStateSnapshot:
    def __init__(self, values=None, next_=()):
        self.values = values or {}
        self.next = next_


class FakeGraph:
    """Scripted stand-in for the compiled LangGraph graph (no LLM involved)."""

    def __init__(self):
        self.final_values = {
            "messages": [AIMessage(content="You get a refund within 30 days.")],
            "safety_result": {"approved": True, "confidence": 0.98, "issues": []},
            "agent_answers": [
                {"index": 0, "question": "refund policy?", "answer": "30 days", "contexts": ["Refunds ..."]}
            ],
            "confidence": 0.9,
            "escalation_required": False,
            "detected_intent": "billing",
            "conversation_summary": "",
        }
        self.checkpointer = None

    async def aget_state(self, config):
        return FakeStateSnapshot(values=self.final_values)

    async def aupdate_state(self, config, values):
        pass

    async def astream(self, stream_input, config=None, stream_mode=None):
        yield (
            AIMessageChunk(content='{"is_clear": true, "questions": ["What is the refund policy?"]}'),
            {"langgraph_node": "rewrite_query"},
        )
        yield (AIMessageChunk(content="You get a refund "), {"langgraph_node": "aggregator"})
        yield (AIMessageChunk(content="within 30 days."), {"langgraph_node": "aggregator"})


class FakeObservability:
    def get_handler(self):
        return None

    def flush(self):
        pass


class FakeRAGSystem:
    def __init__(self):
        self.agent_graph = FakeGraph()
        self.recursion_limit = 50
        self.observability = FakeObservability()
        self.collection_name = "test_collection"


class FakeDocManager:
    def __init__(self):
        class _RS:
            pass

        self.rag_system = _RS()

    def add_documents(self, paths, progress_callback=None, uploaded_by=None, version=None):
        if progress_callback:
            progress_callback(1.0, "Processing test.txt")
        return len(paths), 0, []


@pytest.fixture()
def fake_rag_system():
    return FakeRAGSystem()


@pytest.fixture()
def client(fake_rag_system, monkeypatch):
    async def _noop(*args, **kwargs):
        return None

    from repositories.chat_repository import ChatRepository

    for method in (
        "create_chat",
        "get_or_create_session",
        "add_message",
        "save_safety_report",
        "save_conversation_summary",
    ):
        monkeypatch.setattr(ChatRepository, method, staticmethod(_noop))

    app = create_app(init_resources=False)
    app.dependency_overrides[get_rag_system] = lambda: fake_rag_system
    app.dependency_overrides[get_doc_manager] = FakeDocManager
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def unauthenticated_client(fake_rag_system):
    app = create_app(init_resources=False)
    app.dependency_overrides[get_rag_system] = lambda: fake_rag_system
    with TestClient(app) as test_client:
        yield test_client
