import { Link } from "react-router-dom";
import { User, Shield, Key, Mail, Fingerprint } from "lucide-react";

import { useAuth } from "../hooks/useAuth";

export function ProfilePage() {
  const { user } = useAuth();

  return (
    <>
      {/* Decorative background glows */}

      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto p-8 relative">
        <div className="max-w-xl mx-auto w-full mt-10 space-y-6">
          
          {/* Header title */}
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white">
              <User className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-tight text-white">Account Profile</h2>
              <p className="text-xs text-slate-500 mt-0.5">Manage your credential credentials & role permissions</p>
            </div>
          </div>

          {/* Profile details glass card */}
          <div className="rounded-lg border border-white/5 bg-slate-900 p-6 space-y-5">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4">
              <div className="h-12 w-12 rounded-lg bg-white/5 flex items-center justify-center border border-white/10 text-slate-350">
                <span className="text-lg font-bold uppercase">{user?.email?.slice(0, 2) || "G"}</span>
              </div>
              <div>
                <span className="font-bold text-slate-200 block text-sm">{user?.name || "Support Guest"}</span>
                <span className="text-xs text-slate-555 block font-mono text-slate-500">{user?.email || "Guest Token Session"}</span>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 text-xs font-medium">
              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-white/[0.02]">
                <span className="text-slate-500 flex items-center gap-1.5">
                  <Fingerprint className="h-4 w-4 text-blue-400" />
                  User Identity Key
                </span>
                <span className="font-mono text-slate-300 select-all">{user?.user_id}</span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-white/[0.02]">
                <span className="text-slate-500 flex items-center gap-1.5">
                  <Mail className="h-4 w-4 text-purple-400" />
                  Primary Email
                </span>
                <span className="text-slate-300">{user?.email || "—"}</span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-white/[0.02]">
                <span className="text-slate-500 flex items-center gap-1.5">
                  <Key className="h-4 w-4 text-amber-400" />
                  Workspace Role
                </span>
                <span className={`rounded border px-2 py-0.5 text-[10px] font-bold ${
                  user?.is_admin
                    ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                    : "border-blue-500/20 bg-blue-500/10 text-blue-400"
                }`}>
                  {user?.is_admin ? "Administrator" : "Support Representative"}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-white/[0.02]">
                <span className="text-slate-500 flex items-center gap-1.5">
                  <Shield className="h-4 w-4 text-emerald-400" />
                  Session State
                </span>
                <span className="text-slate-300 font-bold">{user?.is_guest ? "Ephemeral Guest" : "Authenticated Session"}</span>
              </div>
            </div>
          </div>

          <div className="text-center">
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-white underline hover:no-underline transition-all"
            >
              ← Return to active Chat session
            </Link>
          </div>

        </div>
      </div>
    </>
  );
}

