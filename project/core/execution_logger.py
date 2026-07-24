from __future__ import annotations

from datetime import datetime
from datetime import timezone
from pprint import pformat
from typing import Any
import contextvars
import asyncio

import config

# Context variables to track the active thread and chat in a thread-safe manner
active_thread_id = contextvars.ContextVar("active_thread_id", default="default-thread")
active_chat_id = contextvars.ContextVar("active_chat_id", default=None)
active_trace_id = contextvars.ContextVar("active_trace_id", default=None)

COLORS = {
    "blue": "\033[94m",
    "cyan": "\033[96m",
    "green": "\033[92m",
    "magenta": "\033[95m",
    "red": "\033[91m",
    "yellow": "\033[93m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}

def run_sync(coro):
    """Execute coroutine synchronously."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        # Never re-enter the FastAPI event loop.  Persisting telemetry is
        # best-effort, so schedule it and let the request continue normally.
        return loop.create_task(coro)
    return loop.run_until_complete(coro)

def save_log_to_db(node_name: str, event_type: str, payload: Any):
    """Write agent execution log to Supabase."""
    thread_id = active_thread_id.get()
    chat_id = active_chat_id.get()
    
    from repositories.chat_repository import ChatRepository
    from database.supabase_client import prisma_main_loop
    
    envelope = {
        "trace_id": active_trace_id.get(),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    coro = ChatRepository.log_agent_action(
        thread_id=thread_id,
        node_name=node_name,
        event_type=event_type,
        payload=envelope,
        chat_id=chat_id
    )
    
    try:
        # If the main uvicorn thread loop is running and we are on a background worker loop/thread,
        # delegate database execution to the main loop to prevent connection corruption.
        if prisma_main_loop and prisma_main_loop.is_running():
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                current_loop = None
                
            if current_loop is not prisma_main_loop:
                asyncio.run_coroutine_threadsafe(coro, prisma_main_loop)
                return
                
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            run_sync(coro)
    except Exception as e:
        # Fails silently to prevent crashing application on database issues
        print(f"⚠️ Agent Logging failed: {e}")

def _enabled() -> bool:
    return bool(getattr(config, "EXECUTION_LOGGING_ENABLED", True))


def _color(text: str, color: str) -> str:
    if not getattr(config, "EXECUTION_LOG_USE_COLOR", True):
        return text
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


def _truncate(value: Any, max_chars: int | None = None) -> str:
    text = "" if value is None else str(value)
    limit = max_chars or getattr(config, "EXECUTION_LOG_MAX_CHARS", 1200)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... [truncated {len(text) - limit} chars]"


def _message_role(message: Any) -> str:
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage, RemoveMessage
    if isinstance(message, HumanMessage):
        return "human"
    if isinstance(message, AIMessage):
        return "ai"
    if isinstance(message, ToolMessage):
        return "tool"
    if isinstance(message, SystemMessage):
        return "system"
    if isinstance(message, RemoveMessage):
        return "remove"
    return message.__class__.__name__


def _message_preview(message: Any) -> dict[str, Any]:
    from langchain_core.messages import RemoveMessage
    preview = {
        "type": _message_role(message),
        "id": getattr(message, "id", None),
    }

    if isinstance(message, RemoveMessage):
        return preview

    content = getattr(message, "content", "")
    if content:
        preview["content"] = _truncate(content)

    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        preview["tool_calls"] = [
            {
                "name": call.get("name"),
                "args": call.get("args"),
                "id": call.get("id"),
            }
            for call in tool_calls
        ]

    tool_name = getattr(message, "name", None)
    if tool_name:
        preview["name"] = tool_name

    tool_call_id = getattr(message, "tool_call_id", None)
    if tool_call_id:
        preview["tool_call_id"] = tool_call_id

    return preview


def _messages_preview(messages: list[Any]) -> dict[str, Any]:
    return {
        "count": len(messages),
        "last_messages": [_message_preview(message) for message in messages[-4:]],
    }


def state_preview(state: Any) -> dict[str, Any]:
    if not isinstance(state, dict):
        return {"value": _truncate(state)}

    preview: dict[str, Any] = {}

    for key, value in state.items():
        if key == "messages":
            preview[key] = _messages_preview(value or [])
        elif key in {"conversation_summary", "context_summary", "final_answer"}:
            preview[key] = _truncate(value)
        elif key == "agent_answers":
            preview[key] = {
                "count": len(value or []),
                "items": [
                    {
                        "index": item.get("index"),
                        "question": _truncate(item.get("question", ""), 240),
                        "answer": _truncate(item.get("answer", ""), 500),
                    }
                    for item in (value or [])[:3]
                    if isinstance(item, dict)
                ],
            }
        elif isinstance(value, set):
            preview[key] = sorted(value)
        else:
            preview[key] = value

    return preview


def update_preview(update: Any) -> Any:
    if not isinstance(update, dict):
        return _truncate(update)

    preview: dict[str, Any] = {}
    for key, value in update.items():
        if key == "messages":
            preview[key] = [_message_preview(message) for message in value]
        elif key in {"conversation_summary", "context_summary", "final_answer"}:
            preview[key] = _truncate(value)
        elif key == "agent_answers":
            preview[key] = state_preview({"agent_answers": value})["agent_answers"]
        elif isinstance(value, set):
            preview[key] = sorted(value)
        else:
            preview[key] = value
    return preview


def _print_block(title: str, payload: Any, color: str) -> None:
    if not _enabled():
        return

    timestamp = datetime.now().strftime("%H:%M:%S")
    print(_color(f"\n[{timestamp}] {title}", color))
    print(_color("-" * 80, "dim"))
    print(pformat(payload, width=120, sort_dicts=False))


def log_chat_start(message: str, thread_id: str, has_pending_interrupt: bool) -> None:
    active_thread_id.set(thread_id)
    _print_block(
        "USER QUERY",
        {
            "thread_id": thread_id,
            "pending_interrupt": has_pending_interrupt,
            "message": _truncate(message),
        },
        "blue",
    )
    save_log_to_db("user_interface", "chat_start", {
        "message": _truncate(message),
        "pending_interrupt": has_pending_interrupt
    })


def log_chat_end(state: Any) -> None:
    _print_block("FINAL GRAPH STATE", state_preview(state), "blue")
    save_log_to_db("user_interface", "chat_end", state_preview(state))


def log_node_start(name: str, state: Any) -> None:
    _print_block(f"NODE START: {name}", state_preview(state), "cyan")
    save_log_to_db(name, "node_start", state_preview(state))


def log_node_end(name: str, update: Any) -> None:
    _print_block(f"NODE OUTPUT: {name}", update_preview(update), "green")
    save_log_to_db(name, "node_end", update_preview(update))


def log_route(name: str, decision: Any, state: Any | None = None) -> None:
    payload = {"decision": _truncate(decision)}
    if state is not None:
        payload["state"] = state_preview(state)
    _print_block(f"ROUTE: {name}", payload, "yellow")
    save_log_to_db(name, "route", payload)


def log_tool_start(name: str, args: dict[str, Any]) -> None:
    _print_block(f"TOOL START: {name}", args, "magenta")
    save_log_to_db(name, "tool_start", args)


def log_tool_end(name: str, output: Any) -> None:
    payload = output if isinstance(output, dict) else {"output": _truncate(output)}
    _print_block(f"TOOL OUTPUT: {name}", payload, "magenta")
    save_log_to_db(name, "tool_end", payload)


def log_error(scope: str, error: Exception) -> None:
    _print_block(f"ERROR: {scope}", {"type": error.__class__.__name__, "message": str(error)}, "red")
    save_log_to_db(scope, "error", {"type": error.__class__.__name__, "message": str(error)})


def logged_node(name: str, fn):
    def _wrapped(state, *args, **kwargs):
        import time
        import uuid
        trace_id = state.get("trace_id") if isinstance(state, dict) else None
        token = active_trace_id.set(trace_id or active_trace_id.get() or str(uuid.uuid4()))
        started = time.perf_counter()
        log_node_start(name, state)
        try:
            result = fn(state, *args, **kwargs)
        except Exception as exc:
            log_error(name, exc)
            raise
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
        if isinstance(result, dict):
            result.setdefault("trace_id", active_trace_id.get())
            result.setdefault("node_metrics", [])
            result["node_metrics"].append({"node": name, "duration_ms": duration_ms,
                                            "prompt_version": "builtin", "model": getattr(config, "LLM_MODEL", None)})
        log_node_end(name, result)
        save_log_to_db(name, "node_trace", {"duration_ms": duration_ms, "update": update_preview(result)})
        active_trace_id.reset(token)
        return result

    return _wrapped
