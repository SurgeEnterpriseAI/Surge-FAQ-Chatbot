from pydantic import BaseModel, Field
from typing import List, Dict
import time
import config
from langchain_core.messages import SystemMessage, HumanMessage
from rag_agent.graph_state import State
from rag_agent.prompts import get_supervisor_prompt

class SupervisorDecision(BaseModel):
    agents: List[str] = Field(
        default_factory=lambda: ["KnowledgeAgent"],
        description="List of selected agent names. Choices: ['KnowledgeAgent']"
    )
    reason: str = Field(..., description="Reason for the routing decision.")
    intent: str = Field(default="general_support")
    agent_confidence: Dict[str, float] = Field(default_factory=dict)

def supervisor_agent(state: State, llm):
    started = time.perf_counter()
    query = state.get("originalQuery") or (state["messages"][-1].content if state.get("messages") else "")

    if not config.SUPERVISOR_LLM_ENABLED:
        # Routing ignores this decision, so skip the call rather than spend a
        # request from the daily quota on a label. See config.SUPERVISOR_LLM_ENABLED.
        return {
            "supervisor_decision": {
                "agents": ["KnowledgeAgent"],
                "reason": "Routing is fixed to the knowledge agent; LLM classification disabled.",
                "intent": "general_support",
                "agent_confidence": {"KnowledgeAgent": 1.0},
                "routing_latency_ms": round((time.perf_counter() - started) * 1000, 2),
            },
            "selected_agents": ["KnowledgeAgent"],
        }

    llm_with_structure = llm.with_structured_output(SupervisorDecision)
    response = llm_with_structure.invoke([
        SystemMessage(content=get_supervisor_prompt()),
        HumanMessage(content=f"Customer Query: {query}")
    ])

    return {
        "supervisor_decision": {
            "agents": ["KnowledgeAgent"],
            "reason": response.reason,
            "intent": response.intent,
            "agent_confidence": response.agent_confidence,
            "routing_latency_ms": round((time.perf_counter() - started) * 1000, 2),
        },
        "selected_agents": ["KnowledgeAgent"]
    }
