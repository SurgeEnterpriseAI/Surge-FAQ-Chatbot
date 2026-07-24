import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import type { ConversationOut, HistoryResponse } from "../lib/types";

export function useConversations() {
  return useQuery({
    queryKey: ["conversations"],
    queryFn: async () => (await api.get<ConversationOut[]>("/conversations")).data,
  });
}

export async function fetchHistory(sessionId: string): Promise<HistoryResponse> {
  return (await api.get<HistoryResponse>(`/history/${sessionId}`)).data;
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (sessionId: string) => {
      await api.delete(`/conversations/${sessionId}`);
    },
    onMutate: async (deletedId: string) => {
      await queryClient.cancelQueries({ queryKey: ["conversations"] });
      const previousConversations = queryClient.getQueryData<ConversationOut[]>(["conversations"]);
      if (previousConversations) {
        queryClient.setQueryData<ConversationOut[]>(
          ["conversations"],
          previousConversations.filter((c) => c.id !== deletedId)
        );
      }
      return { previousConversations };
    },
    onError: (_err, _deletedId, context) => {
      if (context?.previousConversations) {
        queryClient.setQueryData(["conversations"], context.previousConversations);
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}
