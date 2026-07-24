import { memo, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";
import { Copy, Check, RotateCcw, AlertTriangle, ThumbsUp, ThumbsDown } from "lucide-react";

import type { ChatMessage } from "../../hooks/useChatStream";
import { AgentStatusPanel } from "./AgentStatusPanel";
import { SourcesPanel } from "./SourcesPanel";
import { TypingIndicator } from "./TypingIndicator";

import "highlight.js/styles/github-dark.css";

interface Props {
  message: ChatMessage;
  onRetry?: () => void;
  streaming?: boolean;
}

export const MessageBubble = memo(function MessageBubble({ message, onRetry, streaming }: Props) {
  const [copied, setCopied] = useState(false);
  const [likeState, setLikeState] = useState<"like" | "dislike" | null>(null);
  const isUser = message.role === "user";

  const copy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}
      data-testid="message-bubble"
    >
      <div
        className={`max-w-[85%] rounded-lg p-4 border ${
          isUser
            ? "bg-blue-600 text-white border-blue-500/20 font-medium"
            : "bg-slate-900 text-slate-100 border-white/5"
        }`}
      >
        {/* Assistant Header Actions: System Status & Confidence */}
        {!isUser && (
          <div className="mb-2 flex items-center justify-between gap-4 border-b border-white/5 pb-2">
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                Agentic Stream
              </span>
            </div>
            
            {message.safety?.confidence !== undefined && (
              <div className="flex items-center gap-1 text-[10px] text-slate-400">
                <span className="font-semibold text-slate-200">
                  Confidence Score:
                </span>
                <span className="rounded bg-white/5 px-1.5 py-0.5 font-bold font-mono text-blue-400">
                  {(message.safety.confidence * 100).toFixed(0)}%
                </span>
              </div>
            )}
          </div>
        )}

        {/* LangGraph reasoning node trace within bubble (collapsed layout) */}
        {!isUser && ((message.agentSteps?.length ?? 0) > 0 || (message.tools?.length ?? 0) > 0) && (
          <div className="mb-3">
            <AgentStatusPanel steps={message.agentSteps ?? []} tools={message.tools ?? []} />
          </div>
        )}

        {/* Message Content Body */}
        {isUser ? (
          <p className="whitespace-pre-wrap leading-relaxed text-sm">{message.content}</p>
        ) : message.content ? (
          <div className="prose-chat break-words text-slate-200 leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {message.content}
            </ReactMarkdown>
          </div>
        ) : message.streaming ? (
          <TypingIndicator />
        ) : null}

        {/* Error Notification */}
        {message.error && (
          <div className="mt-3 flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2.5 text-xs text-red-400">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <div className="grow">
              <span>{message.error}</span>
              {onRetry && (
                <button onClick={onRetry} className="ml-2 font-bold underline hover:opacity-80">
                  Retry connection
                </button>
              )}
            </div>
          </div>
        )}

        {/* Sources / Citations list */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-4 border-t border-white/5 pt-3">
            <SourcesPanel answers={message.sources} />
          </div>
        )}

        {/* Safety Warnings */}
        {!isUser && message.safety && !message.safety.approved && (
          <div className="mt-3 flex items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/10 p-2.5 text-xs text-amber-400">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <p>
              Response flagged by safety checks (Approved: FALSE | Confidence: {(message.safety.confidence * 100).toFixed(0)}%).
            </p>
          </div>
        )}

        {/* Handoff escalation notifications */}
        {!isUser && message.escalationRequired && (
          <div className="mt-3 flex items-center gap-2 rounded-lg border border-orange-500/20 bg-orange-500/10 p-2.5 text-xs text-orange-400">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <p>
              Routing anomaly or safety flags triggered. Handoff ticket submitted to operations queue.
            </p>
          </div>
        )}

        {/* Message Footnotes Actions */}
        {!isUser && message.content && !message.streaming && (
          <div className="mt-3 flex items-center justify-between border-t border-white/5 pt-2 text-slate-400">
            <div className="flex items-center gap-3">
              <button
                onClick={copy}
                className="flex items-center gap-1 text-[11px] font-medium transition-colors hover:text-white"
                title="Copy response"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-500" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </button>

              {onRetry && !streaming && (
                <button
                  onClick={onRetry}
                  className="flex items-center gap-1 text-[11px] font-medium transition-colors hover:text-white"
                  title="Regenerate"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span>Regenerate</span>
                </button>
              )}
            </div>

            {/* Thumbs Feedback */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setLikeState(likeState === "like" ? null : "like")}
                className={`rounded p-1 transition-colors hover:bg-white/5 ${
                  likeState === "like" ? "text-emerald-400" : "text-slate-500 hover:text-slate-300"
                }`}
              >
                <ThumbsUp className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => setLikeState(likeState === "dislike" ? null : "dislike")}
                className={`rounded p-1 transition-colors hover:bg-white/5 ${
                  likeState === "dislike" ? "text-red-400" : "text-slate-500 hover:text-slate-300"
                }`}
              >
                <ThumbsDown className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
});

