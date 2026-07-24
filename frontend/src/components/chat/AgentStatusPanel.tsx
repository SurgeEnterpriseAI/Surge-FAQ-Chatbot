import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

import type { ToolActivity } from "../../hooks/useChatStream";
import type { AgentStatusEvent } from "../../lib/types";

function describeStep(step: AgentStatusEvent): string {
  const p = step.parsed;
  if (!p) return step.content ?? "Working...";
  if (step.node === "rewrite_query") {
    if (p.is_clear) {
      const questions = (p.questions as string[] | undefined) ?? [];
      return `Query is clear. Rewritten: ${questions.join(" | ") || "-"}`;
    }
    return `Query unclear. ${(p.clarification_needed as string) ?? ""}`;
  }
  if (step.node === "intent_classifier") {
    return `Intent: ${p.intent ?? "?"} (confidence ${p.confidence ?? "?"}) — ${p.reason ?? ""}`;
  }
  if (step.node === "tool_decision") {
    const action = p.action as string | undefined;
    if (action === "tool") return `Action: call tool ${p.tool ?? ""} — ${p.reason ?? ""}`;
    if (action === "both") return `Action: tool ${p.tool ?? ""} + knowledge base — ${p.reason ?? ""}`;
    return `Action: search knowledge base — ${p.reason ?? ""}`;
  }
  return JSON.stringify(p);
}

interface Props {
  steps: AgentStatusEvent[];
  tools: ToolActivity[];
}

export function AgentStatusPanel({ steps, tools }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mb-2 rounded-lg bg-white/5 border border-white/10 text-xs" data-testid="agent-status-panel">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3 py-2 font-medium text-slate-400 hover:text-slate-200 transition-colors"
      >
        <span>Agent reasoning ({steps.length + tools.length} steps)</span>
        <span>{open ? "▾" : "▸"}</span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <ul className="space-y-1 border-t border-white/10 px-3 py-2 text-slate-300 font-mono leading-relaxed max-h-60 overflow-y-auto">
              {steps.map((step) => (
                <li key={step.node}>
                  <span className="font-semibold">{step.title}:</span> {describeStep(step)}
                </li>
              ))}
              {tools.map((tool) => (
                <li key={tool.id}>
                  <span className="font-semibold">Tool {tool.name}:</span>{" "}
                  {tool.result ? (
                    <code className="break-all">
                      {tool.result.preview}
                      {tool.result.truncated ? " ..." : ""}
                    </code>
                  ) : (
                    "running..."
                  )}
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
