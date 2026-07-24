from rag_agent.graph_state import State
from agents.safety_controller import run_safety_checks

def safety_agent(state: State, llm):
    aggregated_msg = state["messages"][-1].content if state.get("messages") else ""
    checks = run_safety_checks(state.get("originalQuery", ""), str(aggregated_msg), llm)
    approved = all(check["approved"] for check in checks)
    confidence = min((check["confidence"] for check in checks), default=1.0)
    issues = [f"{check['name']}: {check['reason']}" for check in checks if not check["approved"]]
    return {
        "safety_result": {
            "approved": approved,
            "confidence": confidence,
            "issues": issues,
            "checks": checks,
        },
        "confidence": confidence
    }
