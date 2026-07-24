import { useState, type FormEvent } from "react";
import { Send, Square } from "lucide-react";

interface Props {
  disabled: boolean;
  onSend: (message: string) => void;
  onStop?: () => void;
  streaming: boolean;
}

export function ChatInput({ disabled, onSend, onStop, streaming }: Props) {
  const [value, setValue] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!value.trim() || disabled) return;
    onSend(value);
    setValue("");
  };

  return (
    <form onSubmit={submit} className="mx-auto flex w-full max-w-3xl items-center gap-2 rounded-lg border border-white/5 bg-slate-900 p-2 focus-within:border-blue-500/30 transition-all duration-200">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Type a message or ask about invoice balance, tracking packages, system health..."
        className="flex-1 border-none bg-transparent px-3 py-2 text-sm outline-none text-slate-100 placeholder-slate-500 disabled:opacity-50"
        disabled={disabled}
      />
      {streaming && onStop ? (
        <button
          type="button"
          onClick={onStop}
          className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
          title="Stop streaming"
        >
          <Square className="h-4.5 w-4.5 fill-red-400" />
        </button>
      ) : (
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white hover:opacity-95 disabled:opacity-30 transition-all duration-200"
          title="Send message"
        >
          <Send className="h-4.5 w-4.5" />
        </button>
      )}
    </form>
  );
}

