"use client";

import React from "react";
import {
  Webhook,
  DollarSign,
  TrendingUp,
  Server,
  Zap,
  CheckCircle2,
  AlertTriangle,
  ArrowUpRight,
} from "lucide-react";
import { TelemetryKPIs } from "../lib/types";
import { formatCurrency } from "../lib/utils";
import { MetricsSparkline } from "./MetricsSparkline";

interface CommandRibbonProps {
  kpis: TelemetryKPIs;
}

export const CommandRibbon: React.FC<CommandRibbonProps> = ({ kpis }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* 1. Intercepted Webhooks */}
      <div className="rounded-2xl glass-panel p-4 sm:p-5 relative overflow-hidden group hover:border-cyan-500/30 transition-all duration-200">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Webhook className="w-4 h-4" />
            </span>
            <span className="text-xs font-medium text-slate-400">
              Intercepted Webhooks
            </span>
          </div>
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono text-cyan-400 bg-cyan-500/10 border border-cyan-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            LIVE
          </span>
        </div>

        <div className="flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-bold font-mono text-white tracking-tight">
            {kpis.interceptedWebhooks.toLocaleString()}
          </span>
          <span className="text-xs font-mono text-cyan-400">events</span>
        </div>

        <div className="mt-3 flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-white/5">
          <div className="flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-cyan-400" />
            <span className="font-mono text-slate-200">
              {kpis.webhookRatePerSec}
            </span>
            <span>tx/sec rate</span>
          </div>
          <span className="text-[11px] font-mono text-emerald-400">99.98% uptime</span>
        </div>
      </div>

      {/* 2. Protected Monthly Recurring Revenue */}
      <div className="rounded-2xl glass-panel p-4 sm:p-5 relative overflow-hidden group hover:border-emerald-500/30 transition-all duration-200">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <DollarSign className="w-4 h-4" />
            </span>
            <span className="text-xs font-medium text-slate-400">
              Protected MRR
            </span>
          </div>
          <span className="text-[10px] font-mono font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
            ARR SHIELD
          </span>
        </div>

        <div className="flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-bold font-mono text-emerald-400 tracking-tight">
            {formatCurrency(kpis.protectedMRR)}
          </span>
        </div>

        <div className="mt-3 flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-white/5">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span className="font-mono text-slate-200">
              {kpis.recoveredAccounts.toLocaleString()}
            </span>
            <span>accounts recovered</span>
          </div>
          <span className="text-[11px] font-mono text-cyan-400">zero penalty</span>
        </div>
      </div>

      {/* 3. Mean Recovery Delta & Sparkline */}
      <div className="rounded-2xl glass-panel p-4 sm:p-5 relative overflow-hidden group hover:border-indigo-500/30 transition-all duration-200">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <TrendingUp className="w-4 h-4" />
            </span>
            <span className="text-xs font-medium text-slate-400">
              Mean Recovery Delta
            </span>
          </div>
          <div className="flex items-center gap-0.5 text-xs font-mono font-semibold text-emerald-400">
            <ArrowUpRight className="w-3.5 h-3.5" />
            <span>+{kpis.meanRecoveryDelta}%</span>
          </div>
        </div>

        <div className="flex items-end justify-between mt-1">
          <div>
            <div className="text-2xl sm:text-3xl font-bold font-mono text-white tracking-tight">
              +{kpis.meanRecoveryDelta}%
            </div>
            <div className="text-[11px] text-slate-400 font-mono mt-0.5">
              vs naive static dunning
            </div>
          </div>
          {/* Micro Sparkline */}
          <div className="pb-1">
            <MetricsSparkline data={kpis.sparklineHistory} color="#10B981" height={36} />
          </div>
        </div>

        <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-white/5 font-mono">
          <span>Baseline: 11.2%</span>
          <span className="text-cyan-400">Optimized: 44.7%</span>
        </div>
      </div>

      {/* 4. Active Multi-Gateway Routing Status */}
      <div className="rounded-2xl glass-panel p-4 sm:p-5 relative overflow-hidden group hover:border-white/20 transition-all duration-200">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-white/5 text-slate-300 border border-white/10">
              <Server className="w-4 h-4" />
            </span>
            <span className="text-xs font-medium text-slate-400">
              Acquiring Gateways
            </span>
          </div>
          <span className="text-[10px] font-mono text-slate-400 bg-white/5 px-2 py-0.5 rounded-full border border-white/10">
            4 POOLS
          </span>
        </div>

        {/* 4 Gateway Status Pills */}
        <div className="grid grid-cols-2 gap-2">
          {kpis.gateways.map((gw) => (
            <div
              key={gw.name}
              className="px-2.5 py-1.5 rounded-xl bg-slate-900/80 border border-white/5 hover:border-white/15 transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-200">
                  {gw.name}
                </span>
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    gw.status === "optimal"
                      ? "bg-emerald-400 animate-pulse"
                      : "bg-cyan-400"
                  }`}
                />
              </div>
              <div className="flex items-center justify-between mt-1 text-[10px] font-mono text-slate-400">
                <span className="text-emerald-400">{gw.latencyMs}ms</span>
                <span>{gw.loadPct}% load</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

