"""Async, framework-agnostic port of project/core/chat_interface.py.

Streams the existing LangGraph agent graph and emits typed events (rendered
as SSE by the chat router) instead of Gradio message dicts. The graph, agents,
tools, and persistence layer are reused unchanged; only the output format and
the sync/async style differ:
- graph access uses aget_state/aupdate_state/astream to match the
  AsyncPostgresSaver checkpointer,
- repositories are awaited directly instead of via run_sync/nest_asyncio,
- the thread_id comes from the caller (one per conversation) instead of the
  single RAGSystem.thread_id instance attribute.
"""
import json
import re
import uuid
from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from core.execution_logger import (
    active_chat_id,
    active_thread_id,
    log_chat_end,
    log_chat_start,
    log_error,
)
from repositories.chat_repository import ChatRepository

# Nodes whose streamed LLM output is surfaced verbatim in the trace panel.
SYSTEM_NODES = {"summarize_history", "rewrite_query"}
FINAL_RESPONSE_NODES = {"aggregator", "human_escalation"}

# Every node the main graph can execute. The trace panel renders a row per
# node, so a missing title here leaves that row unlabelled.
NODE_TITLES = {
    "summarize_history": "Chat History Summary",
    "rewrite_query": "Query Analysis & Rewriting",
    "request_clarification": "Clarification Requested",
    "supervisor_agent": "Supervisor Routing",
    "knowledge_agent": "Knowledge Retrieval",
    "aggregator": "Response Aggregation",
    "safety_agent": "Safety & Hallucination Check",
    "human_escalation": "Human Escalation",
    "final": "Final Response",
}

# Bookkeeping keys LangGraph emits on the updates stream; not real nodes.
INTERNAL_UPDATE_KEYS = {"__start__", "__end__", "__interrupt__", "__metadata__"}

SYSTEM_NODE_TITLES = NODE_TITLES  # retained for existing callers

TOOL_RESULT_PREVIEW_CHARS = 300


def parse_json_block(buffer: str) -> dict | None:
    match = re.search(r"\{.*\}", buffer, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group())
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _event(name: str, data: dict) -> dict:
    return {"event": name, "data": data}


class ChatService:

    def __init__(self, rag_system):
        self.rag_system = rag_system

    def _build_config(self, session_id: str) -> dict:
        cfg: dict[str, Any] = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": self.rag_system.recursion_limit,
        }
        handler = self.rag_system.observability.get_handler()
        if handler:
            cfg["callbacks"] = [handler]
        return cfg

    async def stream(self, message: str, session_id: str | None = None, user_id: str | None = None) -> AsyncIterator[dict]:
        graph = self.rag_system.agent_graph
        if graph is None:
            yield _event("error", {"code": "not_initialized", "message": "System not initialized"})
            return

        message = message.strip()
        session_id = session_id or str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        active_thread_id.set(session_id)
        active_chat_id.set(session_id)
        yield _event("session", {"session_id": session_id})

        try:
            title = message[:40] + "..." if len(message) > 40 else message
            await ChatRepository.create_chat(chat_id=session_id, user_id=user_id, title=title)
            await ChatRepository.get_or_create_session(thread_id=session_id, user_id=user_id, chat_id=session_id)
            await ChatRepository.add_message(chat_id=session_id, role="user", content=message)
        except Exception as e:
            print(f"Warning: Could not log session initialization to DB: {e}")

        config = self._build_config(session_id)
        current_state = await graph.aget_state(config)
        log_chat_start(message, session_id, bool(current_state.next))

        try:
            if current_state.next:
                # Graph is paused on the clarification interrupt: feed the reply
                # into state and resume by streaming with no new input.
                await graph.aupdate_state(config, {"messages": [HumanMessage(content=message)]})
                stream_input = None
            else:
                stream_input = {"messages": [HumanMessage(content=message)], "trace_id": trace_id}

            system_node_buffer: dict[str, str] = {}
            streamed_final: dict[str, str] = {}
            tool_call_names: dict[str, str] = {}
            tools_dict: dict[str, dict] = {}
            last_clarification: str | None = None

            executed_order: list[str] = []

            def _step_event(node_name: str, status: str) -> dict:
                """Build an agent_status event, carrying any buffered LLM output."""
                buffer = system_node_buffer.get(node_name)
                parsed = parse_json_block(buffer) if buffer else None
                return _event("agent_status", {
                    "node": node_name,
                    "title": NODE_TITLES.get(node_name, node_name.replace("_", " ").title()),
                    "status": status,
                    "parsed": parsed,
                    "content": buffer if (buffer and parsed is None) else None,
                })

            # "updates" reports every node that runs, including ones that never
            # stream tokens (supervisor, knowledge, safety). "messages" alone
            # only ever saw the two LLM-streaming nodes, so the trace panel
            # left the rest of the pipeline permanently greyed out.
            async for mode, payload in graph.astream(
                stream_input, config=config, stream_mode=["updates", "messages"]
            ):
                if mode == "updates":
                    for node_name in (payload or {}):
                        if node_name in INTERNAL_UPDATE_KEYS:
                            continue
                        if node_name not in executed_order:
                            executed_order.append(node_name)
                        yield _step_event(node_name, "done")
                    continue

                chunk, metadata_graph = payload
                node = metadata_graph.get("langgraph_node", "")

                if node in SYSTEM_NODES:
                    if isinstance(chunk, AIMessageChunk) and chunk.content:
                        system_node_buffer[node] = system_node_buffer.get(node, "") + chunk.content
                        buffer = system_node_buffer[node]
                        parsed = parse_json_block(buffer)
                        yield _event("agent_status", {
                            "node": node,
                            "title": SYSTEM_NODE_TITLES.get(node, node),
                            "status": "streaming",
                            "parsed": parsed,
                            "content": buffer if parsed is None else None,
                        })
                        if node == "rewrite_query" and parsed and not parsed.get("is_clear"):
                            clarification = (parsed.get("clarification_needed") or "").strip()
                            if clarification and clarification.lower() != "no" and clarification != last_clarification:
                                last_clarification = clarification
                                yield _event("clarification", {"question": clarification})

                elif getattr(chunk, "tool_calls", None):
                    for tc in chunk.tool_calls:
                        if tc.get("id") and tc["id"] not in tool_call_names:
                            tool_call_names[tc["id"]] = tc.get("name", "")
                            tools_dict[tc["id"]] = {
                                "id": tc["id"],
                                "name": tc.get("name", ""),
                                "args": tc.get("args", {}),
                            }
                            yield _event("tool_call", {
                                "id": tc["id"],
                                "name": tc.get("name", ""),
                                "args": tc.get("args", {}),
                            })

                elif isinstance(chunk, ToolMessage):
                    content = str(chunk.content)
                    if chunk.tool_call_id in tools_dict:
                        tools_dict[chunk.tool_call_id]["result"] = {
                            "id": chunk.tool_call_id,
                            "name": tool_call_names.get(chunk.tool_call_id, ""),
                            "preview": content[:TOOL_RESULT_PREVIEW_CHARS],
                            "truncated": len(content) > TOOL_RESULT_PREVIEW_CHARS,
                        }
                    yield _event("tool_result", {
                        "id": chunk.tool_call_id,
                        "name": tool_call_names.get(chunk.tool_call_id, ""),
                        "preview": content[:TOOL_RESULT_PREVIEW_CHARS],
                        "truncated": len(content) > TOOL_RESULT_PREVIEW_CHARS,
                    })

                elif isinstance(chunk, (AIMessage, AIMessageChunk)) and chunk.content and node in FINAL_RESPONSE_NODES:
                    content = str(chunk.content)
                    # A final node emits its LLM's token chunks *and* the complete
                    # AIMessage it returns. Streaming both duplicated the answer,
                    # so skip a whole message that repeats what was already sent.
                    if isinstance(chunk, AIMessage) and not isinstance(chunk, AIMessageChunk):
                        if content in streamed_final.get(node, ""):
                            continue
                    streamed_final[node] = streamed_final.get(node, "") + content
                    yield _event("token", {"content": content})

            final_state = await graph.aget_state(config)
            log_chat_end(getattr(final_state, "values", final_state))
            values = getattr(final_state, "values", {}) or {}

            answers = [
                {"index": a.get("index"), "question": a.get("question"), "contexts": a.get("contexts", [])}
                for a in values.get("agent_answers", [])
                if isinstance(a, dict)
            ]
            if answers:
                yield _event("sources", {"answers": answers})

            safety = values.get("safety_result") or {}
            if safety:
                yield _event("safety", {
                    "approved": safety.get("approved", True),
                    "confidence": safety.get("confidence", 1.0),
                    "issues": safety.get("issues", []),
                })

            final_reply = ""
            assistant_msgs = [
                m for m in values.get("messages", [])
                if isinstance(m, AIMessage) or (hasattr(m, "role") and m.role == "assistant")
            ]
            if assistant_msgs:
                final_reply = str(assistant_msgs[-1].content)

            # Closes the last row of the trace timeline. Without it the final
            # step only ever completes on the escalation branch.
            if "final" not in executed_order:
                executed_order.append("final")
            yield _step_event("final", "done")

            yield _event("final", {
                "trace_id": values.get("trace_id", trace_id),
                "content": final_reply,
                "confidence": values.get("confidence"),
                "escalation_required": values.get("escalation_required", False),
                "intent": values.get("detected_intent"),
            })

            # Compile final assistant message metadata. Built from the executed
            # node order so a reloaded conversation replays the same timeline.
            agent_steps = []
            for node_name in executed_order:
                content = system_node_buffer.get(node_name)
                parsed = parse_json_block(content) if content else None
                agent_steps.append({
                    "node": node_name,
                    "title": NODE_TITLES.get(node_name, node_name.replace("_", " ").title()),
                    "status": "done",
                    "parsed": parsed,
                    "content": content if (content and parsed is None) else None
                })
            
            msg_metadata = {
                "agentSteps": agent_steps,
                "tools": list(tools_dict.values()),
                "sources": answers,
                "safety": {
                    "approved": safety.get("approved", True),
                    "confidence": safety.get("confidence", 1.0),
                    "issues": safety.get("issues", []),
                } if safety else None,
                "escalationRequired": values.get("escalation_required", False)
            }

            try:
                if final_reply:
                    await ChatRepository.add_message(
                        chat_id=session_id,
                        role="assistant",
                        content=final_reply,
                        metadata=msg_metadata
                    )

                from backend.services.analytics_service import AnalyticsService
                from backend.api.routers.analytics_ws import broadcast_event

                await AnalyticsService.log_event(
                    event_type="ai_request",
                    session_id=session_id,
                    metadata={
                        "confidence": values.get("confidence"),
                        "escalation_required": values.get("escalation_required", False),
                        "intent": values.get("detected_intent"),
                        "steps_count": len(agent_steps)
                    }
                )
                await broadcast_event("ai_request", f"AI response completed for session {session_id}.", "info")

                if safety:
                    approved = safety.get("approved", True)
                    await ChatRepository.save_safety_report(
                        chat_id=session_id,
                        approved=approved,
                        confidence=safety.get("confidence", 1.0),
                        issues=safety.get("issues", []),
                    )

                    if not approved:
                        await AnalyticsService.log_event(
                            event_type="safety_intervention",
                            session_id=session_id,
                            metadata={"issues": safety.get("issues", []), "confidence": safety.get("confidence")}
                        )
                        await broadcast_event(
                            "safety_intervention",
                            f"Safety intervention triggered on session {session_id} due to issues: {', '.join(safety.get('issues', []))}",
                            "high"
                        )

                        if any("injection" in str(issue).lower() for issue in safety.get("issues", [])):
                            await AnalyticsService.log_event(
                                event_type="prompt_injection_blocked",
                                session_id=session_id,
                                metadata={"issues": safety.get("issues", [])}
                            )
                            await broadcast_event(
                                "prompt_injection_blocked",
                                f"Prompt injection block executed on session {session_id}!",
                                "high"
                            )

                if values.get("escalation_required", False):
                    await AnalyticsService.log_event(
                        event_type="escalation_triggered",
                        session_id=session_id,
                        metadata={"reason": "Escalation requested by agent"}
                    )
                    await broadcast_event(
                        "escalation_triggered",
                        f"Conversation {session_id} escalated to human agent.",
                        "medium"
                    )

                summary = values.get("conversation_summary", "")
                if summary:
                    await ChatRepository.save_conversation_summary(chat_id=session_id, summary=summary)
            except Exception as e:
                print(f"Warning: Could not log final outputs to DB: {e}")

            yield _event("done", {})

        except Exception as e:
            log_error("chat", e)
            yield _event("error", {"code": "chat_failed", "message": str(e)})
