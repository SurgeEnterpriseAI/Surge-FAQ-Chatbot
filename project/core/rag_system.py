import uuid
from langchain_google_genai import ChatGoogleGenerativeAI
import config
from db.vector_db_manager import VectorDbManager
from db.parent_store_manager import ParentStoreManager
from document_chunker import DocumentChunker
from rag_agent.tools import ToolFactory
from rag_agent.graph import create_agent_graph
from core.observability import Observability

class RAGSystem:

    def __init__(self, collection_name=config.CHILD_COLLECTION):
        self.collection_name = collection_name
        self.vector_db = VectorDbManager()
        self.parent_store = ParentStoreManager()
        self.chunker = DocumentChunker()
        self.observability = Observability()
        self.agent_graph = None
        self.thread_id = str(uuid.uuid4())
        self.recursion_limit = config.GRAPH_RECURSION_LIMIT

    def initialize(self):
        self.vector_db.create_collection(self.collection_name)
        collection = self.vector_db.get_collection(self.collection_name)

        provider = getattr(config, "LLM_PROVIDER", "google").lower()
        if provider == "google":
            llm = ChatGoogleGenerativeAI(
                model=getattr(config, "GOOGLE_MODEL", "gemini-2.5-flash-lite"),
                temperature=config.LLM_TEMPERATURE,
            )
        elif provider == "nvidia":
            import os
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            llm = ChatNVIDIA(
                model=getattr(config, "NVIDIA_MODEL", "meta/llama-3.3-70b-instruct"),
                api_key=os.environ.get("NVIDIA_API_KEY"),
                temperature=config.LLM_TEMPERATURE,
                top_p=0.7,
                max_tokens=1024,
            )
        elif provider == "ollama":
            from langchain_ollama import ChatOllama
            llm = ChatOllama(
                model=getattr(config, "OLLAMA_MODEL", "granite4.1:8b"),
                temperature=config.LLM_TEMPERATURE,
                seed=config.LLM_SEED,
            )
        elif provider == "openrouter":
            import os
            from langchain_openai import ChatOpenAI
            
            model_name = getattr(config, "OPENROUTER_MODEL", "google/gemma-4-26b-a4b-it:free")
            api_key = os.environ.get("OPENROUTER_API_KEY")
            
            extra_body = {}
            if getattr(config, "OPENROUTER_REASONING_ENABLED", False):
                extra_body["reasoning"] = {"enabled": True}
                
            primary_llm = ChatOpenAI(
                model=model_name,
                openai_api_key=api_key,
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=config.LLM_TEMPERATURE,
                max_tokens=2048,
                extra_body=extra_body if extra_body else None,
            )

            # Build rate-limit fallback LLMs (NVIDIA free models & Direct Google Gemini)
            fallbacks = []
            fallback_models = getattr(
                config,
                "OPENROUTER_FALLBACK_MODELS",
                ["nvidia/nemotron-3-nano-30b-a3b:free", "nvidia/nemotron-nano-9b-v2:free", "google/gemma-4-31b-it:free"]
            )
            for fb_model in fallback_models:
                if fb_model != model_name:
                    fallbacks.append(
                        ChatOpenAI(
                            model=fb_model,
                            openai_api_key=api_key,
                            openai_api_base="https://openrouter.ai/api/v1",
                            temperature=config.LLM_TEMPERATURE,
                            max_tokens=2048,
                        )
                    )

            google_key = os.environ.get("GOOGLE_API_KEY")
            if google_key:
                fallbacks.append(
                    ChatGoogleGenerativeAI(
                        model=getattr(config, "GOOGLE_MODEL", "gemini-2.5-flash-lite"),
                        google_api_key=google_key,
                        temperature=config.LLM_TEMPERATURE,
                    )
                )

            if fallbacks:
                llm = primary_llm.with_fallbacks(fallbacks)
            else:
                llm = primary_llm
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        tools = ToolFactory(collection).create_tools()
        self.agent_graph = create_agent_graph(llm, tools)

        # Auto-ingest company knowledge base documents on startup
        # from core.document_manager import DocumentManager
        # from utils import ingest_knowledge_base
        # doc_manager = DocumentManager(self)
        # ingest_knowledge_base(doc_manager)

    def get_config(self):
        cfg = {"configurable": {"thread_id": self.thread_id}, "recursion_limit": self.recursion_limit}
        handler = self.observability.get_handler()
        if handler:
            cfg["callbacks"] = [handler]
        return cfg

    def reset_thread(self):
        try:
            self.agent_graph.checkpointer.delete_thread(self.thread_id)
        except Exception as e:
            print(f"Warning: Could not delete thread {self.thread_id}: {e}")
        self.thread_id = str(uuid.uuid4())
