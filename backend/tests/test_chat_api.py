def test_chat_streams_tokens_and_final(client):
    response = client.post("/api/chat", json={"message": "What is the refund policy?"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    body = response.text
    assert "event: session" in body
    assert "event: agent_status" in body
    assert "event: token" in body
    assert "You get a refund " in body
    assert "event: sources" in body
    assert "event: safety" in body
    assert "event: final" in body
    assert "event: done" in body


def test_chat_status_covers_every_executed_node(client):
    """The trace panel renders one row per pipeline node; each must report in.

    Only the two LLM-streaming nodes used to emit agent_status, so the
    supervisor, knowledge, safety and final rows stayed greyed out forever.
    """
    import json

    response = client.post("/api/chat", json={"message": "What is the refund policy?"})
    assert response.status_code == 200

    nodes = []
    current_event = None
    for line in response.text.splitlines():
        line = line.strip()
        if line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:") and current_event == "agent_status":
            node = json.loads(line[5:].strip())["node"]
            if node not in nodes:
                nodes.append(node)

    assert nodes == [
        "summarize_history",
        "rewrite_query",
        "supervisor_agent",
        "knowledge_agent",
        "aggregator",
        "safety_agent",
        "final",
    ], nodes


def test_chat_requires_auth(unauthenticated_client):
    response = unauthenticated_client.post("/api/chat", json={"message": "hi"})
    assert response.status_code == 401
