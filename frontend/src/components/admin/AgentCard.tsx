import { motion } from "framer-motion";
import { Cpu, Clock, Award, ShieldAlert, Sparkles, Terminal } from "lucide-react";
import type { AgentMetricRow } from "../../lib/types";

interface AgentCardProps {
  metric: AgentMetricRow;
  index: number;
}

export function AgentCard({ metric, index }: AgentCardProps) {
  const formatTime = (ms: number) => {
    if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`;
    return `${ms.toFixed(0)}ms`;
  };

  const getAgentGlow = (name: string) => {
    const lowercaseName = name.toLowerCase();
    if (lowercaseName.includes("supervisor")) return " hover:border-blue-500/30";
    if (lowercaseName.includes("safety")) return " hover:border-amber-500/30";
    if (lowercaseName.includes("knowledge") || lowercaseName.includes("rag")) return " hover:border-emerald-500/30";
    return " hover:border-purple-500/30";
  };

  const getAgentHeaderStyle = (name: string) => {
    const lowercaseName = name.toLowerCase();
    if (lowercaseName.includes("supervisor")) return "from-blue-500 to-indigo-500";
    if (lowercaseName.includes("safety")) return "from-amber-500 to-orange-500";
    if (lowercaseName.includes("knowledge") || lowercaseName.includes("rag")) return "from-emerald-500 to-teal-500";
    return "from-purple-500 to-pink-500";
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.4 }}
      className={`rounded-lg border border-white/5 bg-slate-900 p-5 transition-all duration-300 ${getAgentGlow(
        metric.agentName
      )}`}
    >
      {/* Title Header */}
      <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-4">
        <div className="flex items-center gap-2">
          <div className={`flex h-8 w-8 items-center justify-center rounded-lg text-white ${getAgentHeaderStyle(metric.agentName)}`}>
            <Cpu className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">{metric.agentName}</h4>
            <p className="text-[10px] text-slate-500 font-mono">Workflow Node</p>
          </div>
        </div>
        <span className="rounded bg-white/5 px-2 py-0.5 text-[9px] font-bold font-mono text-slate-400">
          Nodes active
        </span>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-lg bg-slate-950 p-3 border border-white/[0.02]">
          <div className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider text-slate-500">
            <Sparkles className="h-3 w-3 text-blue-400" />
            <span>Requests</span>
          </div>
          <p className="mt-1 text-base font-extrabold text-white font-mono leading-none">
            {metric.requests}
          </p>
        </div>

        <div className="rounded-lg bg-slate-950 p-3 border border-white/[0.02]">
          <div className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider text-slate-500">
            <Clock className="h-3 w-3 text-purple-400" />
            <span>Avg Latency</span>
          </div>
          <p className="mt-1 text-base font-extrabold text-white font-mono leading-none">
            {formatTime(metric.avgExecTimeMs)}
          </p>
        </div>

        <div className="rounded-lg bg-slate-950 p-3 border border-white/[0.02]">
          <div className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider text-slate-500">
            <Award className="h-3 w-3 text-emerald-400" />
            <span>Confidence</span>
          </div>
          <p className="mt-1 text-base font-extrabold text-white font-mono leading-none">
            {(metric.avgConfidence * 100).toFixed(0)}%
          </p>
        </div>

        <div className="rounded-lg bg-slate-950 p-3 border border-white/[0.02]">
          <div className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider text-slate-500">
            <ShieldAlert className="h-3 w-3 text-red-400" />
            <span>Escalation</span>
          </div>
          <p className="mt-1 text-base font-extrabold text-white font-mono leading-none">
            {metric.escalations}
          </p>
        </div>
      </div>

      {/* Auxiliary Details */}
      <div className="mt-4 border-t border-white/5 pt-3 flex items-center justify-between text-[10px] text-slate-500 font-medium font-mono">
        <div className="flex items-center gap-1">
          <Terminal className="h-3 w-3" />
          <span>Tools Run: <span className="text-slate-350">{metric.toolCalls}</span></span>
        </div>
        <div>
          <span>Failures: <span className={metric.failures > 0 ? "text-red-400 font-bold animate-pulse" : "text-slate-350"}>{metric.failures}</span></span>
        </div>
      </div>
    </motion.div>
  );
}
