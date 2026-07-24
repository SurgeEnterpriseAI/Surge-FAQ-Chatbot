import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import type {
  AIPerformanceData,
  AgentPerformanceData,
  BusinessMetricsData,
  KnowledgeBaseData,
  SystemObservabilityData,
  UserAnalyticsData,
  SecurityDashboardData,
  PredictiveAnalyticsData
} from "../lib/types";

// AI Performance Hook
export function useAIPerformance(days: number = 30) {
  return useQuery<AIPerformanceData>({
    queryKey: ["analytics", "ai-performance", days],
    queryFn: async () => {
      const { data } = await api.get<AIPerformanceData>(`/analytics/ai-performance?days=${days}`);
      return data;
    }
  });
}

// Agent Performance Hook
export function useAgentPerformance() {
  return useQuery<AgentPerformanceData>({
    queryKey: ["analytics", "agent-performance"],
    queryFn: async () => {
      const { data } = await api.get<AgentPerformanceData>("/analytics/agent-performance");
      return data;
    }
  });
}

// Business Metrics Hook
export function useBusinessMetrics(days: number = 30) {
  return useQuery<BusinessMetricsData>({
    queryKey: ["analytics", "business-metrics", days],
    queryFn: async () => {
      const { data } = await api.get<BusinessMetricsData>(`/analytics/business-metrics?days=${days}`);
      return data;
    }
  });
}

// Knowledge Base Metrics Hook
export function useKnowledgeBase() {
  return useQuery<KnowledgeBaseData>({
    queryKey: ["analytics", "knowledge-base"],
    queryFn: async () => {
      const { data } = await api.get<KnowledgeBaseData>("/analytics/knowledge-base");
      return data;
    }
  });
}

// System Observability Hook
export function useSystemMetrics() {
  return useQuery<SystemObservabilityData>({
    queryKey: ["analytics", "system"],
    queryFn: async () => {
      const { data } = await api.get<SystemObservabilityData>("/analytics/system");
      return data;
    },
    refetchInterval: 30000 // Refetch every 30 seconds for live observability trend
  });
}

// User Analytics Hook
export function useUserAnalytics(days: number = 30) {
  return useQuery<UserAnalyticsData>({
    queryKey: ["analytics", "users", days],
    queryFn: async () => {
      const { data } = await api.get<UserAnalyticsData>(`/analytics/users?days=${days}`);
      return data;
    }
  });
}

// Security Dashboard Hook
export function useSecurityMetrics() {
  return useQuery<SecurityDashboardData>({
    queryKey: ["analytics", "security"],
    queryFn: async () => {
      const { data } = await api.get<SecurityDashboardData>("/analytics/security");
      return data;
    }
  });
}

// Predictive Analytics Hook
export function usePredictiveAnalytics() {
  return useQuery<PredictiveAnalyticsData>({
    queryKey: ["analytics", "predictions"],
    queryFn: async () => {
      const { data } = await api.get<PredictiveAnalyticsData>("/analytics/predictions");
      return data;
    }
  });
}

// Admin Actions Hooks
export function useAdminActions() {

  const reindexMutation = useMutation<{ job_id: string }, Error>({
    mutationFn: async () => {
      const { data } = await api.post<{ job_id: string }>("/analytics/admin/reindex");
      return data;
    }
  });

  const restartMutation = useMutation<{ status: string; message: string }, Error>({
    mutationFn: async () => {
      const { data } = await api.post<{ status: string; message: string }>("/analytics/admin/restart-services");
      return data;
    }
  });

  const clearCacheMutation = useMutation<{ status: string; message: string }, Error>({
    mutationFn: async () => {
      const { data } = await api.post<{ status: string; message: string }>("/analytics/admin/clear-cache");
      return data;
    }
  });

  const fetchLogsQuery = async (lines: number = 100) => {
    const { data } = await api.get<{ logs: string[] }>(`/analytics/admin/logs?lines=${lines}`);
    return data.logs;
  };

  return {
    reindex: reindexMutation.mutateAsync,
    isReindexing: reindexMutation.isPending,
    restartServices: restartMutation.mutateAsync,
    isRestarting: restartMutation.isPending,
    clearCache: clearCacheMutation.mutateAsync,
    isClearingCache: clearCacheMutation.isPending,
    fetchLogs: fetchLogsQuery
  };
}
