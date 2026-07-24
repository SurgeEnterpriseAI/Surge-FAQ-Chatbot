import { motion } from "framer-motion";
import { Server, Database, Brain, Network, Activity, Cpu } from "lucide-react";
import type { SystemObservabilityData } from "../../lib/types";

interface HealthIndicatorProps {
  metrics: SystemObservabilityData | null;
}

export function HealthIndicator({ metrics }: HealthIndicatorProps) {
  if (!metrics) {
    return (
      <div className="flex items-center justify-center p-8 rounded-lg border border-white/5 bg-slate-900 text-slate-500 text-xs">
        Loading telemetry diagnostics...
      </div>
    );
  }

  const services = [
    {
      name: "FastAPI Routing API",
      status: metrics.fastapiHealth === "healthy" ? "healthy" : "warning",
      details: `${metrics.avgApiLatencyMs.toFixed(0)}ms latency`,
      icon: Server,
    },
    {
      name: "Supabase PG Database",
      status: metrics.supabaseHealth === "healthy" ? "healthy" : "warning",
      details: `${metrics.avgDbQueryTimeMs.toFixed(0)}ms query`,
      icon: Database,
    },
    {
      name: "Pinecone Vector Cloud",
      status: metrics.pineconeHealth === "healthy" ? "healthy" : "warning",
      details: `${metrics.avgVectorSearchTimeMs.toFixed(0)}ms lookup`,
      icon: Network,
    },
    {
      name: "LLM Completion Host",
      status: metrics.llmAvailable ? "healthy" : "failed",
      details: `${metrics.avgEmbeddingTimeMs.toFixed(0)}ms embed`,
      icon: Brain,
    },
  ];

  const getStatusColor = (status: string) => {
    if (status === "healthy") return "text-emerald-500 bg-emerald-500";
    if (status === "warning") return "text-amber-500 bg-amber-500";
    return "text-red-500 bg-red-500";
  };

  const formatPercent = (pct: number) => {
    return `${pct.toFixed(1)}%`;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 rounded-lg border border-white/5 bg-slate-900 p-5">
      {/* Services Health */}
      <div className="space-y-4">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
          <Activity className="h-4 w-4 text-emerald-400" />
          <span>Services Health Checks</span>
        </h4>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {services.map((s, idx) => {
            const Icon = s.icon;
            return (
              <div key={idx} className="rounded-lg border border-white/5 bg-slate-950 p-3 flex items-start gap-3">
                <div className="shrink-0 mt-0.5 rounded bg-white/5 p-1.5 text-slate-400">
                  <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <div className="text-[11px] font-bold text-white leading-none truncate">{s.name}</div>
                  <div className="text-[9px] text-slate-500 font-mono mt-1">{s.details}</div>
                  <div className="mt-2 flex items-center gap-1.5">
                    <span className={`h-1.5 w-1.5 rounded-full ${getStatusColor(s.status)}`} />
                    <span className="text-[9px] font-mono capitalize text-slate-400">{s.status}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Host Metrics (CPU, Memory, Disk) */}
      <div className="space-y-4">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
          <Cpu className="h-4 w-4 text-purple-400" />
          <span>Host Resource Allocations</span>
        </h4>

        <div className="space-y-3.5">
          {/* CPU Progress Bar */}
          <div>
            <div className="flex justify-between text-[10px] text-slate-400 mb-1.5">
              <span className="font-semibold">CPU Allocation</span>
              <span className="font-mono font-bold">{formatPercent(metrics.cpuUsage)}</span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-850 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${metrics.cpuUsage}%` }}
                className="h-full rounded-full bg-blue-500"
              />
            </div>
          </div>

          {/* Memory Progress Bar */}
          <div>
            <div className="flex justify-between text-[10px] text-slate-400 mb-1.5">
              <span className="font-semibold">Memory Allocation</span>
              <span className="font-mono font-bold">{formatPercent(metrics.memoryUsage)}</span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-850 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${metrics.memoryUsage}%` }}
                className="h-full rounded-full bg-purple-500"
              />
            </div>
          </div>

          {/* Disk Progress Bar */}
          <div>
            <div className="flex justify-between text-[10px] text-slate-400 mb-1.5">
              <span className="font-semibold">Disk Allocation</span>
              <span className="font-mono font-bold">{formatPercent(metrics.diskUsage)}</span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-850 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${metrics.diskUsage}%` }}
                className="h-full rounded-full bg-emerald-500"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
