import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutGrid, Radio, MessageSquare, Database, Network, BarChart3,
  Cpu, ShieldAlert, Inbox, Activity, Settings, ArrowLeft,
  Search, RefreshCw, Sparkles, Clock, DollarSign, Award, FileText
} from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, LineChart, Line
} from "recharts";

import { useAuth } from "../hooks/useAuth";
import { useConversations, fetchHistory } from "../hooks/useConversations";
import { useDocuments, useDeleteDocument, useIngestJob } from "../hooks/useDocuments";
import {
  useAIPerformance, useAgentPerformance,
  useKnowledgeBase, useSystemMetrics,
  useSecurityMetrics, usePredictiveAnalytics, useAdminActions,
  useUserAnalytics
} from "../hooks/useAnalytics";

// Admin components
import { LiveActivityFeed } from "../components/admin/LiveActivityFeed";
import { AgentWorkflowGraph } from "../components/admin/AgentWorkflowGraph";
import { ConversationInspector } from "../components/admin/ConversationInspector";
import { AgentCard } from "../components/admin/AgentCard";
import { HealthIndicator } from "../components/admin/HealthIndicator";
import { SecurityTimeline } from "../components/admin/SecurityTimeline";
import { EscalationQueue } from "../components/admin/EscalationQueue";
import { useEnterpriseTraces } from "../hooks/useEnterprise";

// Document components
import { UploadDropzone } from "../components/documents/UploadDropzone";
import { UploadProgress } from "../components/documents/UploadProgress";

/** Render a metric, or an em dash when the value has not been recorded yet. */
function fmt(value: number | undefined | null, format?: (v: number) => string) {
  if (value === undefined || value === null) return "—";
  return format ? format(value) : value.toLocaleString();
}

type AdminTab =
  | "dashboard"
  | "live"
  | "explorer"
  | "kb"
  | "graph"
  | "analytics"
  | "metrics"
  | "security"
  | "escalations"
  | "health"
  | "settings";

export function AdminPage() {
  const { user, loading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<AdminTab>("dashboard");
  const [searchDocQuery, setSearchDocQuery] = useState("");

  // Conversation Explorer state
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [conversationHistory, setConversationHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Queries
  const { data: conversations = [], isLoading: loadingConvs } = useConversations();
  const { data: documents = [], isLoading: loadingDocs } = useDocuments();
  const deleteDocMutation = useDeleteDocument();
  const { job, error: ingestError, upload, reindex } = useIngestJob();

  // Analytics queries
  const { data: aiPerf } = useAIPerformance(30);
  const { data: agentPerf } = useAgentPerformance();
  const { data: kbStats } = useKnowledgeBase();
  const { data: systemMetrics } = useSystemMetrics();
  const { data: userStats } = useUserAnalytics(30);
  const { data: predictions } = usePredictiveAnalytics();
  const { data: securityMetrics } = useSecurityMetrics();
  const adminActions = useAdminActions();
  const { data: traceEvents = [] } = useEnterpriseTraces(user?.is_admin === true);
  const latestTrace = traceEvents[0];

  // Select conversation & fetch detailed steps
  const handleSelectConversation = async (sessionId: string) => {
    setSelectedConversationId(sessionId);
    setLoadingHistory(true);
    try {
      const history = await fetchHistory(sessionId);
      const messages = history.messages.map((m) => ({
        id: m.id,
        role: m.role === "user" ? "user" : "assistant",
        content: m.content,
        agentSteps: m.metadata?.agentSteps || [],
        tools: m.metadata?.tools || [],
        sources: m.metadata?.sources || [],
        safety: m.metadata?.safety || null,
        escalationRequired: m.metadata?.escalationRequired || false,
      }));
      setConversationHistory(messages);
    } catch {
      setConversationHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Auth RBAC Guard
  if (authLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-slate-500 bg-[#030712]">
        Verifying security clearance...
      </div>
    );
  }
  if (!user || (!user.is_admin && user.email !== "admin@example.com")) {
    return <Navigate to="/" replace />;
  }

  // Sidebar list matching specifications
  const sidebarItems = [
    { id: "dashboard" as const, label: "Operational Overview", icon: LayoutGrid },
    { id: "live" as const, label: "Live Transactions", icon: Radio },
    { id: "explorer" as const, label: "Trace Explorer", icon: MessageSquare },
    { id: "kb" as const, label: "Knowledge base", icon: Database },
    { id: "graph" as const, label: "LangGraph visualizer", icon: Network },
    { id: "analytics" as const, label: "Analytics Engines", icon: BarChart3 },
    { id: "metrics" as const, label: "Specialized Agents", icon: Cpu },
    { id: "security" as const, label: "Security auditing", icon: ShieldAlert },
    { id: "escalations" as const, label: "Escalations desk", icon: Inbox },
    { id: "health" as const, label: "Infrastructure vitals", icon: Activity },
    { id: "settings" as const, label: "Console Settings", icon: Settings },
  ];

  // Search filtered docs
  const filteredDocs = documents.filter((doc) =>
    doc.source.toLowerCase().includes(searchDocQuery.toLowerCase())
  );

  return (
    <div className="flex h-screen bg-[#030712] text-slate-100 overflow-hidden font-sans">
      {/* Decorative background glows */}


      {/* Main Admin Sidebar */}
      <aside className="w-64 border-r border-white/5 bg-slate-950/60 flex flex-col shrink-0">
        <div className="flex items-center gap-2.5 px-6 py-5 border-b border-white/5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white font-extrabold">
            A
          </div>
          <div>
            <h2 className="text-sm font-bold tracking-tight text-white">OPERATIONS DESK</h2>
            <p className="text-[9px] text-slate-500 uppercase tracking-widest font-mono font-bold mt-0.5">
              Enterprise Control
            </p>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto p-4 space-y-1 scrollbar-thin">
          {sidebarItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className="w-full relative group flex h-10 items-center gap-3 rounded-lg px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-100 transition-colors duration-150 shrink-0 text-left"
              >
                {isActive && (
                  <motion.div
                    layoutId="admin-active-indicator"
                    className="absolute inset-0 rounded-lg bg-white/5 border border-white/10 -z-10"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <Icon className={`h-4.5 w-4.5 shrink-0 transition-colors duration-150 ${isActive ? "text-purple-400" : "text-slate-500 group-hover:text-slate-350"}`} />
                <span className={`truncate transition-colors duration-150 ${isActive ? "text-white font-semibold" : "text-slate-400 group-hover:text-slate-200"}`}>
                  {item.label}
                </span>
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-white/5">
          <Link
            to="/"
            className="flex items-center justify-center gap-2 rounded-lg border border-white/10 bg-slate-900 py-2.5 text-xs font-bold text-slate-350 hover:bg-slate-900 transition-all"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Customer portal</span>
          </Link>
        </div>
      </aside>

      {/* Main content display screen */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top telemetry status ticker */}
        <header className="flex h-14 items-center justify-between border-b border-white/5 bg-slate-950 px-6">
          <h2 className="text-sm font-bold text-slate-200 capitalize">
            {sidebarItems.find((s) => s.id === activeTab)?.label}
          </h2>

          <div className="flex items-center gap-4 text-xs font-medium text-slate-400">
            <span className="flex items-center gap-1.5 border border-white/5 rounded px-2.5 py-1 bg-slate-950 font-mono text-[10px]">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse shadow-glow shadow-emerald-500" />
              API: {systemMetrics ? `${systemMetrics.avgApiLatencyMs.toFixed(0)}ms` : "checking..."}
            </span>
            <span className="flex items-center gap-1.5 border border-white/5 rounded px-2.5 py-1 bg-slate-950 font-mono text-[10px]">
              Memory: {systemMetrics ? `${systemMetrics.memoryUsage.toFixed(0)}%` : "checking..."}
            </span>
          </div>
        </header>

        {/* Content Panel */}
        <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
          {activeTab === "dashboard" && (
            <div className="space-y-6">
              {/* KPIs Widgets Grid */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {[
                  { label: "Requests", value: fmt(aiPerf?.totalRequests), desc: `Last 30 days`, icon: Sparkles, color: "text-blue-400" },
                  { label: "Active users", value: fmt(userStats?.dailyActiveUsers), desc: "Active in last 24h", icon: Cpu, color: "text-purple-400" },
                  { label: "Avg latency", value: fmt(systemMetrics?.avgApiLatencyMs, (v) => `${v.toFixed(0)}ms`), desc: "FastAPI gateway", icon: Clock, color: "text-emerald-400" },
                  { label: "Avg confidence", value: fmt(aiPerf?.avgConfidenceScore, (v) => `${v.toFixed(0)}%`), desc: "Safety confidence", icon: Award, color: "text-indigo-400" },
                  { label: "Recorded cost", value: fmt(predictions?.recordedCostDollars, (v) => `$${v.toFixed(2)}`), desc: "From usage records", icon: DollarSign, color: "text-amber-400" },
                ].map((kpi, idx) => {
                  const Icon = kpi.icon;
                  return (
                    <div key={idx} className="rounded-lg border border-white/5 bg-slate-900 p-4">
                      <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                        <Icon className={`h-4 w-4 ${kpi.color}`} />
                        <span>{kpi.label}</span>
                      </div>
                      <p className="mt-2 text-2xl font-extrabold text-white font-mono leading-none">{kpi.value}</p>
                      <p className="mt-1 text-[9px] text-slate-500 font-medium">{kpi.desc}</p>
                    </div>
                  );
                })}
              </div>

              {/* Interactive Dashboard charts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Request Volume Chart */}
                <div className="rounded-lg border border-white/5 bg-slate-900 p-5 space-y-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Request Transactions Trend</h4>
                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={aiPerf?.trends || []}>
                        <defs>
                          <linearGradient id="reqGlow" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                        <XAxis dataKey="date" stroke="#64748b" fontSize={9} />
                        <YAxis stroke="#64748b" fontSize={9} />
                        <Tooltip contentStyle={{ background: "#0f172a", borderColor: "rgba(255,255,255,0.1)", borderRadius: "8px" }} />
                        <Area type="monotone" dataKey="requests" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#reqGlow)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Confidence & Accuracy Trend */}
                <div className="rounded-lg border border-white/5 bg-slate-900 p-5 space-y-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Confidence Accuracy Trend</h4>
                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={aiPerf?.trends || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                        <XAxis dataKey="date" stroke="#64748b" fontSize={9} />
                        <YAxis stroke="#64748b" fontSize={9} domain={[0.8, 1]} />
                        <Tooltip contentStyle={{ background: "#0f172a", borderColor: "rgba(255,255,255,0.1)", borderRadius: "8px" }} />
                        <Line type="monotone" dataKey="confidenceScore" stroke="#10b981" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "live" && <LiveActivityFeed />}

          {activeTab === "explorer" && (
            <ConversationInspector
              conversationId={selectedConversationId}
              messages={conversationHistory}
              loading={loadingHistory}
            />
          )}

          {activeTab === "kb" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Document upload panels */}
              <div className="lg:col-span-1 space-y-4">
                <div className="rounded-lg border border-white/5 bg-slate-900 p-5">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                    Ingest source document
                  </h4>
                  <UploadDropzone onUpload={(files) => void upload(files)} />
                  {ingestError && (
                    <p className="mt-3 text-xs text-red-400 border border-red-500/20 bg-red-500/10 p-2 rounded-lg">
                      {ingestError}
                    </p>
                  )}
                  {job && <div className="mt-4"><UploadProgress job={job} /></div>}
                </div>

                <div className="rounded-lg border border-white/5 bg-slate-900 p-5">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                    Namespace metadata
                  </h4>
                  <div className="space-y-2 text-[11px] font-mono text-slate-400">
                    <div className="flex justify-between">
                      <span>Index Count:</span>
                      <span className="text-slate-200">{kbStats?.indexedDocuments ?? 0} docs</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Pinecone Chunks:</span>
                      <span className="text-slate-200">{kbStats?.totalChunks ?? 0} vectors</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Retrieval latency:</span>
                      <span className="text-slate-200">
                        {fmt(kbStats?.avgRetrievalLatencyMs, (v) => `${v.toFixed(0)}ms`)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Document Listing */}
              <div className="lg:col-span-2 rounded-lg border border-white/5 bg-slate-900 p-5 flex flex-col min-h-[460px]">
                <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-4">
                  <div className="relative w-72">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                    <input
                      type="text"
                      value={searchDocQuery}
                      onChange={(e) => setSearchDocQuery(e.target.value)}
                      placeholder="Search files..."
                      className="w-full rounded-lg border border-white/5 bg-white/5 pl-9 pr-4 py-1.5 text-xs outline-none focus:border-blue-500"
                    />
                  </div>
                  
                  <button
                    onClick={() => {
                      if (window.confirm("Rebuild the whole index from the knowledge_base folder?")) {
                        void reindex();
                      }
                    }}
                    className="flex items-center gap-1.5 rounded-lg bg-white/5 border border-white/10 px-3 py-1.5 text-[10px] font-bold text-slate-300 hover:bg-white/10"
                  >
                    <RefreshCw className="h-3 w-3" />
                    Reindex knowledge base
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto space-y-2 max-h-[360px] scrollbar-thin">
                  {loadingDocs ? (
                    <p className="text-xs text-slate-500 text-center py-8">Loading indexed documents...</p>
                  ) : filteredDocs.length === 0 ? (
                    <p className="text-xs text-slate-500 text-center py-8">No documents matched search.</p>
                  ) : (
                    filteredDocs.map((doc) => (
                      <div
                        key={doc.source}
                        className="rounded-lg border border-white/5 bg-slate-950 px-4 py-3 flex items-center justify-between hover:border-white/10 transition-colors"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <FileText className="h-4.5 w-4.5 text-purple-400 shrink-0" />
                          <span className="truncate text-xs font-semibold text-slate-200" title={doc.source}>
                            {doc.source}
                          </span>
                        </div>
                        <button
                          onClick={() => deleteDocMutation.mutate(doc.source)}
                          disabled={deleteDocMutation.isPending}
                          className="shrink-0 text-[10px] font-bold text-slate-500 hover:text-red-400 transition-colors disabled:opacity-30"
                        >
                          Delete
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === "graph" && <AgentWorkflowGraph activeNode={latestTrace?.node?.replace("main.", "").replace("_agent", "") || null} />}

          {activeTab === "analytics" && (
            <div className="space-y-6">
              {/* API latency trends */}
              <div className="rounded-lg border border-white/5 bg-slate-900 p-5 space-y-4">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Response latencies breakdown</h4>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={systemMetrics?.trends || []}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                      <XAxis dataKey="time" stroke="#64748b" fontSize={9} />
                      <YAxis stroke="#64748b" fontSize={9} />
                      <Tooltip contentStyle={{ background: "#0f172a", borderColor: "rgba(255,255,255,0.1)" }} />
                      <Line type="monotone" dataKey="apiLatency" stroke="#3b82f6" name="FastAPI Gate" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="dbLatency" stroke="#8b5cf6" name="Supabase PG" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="vectorLatency" stroke="#10b981" name="Pinecone Vector" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {activeTab === "metrics" && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {(agentPerf?.metrics || []).map((metric, idx) => (
                <AgentCard key={metric.agentName} metric={metric} index={idx} />
              ))}
            </div>
          )}

          {activeTab === "security" && <SecurityTimeline securityData={securityMetrics || null} />}

          {activeTab === "escalations" && (
            <EscalationQueue
              onSelectTicket={(convId) => {
                setActiveTab("explorer");
                handleSelectConversation(convId);
              }}
            />
          )}

          {activeTab === "health" && <HealthIndicator metrics={systemMetrics || null} />}

          {activeTab === "settings" && (
            <div className="max-w-xl rounded-lg border border-white/5 bg-slate-900 p-6 space-y-6">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-350">
                Operations Settings Panel
              </h3>

              <div className="space-y-4">
                <div className="rounded-lg border border-white/5 bg-slate-950 p-4 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-xs text-white block">Refresh API Cache</span>
                    <span className="text-[10px] text-slate-500">Flush active agent logs checkpointers</span>
                  </div>
                  <button
                    onClick={async () => {
                      await adminActions.clearCache();
                      alert("Cache cleared successfully!");
                    }}
                    className="rounded-lg bg-white/5 border border-white/10 px-3 py-1.5 text-xs font-semibold hover:bg-white/10"
                  >
                    Clear cache
                  </button>
                </div>

                <div className="rounded-lg border border-white/5 bg-slate-950 p-4 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-xs text-white block">Restart Workspace Services</span>
                    <span className="text-[10px] text-slate-500">Reboot FastAPI checkpointer pool</span>
                  </div>
                  <button
                    onClick={async () => {
                      await adminActions.restartServices();
                      alert("Services rebooted successfully!");
                    }}
                    className="rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 px-3 py-1.5 text-xs font-semibold hover:bg-red-500/20"
                  >
                    Restart services
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Sidebar conversation selector helper (embedded inside trace tab) */}
      {activeTab === "explorer" && (
        <div className="w-80 border-l border-white/5 bg-slate-950 flex flex-col shrink-0">
          <div className="p-4 border-b border-white/5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Conversations list</h3>
            <p className="text-[9px] text-slate-500 mt-0.5">Click a thread to inspect execution steps</p>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
            {loadingConvs ? (
              <p className="text-xs text-slate-500 text-center py-6">Loading conversations...</p>
            ) : conversations.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-6">No sessions logged</p>
            ) : (
              conversations.map((c) => (
                <button
                  key={c.id}
                  onClick={() => handleSelectConversation(c.id)}
                  className={`w-full text-left p-3 rounded-lg border text-xs transition-all ${
                    selectedConversationId === c.id
                      ? "bg-blue-600/15 border-blue-500/35 text-white"
                      : "bg-slate-950 border-white/5 text-slate-450 hover:bg-white/5"
                  }`}
                >
                  <div className="font-semibold truncate">{c.title || `Thread (${c.id.slice(0, 8)})`}</div>
                  <div className="text-[9px] text-slate-500 font-mono mt-1">
                    {c.created_at ? new Date(c.created_at).toLocaleString() : ""}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
