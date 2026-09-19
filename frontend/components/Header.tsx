"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Cpu,
  LogOut,
  ChevronDown,
  Shield,
  Zap,
  Activity,
  User,
  Radio,
} from "lucide-react";

interface HeaderProps {
  userEmail: string;
  onSignOut: () => void;
  streamPaused: boolean;
  onToggleStream: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  userEmail,
  onSignOut,
  streamPaused,
  onToggleStream,
}) => {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <header className="sticky top-0 z-30 w-full border-b border-white/10 bg-obsidian/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Brand & Product Identifier */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500/20 to-emerald-500/20 border border-cyan-500/30 text-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.25)]">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-white tracking-tight text-sm sm:text-base">
                  FT-04
                </span>
                <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-mono uppercase rounded-md bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  Algorithmic Dunning
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                Autonomous Churn Mitigation & Optimization Layer
              </p>
            </div>
          </div>

          <div className="h-4 w-px bg-white/10 hidden md:block" />

          {/* Engine Status Pill */}
          <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-900/60 border border-white/5 text-xs text-slate-300">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="font-mono text-[11px] text-emerald-400">
              CatBoost & Circuit Breaker Active
            </span>
          </div>
        </div>

        {/* Right: Actions & User Avatar */}
        <div className="flex items-center gap-3">
          {/* Stream Status Toggle */}
          <button
            onClick={onToggleStream}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium border transition-colors ${
              streamPaused
                ? "bg-amber-500/10 border-amber-500/30 text-amber-300 hover:bg-amber-500/20"
                : "bg-cyan-500/10 border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20"
            }`}
            title={streamPaused ? "Resume Live Ingestion" : "Pause Live Ingestion"}
          >
            <Radio className={`w-3.5 h-3.5 ${!streamPaused ? "animate-pulse" : ""}`} />
            <span>{streamPaused ? "Stream Paused" : "Live Ingestion"}</span>
          </button>

          {/* User Profile Dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 p-1.5 sm:px-2.5 rounded-xl bg-slate-900/60 hover:bg-slate-800/60 border border-white/10 transition-colors"
            >
              <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center text-white text-xs font-semibold shadow-inner">
                {userEmail ? userEmail[0].toUpperCase() : "U"}
              </div>
              <span className="text-xs text-slate-300 max-w-[120px] truncate hidden md:block">
                {userEmail || "Engineer"}
              </span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-xl glass-panel p-2 shadow-2xl border border-white/15 bg-slate-950/95 backdrop-blur-xl animate-fade-in">
                <div className="px-3 py-2 border-b border-white/10">
                  <p className="text-[11px] uppercase tracking-wider text-slate-400 font-mono">
                    Active Session
                  </p>
                  <p className="text-xs font-medium text-white truncate mt-0.5">
                    {userEmail}
                  </p>
                  <div className="mt-1.5 flex items-center gap-1.5 text-[10px] text-emerald-400 font-mono">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    <span>Role: Principal ML Engineer</span>
                  </div>
                </div>

                <div className="py-1">
                  <div className="px-3 py-2 text-[11px] text-slate-400 flex items-center justify-between font-mono">
                    <span>Region</span>
                    <span className="text-slate-200">US-East (Low Latency)</span>
                  </div>
                  <div className="px-3 py-1.5 text-[11px] text-slate-400 flex items-center justify-between font-mono">
                    <span>Model Sync</span>
                    <span className="text-cyan-400">Calibrated (Isotonic)</span>
                  </div>
                </div>

                <div className="pt-1 border-t border-white/10">
                  <button
                    onClick={() => {
                      setDropdownOpen(false);
                      onSignOut();
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

