"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Play,
  Pause,
  Trash2,
  Send,
  ChevronDown,
  ArrowRight,
  Filter,
  Search,
  CheckCircle,
  ShieldAlert,
  Clock,
  Sparkles,
  Zap,
} from "lucide-react";
import {
  DeclineCategory,
  TestScenario,
  TransactionItem,
} from "../lib/types";
import { TEST_SCENARIOS } from "../lib/mockData";
import { formatCurrency } from "../lib/utils";

interface LiveFeedProps {
  transactions: TransactionItem[];
  selectedTxnId: string | null;
  onSelectTransaction: (txn: TransactionItem) => void;
  streamPaused: boolean;
  onToggleStream: () => void;
  onClearFeed: () => void;
  onTriggerScenario: (scenarioId: string) => void;
}

export const LiveFeed: React.FC<LiveFeedProps> = ({
  transactions,
  selectedTxnId,
  onSelectTransaction,
  streamPaused,
  onToggleStream,
  onClearFeed,
  onTriggerScenario,
}) => {
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [scenarioDropdownOpen, setScenarioDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setScenarioDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Filter transactions
  const filteredTransactions = transactions.filter((txn) => {
    const matchesCategory =
      activeCategory === "all" || txn.declineCategory === activeCategory;
    const matchesSearch =
      searchQuery === "" ||
      txn.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      txn.customerEmail.toLowerCase().includes(searchQuery.toLowerCase()) ||
      txn.issuingBank.toLowerCase().includes(searchQuery.toLowerCase()) ||
      txn.declineCode.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const categoryCounts = {
    all: transactions.length,
    soft_liquidity: transactions.filter(
      (t) => t.declineCategory === "soft_liquidity"
    ).length,
    soft_technical: transactions.filter(
      (t) => t.declineCategory === "soft_technical"
    ).length,
    soft_authorization: transactions.filter(
      (t) => t.declineCategory === "soft_authorization"
    ).length,
    hard_decline: transactions.filter(
      (t) => t.declineCategory === "hard_decline"
    ).length,
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case "Enterprise":
        return "text-indigo-300 bg-indigo-500/10 border-indigo-500/20";
      case "Pro":
        return "text-cyan-300 bg-cyan-500/10 border-cyan-500/20";
      case "Growth":
        return "text-emerald-300 bg-emerald-500/10 border-emerald-500/20";
      default:
        return "text-slate-300 bg-white/5 border-white/10";
    }
  };

  return (
    <div className="rounded-2xl glass-panel border border-white/10 overflow-hidden bg-slate-950/70 shadow-2xl">
      {/* Action Toolbar */}
      <div className="p-4 sm:p-5 border-b border-white/10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 bg-slate-900/40">
        {/* Category Filters */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full lg:w-auto pb-1 lg:pb-0">
          {[
            { id: "all", label: "All Interceptions", count: categoryCounts.all },
            {
              id: "soft_liquidity",
              label: "Soft Liquidity",
              count: categoryCounts.soft_liquidity,
            },
            {
              id: "soft_technical",
              label: "Technical Backoff",
              count: categoryCounts.soft_technical,
            },
            {
              id: "soft_authorization",
              label: "Soft Authorization",
              count: categoryCounts.soft_authorization,
            },
            {
              id: "hard_decline",
              label: "Hard Declines",
              count: categoryCounts.hard_decline,
            },
          ].map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-all duration-150 flex items-center gap-1.5 ${
                activeCategory === cat.id
                  ? "bg-white/15 text-white shadow-sm border border-white/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
              }`}
            >
              <span>{cat.label}</span>
              <span
                className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${
                  activeCategory === cat.id
                    ? "bg-cyan-500/20 text-cyan-300"
                    : "bg-white/5 text-slate-500"
                }`}
              >
                {cat.count}
              </span>
            </button>
          ))}
        </div>

        {/* Action Controls & Trigger Scenario Dropdown */}
        <div className="flex items-center gap-2.5 w-full lg:w-auto justify-between lg:justify-end">
          {/* Search Box */}
          <div className="relative w-full sm:w-48">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search txn, bank..."
              className="w-full pl-8 pr-3 py-1.5 bg-slate-900/60 border border-white/10 rounded-xl text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/40"
            />
          </div>

          {/* Stream Pause/Play Toggle */}
          <button
            onClick={onToggleStream}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono border transition-colors ${
              streamPaused
                ? "bg-amber-500/10 border-amber-500/30 text-amber-300 hover:bg-amber-500/20"
                : "bg-white/5 border-white/10 text-slate-300 hover:bg-white/10"
            }`}
          >
            {streamPaused ? (
              <>
                <Play className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Resume</span>
              </>
            ) : (
              <>
                <Pause className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Pause</span>
              </>
            )}
          </button>

          {/* Clear Feed */}
          <button
            onClick={onClearFeed}
            className="p-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 border border-white/10 transition-colors"
            title="Clear Feed"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>

          {/* TRIGGER TEST WEBHOOK DROPDOWN */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setScenarioDropdownOpen(!scenarioDropdownOpen)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-gradient-to-r from-cyan-500 to-emerald-500 text-black hover:opacity-95 shadow-[0_0_15px_rgba(6,182,212,0.25)] transition-all active:scale-[0.99]"
            >
              <Zap className="w-3.5 h-3.5 fill-black" />
              <span>Trigger Test Webhook</span>
              <ChevronDown className="w-3.5 h-3.5 ml-0.5" />
            </button>

            {scenarioDropdownOpen && (
              <div className="absolute right-0 mt-2 w-80 rounded-2xl glass-panel p-2 shadow-2xl border border-white/15 bg-slate-950/95 backdrop-blur-2xl z-40 animate-fade-in">
                <div className="px-3 py-2 border-b border-white/10">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 font-semibold">
                    Simulate Gateway Webhook Payload
                  </span>
                </div>
                <div className="py-1 space-y-1 max-h-72 overflow-y-auto">
                  {TEST_SCENARIOS.map((sc) => (
                    <button
                      key={sc.id}
                      onClick={() => {
                        onTriggerScenario(sc.id);
                        setScenarioDropdownOpen(false);
                      }}
                      className="w-full text-left p-2.5 rounded-xl hover:bg-white/5 border border-transparent hover:border-white/10 transition-colors group"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-slate-100 group-hover:text-cyan-300">
                          {sc.label}
                        </span>
                        <span className="text-[10px] font-mono text-emerald-400">
                          {formatCurrency(sc.amount)}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1 line-clamp-1">
                        {sc.description}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Real-time Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="sticky top-0 z-10 border-b border-white/10 bg-slate-950/90 text-[11px] font-mono uppercase tracking-wider text-slate-400 backdrop-blur-md">
              <th className="py-3 px-4 sm:px-6">Status & Txn ID</th>
              <th className="py-3 px-4">Customer & Tier</th>
              <th className="py-3 px-4">Decline Code</th>
              <th className="py-3 px-4">Issuing Bank</th>
              <th className="py-3 px-4">Dynamic Target Route</th>
              <th className="py-3 px-4 text-right pr-6">ML Logic</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-xs font-sans">
            {filteredTransactions.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-slate-500">
                  <div className="flex flex-col items-center justify-center">
                    <Filter className="w-6 h-6 mb-2 text-slate-600" />
                    <p className="text-sm text-slate-400">
                      No intercepted transactions match this filter.
                    </p>
                    <p className="text-xs text-slate-600 mt-0.5">
                      Trigger a test webhook scenario above to simulate new traffic.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              filteredTransactions.map((txn) => {
                const isSelected = selectedTxnId === txn.id;
                const isHard = txn.declineCategory === "hard_decline";

                return (
                  <tr
                    key={txn.id}
                    onClick={() => onSelectTransaction(txn)}
                    className={`cursor-pointer transition-colors group ${
                      isSelected
                        ? "bg-cyan-500/10"
                        : "hover:bg-slate-900/60"
                    }`}
                  >
                    {/* Status & Txn ID */}
                    <td className="py-3.5 px-4 sm:px-6 whitespace-nowrap">
                      <div className="flex items-center gap-2.5">
                        {/* Status Dot */}
                        <span
                          className={`w-2 h-2 rounded-full shrink-0 ${
                            isHard
                              ? "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)]"
                              : "bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.6)]"
                          }`}
                        />
                        <div>
                          <span className="font-mono text-slate-200 group-hover:text-cyan-300 transition-colors font-medium">
                            {txn.id}
                          </span>
                          <span className="text-[10px] text-slate-500 block font-mono">
                            {txn.timestamp}
                          </span>
                        </div>
                      </div>
                    </td>

                    {/* Customer & Subscription Tier */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div>
                        <span className="text-slate-200 font-medium block truncate max-w-[160px]">
                          {txn.customerEmail}
                        </span>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span
                            className={`px-1.5 py-0.2 rounded text-[10px] font-mono border ${getTierColor(
                              txn.subscriptionTier
                            )}`}
                          >
                            {txn.subscriptionTier}
                          </span>
                          <span className="text-[11px] font-mono text-slate-400">
                            {formatCurrency(txn.invoiceAmount)}
                          </span>
                        </div>
                      </div>
                    </td>

                    {/* Decline Code Badge */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono ${
                          isHard
                            ? "bg-rose-500/10 text-rose-300 border border-rose-500/20"
                            : txn.declineCategory === "soft_technical"
                            ? "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                            : txn.declineCategory === "soft_authorization"
                            ? "bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"
                            : "bg-cyan-500/10 text-cyan-300 border border-cyan-500/20"
                        }`}
                      >
                        {txn.declineCode}
                      </span>
                    </td>

                    {/* Issuing Bank */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="text-slate-300 font-medium">
                        {txn.issuingBank}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono capitalize">
                        {txn.binCountry} • {txn.cardNetwork} ({txn.cardType})
                      </div>
                    </td>

                    {/* Dynamic Target Route */}
                    <td className="py-3.5 px-4 whitespace-nowrap font-mono text-xs">
                      {isHard ? (
                        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-rose-950/40 border border-rose-500/20 text-rose-300">
                          <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
                          <span>Direct Self-Serve • Circuit Tripped</span>
                        </div>
                      ) : (
                        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-xl bg-slate-900 border border-white/10 text-slate-300 group-hover:border-cyan-500/30">
                          <span className="text-cyan-400 font-semibold">
                            {txn.targetTimeFormatted}
                          </span>
                          <span className="text-slate-600">•</span>
                          <span className="text-slate-200 uppercase font-semibold">
                            {txn.targetGateway}
                          </span>
                          <span className="text-slate-600">•</span>
                          <span className="text-emerald-400 font-semibold">
                            +{(txn.recoveryLift * 100).toFixed(0)}% Lift
                          </span>
                        </div>
                      )}
                    </td>

                    {/* ML Logic Trigger */}
                    <td className="py-3.5 px-4 text-right pr-6 whitespace-nowrap">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectTransaction(txn);
                        }}
                        className="inline-flex items-center gap-1 text-xs font-mono text-slate-400 group-hover:text-cyan-400 transition-colors"
                      >
                        <span>Inspect Logic</span>
                        <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

