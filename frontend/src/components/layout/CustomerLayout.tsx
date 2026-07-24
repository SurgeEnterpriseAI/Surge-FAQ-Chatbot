import { useCallback } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { useChatStream, type ChatMessage } from "../../hooks/useChatStream";
import { fetchHistory } from "../../hooks/useConversations";

export interface CustomerLayoutContext {
  chat: ReturnType<typeof useChatStream>;
  selectConversation: (sessionId: string) => Promise<void>;
}

export function CustomerLayout() {
  const chat = useChatStream();
  const navigate = useNavigate();
  const location = useLocation();

  const selectConversation = useCallback(
    async (sessionId: string) => {
      try {
        const history = await fetchHistory(sessionId);
        const messages: ChatMessage[] = history.messages.map((m) => ({
          id: m.id,
          role: m.role === "user" ? "user" : "assistant",
          content: m.content,
          agentSteps: m.metadata?.agentSteps || [],
          tools: m.metadata?.tools || [],
          sources: m.metadata?.sources || [],
          safety: m.metadata?.safety || null,
          escalationRequired: m.metadata?.escalationRequired || false,
        }));
        chat.loadHistory(sessionId, messages);
      } catch {
        chat.loadHistory(sessionId, []);
      }

      if (location.pathname !== "/") {
        navigate("/");
      }
    },
    [chat, navigate, location.pathname],
  );

  const handleNewChat = useCallback(() => {
    chat.reset();
    if (location.pathname !== "/") {
      navigate("/");
    }
  }, [chat, navigate, location.pathname]);

  return (
    <div className="flex h-screen w-screen bg-[#030712] text-slate-100 overflow-hidden font-sans">
      {/* Persisted Sidebar */}
      <Sidebar
        activeSessionId={location.pathname === "/" ? chat.sessionId : null}
        onSelectConversation={selectConversation}
        onNewChat={handleNewChat}
      />
      
      {/* Render children dynamically */}
      <div className="flex-1 flex flex-col min-w-0 relative h-full overflow-hidden">
        <Outlet context={{ chat, selectConversation } satisfies CustomerLayoutContext} />
      </div>
    </div>
  );
}
