def handoff_to_human(reason: str) -> str:
    """Initiate a handoff to a human support agent.
    
    Args:
        reason: The reason for the handoff (e.g. customer frustration, request too complex).
    """
    if not reason:
        reason = "Customer requested human support."
    return f"Handoff initiated: A human support agent is joining the chat shortly because: {reason}."
