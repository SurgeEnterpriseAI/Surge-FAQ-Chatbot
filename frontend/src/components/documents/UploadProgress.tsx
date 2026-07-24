import type { UploadJobStatus } from "../../lib/types";

export function UploadProgress({ job }: { job: UploadJobStatus }) {
  const pct = Math.round(job.progress * 100);
  const done = job.status === "completed" || job.status === "completed_with_errors";
  const hasErrors = job.status === "failed" || job.status === "completed_with_errors";

  return (
    <div className="rounded-lg border border-white/10 bg-slate-900 p-4 text-sm">
      <div className="flex items-center justify-between">
        <span className="font-medium text-gray-200">
          {job.kind === "reindex" ? "Reindexing knowledge base" : "Ingesting documents"}
        </span>
        <span className="text-xs text-gray-400">{job.status.replace(/_/g, " ")}</span>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-white/5">
        <div
          className={`h-full transition-all ${hasErrors ? "bg-red-500" : "bg-blue-600"}`}
          style={{ width: `${done ? 100 : pct}%` }}
        />
      </div>
      {job.current_file && <p className="mt-1 text-xs text-gray-400">{job.current_file}</p>}
      {done && (
        <p className={`mt-1 text-xs ${hasErrors ? "text-amber-400" : "text-green-500"}`}>
          Added {job.added}, already indexed {job.skipped}.
        </p>
      )}
      {job.error && <p className="mt-1 text-xs text-red-400">{job.error}</p>}
    </div>
  );
}
