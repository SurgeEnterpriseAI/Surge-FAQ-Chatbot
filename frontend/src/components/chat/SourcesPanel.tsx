import { useState } from "react";

import type { SourceAnswer } from "../../lib/types";

export function SourcesPanel({ answers }: { answers: SourceAnswer[] }) {
  const [open, setOpen] = useState(false);
  const contextCount = answers.reduce((n, a) => n + a.contexts.length, 0);
  if (contextCount === 0) return null;

  return (
    <div className="mt-2 rounded-lg bg-gray-50 text-xs">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3 py-2 font-medium text-gray-500"
      >
        <span>Sources ({contextCount})</span>
        <span>{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <div className="space-y-2 border-t border-gray-200 px-3 py-2 text-gray-600">
          {answers.map((answer, i) => (
            <div key={i}>
              {answer.question && <p className="font-semibold">{answer.question}</p>}
              {answer.contexts.map((ctx, j) => (
                <blockquote key={j} className="mt-1 border-l-2 border-gray-300 pl-2 italic">
                  {ctx.length > 400 ? `${ctx.slice(0, 400)}...` : ctx}
                </blockquote>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
