import { motion, AnimatePresence } from "framer-motion";
import { Radio, Trash2, Cpu, Clock } from "lucide-react";
import { useAnalyticsWS } from "../../hooks/useAnalyticsWS";

export function LiveActivityFeed() {
  const { events, isConnected, clearEvents } = useAnalyticsWS();

  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case "high":
        return "bg-red-500/10 border-red-500/20 text-red-400";
      case "medium":
        return "bg-amber-500/10 border-amber-500/20 text-amber-400";
      case "low":
        return "bg-blue-500/10 border-blue-500/20 text-blue-400";
      default:
        return "bg-slate-500/10 border-slate-500/20 text-slate-400";
    }
  };

  return (
    <div className="flex flex-col h-full rounded-lg border border-white/5 bg-slate-900 p-5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-4">
        <div className="flex items-center gap-2">
          <div className={`relative flex h-3 w-3`}>
            {isConnected && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            )}
            <span className={`relative inline-flex rounded-full h-3 w-3 ${isConnected ? "bg-emerald-500" : "bg-red-500"}`}></span>
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
              Live Activity Stream
              <span className="text-[10px] rounded px-1 py-0.5 border border-white/10 font-mono text-slate-400">
                WS
              </span>
            </h3>
            <p className="text-[10px] text-slate-400">
              {isConnected ? "Connected to analytics gateway" : "Gateway disconnected"}
            </p>
          </div>
        </div>

        <button
          onClick={clearEvents}
          disabled={events.length === 0}
          className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white transition-colors disabled:opacity-30"
          title="Clear events"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      {/* Events List */}
      <div className="flex-1 overflow-y-auto min-h-0 space-y-3 pr-1 scrollbar-thin">
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <Radio className="h-8 w-8 text-slate-600 animate-pulse mb-2" />
            <p className="text-xs font-semibold text-slate-500">Awaiting stream packets...</p>
            <p className="text-[10px] text-slate-650 mt-0.5">Start a chat thread to trigger workspace logs</p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {events.map((e, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -10, height: 0 }}
                animate={{ opacity: 1, x: 0, height: "auto" }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="rounded-lg border border-white/5 bg-slate-950 p-3 hover:border-white/10 transition-colors">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex gap-2">
                      <div className="mt-0.5 shrink-0 rounded bg-white/5 p-1 text-slate-400">
                        <Cpu className="h-3.5 w-3.5" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-slate-200 leading-snug">
                          {e.event}
                        </p>
                        <p className="text-[10px] font-mono text-slate-500 mt-0.5">
                          Type: {e.type}
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-col items-end shrink-0 gap-1.5">
                      <span className={`rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${getSeverityStyle(e.severity)}`}>
                        {e.severity}
                      </span>
                      <div className="flex items-center gap-1 text-[9px] text-slate-500">
                        <Clock className="h-3 w-3" />
                        <span>{new Date(e.timestamp || Date.now()).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  </div>

                  {e.metadata && Object.keys(e.metadata).length > 0 && (
                    <div className="mt-2 rounded bg-slate-950 p-2 font-mono text-[9px] text-slate-400 max-h-24 overflow-y-auto scrollbar-thin">
                      {JSON.stringify(e.metadata, null, 2)}
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
