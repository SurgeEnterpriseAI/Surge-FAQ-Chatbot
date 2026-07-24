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


def test_chat_requires_auth(unauthenticated_client):
    response = unauthenticated_client.post("/api/chat", json={"message": "hi"})
    assert response.status_code == 401
