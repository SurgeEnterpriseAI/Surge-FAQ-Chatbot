import { motion, AnimatePresence } from "framer-motion";
import { X, CheckCircle2, Loader2, CornerDownRight } from "lucide-react";
import type { ChatMessage } from "../../hooks/useChatStream";

interface ProcessDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  message: ChatMessage | null;
}

export function ProcessDrawer({ isOpen, onClose, message }: ProcessDrawerProps) {
  if (!message) return null;

  // Derive active steps from agentSteps
  const steps = message.agentSteps || [];
  const tools = message.tools || [];
  const safety = message.safety;

  // Let's create a list of nodes that represent the timeline
  const timelineNodes = [
    {
      key: "summarize_history",
      label: "History Summary",
      description: "Summarize previous chat context",
      nodeName: "summarize_history",
    },
    {
      key: "rewrite_query",
      label: "Query Rewrite",
      description: "Optimize user input for retrieval",
      nodeName: "rewrite_query",
    },
    {
      key: "supervisor_agent",
      label: "Supervisor Routing",
      description: "Classify intent & route the request",
      nodeName: "supervisor_agent",
    },
    {
      key: "knowledge_retrieval",
      label: "Knowledge Retrieval",
      description: "Vector query and semantic retrieval",
      nodeName: "knowledge_agent",
    },
    {
      key: "aggregator",
      label: "Aggregation",
      description: "Synthesize response variants",
      nodeName: "aggregator",
    },
    {
      key: "safety_agent",
      label: "Safety & Hallucination Check",
      description: "Evaluate response policies & trust",
      nodeName: "safety_agent",
    },
    {
      key: "final_response",
      label: "Final Response / Handoff",
      description: "Final output stream or escalation routing",
      nodeName: ["human_escalation", "done", "final"],
    },
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop blur */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/60"
          />

          {/* Drawer slide-in panel */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed bottom-0 right-0 top-0 z-50 w-full max-w-lg border-l border-white/10 bg-slate-950 p-6 flex flex-col"
          >
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div>
                <h2 className="text-lg font-bold text-white">
                  Execution Trace & AI Process
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Real-time multi-agent execution pipeline log
                </p>
              </div>
              <button
                onClick={onClose}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Scrollable nodes list */}
            <div className="flex-1 overflow-y-auto py-6 pr-1 space-y-6 scrollbar-thin">
              {timelineNodes.map((node, index) => {
                // Check if this node was executed
                const matchedStep = steps.find((s) => {
                  if (Array.isArray(node.nodeName)) {
                    return node.nodeName.includes(s.node);
                  }
                  return s.node === node.nodeName;
                });

                const isCurrentMessageStreaming = message.streaming;
                const isExecuted = !!matchedStep;
                const isLastExecuted = isExecuted && steps[steps.length - 1]?.node === matchedStep.node;
                const isRunning = isCurrentMessageStreaming && isLastExecuted;

                // Status icons
                let statusIcon = <div className="h-2 w-2 rounded-full bg-slate-700" />;
                let statusColor = "border-slate-800 text-slate-500";
                
                if (isExecuted) {
                  if (isRunning) {
                    statusIcon = <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
                    statusColor = "border-blue-500/30 bg-blue-950/20 text-blue-400";
                  } else {
                    statusIcon = <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
                    statusColor = "border-emerald-500/30 bg-emerald-950/20 text-emerald-400";
                  }
                }

                // Render dynamic details inside expanded nodes
                return (
                  <div key={node.key} className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className={`flex h-8 w-8 items-center justify-center rounded-lg border-2 transition-all ${statusColor}`}>
                        {statusIcon}
                      </div>
                      {index < timelineNodes.length - 1 && (
                        <div className={`w-0.5 grow my-1 ${isExecuted ? "bg-emerald-500/30" : "bg-slate-800"}`} />
                      )}
                    </div>

                    <div className="flex-1 rounded-lg border border-white/5 bg-white/[0.02] p-4 hover:bg-white/[0.04] transition-colors">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-semibold text-white">{node.label}</h4>
                        {matchedStep?.node && (
                          <span className="text-[10px] font-mono rounded bg-white/5 px-1.5 py-0.5 text-slate-400">
                            {matchedStep.node}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 mt-1">{node.description}</p>

                      {/* Display retrieved details if available */}
                      {isExecuted && matchedStep?.content && (
                        <div className="mt-3 text-xs border-l-2 border-white/10 bg-slate-900/50 p-2 text-slate-350 rounded-r font-mono whitespace-pre-wrap max-h-40 overflow-y-auto scrollbar-thin">
                          {matchedStep.content}
                        </div>
                      )}

                      {/* Tool calls made during retrieval */}
                      {node.key === "knowledge_retrieval" && tools.length > 0 && (
                        <div className="mt-3 space-y-2 border-t border-white/5 pt-2">
                          <p className="text-[10px] font-bold uppercase tracking-wider text-purple-400">
                            Tool Activity Calls
                          </p>
                          {tools.map((t, tIdx) => (
                            <div key={tIdx} className="flex items-start gap-1.5 text-xs text-slate-300">
                              <CornerDownRight className="h-3.5 w-3.5 mt-0.5 text-purple-500 shrink-0" />
                              <div className="grow">
                                <span className="font-mono font-bold text-slate-200">{t.name}</span>
                                <span className="text-[10px] text-slate-500 font-mono ml-2">
                                  ({Object.keys(t.args || {}).join(", ")})
                                </span>
                                {t.result && (
                                  <div className="mt-1 rounded bg-slate-900 p-1.5 font-mono text-[10px] text-emerald-400 border border-emerald-950/20 max-h-24 overflow-y-auto">
                                    {t.result.preview}
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Special info for Safety audits */}
                      {node.key === "safety_agent" && safety && (
                        <div className="mt-3 flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-2.5 text-xs text-emerald-400">
                          <CheckCircle2 className="h-4 w-4 shrink-0" />
                          <div>
                            <span className="font-bold">Trust Approval Score:</span> {(safety.confidence * 100).toFixed(0)}%
                            {safety.issues && safety.issues.length > 0 && (
                              <p className="text-[10px] text-slate-400 mt-1">Issues: {safety.issues.join(", ")}</p>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
