"""The escalation ticket is internal; only a handoff message reaches the chat."""
from agents.escalation_agent import _customer_message, _related_topics

CONTEXTS = [
    "Parent ID: medquad_p6815\nFile Name: medquad.csv\n"
    "Content: Question: What are the symptoms of Glucose transporter type 1 deficiency syndrome ?\n"
    "Focus: Glucose transporter type 1 deficiency syndrome",
    "Parent ID: medquad_p2974\nFile Name: medquad.csv\n"
    "Content: Question: What are the symptoms of Glycogen storage disease type 13 ?\n"
    "Focus: Glycogen storage disease type 13",
]


def _state(contexts):
    return {"agent_answers": [{"index": 0, "question": "q", "contexts": contexts}]}


def test_customer_message_lists_related_topics():
    msg = _customer_message(_state(CONTEXTS))
    assert "passed it to our support team" in msg
    assert "- Glucose transporter type 1 deficiency syndrome" in msg
    assert "- Glycogen storage disease type 13" in msg


def test_customer_message_never_leaks_internal_ticket_fields():
    """These headings come from get_escalation_prompt and are agent-only."""
    msg = _customer_message(_state(CONTEXTS))
    for internal in ("Actions Taken", "Reason For Escalation", "Suggested Next Step",
                     "KnowledgeAgent", "Safety Check Result", "Intent:"):
        assert internal not in msg, internal


def test_customer_message_without_context_is_still_valid():
    assert "support team" in _customer_message({"agent_answers": []})


def test_related_topics_tolerates_malformed_entries():
    assert _related_topics({"agent_answers": [{"contexts": ["junk", ""]}, "not-a-dict"]}) == []


def test_related_topics_are_capped_and_deduped():
    dupes = CONTEXTS * 5
    assert len(_related_topics(_state(dupes))) == 2
