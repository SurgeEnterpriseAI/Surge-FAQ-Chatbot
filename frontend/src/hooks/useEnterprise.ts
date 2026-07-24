import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export type TraceEvent = { id?: string; thread_id?: string; node: string; event: string; timestamp: string; payload?: unknown };

export function useEnterpriseTraces(isAdmin = false) {
  return useQuery<TraceEvent[]>({
    queryKey: ["enterprise", "traces"],
    queryFn: async () => {
      const res = await api.get<TraceEvent[]>("/enterprise/traces?limit=100");
      return res.data;
    },
    // Only run this query when the user is confirmed admin
    enabled: isAdmin,
    // Poll every 5 s while the admin panel is open, but stop immediately on error
    refetchInterval: (query) => {
      if (query.state.status === "error") return false;
      return isAdmin ? 5000 : false;
    },
    // Do not auto-retry on 401/403 — these are permanent auth errors
    retry: (failureCount, error: any) => {
      const status = error?.response?.status;
      if (status === 401 || status === 403 || status === 404) return false;
      return failureCount < 2;
    },
    // Return empty array on error so the UI renders gracefully
    placeholderData: [],
  });
}
