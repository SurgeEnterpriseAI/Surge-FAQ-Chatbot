import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { Activity, Terminal, Menu, ShieldCheck } from "lucide-react";

import { ChatInput } from "../components/chat/ChatInput";
import { ChatWindow } from "../components/chat/ChatWindow";
import { FeedbackDialog } from "../components/feedback/FeedbackDialog";
import { ProcessDrawer } from "../components/chat/ProcessDrawer";
import { useAuth } from "../hooks/useAuth";
import type { CustomerLayoutContext } from "../components/layout/CustomerLayout";

export function ChatPage() {
  const { chat, onOpenSidebar } = useOutletContext<CustomerLayoutContext>();
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

      <div className="flex h-full min-w-0 min-h-0 flex-1 flex-col overflow-hidden">
        {/* Floating Premium Header */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-white/5 bg-slate-950 px-4 sm:px-6">
          <div className="flex items-center gap-2 min-w-0">
            <button
              type="button"
              onClick={onOpenSidebar}
              className="lg:hidden -ml-1 mr-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-400 hover:bg-white/5 hover:text-white transition-colors duration-200"
              title="Open menu"
              aria-label="Open navigation menu"
            >
              <Menu className="h-5 w-5" />
            </button>
            <span className="flex h-2 w-2 shrink-0 rounded-full bg-emerald-500 shadow shadow-emerald-500" />
            <h1 className="truncate text-sm font-semibold tracking-tight text-slate-200">
              {chat.sessionId ? `Session Thread` : "Medical FAQ Assistant"}
            </h1>
            <span className="hidden sm:inline-block text-[10px] font-medium text-slate-500 border border-white/5 rounded px-1.5 py-0.5 ml-2 font-mono">
              Model: Medical AI Assistant
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
        />

        {/* Footer Area with Glass Input Panel */}
        <div className="shrink-0 bg-slate-950 px-4 pb-4 pt-2 sm:px-6 sm:pb-6">
          <ChatInput
            disabled={chat.streaming}
            streaming={chat.streaming}
            onSend={(msg) => void chat.send(msg)}
            onStop={chat.stop}
          />

          <div className="mx-auto mt-2.5 flex w-full max-w-3xl items-center justify-center gap-1.5 px-2 text-[11px] font-medium text-slate-500">
            <ShieldCheck className="h-3.5 w-3.5 text-slate-600" />
            <span>General information only — not a substitute for professional medical advice.</span>
          </div>

          {chat.sessionId && (
            <div className="mx-auto mt-2 flex w-full max-w-3xl justify-end px-2 text-[11px] text-slate-500 font-medium">
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

