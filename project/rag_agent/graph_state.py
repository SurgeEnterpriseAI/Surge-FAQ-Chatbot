from typing import List, Annotated, Set
from langgraph.graph import MessagesState
import operator

def accumulate_or_reset(existing: List[dict], new: List[dict]) -> List[dict]:
    if new and any(item.get('__reset__') for item in new):
        return []
    return existing + new

def accumulate_tool_results(existing: List[dict], new: List[dict]) -> List[dict]:
    if new and any(item.get('__reset__') for item in new):
        return []
    return existing + new

def set_union(a: Set[str], b: Set[str]) -> Set[str]:
    return a | b

def append_unique(existing: List[str], new: List[str]) -> List[str]:
    return list(dict.fromkeys(existing + new))

class State(MessagesState):
    """State for main agent graph"""
    questionIsClear: bool = False
    conversation_summary: str = ""
    originalQuery: str = ""
    pendingQuery: str = ""
    pendingClarifications: List[str] = []
    rewrittenQuestions: List[str] = []
    agent_answers: Annotated[List[dict], accumulate_or_reset] = []
    detected_intent: dict = {}
    tool_decision: dict = {}
    tool_results: Annotated[List[dict], accumulate_tool_results] = []
    
    # New Multi-Agent State Fields
    supervisor_decision: dict = {}
    selected_agents: List[str] = []
    agent_outputs: Annotated[List[dict], accumulate_or_reset] = []
    safety_result: dict = {}
    confidence: float = 1.0
    escalation_required: bool = False
    trace_id: str = ""
    node_metrics: Annotated[List[dict], accumulate_or_reset] = []


class AgentState(MessagesState):
    """State for individual agent subgraph"""
    question: str = ""
    question_index: int = 0
    context_summary: str = ""
    retrieval_keys: Annotated[Set[str], set_union] = set()
    retrieved_contexts: Annotated[List[str], append_unique] = []
    final_answer: str = ""
    agent_answers: List[dict] = []
    tool_call_count: Annotated[int, operator.add] = 0
    iteration_count: Annotated[int, operator.add] = 0
    detected_intent: dict = {}
    tool_results: List[dict] = []
