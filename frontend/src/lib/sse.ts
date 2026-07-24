import { fetchEventSource } from "@microsoft/fetch-event-source";

import { getToken } from "./api";
import type { ChatSSEEvent } from "./types";

export interface PostSSEOptions {
  signal?: AbortSignal;
  onEvent: (event: ChatSSEEvent) => void;
  onError: (message: string) => void;
}

/** POST a chat message and dispatch each typed SSE event. */
export async function postChatSSE(
  body: { message: string; session_id: string | null },
  { signal, onEvent, onError }: PostSSEOptions,
): Promise<void> {
  const token = getToken();
  try {
    await fetchEventSource("/api/chat", {
      method: "POST",
      signal,
      openWhenHidden: true,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      onopen: async (response) => {
        if (!response.ok) {
          throw new Error(
            response.status === 401
              ? "Your session has expired. Please sign in again."
              : `Chat request failed (${response.status})`,
          );
        }
      },
      onmessage: (message) => {
        if (!message.event) return;
        try {
          onEvent({ event: message.event, data: JSON.parse(message.data || "{}") } as ChatSSEEvent);
        } catch {
          // Ignore malformed frames.
        }
      },
      onerror: (err) => {
        // Rethrow to stop fetch-event-source's automatic retry loop.
        throw err;
      },
    });
  } catch (err) {
    if (signal?.aborted) return;
    onError(err instanceof Error ? err.message : "The connection was interrupted.");
  }
}
