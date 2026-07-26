from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from functools import partial

import config
from .graph_state import State, AgentState
from core.execution_logger import logged_node
from .nodes import (
    collect_answer,
    compress_context,
    fallback_response,
    orchestrator,
    request_clarification,
    rewrite_query,
    should_compress_context,
    summarize_history,
)
from .edges import (
    route_after_orchestrator_call,
    route_after_rewrite,
    route_from_supervisor,
    route_after_safety,
)

# Import new multi-agent desk agents
from agents.supervisor_agent import supervisor_agent
from agents.aggregator import aggregator
from agents.safety_agent import safety_agent
from agents.escalation_agent import human_escalation

# Connection-string parameters Prisma understands but libpq does not. The same
# DATABASE_URL feeds both Prisma and psycopg, and psycopg aborts the connection
# with "invalid URI query parameter" rather than ignoring what it cannot use.
_PRISMA_ONLY_PARAMS = frozenset({
    "pgbouncer",
    "prepared_statements",
    "connection_limit",
    "pool_timeout",
    "socket_timeout",
    "statement_cache_size",
    "schema",
    "sslidentity",
    "sslpassword",
})


def _normalize_conninfo(conninfo: str) -> str:
    """Strip Prisma-only query parameters so libpq accepts the URL.

    Everything else is left alone — genuine libpq parameters such as ``sslmode``
    and ``connect_timeout`` must survive.
    """
    import urllib.parse

    url_parts = urllib.parse.urlparse(conninfo)
    if not url_parts.query:
        return conninfo

    query_params = urllib.parse.parse_qs(url_parts.query)
    kept = {k: v for k, v in query_params.items() if k.lower() not in _PRISMA_ONLY_PARAMS}
    if len(kept) == len(query_params):
        return conninfo

    new_query = urllib.parse.urlencode(kept, doseq=True)
    return urllib.parse.urlunparse(url_parts._replace(query=new_query))


def build_postgres_checkpointer():
    """Build an AsyncPostgresSaver whose pool is deliberately left closed.

    An AsyncConnectionPool binds to the event loop that opens it, so it must be
    opened on the loop that will later use it. Constructing it with the default
    ``open=True`` from the worker thread that builds the RAG system fails with
    "AsyncConnectionPool open with no running loop", and opening it on a
    throwaway loop would bind the pool to a loop that is then discarded.

    Opening and ``setup()`` are therefore deferred to ``open_postgres_checkpointer``,
    which the FastAPI lifespan awaits on Uvicorn's own loop.

    Returns ``(checkpointer, pool)``, or ``(None, None)`` when Postgres is not
    configured or its driver is missing.
    """
    from config.settings import settings

    if not settings.DATABASE_URL:
        return None, None

    try:
        from psycopg_pool import AsyncConnectionPool
        from psycopg.rows import dict_row
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    except ImportError as e:
        print(f"WARNING: Postgres checkpointer packages are unavailable ({e}).")
        return None, None

    pool = AsyncConnectionPool(
        conninfo=_normalize_conninfo(settings.DATABASE_URL),
        max_size=5,
        open=False,
        kwargs={
            "autocommit": True,
            "row_factory": dict_row,
            "prepare_threshold": None,
        },
    )
    return AsyncPostgresSaver(pool), pool


async def open_postgres_checkpointer(timeout: float = 15.0):
    """Open the checkpointer pool and create its tables on the running loop.

    Returns ``(checkpointer, pool)`` when Postgres is usable, else ``(None, None)``
    so the caller can fall back to in-memory checkpointing.
    """
    checkpointer, pool = build_postgres_checkpointer()
    if checkpointer is None:
        return None, None

    try:
        await pool.open(wait=True, timeout=timeout)
        await checkpointer.setup()
    except Exception as e:
        print(f"WARNING: Failed to connect to Postgres checkpointer: {e}. Falling back to in-memory checkpointing.")
        try:
            await pool.close()
        except Exception:
            pass
        return None, None

    print("Connected to Postgres checkpointer.")
    return checkpointer, pool


def create_agent_graph(llm, tools_list, checkpointer=None):
    llm_with_tools = llm.bind_tools(tools_list)
    tool_node = ToolNode(tools_list)

    if checkpointer is None:
        print("WARNING: Using in-memory checkpointing (MemorySaver); paused chats will not survive a restart.")
        checkpointer = MemorySaver()

    print("Compiling agent graph...")
    agent_builder = StateGraph(AgentState)
    agent_builder.add_node("orchestrator", logged_node("agent.orchestrator", partial(orchestrator, llm_with_tools=llm_with_tools)))
    agent_builder.add_node("tools", tool_node)
    agent_builder.add_node("compress_context", logged_node("agent.compress_context", partial(compress_context, llm=llm)))
    agent_builder.add_node("fallback_response", logged_node("agent.fallback_response", partial(fallback_response, llm=llm)))
    agent_builder.add_node("should_compress_context", logged_node("agent.should_compress_context", should_compress_context))
    agent_builder.add_node("collect_answer", logged_node("agent.collect_answer", collect_answer))

    agent_builder.add_edge(START, "orchestrator")
    agent_builder.add_conditional_edges("orchestrator", route_after_orchestrator_call, {"tools": "tools", "fallback_response": "fallback_response", "collect_answer": "collect_answer"})
    agent_builder.add_edge("tools", "should_compress_context")
    agent_builder.add_edge("compress_context", "orchestrator")
    agent_builder.add_edge("fallback_response", "collect_answer")
    agent_builder.add_edge("collect_answer", END)

    agent_subgraph = agent_builder.compile()

    # Knowledge Agent wrapper node to run existing agent_subgraph
    def knowledge_agent_node(state: State):
        queries = state.get("rewrittenQuestions") or [state.get("originalQuery") or ""]
        answers = []
        # The subgraph's agent_answers carry the retrieved contexts. Dropping
        # them left the main graph with an empty agent_answers, so the caller
        # never emitted a "sources" event and the UI showed no citations.
        collected_answers = []
        for idx, query in enumerate(queries):
            sub_state = {
                "question": query,
                "question_index": idx,
                "messages": [],
                "detected_intent": state.get("detected_intent", {}),
                "tool_results": state.get("tool_results", [])
            }
            res = agent_subgraph.invoke(sub_state)
            for ans in res.get("agent_answers", []):
                collected_answers.append(ans)
                answers.append({
                    "agent": "KnowledgeAgent",
                    "answer": ans.get("answer", ""),
                    "success": True
                })
        if not answers:
            answers.append({
                "agent": "KnowledgeAgent",
                "answer": "No relevant documents found in support system.",
                "success": False
            })
        return {"agent_outputs": answers, "agent_answers": collected_answers}

    graph_builder = StateGraph(State)

    # Query preparation nodes
    graph_builder.add_node("summarize_history", logged_node("main.summarize_history", partial(summarize_history, llm=llm)))
    graph_builder.add_node("rewrite_query", logged_node("main.rewrite_query", partial(rewrite_query, llm=llm)))
    graph_builder.add_node("request_clarification", logged_node("main.request_clarification", request_clarification))

    # Support desk nodes
    graph_builder.add_node("supervisor_agent", logged_node("main.supervisor_agent", partial(supervisor_agent, llm=llm)))
    graph_builder.add_node("knowledge_agent", logged_node("main.knowledge_agent", knowledge_agent_node))
    graph_builder.add_node("aggregator", logged_node("main.aggregator", partial(aggregator, llm=llm)))
    graph_builder.add_node("safety_agent", logged_node("main.safety_agent", partial(safety_agent, llm=llm)))
    graph_builder.add_node("human_escalation", logged_node("main.human_escalation", partial(human_escalation, llm=llm)))

    # Memory / query preparation loops
    graph_builder.add_edge(START, "summarize_history")
    graph_builder.add_edge("summarize_history", "rewrite_query")
    graph_builder.add_conditional_edges("rewrite_query", route_after_rewrite)
    graph_builder.add_edge("request_clarification", "rewrite_query")
    
    # Supervisor routing
    graph_builder.add_conditional_edges(
        "supervisor_agent",
        route_from_supervisor,
        {"knowledge_agent": "knowledge_agent"},
    )

    # Fan-in
    graph_builder.add_edge("knowledge_agent", "aggregator")

    # Aggregated response processing
    graph_builder.add_edge("aggregator", "safety_agent")
    
    # Safety Check Routing
    graph_builder.add_conditional_edges(
        "safety_agent",
        route_after_safety,
        {
            "human_escalation": "human_escalation",
            "end": END
        }
    )
    
    # Escalation Handoff
    graph_builder.add_edge("human_escalation", END)

    # Compile the graph
    agent_graph = graph_builder.compile(checkpointer=checkpointer, interrupt_before=["request_clarification"])

    print("Multi-Agent Support Desk graph compiled successfully.")
    return agent_graph

