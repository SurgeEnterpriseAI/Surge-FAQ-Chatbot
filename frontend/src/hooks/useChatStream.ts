import { useCallback, useReducer, useRef } from "react";

import { postChatSSE } from "../lib/sse";
import type {
  AgentStatusEvent,
  ChatSSEEvent,
  SafetyEvent,
  SourceAnswer,
  ToolCallEvent,
  ToolResultEvent,
} from "../lib/types";

export interface ToolActivity extends ToolCallEvent {
  result?: ToolResultEvent;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  agentSteps?: AgentStatusEvent[];
  tools?: ToolActivity[];
  sources?: SourceAnswer[];
  safety?: SafetyEvent | null;
  escalationRequired?: boolean;
  intent?: string | null;
  error?: string | null;
}

interface ChatState {
  sessionId: string | null;
  messages: ChatMessage[];
  streaming: boolean;
  clarification: string | null;
  lastUserMessage: string | null;
}

type Action =
  | { type: "user_message"; content: string }
  | { type: "sse"; event: ChatSSEEvent }
  | { type: "stream_error"; message: string }
  | { type: "stream_end" }
  | { type: "load_history"; sessionId: string; messages: ChatMessage[] }
  | { type: "reset" };

const initialState: ChatState = {
  sessionId: null,
  messages: [],
  streaming: false,
  clarification: null,
  lastUserMessage: null,
};

let nextId = 0;
const genId = () => `msg-${Date.now()}-${nextId++}`;

function updateLastAssistant(
  messages: ChatMessage[],
  update: (msg: ChatMessage) => ChatMessage,
): ChatMessage[] {
  const idx = messages.length - 1;
  if (idx < 0 || messages[idx].role !== "assistant") return messages;
  const copy = messages.slice();
  copy[idx] = update(copy[idx]);
  return copy;
}

function reducer(state: ChatState, action: Action): ChatState {
  switch (action.type) {
    case "user_message":
      return {
        ...state,
        streaming: true,
        clarification: null,
        lastUserMessage: action.content,
        messages: [
          ...state.messages,
          { id: genId(), role: "user", content: action.content },
          {
            id: genId(),
            role: "assistant",
            content: "",
            streaming: true,
            agentSteps: [],
            tools: [],
          },
        ],
      };

    case "sse": {
      const { event } = action;
      switch (event.event) {
        case "session":
          return { ...state, sessionId: event.data.session_id };
        case "agent_status":
          return {
            ...state,
            messages: updateLastAssistant(state.messages, (msg) => {
              const steps = [...(msg.agentSteps ?? [])];
              const idx = steps.findIndex((s) => s.node === event.data.node);
              if (idx >= 0) steps[idx] = event.data;
              else steps.push(event.data);
              return { ...msg, agentSteps: steps };
            }),
          };
        case "tool_call":
          return {
            ...state,
            messages: updateLastAssistant(state.messages, (msg) => ({
              ...msg,
              tools: [...(msg.tools ?? []), { ...event.data }],
            })),
          };
        case "tool_result":
          return {
            ...state,
            messages: updateLastAssistant(state.messages, (msg) => ({
              ...msg,
              tools: (msg.tools ?? []).map((t) =>
                t.id === event.data.id ? { ...t, result: event.data } : t,
              ),
            })),
          };
        case "clarification":
          return { ...state, clarification: event.data.question };
        case "token":
          return {
            ...state,
            messages: updateLastAssistant(state.messages, (msg) => ({
              ...msg,
              content: msg.content + event.data.content,
            })),
          };
        case "sources":
          return {
            ...state,
            messages: updateLastAssistant(state.messages, (msg) => ({
              ...msg,
              sources: event.data.answers,
            })),
          };
        case "safety":
          return {
            ...state,
            messages: updateLastAssistant(state.messages, (msg) => ({
              ...msg,
              safety: event.data,
            })),
          };
        case "final":
          return {
            ...state,
            messages: updateLastAssistant(state.messages, (msg) => ({
              ...msg,
              content: event.data.content || msg.content,
              escalationRequired: event.data.escalation_required,
              intent: event.data.intent,
            })),
          };
        case "error":
          return {
            ...state,
            streaming: false,
            messages: updateLastAssistant(state.messages, (msg) => ({
              ...msg,
              streaming: false,
              error: event.data.message,
            })),
          };
        case "done":
          return {
            ...state,
            streaming: false,
            messages: updateLastAssistant(state.messages, (msg) => ({
              ...msg,
              streaming: false,
            })),
          };
        default:
          return state;
      }
    }

    case "stream_error":
      return {
        ...state,
        streaming: false,
        messages: updateLastAssistant(state.messages, (msg) => ({
          ...msg,
          streaming: false,
          error: action.message,
        })),
      };

    case "stream_end":
      return {
        ...state,
        streaming: false,
        messages: updateLastAssistant(state.messages, (msg) => ({ ...msg, streaming: false })),
      };

    case "load_history": {
      const userMsgs = action.messages.filter((m) => m.role === "user");
      const lastUserMsg = userMsgs.length > 0 ? userMsgs[userMsgs.length - 1].content : null;
      return {
        ...initialState,
        sessionId: action.sessionId,
        messages: action.messages,
        lastUserMessage: lastUserMsg,
      };
    }

    case "reset":
      return { ...initialState };

    default:
      return state;
  }
}

export function useChatStream() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const abortRef = useRef<AbortController | null>(null);
  const sessionRef = useRef<string | null>(null);
  sessionRef.current = state.sessionId;

  const send = useCallback(async (message: string) => {
    const trimmed = message.trim();
    if (!trimmed) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    dispatch({ type: "user_message", content: trimmed });
    await postChatSSE(
      { message: trimmed, session_id: sessionRef.current },
      {
        signal: controller.signal,
        onEvent: (event) => dispatch({ type: "sse", event }),
        onError: (msg) => dispatch({ type: "stream_error", message: msg }),
      },
    );
    dispatch({ type: "stream_end" });
  }, []);

  const retry = useCallback(() => {
    if (state.lastUserMessage) void send(state.lastUserMessage);
  }, [send, state.lastUserMessage]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    dispatch({ type: "stream_end" });
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    dispatch({ type: "reset" });
  }, []);

  const loadHistory = useCallback((sessionId: string, messages: ChatMessage[]) => {
    abortRef.current?.abort();
    dispatch({ type: "load_history", sessionId, messages });
  }, []);

  return { ...state, send, retry, stop, reset, loadHistory };
}
