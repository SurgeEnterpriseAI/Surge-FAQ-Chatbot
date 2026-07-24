// Mirrors the SSE event schema emitted by backend/services/chat_service.py.

export interface SessionEvent {
  session_id: string;
}

export interface AgentStatusEvent {
  node: string;
  title: string;
  status: "streaming" | "done";
  parsed: Record<string, unknown> | null;
  content: string | null;
}

export interface ToolCallEvent {
  id: string;
  name: string;
  args: Record<string, unknown>;
}

export interface ToolResultEvent {
  id: string;
  name: string;
  preview: string;
  truncated: boolean;
}

export interface ClarificationEvent {
  question: string;
}

export interface TokenEvent {
  content: string;
}

export interface SourceAnswer {
  index: number | null;
  question: string | null;
  contexts: string[];
}

export interface SourcesEvent {
  answers: SourceAnswer[];
}

export interface SafetyEvent {
  approved: boolean;
  confidence: number;
  issues: string[];
}

export interface FinalEvent {
  content: string;
  confidence: number | null;
  escalation_required: boolean;
  intent: string | null;
}

export interface ErrorEvent {
  code: string;
  message: string;
}

export type ChatSSEEvent =
  | { event: "session"; data: SessionEvent }
  | { event: "agent_status"; data: AgentStatusEvent }
  | { event: "tool_call"; data: ToolCallEvent }
  | { event: "tool_result"; data: ToolResultEvent }
  | { event: "clarification"; data: ClarificationEvent }
  | { event: "token"; data: TokenEvent }
  | { event: "sources"; data: SourcesEvent }
  | { event: "safety"; data: SafetyEvent }
  | { event: "final"; data: FinalEvent }
  | { event: "error"; data: ErrorEvent }
  | { event: "done"; data: Record<string, never> };

// REST API shapes

export interface UserProfile {
  user_id: string;
  email: string;
  name: string | null;
  is_guest: boolean;
  is_admin: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface MessageOut {
  id: string;
  role: string;
  content: string;
  metadata: any;
  timestamp: string | null;
}

export interface HistoryResponse {
  session_id: string;
  messages: MessageOut[];
  summary: string | null;
}

export interface ConversationOut {
  id: string;
  title: string | null;
  created_at: string | null;
}

export interface UploadJobStatus {
  job_id: string;
  kind: string;
  status: "pending" | "running" | "completed" | "completed_with_errors" | "failed";
  progress: number;
  current_file: string;
  added: number;
  skipped: number;
  error: string | null;
}

export interface DocumentOut {
  source: string;
  markdown_file: string;
  /** False when the document has parent chunks but no vectors, so it cannot be answered from. */
  searchable?: boolean;
}

// Analytics Dashboard Types

export interface AIPerformanceTrend {
  date: string;
  requests: number;
  confidenceScore: number;
  hallucinations: number;
  safetyInterventions: number;
  promptInjectionsBlocked: number;
}

export interface AIPerformanceData {
  hasData: boolean;
  totalRequests: number;
  successfulResponses: number;
  failedResponses: number;
  hallucinationCount: number;
  safetyInterventions: number;
  blockedInjections: number;
  avgConfidenceScore: number;
  avgRetrievalScore: number;
  avgContextSizeTokens: number;
  avgTokensPerResponse: number;
  avgCompletionTimeSeconds: number;
  avgLlmLatencySeconds: number;
  trends: AIPerformanceTrend[];
}

export interface AgentMetricRow {
  agentName: string;
  requests: number;
  successes: number;
  failures: number;
  avgExecTimeMs: number;
  avgConfidence: number;
  toolCalls: number;
  ragCalls: number;
  escalations: number;
}

export interface AgentPerformanceData {
  hasData: boolean;
  metrics: AgentMetricRow[];
  topUsedAgent: string | null;
  leastUsedAgent: string | null;
}

export interface BusinessTrend {
  date: string;
  created: number;
  resolved: number;
  csat: number;
  escalated: number;
}

export interface BusinessMetricsData {
  hasData: boolean;
  firstResponseTimeMinutes: number;
  avgResolutionTimeHours: number;
  csatScore: number;
  avgFeedbackRating: number;
  escalationRatePct: number;
  resolutionRatePct: number;
  reopenRatePct: number;
  ticketBacklog: number;
  openTickets: number;
  pendingTickets: number;
  resolvedTickets: number;
  closedTickets: number;
  trends: BusinessTrend[];
}

export interface KBChunkAccess {
  chunk_id: string;
  hits: number;
  score: number;
}

export interface KBNamespaceUsage {
  namespace: string;
  vectorCount: number;
}

export interface KnowledgeBaseData {
  hasData: boolean;
  indexedDocuments: number;
  documents: string[];
  totalChunks: number;
  totalEmbeddings: number;
  mostRetrievedChunks: KBChunkAccess[];
  avgRetrievalLatencyMs: number;
  pineconeNamespaceUsage: KBNamespaceUsage[];
}

export interface SystemTrend {
  time: string;
  cpu: number;
  mem: number;
  apiLatency: number;
  dbLatency: number;
  vectorLatency: number;
}

export interface SystemObservabilityData {
  hasData: boolean;
  cpuUsage: number;
  memoryUsage: number;
  diskUsage: number;
  fastapiHealth: string;
  langgraphHealth: string;
  pineconeHealth: string;
  supabaseHealth: string;
  parentStoreHealth: string;
  parentStoreDegradationReason: string | null;
  llmAvailable: boolean;
  avgApiLatencyMs: number;
  avgDbQueryTimeMs: number;
  avgVectorSearchTimeMs: number;
  avgEmbeddingTimeMs: number;
  trends: SystemTrend[];
}

export interface UserTrend {
  date: string;
  totalUsers: number;
  activeUsers: number;
  retentionRate: number;
  sessionDurationSeconds: number;
}

export interface UserAnalyticsData {
  hasData: boolean;
  registeredUsers: number;
  guestUsers: number;
  dailyActiveUsers: number;
  weeklyActiveUsers: number;
  monthlyActiveUsers: number;
  avgSessionDurationMinutes: number;
  avgMessagesPerSession: number;
  avgConversationsPerUser: number;
  returningUsersPct: number;
  newUsers: number;
  trends: UserTrend[];
}

export interface SecurityEventRow {
  timestamp: string;
  event: string;
  ip: string | null;
  severity: "info" | "low" | "medium" | "high";
}

export interface AdminLoginHistoryRow {
  timestamp: string;
  userId: string | null;
  ip: string | null;
  status: "success" | "failed";
}

export interface SecurityTrend {
  date: string;
  securityEvents: number;
  authSuccessRate: number;
  blockedRequests: number;
}

export interface SecurityDashboardData {
  hasData: boolean;
  failedLoginAttempts: number;
  blockedRequests: number;
  rateLimitedRequests: number;
  promptInjectionAttempts: number;
  unauthorizedAccessAttempts: number;
  invalidTokens: number;
  expiredTokens: number;
  adminLoginHistory: AdminLoginHistoryRow[];
  recentSecurityEvents: SecurityEventRow[];
  trends: SecurityTrend[];
}

export interface PredictionTrend {
  date: string;
  projectedTickets: number;
  projectedResponseTime: number;
}

/** Projections are only returned once enough real history exists. */
export interface PredictiveAnalyticsData {
  available: boolean;
  reason?: string;
  minHistoryDays?: number;
  observedDays?: number;
  expectedTicketsTomorrow?: number;
  avgResponseTimeTomorrowSeconds?: number;
  recordedTokens?: number;
  recordedCostDollars?: number;
  projectedMonthlyTokens?: number;
  projectedMonthlyCostDollars?: number;
  trends: PredictionTrend[];
}

export interface LiveActivityEvent {
  timestamp: string;
  event: string;
  type: string;
  severity: "info" | "low" | "medium" | "high";
  metadata?: any;
}
