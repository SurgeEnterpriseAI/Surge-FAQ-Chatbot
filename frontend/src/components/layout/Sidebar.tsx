import { NavLink, useNavigate } from "react-router-dom";
import { MessageSquare, LayoutGrid, User, LogOut, Terminal } from "lucide-react";
import { motion } from "framer-motion";

import { useAuth } from "../../hooks/useAuth";
import { ConversationList } from "./ConversationList";

interface Props {
  activeSessionId: string | null;
  onSelectConversation: (sessionId: string) => void;
  onNewChat: () => void;
}

export function Sidebar({ activeSessionId, onSelectConversation, onNewChat }: Props) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const isAdmin = user?.is_admin || user?.email?.includes("admin");

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-white/5 bg-slate-950/65 select-none">
      {/* Brand Header */}
      <div className="flex items-center gap-2 px-6 py-5 border-b border-white/5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 shrink-0">
          <Terminal className="h-4.5 w-4.5 text-white shrink-0" />
        </div>
        <div className="min-w-0">
          <span className="font-extrabold text-white text-sm tracking-tight block truncate">
            AETHER FLOW
          </span>
          <span className="text-[10px] text-slate-500 font-bold block uppercase tracking-wider truncate">
            Enterprise Ops
          </span>
        </div>
      </div>

      {/* New Chat Button Trigger */}
      <div className="p-4 border-b border-white/5">
        <button
          onClick={onNewChat}
          className="flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:opacity-95 shrink-0"
        >
          <MessageSquare className="h-4.5 w-4.5 shrink-0" />
          <span className="truncate">New Session</span>
        </button>
      </div>

      {/* Scrollable Conversation List */}
      <div className="flex-1 overflow-y-auto min-h-0 py-2 scrollbar-thin">
        <div className="px-4 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
          Recent Sessions
        </div>
        <ConversationList activeSessionId={activeSessionId} onSelect={onSelectConversation} />
      </div>

      {/* Navigation Footnotes Links */}
      <nav className="space-y-1 border-t border-white/5 p-4 shrink-0">
        <NavLink
          to="/"
          end
          className="relative group flex h-10 items-center gap-3 rounded-lg px-4 py-2 text-sm font-medium text-slate-400 hover:text-slate-100 transition-colors duration-150 shrink-0"
        >
          {({ isActive }) => (
            <>
              {isActive && (
                <motion.div
                  layoutId="sidebar-active-indicator"
                  className="absolute inset-0 rounded-lg bg-white/5 border border-white/10 -z-10"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                />
              )}
              <MessageSquare className={`h-4.5 w-4.5 shrink-0 transition-colors duration-150 ${isActive ? "text-purple-400" : "text-slate-500 group-hover:text-slate-350"}`} />
              <span className={`truncate transition-colors duration-150 ${isActive ? "text-white" : "text-slate-400 group-hover:text-slate-200"}`}>
                Assistant Chat
              </span>
            </>
          )}
        </NavLink>

        {isAdmin && (
          <NavLink
            to="/admin"
            className="relative group flex h-10 items-center gap-3 rounded-lg px-4 py-2 text-sm font-medium text-slate-400 hover:text-slate-100 transition-colors duration-150 shrink-0"
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.div
                    layoutId="sidebar-active-indicator"
                    className="absolute inset-0 rounded-lg bg-white/5 border border-white/10 -z-10"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <LayoutGrid className={`h-4.5 w-4.5 shrink-0 transition-colors duration-150 ${isActive ? "text-purple-400" : "text-slate-500 group-hover:text-slate-350"}`} />
                <span className={`truncate transition-colors duration-150 ${isActive ? "text-white" : "text-slate-400 group-hover:text-slate-200"}`}>
                  Operations Center
                </span>
              </>
            )}
          </NavLink>
        )}

        <NavLink
          to="/profile"
          className="relative group flex h-10 items-center gap-3 rounded-lg px-4 py-2 text-sm font-medium text-slate-400 hover:text-slate-100 transition-colors duration-150 shrink-0"
        >
          {({ isActive }) => (
            <>
              {isActive && (
                <motion.div
                  layoutId="sidebar-active-indicator"
                  className="absolute inset-0 rounded-lg bg-white/5 border border-white/10 -z-10"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                />
              )}
              <User className={`h-4.5 w-4.5 shrink-0 transition-colors duration-150 ${isActive ? "text-purple-400" : "text-slate-500 group-hover:text-slate-350"}`} />
              <span className={`truncate transition-colors duration-150 ${isActive ? "text-white" : "text-slate-400 group-hover:text-slate-200"}`}>
                Profile Detail
              </span>
            </>
          )}
        </NavLink>

        {/* User Card & Logout Trigger */}
        <div className="border-t border-white/5 mt-3 pt-3 flex items-center justify-between text-xs shrink-0">
          <div className="flex flex-col min-w-0 max-w-[130px]">
            <span className="font-semibold text-slate-350 truncate">
              {user?.name || "Support Guest"}
            </span>
            <span className="text-[10px] text-slate-500 truncate">
              {user?.email || "Guest User"}
            </span>
          </div>
          <button
            onClick={handleLogout}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-red-500/10 hover:text-red-400 transition-all shrink-0"
            title="Log out"
          >
            <LogOut className="h-4.5 w-4.5 shrink-0" />
          </button>
        </div>
      </nav>
    </aside>
  );
}
