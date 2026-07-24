import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { Activity, Terminal, HelpCircle } from "lucide-react";

import { ChatInput } from "../components/chat/ChatInput";
import { ChatWindow } from "../components/chat/ChatWindow";
import { FeedbackDialog } from "../components/feedback/FeedbackDialog";
import { ProcessDrawer } from "../components/chat/ProcessDrawer";
import { useAuth } from "../hooks/useAuth";
import type { CustomerLayoutContext } from "../components/layout/CustomerLayout";

export function ChatPage() {
  const { chat } = useOutletContext<CustomerLayoutContext>();
  const { user } = useAuth();
  const [showFeedback, setShowFeedback] = useState(false);
  const [showProcessDrawer, setShowProcessDrawer] = useState(false);

  // Focus on the last assistant message to trace process logs
  const lastAssistantMsg = chat.messages
    .slice()
    .reverse()
    .find((m) => m.role === "assistant") || null;

  return (
    <>
      {/* Dynamic glow overlays */}

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Floating Premium Header */}
        <header className="flex h-14 items-center justify-between border-b border-white/5 bg-slate-950 px-6">
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-emerald-500 shadow shadow-emerald-500" />
            <h1 className="text-sm font-semibold tracking-tight text-slate-200">
              {chat.sessionId ? `Session Thread` : "Aether Support Assistant"}
            </h1>
            <span className="text-[10px] font-medium text-slate-500 border border-white/5 rounded px-1.5 py-0.5 ml-2 font-mono">
              Model: Gemma-4 (26B)
            </span>
          </div>

          <div className="flex items-center gap-3">
            {chat.sessionId && (
              <button
                onClick={() => setShowProcessDrawer(true)}
                className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold text-slate-350 hover:bg-white/10 hover:text-white transition-all"
              >
                <Activity className="h-3.5 w-3.5 text-purple-400" />
                <span>Show AI Process</span>
              </button>
            )}

            {user?.is_admin && (
              <a
                href="/admin"
                className="flex items-center gap-1.5 rounded-lg border border-blue-500/20 bg-blue-500/10 px-3 py-1.5 text-xs font-semibold text-blue-400 hover:bg-blue-500/25 transition-all"
              >
                <Terminal className="h-3.5 w-3.5" />
                <span>Ops Dashboard</span>
              </a>
            )}
          </div>
        </header>

        {/* Messaging Pane */}
        <ChatWindow
          messages={chat.messages}
          streaming={chat.streaming}
          clarification={chat.clarification}
          onRetry={chat.retry}
          onSend={(msg) => void chat.send(msg)}
        />

        {/* Footer Area with Glass Input Panel */}
        <div className="bg-slate-950 px-6 pb-6 pt-2">
          <ChatInput
            disabled={chat.streaming}
            streaming={chat.streaming}
            onSend={(msg) => void chat.send(msg)}
            onStop={chat.stop}
          />

          {chat.sessionId && (
            <div className="mx-auto mt-2.5 flex w-full max-w-3xl justify-between px-2 text-[11px] text-slate-500 font-medium">
              <span className="flex items-center gap-1">
                <HelpCircle className="h-3.5 w-3.5 text-slate-600" />
                Double check key transaction metrics.
              </span>
              <button
                onClick={() => setShowFeedback(true)}
                className="text-slate-400 hover:text-white underline hover:no-underline transition-all"
              >
                Escalate ticket / Submit feedback
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Floating Reasoning Trace Panel */}
      <ProcessDrawer
        isOpen={showProcessDrawer}
        onClose={() => setShowProcessDrawer(false)}
        message={lastAssistantMsg}
      />

      {/* Feedback & Escalate Popup */}
      {showFeedback && chat.sessionId && (
        <FeedbackDialog sessionId={chat.sessionId} onClose={() => setShowFeedback(false)} />
      )}
    </>
  );
}

