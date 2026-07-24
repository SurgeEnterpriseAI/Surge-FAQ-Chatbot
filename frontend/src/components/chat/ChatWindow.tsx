import { useEffect, useRef } from "react";

import type { ChatMessage } from "../../hooks/useChatStream";
import { ClarificationBanner } from "./ClarificationBanner";
import { MessageBubble } from "./MessageBubble";
import { SuggestedPrompts } from "./SuggestedPrompts";

interface Props {
  messages: ChatMessage[];
  streaming: boolean;
  clarification: string | null;
  onRetry: () => void;
  onSend: (message: string) => void;
}

export function ChatWindow({ messages, streaming, clarification, onRetry, onSend }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const prevMessagesLength = useRef(0);
  const prevLastMessageContent = useRef("");

  useEffect(() => {
    const len = messages.length;
    const lastContent = len > 0 ? messages[len - 1].content : "";
    if (len !== prevMessagesLength.current || lastContent !== prevLastMessageContent.current) {
      prevMessagesLength.current = len;
      prevLastMessageContent.current = lastContent;
      
      const timer = setTimeout(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
        {messages.length === 0 && (
          <div className="mt-12 space-y-8">
            <div className="text-center">
              <h2 className="text-3xl font-extrabold tracking-tight text-white">
                How can I assist you today?
              </h2>
              <p className="mt-2 text-slate-400 text-sm max-w-md mx-auto">
                Ask about transactions, product routing, server logs, safety constraints, or query our knowledge repositories.
              </p>
            </div>
            <div className="max-w-2xl mx-auto">
              <SuggestedPrompts onSelect={onSend} />
            </div>
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

