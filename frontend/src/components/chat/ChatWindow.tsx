import { useEffect, useRef } from "react";

import type { ChatMessage } from "../../hooks/useChatStream";
import { ClarificationBanner } from "./ClarificationBanner";
import { MessageBubble } from "./MessageBubble";

interface Props {
  messages: ChatMessage[];
  streaming: boolean;
  clarification: string | null;
  onRetry: () => void;
}

// Distance (px) from the bottom within which we consider the user "at the bottom"
// and are allowed to auto-scroll on new/streamed content.
const NEAR_BOTTOM_THRESHOLD = 120;

export function ChatWindow({ messages, streaming, clarification, onRetry }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const prevMessagesLength = useRef(0);
  const prevLastMessageContent = useRef("");
  const prevStreaming = useRef(false);
  // Whether the user is pinned near the bottom. Starts true so first messages scroll.
  const isNearBottom = useRef(true);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    isNearBottom.current = distance <= NEAR_BOTTOM_THRESHOLD;
  };

  useEffect(() => {
    const len = messages.length;
    const lastContent = len > 0 ? messages[len - 1].content : "";
    const changed =
      len !== prevMessagesLength.current || lastContent !== prevLastMessageContent.current;
    prevMessagesLength.current = len;
    prevLastMessageContent.current = lastContent;

    // A send always re-pins to the bottom, even if the user had scrolled up
    // to read earlier history.
    if (streaming && !prevStreaming.current) {
      isNearBottom.current = true;
    }
    prevStreaming.current = streaming;

    // Only follow the stream if the user hasn't scrolled up to read history.
    // "auto" (instant) avoids the animated scroll lagging behind rapidly
    // streamed tokens, which would otherwise make handleScroll see a large
    // distance-from-bottom and incorrectly latch the follow off.
    if (changed && isNearBottom.current) {
      bottomRef.current?.scrollIntoView({ behavior: "auto" });
    }
  }, [messages, streaming]);

  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      className="flex-1 min-h-0 overflow-y-auto px-4 py-6 scrollbar-thin"
    >
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
        {messages.length === 0 && (
          <div className="mt-16 flex flex-col items-center text-center">
            <h2 className="text-3xl font-extrabold tracking-tight text-white">
              Welcome to the Medical FAQ Assistant
            </h2>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-slate-400">
              Ask questions about diseases, symptoms, medications, treatments, preventive care,
              healthy lifestyle, medical conditions, or general healthcare information.
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            streaming={streaming}
            onRetry={!streaming && i === messages.length - 1 ? onRetry : undefined}
          />
        ))}
        {clarification && <ClarificationBanner question={clarification} />}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

