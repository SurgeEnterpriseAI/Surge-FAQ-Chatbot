import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { LogIn, Key, Mail, ShieldAlert, Sparkles, UserCheck } from "lucide-react";

import { useAuth } from "../hooks/useAuth";
import { supabaseEnabled } from "../lib/supabase";

export function LoginPage() {
  const { loginWithEmail, loginWithGoogle, loginAsGuest } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async (fn: () => Promise<void>) => {
    setError(null);
    setBusy(true);
    try {
      await fn();
      navigate("/");
    } catch (e: unknown) {
      const err = e as { response?: { status?: number; data?: { detail?: string } } };
      const status = err.response?.status;
      const detail = err.response?.data?.detail;

      let message: string;
      if (detail) {
        message = detail;
      } else if (!err.response || (status && status >= 500)) {
        // No response (server booting / network) or a transient 5xx with no detail.
        message = "The server is still starting up or is temporarily unavailable. Please try again in a moment.";
      } else {
        message = e instanceof Error ? e.message : "Login failed";
      }
      setError(message);
    } finally {
      setBusy(false);
    }
  };

  const submitEmail = (e: FormEvent) => {
    e.preventDefault();
    void run(() => loginWithEmail(email, password));
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center p-4 bg-[#030712] overflow-hidden">
      {/* Decorative background blur shapes */}


      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="w-full max-w-md rounded-lg border border-white/10 bg-slate-900 p-8"
      >
        <div className="flex flex-col items-center justify-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-600 text-white">
            <Sparkles className="h-6 w-6" />
          </div>
          <h1 className="mt-4 text-2xl font-bold tracking-tight text-white">
            Enterprise AI Suite
          </h1>
          <p className="mt-1 text-sm text-slate-400 font-medium">
            Agentic RAG & Multi-Agent Operations
          </p>
        </div>

        <form onSubmit={submitEmail} className="mt-8 space-y-4">
          <div className="relative">
            <Mail className="absolute left-3 top-3 h-5 w-5 text-slate-500" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@enterprise.com"
              className="w-full rounded-lg border border-white/5 bg-white/5 pl-10 pr-4 py-2.5 text-sm font-medium outline-none transition-all focus:border-blue-500/50 focus:bg-white/[0.08]"
              required
            />
          </div>

          <div className="relative">
            <Key className="absolute left-3 top-3 h-5 w-5 text-slate-500" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="🔑 Enter password"
              className="w-full rounded-lg border border-white/5 bg-white/5 pl-10 pr-4 py-2.5 text-sm font-medium outline-none transition-all focus:border-blue-500/50 focus:bg-white/[0.08]"
              required
            />
          </div>

          <button
            type="submit"
            disabled={busy}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-3 text-sm font-semibold text-white transition-all hover:opacity-95 disabled:opacity-50"
          >
            <LogIn className="h-4 w-4" />
            {busy ? "Authenticating..." : "Sign in with email"}
          </button>
        </form>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center" aria-hidden="true">
            <div className="w-full border-t border-white/5"></div>
          </div>
          <div className="relative flex justify-center text-xs font-semibold uppercase">
            <span className="bg-slate-900/0 px-2 text-slate-500">Or integrate with</span>
          </div>
        </div>

        <div className="space-y-3">
          {supabaseEnabled && (
            <button
              onClick={() => void run(loginWithGoogle)}
              disabled={busy}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/5 py-2.5 text-sm font-medium text-slate-350 transition-all hover:bg-white/[0.08] disabled:opacity-50"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l3.66-2.85z" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
              </svg>
              Google Workspace
            </button>
          )}

          <button
            onClick={() => void run(loginAsGuest)}
            disabled={busy}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-white/5 bg-slate-950 py-2.5 text-sm font-medium text-slate-400 transition-all hover:bg-slate-950/60 disabled:opacity-50"
          >
            <UserCheck className="h-4 w-4" />
            Access Demo Environment
          </button>
        </div>

        {error && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs font-medium text-red-400"
          >
            <ShieldAlert className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}

