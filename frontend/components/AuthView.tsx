"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  KeyRound,
  Mail,
  Zap,
  ArrowRight,
  Cpu,
  Lock,
  Sparkles,
} from "lucide-react";

interface AuthViewProps {
  onAuthenticate: (user: { email: string; apiKey: string }) => void;
}

export const AuthView: React.FC<AuthViewProps> = ({ onAuthenticate }) => {
  const [email, setEmail] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setIsLoading(true);
    setTimeout(() => {
      const session = {
        email: email || "developer@enterprise.io",
        apiKey: apiKey || "ak_live_9942a0fe...",
      };
      localStorage.setItem("ft04_session", JSON.stringify(session));
      setIsLoading(false);
      onAuthenticate(session);
    }, 400);
  };

  const handleLaunchDemo = () => {
    setIsLoading(true);
    const demoSession = {
      email: "principal-eng@hackathon.dev",
      apiKey: "ak_live_ft04_production_key_0x89",
    };
    localStorage.setItem("ft04_session", JSON.stringify(demoSession));
    setTimeout(() => {
      setIsLoading(false);
      onAuthenticate(demoSession);
    }, 300);
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center p-4 bg-obsidian overflow-hidden">
      {/* Background Ambient Grid & Radial Glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(6,182,212,0.15),rgba(255,255,255,0))]" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff05_1px,transparent_1px),linear-gradient(to_bottom,#ffffff05_1px,transparent_1px)] bg-[size:32px_32px]" />

      {/* Decorative Blur Orbs */}
      <div className="absolute -top-32 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Center Glass Card Container with Rotating Gradient Ring */}
      <div className="relative w-full max-w-md">
        {/* Animated Gradient Ring Border */}
        <div className="absolute -inset-0.5 rounded-2xl bg-gradient-to-r from-cyan-500 via-indigo-500 to-emerald-500 opacity-60 blur-sm animate-gradient-ring pointer-events-none" />

        <div className="relative rounded-2xl glass-panel p-8 shadow-2xl border border-white/10 bg-slate-950/80 backdrop-blur-2xl">
          {/* Header Brand */}
          <div className="flex flex-col items-center text-center mb-8">
            <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 mb-3 shadow-[0_0_15px_rgba(6,182,212,0.2)]">
              <Cpu className="w-6 h-6 animate-pulse" />
            </div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 mb-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
              FT-04 ML MIDDLEWARE v2.4
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-white">
              Algorithmic Dunning
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-xs">
              Autonomous passive churn mitigation & Net Expected Value recovery.
            </p>
          </div>

          {/* One-Click Hackathon Button (Primary Highlight) */}
          <button
            type="button"
            onClick={handleLaunchDemo}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2.5 py-3.5 px-4 rounded-xl font-medium text-sm text-black bg-gradient-to-r from-cyan-400 to-emerald-400 hover:from-cyan-300 hover:to-emerald-300 transition-all duration-200 shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_25px_rgba(6,182,212,0.5)] active:scale-[0.99] disabled:opacity-50 group"
          >
            <Zap className="w-4 h-4 fill-black text-black group-hover:scale-110 transition-transform" />
            <span>Launch Hackathon Demo Session</span>
            <ArrowRight className="w-4 h-4 ml-1 text-black group-hover:translate-x-1 transition-transform" />
          </button>

          {/* Divider */}
          <div className="relative my-6 text-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/10" />
            </div>
            <span className="relative px-3 text-[11px] uppercase tracking-wider text-slate-500 bg-slate-950 font-mono">
              or enter credentials
            </span>
          </div>

          {/* Manual Form */}
          <form onSubmit={handleManualSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Work Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="engineer@company.com"
                  className="w-full pl-10 pr-3.5 py-2.5 bg-slate-900/60 border border-white/10 rounded-xl text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/40 transition-colors"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-slate-300">
                  Middleware API Key
                </label>
                <span className="text-[11px] text-slate-500 font-mono">ak_live_...</span>
              </div>
              <div className="relative">
                <KeyRound className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="ak_live_79a2..."
                  className="w-full pl-10 pr-3.5 py-2.5 bg-slate-900/60 border border-white/10 rounded-xl text-sm font-mono text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/40 transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 rounded-xl font-medium text-sm text-slate-200 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 transition-all duration-150 active:scale-[0.99] disabled:opacity-50"
            >
              Authenticate Workspace
            </button>
          </form>

          {/* Security Footnote */}
          <div className="mt-6 pt-4 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-500">
            <div className="flex items-center gap-1">
              <Lock className="w-3 h-3 text-emerald-400/80" />
              <span>PCI-DSS Level 1</span>
            </div>
            <div className="flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 text-cyan-400/80" />
              <span>Circuit Breaker Active</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

