export function ClarificationBanner({ question }: { question: string }) {
  return (
    <div className="mx-auto mb-2 w-full max-w-3xl rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-800">
      <span className="font-semibold">Clarification needed: </span>
      {question}
    </div>
  );
}
