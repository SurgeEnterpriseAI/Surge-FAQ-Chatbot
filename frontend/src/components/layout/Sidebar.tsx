import type { ComponentType } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { MessageSquare, LayoutGrid, User, LogOut, Stethoscope } from "lucide-react";
import { motion } from "framer-motion";

import { useAuth } from "../../hooks/useAuth";
import { ConversationList } from "./ConversationList";

interface Props {
  activeSessionId: string | null;
  onSelectConversation: (sessionId: string) => void;
  onNewChat: () => void;
  isOpen: boolean;
  onClose: () => void;
}

interface NavItemProps {
  to: string;
  end?: boolean;
  icon: ComponentType<{ className?: string }>;
  label: string;
  onNavigate: () => void;
}

/** Single sidebar nav link with the shared animated active-pill indicator. */
function SidebarNavItem({ to, end, icon: Icon, label, onNavigate }: NavItemProps) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      className="relative group flex h-10 items-center gap-3 rounded-lg px-4 text-sm font-medium transition-colors duration-200"
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <motion.div
              layoutId="sidebar-active-indicator"
              className="absolute inset-0 -z-10 rounded-lg border border-white/10 bg-white/5"
              transition={{ type: "spring", stiffness: 380, damping: 30 }}
            />
          )}
          <Icon
            className={`h-4.5 w-4.5 shrink-0 transition-colors duration-200 ${
              isActive ? "text-purple-400" : "text-slate-500 group-hover:text-slate-300"
            }`}
          />
          <span
            className={`truncate transition-colors duration-200 ${
              isActive ? "text-white" : "text-slate-400 group-hover:text-slate-200"
            }`}
          >
            {label}
          </span>
        </>
      )}
    </NavLink>
  );
}

export function Sidebar({ activeSessionId, onSelectConversation, onNewChat, isOpen, onClose }: Props) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const isAdmin = user?.is_admin || user?.email?.includes("admin");

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 flex h-screen w-64 shrink-0 select-none flex-col border-r border-white/5 bg-slate-950 transition-transform duration-200 ease-out lg:static lg:z-auto lg:translate-x-0 ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      }`}
    >
      {/* Brand Header (fixed) */}
      <div className="flex shrink-0 items-center gap-2.5 border-b border-white/5 px-6 py-5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600">
          <Stethoscope className="h-4.5 w-4.5 text-white" />
        </div>
        <div className="min-w-0">
          <span className="block truncate text-sm font-extrabold tracking-tight text-white">
            Medical FAQ Chatbot
          </span>
          <span className="block truncate text-[10px] font-bold uppercase tracking-wider text-slate-500">
            AI Healthcare Assistant
          </span>
        </div>
      </div>

      {/* New Chat Button (fixed) */}
      <div className="shrink-0 border-b border-white/5 p-4">
        <button
          onClick={onNewChat}
          className="flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white transition-all duration-200 hover:opacity-95"
        >
          <MessageSquare className="h-4.5 w-4.5 shrink-0" />
          <span className="truncate">New Session</span>
        </button>
      </div>

      {/* Scrollable Conversation List (only this area scrolls) */}
      <div className="min-h-0 flex-1 overflow-y-auto py-2 scrollbar-thin">
        <div className="mb-1 px-4 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          Recent Sessions
        </div>
        <ConversationList activeSessionId={activeSessionId} onSelect={onSelectConversation} />
      </div>

      {/* Navigation + User Profile (fixed footer) */}
      <nav className="shrink-0 space-y-1 border-t border-white/5 p-4">
        <SidebarNavItem to="/" end icon={MessageSquare} label="Assistant Chat" onNavigate={onClose} />

        {isAdmin && (
          <SidebarNavItem to="/admin" icon={LayoutGrid} label="Operations Center" onNavigate={onClose} />
        )}

        <SidebarNavItem to="/profile" icon={User} label="Profile Detail" onNavigate={onClose} />

        {/* User Card & Logout */}
        <div className="mt-3 flex items-center justify-between border-t border-white/5 pt-3 text-xs">
          <div className="flex min-w-0 max-w-[130px] flex-col">
            <span className="truncate font-semibold text-slate-300">
              {user?.name || "Support Guest"}
            </span>
            <span className="truncate text-[10px] text-slate-500">
              {user?.email || "Guest User"}
            </span>
          </div>
          <button
            onClick={handleLogout}
            className="shrink-0 rounded-lg p-1.5 text-slate-500 transition-all duration-200 hover:bg-red-500/10 hover:text-red-400"
            title="Log out"
          >
            <LogOut className="h-4.5 w-4.5 shrink-0" />
          </button>
        </div>
      </nav>
    </aside>
  );
}
