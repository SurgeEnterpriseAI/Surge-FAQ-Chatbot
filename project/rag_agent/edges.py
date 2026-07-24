from typing import List, Literal
from langgraph.graph import END
from langchain_core.messages import HumanMessage
from .graph_state import State, AgentState
from config import MAX_ITERATIONS, MAX_TOOL_CALLS
from core.execution_logger import log_route

def route_after_rewrite(state: State) -> str:
    if not state.get("questionIsClear", False):
        decision = "request_clarification"
    else:
        decision = "supervisor_agent"
    log_route("after_rewrite", decision, state)
    return decision

def route_from_supervisor(state: State) -> List[str]:
    # The knowledge agent is the only executor; the supervisor still records the
    # classified intent and its reasoning for the admin workflow view.
    decision = ["knowledge_agent"]
    log_route("from_supervisor", f"execution: {decision}", state)
    return decision

def route_after_safety(state: State) -> str:
    safety = state.get("safety_result", {})
    confidence = state.get("confidence", 1.0)
    agent_outputs = state.get("agent_outputs", [])
    messages = state.get("messages", [])
    
    # Check user explicit request
    user_explicit = False
    for m in messages:
        if isinstance(m, HumanMessage) and any(kw in str(m.content).lower() for kw in ["human", "agent", "representative", "escalate"]):
            user_explicit = True
            break
            
    # Check empty answers
    empty_answers = len(agent_outputs) == 0 or all(not str(ans.get("answer", "")).strip() for ans in agent_outputs)
    
    # Check errors
    has_errors = any("error" in str(ans.get("answer", "")).lower() for ans in agent_outputs)
    
    if (
        confidence < 0.60 
        or safety.get("approved") is False 
        or has_errors 
        or empty_answers 
        or user_explicit
    ):
        decision = "human_escalation"
    else:
        decision = "end"
        
    log_route("after_safety", decision, state)
    return decision

def route_after_orchestrator_call(state: AgentState) -> Literal["tools", "fallback_response", "collect_answer"]:
    iteration = state.get("iteration_count", 0)
    tool_count = state.get("tool_call_count", 0)

    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []

    if not tool_calls:
        decision = "collect_answer"
        log_route("after_orchestrator_call", decision, state)
        return decision

    # The counters already include the current LLM response. Allow a final
    # answer at the iteration boundary, but do not execute tool calls that
    # would exceed the configured research budget.
    if iteration >= MAX_ITERATIONS or tool_count > MAX_TOOL_CALLS:
        decision = "fallback_response"
        log_route("after_orchestrator_call", decision, state)
        return decision
    
    decision = "tools"
    log_route("after_orchestrator_call", decision, state)
    return decision

