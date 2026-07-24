import { useState } from "react";
import { motion } from "framer-motion";
import { ShieldAlert, CheckCircle, Clock, MessageSquare } from "lucide-react";

export interface Ticket {
  id: string;
  summary: string;
  reason: string;
  confidence: number;
  assignedAgent: string;
  status: "open" | "closed" | "pending";
  createdAt: string;
  conversationId: string;
}

interface EscalationQueueProps {
  tickets?: Ticket[];
  onSelectTicket?: (id: string) => void;
  onUpdateStatus?: (id: string, status: "open" | "closed" | "pending") => void;
}

export function EscalationQueue({
  tickets = [],
  onSelectTicket,
  onUpdateStatus,
}: EscalationQueueProps) {
  const [filterStatus, setFilterStatus] = useState<"all" | "open" | "closed" | "pending">("open");

  const filteredTickets = tickets.filter(
    (t) => filterStatus === "all" || t.status === filterStatus
  );

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "closed":
        return "border-emerald-500/20 bg-emerald-500/10 text-emerald-400";
      case "pending":
        return "border-amber-500/20 bg-amber-500/10 text-amber-400";
      default:
        return "border-red-500/20 bg-red-500/10 text-red-400";
    }
  };

  const getAgentTagStyle = (agent: string) => {
    if (agent.includes("Shipping")) return "bg-purple-500/10 border-purple-500/20 text-purple-400";
    if (agent.includes("Billing")) return "bg-blue-500/10 border-blue-500/20 text-blue-400";
    if (agent.includes("Safety")) return "bg-orange-500/10 border-orange-500/20 text-orange-400";
    return "bg-slate-500/10 border-slate-500/20 text-slate-400";
  };

  return (
    <div className="rounded-lg border border-white/5 bg-slate-900 p-5 space-y-4">
      {/* Header filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/5 pb-4">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
            <ShieldAlert className="h-4 w-4 text-red-400" />
            Human Escalation Queue
          </h3>
          <p className="text-[10px] text-slate-550 mt-0.5">
            Manage routed client sessions and fallback tickets
          </p>
        </div>

        {/* Filters */}
        <div className="flex gap-1.5 rounded-lg bg-slate-950 p-1 border border-white/5">
          {(["all", "open", "pending", "closed"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setFilterStatus(s)}
              className={`rounded-md px-2.5 py-1 text-[10px] font-bold capitalize transition-all ${
                filterStatus === s
                  ? "bg-blue-600 text-white"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Tickets List */}
      <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1 scrollbar-thin">
        {filteredTickets.length === 0 ? (
          <p className="text-xs text-slate-500 text-center py-8">
            {tickets.length === 0
              ? "No escalations recorded yet."
              : "No tickets match the active status filter."}
          </p>
        ) : (
          filteredTickets.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-lg border border-white/5 bg-slate-950 p-4 hover:border-white/10 transition-all flex flex-col gap-3"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-xs text-slate-200">{t.id}</span>
                    <span className={`rounded border px-2 py-0.5 text-[8px] font-bold uppercase tracking-wider ${getStatusBadge(t.status)}`}>
                      {t.status}
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-slate-350 leading-relaxed mt-2">
                    {t.summary}
                  </p>
                </div>

                <div className="shrink-0 text-right">
                  <span className={`rounded border px-1.5 py-0.5 text-[9px] font-bold font-mono ${getAgentTagStyle(t.assignedAgent)}`}>
                    {t.assignedAgent}
                  </span>
                  <div className="text-[9px] text-slate-500 font-mono mt-2">
                    Conf: {(t.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex items-center justify-between border-t border-white/5 pt-3 mt-1">
                <div className="flex items-center gap-1.5 text-[9px] text-slate-500 font-mono">
                  <Clock className="h-3 w-3" />
                  <span>{new Date(t.createdAt).toLocaleString()}</span>
                </div>

                <div className="flex gap-2">
                  {onSelectTicket && (
                    <button
                      onClick={() => onSelectTicket(t.conversationId)}
                      className="flex items-center gap-1 rounded bg-white/5 px-2 py-1 text-[10px] font-bold text-slate-300 hover:bg-white/10 transition-colors"
                    >
                      <MessageSquare className="h-3.5 w-3.5" />
                      <span>Inspect Logs</span>
                    </button>
                  )}

                  {onUpdateStatus && t.status !== "closed" && (
                    <button
                      onClick={() => onUpdateStatus(t.id, "closed")}
                      className="flex items-center gap-1 rounded bg-emerald-500/10 border border-emerald-500/20 px-2 py-1 text-[10px] font-bold text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                    >
                      <CheckCircle className="h-3.5 w-3.5" />
                      <span>Resolve</span>
                    </button>
                  )}
                </div>
              </div>
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
}
