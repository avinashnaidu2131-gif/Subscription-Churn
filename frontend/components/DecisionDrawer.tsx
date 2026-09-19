"use client";

import React, { useState } from "react";
import {
  X,
  ShieldAlert,
  TrendingUp,
  Info,
  Copy,
  Check,
  Calculator,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  Cell,
} from "recharts";

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

export interface SHAPFeaturePoint {
  feature: string;
  impact: number; // percentage: positive (+10B981) or negative (#F43F5E)
  value?: string | number;
}

export interface DecisionTransactionData {
  id: string;
  customerEmail?: string;
  subscriptionTier?: "Enterprise" | "Pro" | "Growth" | "Starter" | string;
  invoiceAmount?: number;
  declineCode?: string;
  issuingBank?: string;
  targetGateway?: string;
  targetTimeFormatted?: string;
  retryAttempt?: number;
  // Net EV Components
  successProbability?: number;
  baselineProbability?: number;
  gatewayAuthFee?: number;
  fatigueCost?: number;
  expectedValue?: number;
  baselineExpectedValue?: number;
  // Explanations & SHAP
  shapFeatures?: SHAPFeaturePoint[];
  aiRationale?: string;
  isCircuitTripped?: boolean;
  circuitBreakerReason?: string;
  // Fallbacks for nested objects
  shapExplanation?: {
    topPositiveFeatures?: Array<{ feature: string; attributionPct: number; value?: any }>;
    topNegativeFeatures?: Array<{ feature: string; attributionPct: number; value?: any }>;
    rationale?: string;
  } | null;
  circuitBreaker?: {
    isUnrecoverable?: boolean;
    reason?: string;
  } | null;
  [key: string]: any;
}

export interface DecisionDrawerProps {
  transaction?: DecisionTransactionData | null;
  isOpen: boolean;
  onClose: () => void;
}

// ============================================================================
// DEFAULT DUMMY DATA (For immediate testing & isolated preview)
// ============================================================================

const DUMMY_SHAP_DATA: SHAPFeaturePoint[] = [
  { feature: "Payday Proximity", impact: 28.4, value: "1st/15th Cycle" },
  { feature: "Stripe Routing", impact: 14.8, value: "US Direct" },
  { feature: "Issuer Settlement", impact: 12.2, value: "04:00 AM ACH" },
  { feature: "Invoice Friction", impact: -5.2, value: "$149.00 Tier" },
  { feature: "Attempt Fatigue", impact: -11.6, value: "k=2 Decay" },
];

const DEFAULT_TRANSACTION: DecisionTransactionData = {
  id: "txn_8f3a9e02c1",
  customerEmail: "alex.morgan@hypergrowth.io",
  subscriptionTier: "Enterprise",
  invoiceAmount: 149.0,
  declineCode: "insufficient_funds",
  issuingBank: "Chase",
  targetGateway: "Adyen",
  targetTimeFormatted: "Sun 04:00 AM Local",
  retryAttempt: 1,
  successProbability: 0.524,
  baselineProbability: 0.082,
  gatewayAuthFee: 0.12,
  fatigueCost: 0.5,
  expectedValue: 77.46,
  baselineExpectedValue: 11.6,
  shapFeatures: DUMMY_SHAP_DATA,
  aiRationale:
    "Shifted to Adyen at 04:00 AM to capitalize on payday liquidity (+28.4% attribution) and bypass issuer rate limits with local clearing.",
};

// ============================================================================
// COMPONENT: DecisionDrawer
// ============================================================================

export const DecisionDrawer: React.FC<DecisionDrawerProps> = ({
  transaction,
  isOpen,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  // Use provided transaction or fallback to demo dummy transaction
  const activeTxn: DecisionTransactionData = transaction || DEFAULT_TRANSACTION;

  // Extract Values with Safe Defaults
  const invoice = activeTxn.invoiceAmount ?? 149.0;
  const pOpt = activeTxn.successProbability ?? 0.524;
  const pBase = activeTxn.baselineProbability ?? 0.082;
  const authFee = activeTxn.gatewayAuthFee ?? 0.12;
  const fatigue = activeTxn.fatigueCost ?? 0.5;

  const optEV =
    activeTxn.expectedValue ?? pOpt * invoice - authFee - fatigue;

  const baseEV =
    activeTxn.baselineExpectedValue ?? pBase * invoice - authFee - fatigue;

  const financialLiftEV = optEV - baseEV;
  const liftPct = pBase > 0 ? (((pOpt - pBase) / pBase) * 100).toFixed(0) : "+33";

  // Check Circuit Breaker / Unrecoverable Hard Decline
  const isHardDecline = Boolean(
    activeTxn.isCircuitTripped ||
      activeTxn.circuitBreaker?.isUnrecoverable ||
      activeTxn.declineCategory === "hard_decline" ||
      activeTxn.status === "circuit_tripped" ||
      ["stolen_card", "lost_card", "fraudulent", "account_closed"].includes(
        activeTxn.declineCode || ""
      )
  );

  // Derive SHAP features or fallback to built-in dummy SHAP data
  let shapData: SHAPFeaturePoint[] = [];
  if (activeTxn.shapFeatures && activeTxn.shapFeatures.length > 0) {
    shapData = activeTxn.shapFeatures;
  } else if (activeTxn.shapExplanation) {
    const pos =
      activeTxn.shapExplanation.topPositiveFeatures?.map((f) => ({
        feature: f.feature,
        impact: Math.abs(f.attributionPct),
        value: f.value,
      })) ?? [];
    const neg =
      activeTxn.shapExplanation.topNegativeFeatures?.map((f) => ({
        feature: f.feature,
        impact: -Math.abs(f.attributionPct),
        value: f.value,
      })) ?? [];
    shapData = [...neg, ...pos];
  }

  if (shapData.length === 0) {
    shapData = DUMMY_SHAP_DATA;
  }

  // Sort: negative friction first, positive drivers last for clean vertical flow
  const sortedShapData = [...shapData].sort((a, b) => a.impact - b.impact);

  const aiRationale =
    activeTxn.aiRationale ||
    activeTxn.shapExplanation?.rationale ||
    "Shifted to Adyen at 04:00 AM to capitalize on payday liquidity and optimize acquiring route.";

  const tier = activeTxn.subscriptionTier || "Pro";

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(activeTxn, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden font-sans">
      {/* Dark Blurred Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/40 backdrop-blur-sm transition-opacity animate-fade-in"
      />

      {/* Slide-over Right Drawer */}
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10 pointer-events-none">
        <aside
          aria-label="Decision Logic Inspector"
          className="w-screen max-w-lg bg-slate-900 border-l border-white/10 shadow-2xl flex flex-col pointer-events-auto transform translate-x-0 transition-transform duration-300 ease-in-out overflow-y-auto"
        >
          {/* =============================================================== */}
          {/* HEADER                                                          */}
          {/* =============================================================== */}
          <header className="sticky top-0 z-20 px-6 py-5 border-b border-white/10 bg-slate-900/90 backdrop-blur-xl flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-cyan-400 tracking-tight">
                    {activeTxn.id}
                  </span>
                  {/* Customer Tier Badge */}
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                    {tier} Tier
                  </span>
                  {isHardDecline ? (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono uppercase font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                      Circuit Tripped
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      {activeTxn.declineCode || "Optimized"}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  {activeTxn.customerEmail || "customer@example.com"} •{" "}
                  {activeTxn.issuingBank || "Issuing Bank"}
                </p>
              </div>
            </div>

            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 border border-transparent hover:border-white/10 transition-colors"
              aria-label="Close drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </header>

          {/* =============================================================== */}
          {/* DRAWER BODY CONTENT                                             */}
          {/* =============================================================== */}
          <div className="p-6 space-y-6 flex-1 text-slate-200">
            {/* Quick Metadata Pill Strip */}
            <div className="grid grid-cols-3 gap-2.5 p-3.5 rounded-xl bg-slate-950/60 border border-white/5 font-mono text-xs">
              <div>
                <span className="text-[10px] text-slate-500 uppercase block">
                  Invoice
                </span>
                <span className="font-bold text-white text-sm">
                  ${invoice.toFixed(2)}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 uppercase block">
                  Route
                </span>
                <span className="font-semibold text-cyan-400 truncate block">
                  {activeTxn.targetGateway || "Adyen"}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 uppercase block">
                  Target Window
                </span>
                <span className="font-medium text-emerald-400 truncate block">
                  {activeTxn.targetTimeFormatted || "Immediate"}
                </span>
              </div>
            </div>

            {/* ------------------------------------------------------------- */}
            {/* HARD DECLINE CIRCUIT BREAKER ALERT                            */}
            {/* ------------------------------------------------------------- */}
            {isHardDecline && (
              <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-500/40 text-rose-200 space-y-2">
                <div className="flex items-center gap-2 font-semibold text-sm text-rose-300">
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                  <span>Unrecoverable Hard Decline • Zero ML Bypass</span>
                </div>
                <p className="text-xs text-rose-200/80 leading-relaxed">
                  {activeTxn.circuitBreakerReason ||
                    activeTxn.circuitBreaker?.reason ||
                    "Deterministic decline code detected. Machine learning inference was bypassed to eliminate card brand network fees and retry penalties."}
                </p>
                <div className="pt-2 border-t border-rose-500/20 flex items-center justify-between text-xs font-mono">
                  <span className="text-rose-300 font-medium">
                    Route: Customer Self-Serve Dunning
                  </span>
                  <span className="text-slate-400">P(success) = 0.0%</span>
                </div>
              </div>
            )}

            {/* ------------------------------------------------------------- */}
            {/* SECTION 1: NET EV BREAKDOWN (THE MATH)                        */}
            {/* ------------------------------------------------------------- */}
            {!isHardDecline && (
              <div className="rounded-2xl p-5 bg-white/[0.03] backdrop-blur-md border border-white/10 shadow-xl space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                      <Calculator className="w-4 h-4" />
                    </span>
                    <span className="text-xs font-mono uppercase tracking-wider text-cyan-300 font-semibold">
                      Net EV Breakdown (The Math)
                    </span>
                  </div>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                    +{liftPct}% Lift
                  </span>
                </div>

                {/* Mathematical Equation Display */}
                <div className="p-3.5 rounded-xl bg-slate-950/70 border border-white/10 font-mono text-xs text-slate-300 space-y-1.5">
                  <div className="text-[11px] text-slate-400">
                    EV = P(success) × Invoice - Auth Fee - Fatigue
                  </div>
                  <div className="text-sm font-semibold text-white">
                    = ({(pOpt * 100).toFixed(1)}% × ${invoice.toFixed(2)}) - ${authFee.toFixed(2)} - ${fatigue.toFixed(2)}
                  </div>
                  <div className="text-base font-bold text-emerald-400 pt-1.5 border-t border-white/10 flex items-center justify-between">
                    <span>Optimized EV:</span>
                    <span>+${optEV.toFixed(2)}</span>
                  </div>
                </div>

                {/* Side-by-Side Comparison: Baseline EV vs Optimized EV */}
                <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                  {/* Baseline EV Card */}
                  <div className="p-3.5 rounded-xl bg-slate-950/50 border border-white/5 space-y-1">
                    <span className="text-[10px] text-slate-400 uppercase block font-medium">
                      Baseline EV
                    </span>
                    <div className="text-slate-300 font-semibold text-sm">
                      {(pBase * 100).toFixed(1)}% odds
                    </div>
                    <div className="text-[12px] text-slate-400 font-mono">
                      EV: +${baseEV.toFixed(2)}
                    </div>
                    <span className="text-[10px] text-slate-500 block pt-1 border-t border-white/5">
                      Naive Immediate Retry
                    </span>
                  </div>

                  {/* Optimized EV Card */}
                  <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-emerald-400 uppercase font-semibold">
                        Optimized EV
                      </span>
                      <Sparkles className="w-3 h-3 text-emerald-400" />
                    </div>
                    <div className="text-emerald-300 font-bold text-sm">
                      {(pOpt * 100).toFixed(1)}% odds
                    </div>
                    <div className="text-[12px] text-emerald-400 font-bold font-mono">
                      EV: +${optEV.toFixed(2)}
                    </div>
                    <span className="text-[10px] text-emerald-500 block pt-1 border-t border-emerald-500/20 font-semibold">
                      Lift: +${financialLiftEV.toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* ------------------------------------------------------------- */}
            {/* SECTION 2: LOCAL SHAP ATTRIBUTION CHART                       */}
            {/* ------------------------------------------------------------- */}
            {!isHardDecline && (
              <div className="rounded-2xl p-5 bg-white/[0.03] backdrop-blur-md border border-white/10 shadow-xl space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      <TrendingUp className="w-4 h-4" />
                    </span>
                    <div>
                      <h3 className="text-xs font-mono uppercase tracking-wider text-emerald-300 font-semibold">
                        Local SHAP Attribution
                      </h3>
                      <p className="text-[11px] text-slate-400 font-mono">
                        TreeExplainer Margin Impact (%)
                      </p>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400 bg-white/5 px-2 py-0.5 rounded border border-white/10">
                    Mean Centered
                  </span>
                </div>

                {/* Horizontal Recharts BarChart (layout="vertical") */}
                <div className="h-60 w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      layout="vertical"
                      data={sortedShapData}
                      margin={{ top: 5, right: 30, left: 15, bottom: 5 }}
                    >
                      {/* Grid lines hidden for clean look */}
                      <XAxis
                        type="number"
                        domain={[-30, 35]}
                        tick={{ fill: "#64748B", fontSize: 10, fontFamily: "monospace" }}
                        axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
                        tickLine={false}
                        unit="%"
                      />
                      <YAxis
                        type="category"
                        dataKey="feature"
                        width={130}
                        tick={{ fill: "#CBD5E1", fontSize: 11, fontFamily: "monospace" }}
                        axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
                        tickLine={false}
                      />
                      <Tooltip
                        cursor={{ fill: "rgba(255, 255, 255, 0.04)" }}
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const data = payload[0].payload as SHAPFeaturePoint;
                            const isPos = data.impact >= 0;
                            return (
                              <div className="rounded-xl p-3 bg-slate-950/95 border border-white/20 shadow-2xl font-mono text-xs">
                                <p className="text-white font-semibold">{data.feature}</p>
                                {data.value && (
                                  <p className="text-slate-400 text-[11px] mt-0.5">
                                    Signal: <span className="text-slate-200">{String(data.value)}</span>
                                  </p>
                                )}
                                <p
                                  className={`mt-1 font-bold ${
                                    isPos ? "text-emerald-400" : "text-rose-400"
                                  }`}
                                >
                                  Impact: {isPos ? "+" : ""}
                                  {data.impact.toFixed(1)}%
                                </p>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <ReferenceLine x={0} stroke="rgba(255,255,255,0.25)" strokeWidth={1} />
                      <Bar dataKey="impact" radius={[4, 4, 4, 4]}>
                        {sortedShapData.map((entry, index) => (
                          <Cell
                            key={`shap-bar-${index}`}
                            fill={entry.impact >= 0 ? "#10B981" : "#F43F5E"}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Dynamic Color Legend */}
                <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-2 border-t border-white/10">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded bg-[#10B981]" />
                    <span>Positive Driver (#10B981)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded bg-[#F43F5E]" />
                    <span>Fatigue Friction (#F43F5E)</span>
                  </div>
                </div>
              </div>
            )}

            {/* ------------------------------------------------------------- */}
            {/* SECTION 3: AI REASONING BLOCK                                 */}
            {/* ------------------------------------------------------------- */}
            {!isHardDecline && (
              <div className="rounded-2xl p-5 bg-gradient-to-br from-slate-950/80 to-cyan-950/20 border border-cyan-500/20 shadow-xl space-y-2.5">
                <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-cyan-300 font-semibold">
                  <Info className="w-4 h-4 text-cyan-400" />
                  <span>AI Reasoning Block</span>
                </div>

                {/* Natural language string explaining routing decision */}
                <div className="p-3.5 rounded-xl bg-slate-950/80 border border-white/5 text-sm text-slate-200 leading-relaxed font-sans">
                  &ldquo;{aiRationale}&rdquo;
                </div>

                <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-slate-400 pt-1">
                  <span className="px-2.5 py-1 rounded-lg bg-slate-900 border border-white/10 text-cyan-300">
                    Route: {activeTxn.targetGateway?.toUpperCase() || "ADYEN"}
                  </span>
                  <span className="px-2.5 py-1 rounded-lg bg-slate-900 border border-white/10 text-emerald-300">
                    Window: {activeTxn.targetTimeFormatted || "04:00 AM"}
                  </span>
                  <span className="px-2.5 py-1 rounded-lg bg-slate-900 border border-white/10 text-slate-300">
                    Attempt #{activeTxn.retryAttempt ?? 1}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* =============================================================== */}
          {/* STICKY FOOTER ACTIONS                                           */}
          {/* =============================================================== */}
          <footer className="sticky bottom-0 p-4 sm:p-5 border-t border-white/10 bg-slate-900/90 backdrop-blur-xl flex items-center justify-between gap-3">
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-mono text-slate-300 bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Copied JSON</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy Payload</span>
                </>
              )}
            </button>

            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-black bg-cyan-400 hover:bg-cyan-300 transition-colors shadow-[0_0_15px_rgba(6,182,212,0.3)] active:scale-[0.99]"
            >
              Dismiss Inspector
            </button>
          </footer>
        </aside>
      </div>
    </div>
  );
};
