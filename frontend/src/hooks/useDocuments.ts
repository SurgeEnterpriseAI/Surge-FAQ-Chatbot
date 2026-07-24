import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";

import { api } from "../lib/api";
import type { DocumentOut, UploadJobStatus } from "../lib/types";

export function useDocuments() {
  return useQuery({
    queryKey: ["documents"],
    queryFn: async () =>
      (await api.get<{ documents: DocumentOut[] }>("/documents")).data.documents,
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (sourceName: string) => {
      await api.delete(`/document/${encodeURIComponent(sourceName)}`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

/** Upload files (or trigger a reindex) and poll the resulting job until done. */
export function useIngestJob() {
  const queryClient = useQueryClient();
  const [job, setJob] = useState<UploadJobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const poll = useCallback(
    (jobId: string) => {
      stopPolling();
      pollRef.current = window.setInterval(async () => {
        try {
          const { data } = await api.get<UploadJobStatus>(`/upload/${jobId}`);
          setJob(data);
          if (
            data.status === "completed" ||
            data.status === "completed_with_errors" ||
            data.status === "failed"
          ) {
            stopPolling();
            void queryClient.invalidateQueries({ queryKey: ["documents"] });
          }
        } catch {
          stopPolling();
          setError("Lost track of the ingestion job.");
        }
      }, 750);
    },
    [queryClient, stopPolling],
  );

  const upload = useCallback(
    async (files: File[]) => {
      setError(null);
      setJob(null);
      const form = new FormData();
      files.forEach((f) => form.append("files", f));
      try {
        const { data } = await api.post<{ job_id: string }>("/upload", form);
        setJob({
          job_id: data.job_id,
          kind: "upload",
          status: "pending",
          progress: 0,
          current_file: "",
          added: 0,
          skipped: 0,
          error: null,
        });
        poll(data.job_id);
      } catch (e: unknown) {
        const detail =
          (e as { response?: { data?: { detail?: string } } }).response?.data?.detail;
        setError(detail ?? "Upload failed. Please try again.");
      }
    },
    [poll],
  );

  const reindex = useCallback(async () => {
    setError(null);
    setJob(null);
    try {
      const { data } = await api.post<{ job_id: string }>("/reindex");
      poll(data.job_id);
    } catch {
      setError("Could not start reindexing.");
    }
  }, [poll]);

  return { job, error, upload, reindex };
}
