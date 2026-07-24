import { Shield, ShieldAlert, Key, UserX, Clock, MapPin } from "lucide-react";
import type { SecurityDashboardData } from "../../lib/types";

interface SecurityTimelineProps {
  securityData: SecurityDashboardData | null;
}

export function SecurityTimeline({ securityData }: SecurityTimelineProps) {
  if (!securityData) {
    return (
      <div className="flex items-center justify-center p-8 rounded-lg border border-white/5 bg-slate-900 text-slate-500 text-xs">
        Loading security logs...
      </div>
    );
  }

  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case "high":
        return "bg-red-500/10 text-red-400 border border-red-500/20";
      case "medium":
        return "bg-amber-500/10 text-amber-400 border border-amber-500/20";
      default:
        return "bg-blue-500/10 text-blue-400 border border-blue-500/20";
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 rounded-lg border border-white/5 bg-slate-900 p-5">
      {/* Recent Security Incidents */}
      <div className="space-y-4">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 border-b border-white/5 pb-2">
          <ShieldAlert className="h-4 w-4 text-red-400 animate-pulse" />
          <span>Intrusion Prevention & Safety Logs</span>
        </h4>

        <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1 scrollbar-thin">
          {securityData.recentSecurityEvents.length === 0 ? (
            <p className="text-xs text-slate-500 text-center py-8">No security threats detected in current window.</p>
          ) : (
            securityData.recentSecurityEvents.map((e, idx) => (
              <div key={idx} className="rounded-lg border border-white/5 bg-slate-950 p-3.5 flex items-start justify-between gap-3">
                <div className="flex gap-2.5">
                  <div className="shrink-0 mt-0.5 rounded bg-white/5 p-1 text-slate-400">
                    <Shield className="h-3.5 w-3.5 text-red-400" />
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-slate-200 block">{e.event}</span>
                    <span className="text-[9px] text-slate-500 mt-1 flex items-center gap-1 font-mono">
                      <Clock className="h-3 w-3" />
                      {new Date(e.timestamp).toLocaleString()}
                    </span>
                  </div>
                </div>
                <span className={`shrink-0 text-[8px] font-bold uppercase tracking-wider rounded px-1.5 py-0.5 ${getSeverityStyle(e.severity)}`}>
                  {e.severity}
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Admin Login Auditing */}
      <div className="space-y-4">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 border-b border-white/5 pb-2">
          <Key className="h-4 w-4 text-blue-400" />
          <span>Access Control Auditing</span>
        </h4>

        <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1 scrollbar-thin">
          {securityData.adminLoginHistory.length === 0 ? (
            <p className="text-xs text-slate-500 text-center py-8">No access logs collected.</p>
          ) : (
            securityData.adminLoginHistory.map((h, idx) => (
              <div key={idx} className="rounded-lg border border-white/5 bg-slate-950 p-3.5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="shrink-0 rounded bg-white/5 p-1.5 text-slate-400">
                    <UserX className={`h-4 w-4 ${h.status === "success" ? "text-emerald-400" : "text-red-400"}`} />
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-slate-250 block">{h.userId ?? "unknown user"}</span>
                    <div className="flex gap-3 text-[9px] text-slate-500 mt-1 font-mono">
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {h.ip}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(h.timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>

                <span className={`text-[9px] font-bold rounded px-1.5 py-0.5 border ${
                  h.status === "success"
                    ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                    : "border-red-500/20 bg-red-500/10 text-red-400"
                }`}>
                  {h.status === "success" ? "Authorized" : "Block"}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
