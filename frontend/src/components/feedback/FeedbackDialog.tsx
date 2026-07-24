import { useState } from "react";

import { api } from "../../lib/api";

interface Props {
  sessionId: string;
  onClose: () => void;
}

export function FeedbackDialog({ sessionId, onClose }: Props) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [escalate, setEscalate] = useState(false);
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "done" | "error">("idle");

  const submit = async () => {
    setStatus("sending");
    try {
      if (rating > 0) {
        await api.post("/feedback", { session_id: sessionId, rating, comment: comment || null });
      }
      if (escalate) {
        await api.post("/escalate", {
          session_id: sessionId,
          reason: comment || "User requested human assistance",
          customer_email: email || null,
        });
      }
      setStatus("done");
      setTimeout(onClose, 1200);
    } catch {
      setStatus("error");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-6">
        <h2 className="text-base font-semibold text-gray-800">How did we do?</h2>

        <div className="mt-3 flex gap-1">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              onClick={() => setRating(n)}
              className={`text-2xl ${n <= rating ? "text-amber-400" : "text-gray-300"}`}
              aria-label={`${n} star${n > 1 ? "s" : ""}`}
            >
              ★
            </button>
          ))}
        </div>

        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Optional comment..."
          className="mt-3 w-full rounded-lg border border-gray-300 p-2 text-sm outline-none focus:border-blue-500"
          rows={3}
        />

        <label className="mt-2 flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" checked={escalate} onChange={(e) => setEscalate(e.target.checked)} />
          Escalate to a human agent
        </label>
        {escalate && (
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Your email (optional, creates a support ticket)"
            className="mt-2 w-full rounded-lg border border-gray-300 p-2 text-sm outline-none focus:border-blue-500"
          />
        )}

        {status === "error" && (
          <p className="mt-2 text-xs text-red-600">Could not submit. Please try again.</p>
        )}
        {status === "done" && <p className="mt-2 text-xs text-green-600">Thank you!</p>}

        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100">
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={status === "sending" || (rating === 0 && !escalate)}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  );
}
