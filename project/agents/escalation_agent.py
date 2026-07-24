from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from rag_agent.graph_state import State
from rag_agent.prompts import get_escalation_prompt

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
    
    return {
        "conversation_summary": escalation_text,
        "escalation_required": True,
        "messages": [AIMessage(content=f"⚠️ {escalation_text}", name="human_escalation_message")]
    }
