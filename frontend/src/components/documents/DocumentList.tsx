import { useDeleteDocument, useDocuments } from "../../hooks/useDocuments";

export function DocumentList() {
  const { data: documents, isLoading, error } = useDocuments();
  const deleteDocument = useDeleteDocument();

  if (isLoading) return <p className="text-sm text-gray-400">Loading documents...</p>;
  if (error) return <p className="text-sm text-red-500">Could not load documents.</p>;
  if (!documents || documents.length === 0)
    return <p className="text-sm text-gray-400">No documents indexed yet.</p>;

  return (
    <ul className="divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
      {documents.map((doc) => (
        <li key={doc.source} className="flex items-center justify-between px-4 py-2 text-sm">
          <span className="flex min-w-0 items-center gap-2">
            <span className="truncate text-gray-700" title={doc.source}>
              {doc.source}
            </span>
            {doc.searchable === false && (
              <span
                className="shrink-0 rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-amber-500"
                title="Parent chunks exist but no vectors were indexed, so questions about this document cannot be answered. Re-index or delete and re-upload."
              >
                not searchable
              </span>
            )}
          </span>
          <button
            onClick={() => deleteDocument.mutate(doc.source)}
            disabled={deleteDocument.isPending}
            className="ml-3 shrink-0 text-xs text-gray-400 hover:text-red-500 disabled:opacity-50"
          >
            Delete
          </button>
        </li>
      ))}
      {deleteDocument.isError && (
        <li className="px-4 py-2 text-xs text-amber-600">
          {(deleteDocument.error as { response?: { data?: { detail?: string } } }).response?.data
            ?.detail ?? "Delete failed."}
        </li>
      )}
    </ul>
  );
}
