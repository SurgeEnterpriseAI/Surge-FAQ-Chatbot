import { useState } from "react";
import { MessageSquare, CornerDownRight } from "lucide-react";
import type { ChatMessage } from "../../hooks/useChatStream";

interface ConversationInspectorProps {
  conversationId: string | null;
  messages: ChatMessage[];
  loading?: boolean;
}

export function ConversationInspector({ conversationId, messages, loading = false }: ConversationInspectorProps) {
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);

  if (!conversationId) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8 rounded-lg border border-white/5 bg-slate-900/20">
        <MessageSquare className="h-8 w-8 text-slate-600 mb-2" />
        <p className="text-xs font-semibold text-slate-500">Select a conversation thread</p>
        <p className="text-[10px] text-slate-650 mt-0.5">Choose from the active list to inspect LLM execution traces</p>
      </div>
    );
  }

  const selectedMsg = messages.find((m) => m.id === selectedMessageId) || messages.find((m) => m.role === "assistant") || null;

  return (
    <div className="flex h-[620px] rounded-lg border border-white/5 bg-slate-900 overflow-hidden">
      {/* Messages Timeline List (Left) */}
      <div className="w-1/3 border-r border-white/5 flex flex-col h-full bg-slate-950">
        <div className="p-4 border-b border-white/5">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Thread Logs</h4>
          <p className="text-[9px] text-slate-500 mt-0.5">Select a message bubble to view node payload</p>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
          {loading ? (
            <div className="text-center py-8 text-xs text-slate-500">Loading conversation history...</div>
          ) : messages.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-500">No logs generated for this session.</div>
          ) : (
            messages.map((m) => (
              <button
                key={m.id}
                onClick={() => setSelectedMessageId(m.id)}
                className={`w-full text-left p-3 rounded-lg border transition-all text-xs flex flex-col gap-1.5 ${
                  (selectedMsg?.id === m.id)
                    ? "bg-white/5 border-blue-500/35 text-white"
                    : "bg-slate-950/10 border-white/5 text-slate-350 hover:bg-white/5 hover:text-slate-100"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                    m.role === "user" ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" : "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                  }`}>
                    {m.role === "user" ? "User input" : "Agent output"}
                  </span>
                  <span className="text-[9px] text-slate-500 font-mono">
                    {m.agentSteps?.length || 0} nodes
                  </span>
                </div>
                <p className="line-clamp-2 text-slate-450 leading-relaxed font-mono font-medium">{m.content}</p>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Node Trace Inspector (Right) */}
      <div className="flex-1 flex flex-col h-full bg-slate-900/10">
        {selectedMsg ? (
          <>
            <div className="p-4 border-b border-white/5 flex items-center justify-between">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-350">
                  Execution Trace Details
                </h4>
                <p className="text-[10px] text-slate-500 mt-0.5 font-mono">
                  Message ID: {selectedMsg.id}
                </p>
              </div>

              {selectedMsg.safety?.confidence !== undefined && (
                <span className="rounded border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 text-[10px] font-bold text-blue-400 font-mono">
                  Confidence: {(selectedMsg.safety.confidence * 100).toFixed(0)}%
                </span>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4 scrollbar-thin">
              {/* If User message, show simple raw inputs */}
              {selectedMsg.role === "user" ? (
                <div className="space-y-4">
                  <div className="rounded-lg border border-white/5 bg-slate-950 p-4">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                      Raw Query Content
                    </span>
                    <p className="text-sm text-slate-300 font-mono whitespace-pre-wrap leading-relaxed">
                      {selectedMsg.content}
                    </p>
                  </div>
                </div>
              ) : (
                /* Assistant Node Timeline Details */
                <div className="space-y-4">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2">
                    Traversed Nodes Flow
                  </div>

                  {(selectedMsg.agentSteps || []).map((step, idx) => {
                    const matchedTools = selectedMsg.tools?.filter((t) => {
                      // Billing Agent calls billing tools, technical calls tech tools, etc.
                      if (step.node === "billing_agent" && t.name.includes("billing")) return true;
                      if (step.node === "technical_agent" && t.name.includes("db")) return true;
                      if (step.node === "knowledge_agent" && t.name.includes("pinecone")) return true;
                      return false;
                    }) || [];

                    return (
                      <div key={idx} className="flex gap-4">
                        <div className="flex flex-col items-center">
                          <div className="flex h-6 w-6 items-center justify-center rounded-lg border border-slate-700 bg-slate-800 text-[10px] font-bold font-mono text-slate-400">
                            {idx + 1}
                          </div>
                          {idx < (selectedMsg.agentSteps?.length ?? 0) - 1 && (
                            <div className="w-0.5 grow bg-slate-800 my-1" />
                          )}
                        </div>

                        <div className="flex-1 rounded-lg border border-white/5 bg-slate-950/15 p-4 space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-200 text-xs">
                              {step.title || step.node}
                            </span>
                            <span className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[9px] text-slate-500">
                              status: {step.status}
                            </span>
                          </div>

                          {step.content && (
                            <div className="rounded border border-white/5 bg-slate-950 p-2.5 font-mono text-[10px] text-slate-400 whitespace-pre-wrap max-h-40 overflow-y-auto">
                              {step.content}
                            </div>
                          )}

                          {/* Nested Tools */}
                          {matchedTools.length > 0 && (
                            <div className="space-y-2 border-t border-white/5 pt-2">
                              <span className="text-[9px] font-bold uppercase tracking-wider text-purple-400 block">
                                Invoked Tool Traces
                              </span>
                              {matchedTools.map((t, tIdx) => (
                                <div key={tIdx} className="rounded border border-purple-500/10 bg-purple-500/5 p-2 text-[10px] space-y-1">
                                  <div className="flex items-center justify-between">
                                    <span className="font-bold text-purple-300 font-mono flex items-center gap-1">
                                      <CornerDownRight className="h-3 w-3 text-purple-500" />
                                      {t.name}
                                    </span>
                                  </div>
                                  <div className="text-[9px] text-slate-500 font-mono">
                                    Args: {JSON.stringify(t.args)}
                                  </div>
                                  {t.result && (
                                    <div className="rounded bg-slate-950 p-1.5 text-[9px] font-mono text-emerald-400 overflow-x-auto">
                                      {t.result.preview}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}

                  {/* Final message render preview */}
                  <div className="rounded-lg border border-white/5 bg-slate-950 p-4 space-y-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                      Synthesized Response Delivery
                    </span>
                    <p className="text-xs text-slate-300 leading-relaxed font-mono">
                      {selectedMsg.content}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full text-xs text-slate-500">
            No trace available
          </div>
        )}
      </div>
    </div>
  );
}
