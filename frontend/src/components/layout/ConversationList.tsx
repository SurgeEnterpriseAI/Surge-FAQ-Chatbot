import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { useConversations, useDeleteConversation } from "../../hooks/useConversations";
import { MessageSquare, Trash2 } from "lucide-react";

interface Props {
  activeSessionId: string | null;
  onSelect: (sessionId: string) => void;
}

// Global variable to persist scroll position across unmount/remount
let savedScrollTop = 0;

export function ConversationList({ activeSessionId, onSelect }: Props) {
  const { data: conversations, isLoading } = useConversations();
  const deleteConversation = useDeleteConversation();
  const containerRef = useRef<HTMLDivElement>(null);

  // Restore scroll position on mount
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = savedScrollTop;
    }
  }, []);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    savedScrollTop = e.currentTarget.scrollTop;
  };

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto px-3 space-y-1 scrollbar-thin"
    >
      {isLoading && <p className="px-3 text-xs text-slate-500">Loading sessions...</p>}
      {conversations?.length === 0 && (
        <p className="px-3 text-xs text-slate-500 font-medium">No active sessions.</p>
      )}
      <ul className="space-y-1">
        {conversations?.map((c) => {
          const isActive = c.id === activeSessionId;
          return (
            <li key={c.id} className="group relative flex items-center h-8" title={c.title || "Session Thread"}>
              <button
                onClick={() => onSelect(c.id)}
                className="w-full relative h-8 rounded-lg px-3 py-1.5 text-left text-xs font-medium transition-colors duration-150 flex items-center gap-2 text-slate-400 hover:text-slate-100 min-w-0"
              >
                {isActive && (
                  <motion.div
                    layoutId="session-active-indicator"
                    className="absolute inset-0 rounded-lg bg-white/5 border border-white/5 -z-10"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <MessageSquare className={`h-3.5 w-3.5 shrink-0 transition-colors duration-150 ${isActive ? "text-purple-400" : "text-slate-500 group-hover:text-slate-350"}`} />
                <span className={`truncate transition-colors duration-150 ${isActive ? "text-white font-semibold" : "text-slate-400 group-hover:text-slate-200"}`}>
                  {c.title ?? "Untitled Session"}
                </span>
              </button>
              <button
                onClick={() => deleteConversation.mutate(c.id)}
                className="absolute right-2 opacity-0 group-hover:opacity-100 rounded p-1 text-slate-500 hover:bg-red-500/15 hover:text-red-400 transition-all duration-150 shrink-0"
                title="Delete session"
              >
                <Trash2 className="h-3.5 w-3.5 shrink-0" />
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
