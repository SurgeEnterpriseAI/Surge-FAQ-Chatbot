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

def create_agent_graph(llm, tools_list):
    llm_with_tools = llm.bind_tools(tools_list)
    tool_node = ToolNode(tools_list)

    from config.settings import settings
    checkpointer = None
    if settings.DATABASE_URL:
        try:
            import sys
            import asyncio
            if sys.platform == 'win32':
                try:
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                except Exception:
                    pass

            from psycopg_pool import AsyncConnectionPool
            from psycopg.rows import dict_row
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            import urllib.parse
            
            conninfo = settings.DATABASE_URL
            if "pgbouncer=" in conninfo:
                url_parts = urllib.parse.urlparse(conninfo)
                query_params = urllib.parse.parse_qs(url_parts.query)
                query_params.pop("pgbouncer", None)
                new_query = urllib.parse.urlencode(query_params, doseq=True)
                url_parts = url_parts._replace(query=new_query)
                conninfo = urllib.parse.urlunparse(url_parts)
            
            pool = AsyncConnectionPool(
                conninfo=conninfo,
                max_size=5,
                kwargs={
                    "autocommit": True, 
                    "row_factory": dict_row,
                    "prepare_threshold": None
                }
            )
            checkpointer = AsyncPostgresSaver(pool)
            
            # Run async setup synchronously
            try:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                if loop.is_running():
                    # Graph creation can occur during an ASGI request.  Do
                    # not nest Uvicorn's loop just to initialise optional
                    # persistence; MemorySaver below remains a safe fallback.
                    raise RuntimeError("Postgres checkpointer setup requires a worker thread")
                loop.run_until_complete(checkpointer.setup())
            except Exception as e:
                print(f"Warning during PostgresSaver setup: {e}")
                
            print("Connected to Supabase Postgres checkpointer.")
        except Exception as e:
            print(f"WARNING: Failed to connect to Postgres checkpointer: {e}. Falling back to in-memory checkpointing.")

    if checkpointer is None:
        print("WARNING: Using in-memory checkpointing (MemorySaver) as fallback.")
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
        return {"agent_outputs": answers}

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

