import { useCallback, useEffect, useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { useChatStream, type ChatMessage } from "../../hooks/useChatStream";
import { fetchHistory } from "../../hooks/useConversations";

export interface CustomerLayoutContext {
  chat: ReturnType<typeof useChatStream>;
  selectConversation: (sessionId: string) => Promise<void>;
  onOpenSidebar: () => void;
}

export function CustomerLayout() {
  const chat = useChatStream();
  const navigate = useNavigate();
  const location = useLocation();
  // Mobile/tablet off-canvas drawer state. Desktop (lg+) ignores this and pins the sidebar.
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const closeSidebar = useCallback(() => setSidebarOpen(false), []);
  const openSidebar = useCallback(() => setSidebarOpen(true), []);

  // Close the drawer whenever the route changes (e.g. after tapping a nav link).
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

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

      setSidebarOpen(false);
      if (location.pathname !== "/") {
        navigate("/");
      }
    },
    [chat, navigate, location.pathname],
  );

  const handleNewChat = useCallback(() => {
    chat.reset();
    setSidebarOpen(false);
    if (location.pathname !== "/") {
      navigate("/");
    }
  }, [chat, navigate, location.pathname]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#030712] font-sans text-slate-100">
      {/* Backdrop overlay — mobile/tablet only, closes the drawer on tap */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      {/* Persisted Sidebar: static column on desktop, off-canvas drawer below lg */}
      <Sidebar
        activeSessionId={location.pathname === "/" ? chat.sessionId : null}
        onSelectConversation={selectConversation}
        onNewChat={handleNewChat}
        isOpen={sidebarOpen}
        onClose={closeSidebar}
      />

      {/* Render children dynamically */}
      <div className="relative flex h-full min-w-0 flex-1 flex-col overflow-hidden">
        <Outlet
          context={
            { chat, selectConversation, onOpenSidebar: openSidebar } satisfies CustomerLayoutContext
          }
        />
      </div>
    </div>
  );
}
