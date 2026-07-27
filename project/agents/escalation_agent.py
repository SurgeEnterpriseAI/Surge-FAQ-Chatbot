import re

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from rag_agent.graph_state import State
from rag_agent.prompts import get_escalation_prompt

MAX_RELATED_ITEMS = 3
MAX_RELATED_CHARS = 140

HANDOFF_MESSAGE = (
    "I couldn't confirm an answer for this, so I've passed it to our support "
    "team. They'll follow up shortly."
)


def _related_topics(state: State) -> list[str]:
    """Readable topics from retrieved context, for the customer-facing reply.

    Sourced from retrieval rather than the drafted answer: escalation often
    means that answer was rejected, so it must not be surfaced.
    """
    safety = state.get("safety_result") or {}
    if safety.get("approved") is False:
        # The drafted answer was rejected by the safety agent; the retrieved
        # context that fed it is untrusted for direct display (may contain
        # injected or unsafe text), so nothing context-derived is shown.
        return []

    topics: list[str] = []
    for answer in state.get("agent_answers", []):
        if not isinstance(answer, dict):
            continue
        for context in answer.get("contexts", []):
            text = str(context)
            # Contexts arrive as "Parent ID: ...\nFile Name: ...\nContent: ..."
            # Only the curated Focus line is shown; raw Content is internal
            # document text and must never be forwarded to the customer.
            match = re.search(r"^Focus:\s*(.+)$", text, re.MULTILINE)
            if not match:
                continue
            topic = match.group(1).strip().rstrip("?").strip()
            if not topic:
                continue
            topic = topic[:MAX_RELATED_CHARS]
            if topic not in topics:
                topics.append(topic)
            if len(topics) >= MAX_RELATED_ITEMS:
                return topics
    return topics


def _customer_message(state: State) -> str:
    """The chat reply. The structured ticket stays internal."""
    lines = [f"⚠️ {HANDOFF_MESSAGE}"]
    topics = _related_topics(state)
    if topics:
        lines.append("")
        lines.append("What I did find that may be related:")
        lines.extend(f"- {topic}" for topic in topics)
    return "\n".join(lines)

def human_escalation(state: State, llm):
    query = state.get("originalQuery") or ""
    history = state.get("messages", [])
    agent_outputs = state.get("agent_outputs", [])
    safety = state.get("safety_result", {})
    
    actions = []
    for out in agent_outputs:
        actions.append(out.get("agent", "Unknown"))
    if not actions:
        actions.append("None")
        
    reasons = []
    if safety.get("approved") is False:
        reasons.append("Safety validation rejected proposed answer")
    if state.get("confidence", 1.0) < 0.60:
        reasons.append(f"Confidence score {state.get('confidence')} was below threshold 0.60")
    if any("error" in str(out.get("answer", "")).lower() for out in agent_outputs):
        reasons.append("A specialized tool or retrieval action encountered an error")
    if any(isinstance(m, HumanMessage) and "human" in str(m.content).lower() for m in history):
        reasons.append("Customer explicitly requested human intervention")
        
    reason_str = ", ".join(reasons) if reasons else "Unable to resolve query automatically"
    
    context = (
        f"User Query: {query}\n"
        f"Agents Run: {', '.join(actions)}\n"
        f"Safety Check Result: {safety}\n"
        f"Escalation Reason: {reason_str}\n"
    )
    
    response = llm.invoke([
        SystemMessage(content=get_escalation_prompt()),
        HumanMessage(content=context)
    ])
    
    escalation_text = response.content
    
    # Save escalation to Supabase Database
    try:
        from repositories.escalation_repository import EscalationRepository
        from core.execution_logger import active_chat_id
        from db.parent_store_manager import run_sync
        
        chat_id = active_chat_id.get()
        if chat_id:
            run_sync(EscalationRepository.create_escalation(
                chat_id=chat_id,
                reason=reason_str
            ))
            print(f"✓ Recorded human escalation case in Supabase for chat: {chat_id}")
    except Exception as e:
        print(f"⚠️ Failed to log escalation to Supabase: {e}")
    
    # escalation_text is an internal handoff ticket (see get_escalation_prompt):
    # it names the agents that ran and instructs a human what to do next, so it
    # is kept in the summary and the escalations table, never sent to the chat.
    return {
        "conversation_summary": escalation_text,
        "escalation_required": True,
        "messages": [
            AIMessage(content=_customer_message(state), name="human_escalation_message")
        ]
    }
