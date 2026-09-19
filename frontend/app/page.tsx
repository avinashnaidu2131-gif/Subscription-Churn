"use client";

import React, { useState, useEffect } from "react";
import { AuthView } from "../components/AuthView";
import { Header } from "../components/Header";
import { CommandRibbon } from "../components/CommandRibbon";
import { LiveFeed } from "../components/LiveFeed";
import { DecisionDrawer } from "../components/DecisionDrawer";
import {
  INITIAL_KPIS,
  INITIAL_TRANSACTIONS,
  createScenarioTransaction,
} from "../lib/mockData";
import { TelemetryKPIs, TransactionItem } from "../lib/types";

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [userEmail, setUserEmail] = useState<string>("");
  const [transactions, setTransactions] =
    useState<TransactionItem[]>(INITIAL_TRANSACTIONS);
  const [kpis, setKpis] = useState<TelemetryKPIs>(INITIAL_KPIS);
  const [selectedTransaction, setSelectedTransaction] =
    useState<TransactionItem | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [streamPaused, setStreamPaused] = useState(false);

  // Check persisted session from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem("ft04_session");
      if (stored) {
        const parsed = JSON.parse(stored);
        setUserEmail(parsed.email || "developer@enterprise.io");
        setIsAuthenticated(true);
      } else {
        setIsAuthenticated(false);
      }
    } catch {
      setIsAuthenticated(false);
    }
  }, []);

  // Periodic streaming simulation when stream is not paused
  useEffect(() => {
    if (!isAuthenticated || streamPaused) return;

    const interval = setInterval(() => {
      // Pick a realistic random scenario
      const scenarioPool = [
        "chase_debit_funds",
        "stripe_timeout",
        "svb_do_not_honor",
        "barclays_payday",
      ];
      const randScenario =
        scenarioPool[Math.floor(Math.random() * scenarioPool.length)];
      const newTxn = createScenarioTransaction(randScenario);

      setTransactions((prev) => [newTxn, ...prev.slice(0, 30)]);

      setKpis((prev) => ({
        ...prev,
        interceptedWebhooks: prev.interceptedWebhooks + 1,
        protectedMRR: prev.protectedMRR + (newTxn.expectedValue > 0 ? newTxn.expectedValue : 0),
        recoveredAccounts:
          prev.recoveredAccounts + (newTxn.expectedValue > 0 ? 1 : 0),
        webhookRatePerSec: parseFloat(
          (40 + Math.random() * 5).toFixed(1)
        ),
      }));
    }, 14000);

    return () => clearInterval(interval);
  }, [isAuthenticated, streamPaused]);

  const handleAuthenticate = (user: { email: string; apiKey: string }) => {
    setUserEmail(user.email);
    setIsAuthenticated(true);
  };

  const handleSignOut = () => {
    localStorage.removeItem("ft04_session");
    setIsAuthenticated(false);
    setUserEmail("");
  };

  const handleSelectTransaction = (txn: TransactionItem) => {
    setSelectedTransaction(txn);
    setDrawerOpen(true);
  };

  const handleTriggerScenario = (scenarioId: string) => {
    const newTxn = createScenarioTransaction(scenarioId);
    setTransactions((prev) => [newTxn, ...prev]);

    setKpis((prev) => ({
      ...prev,
      interceptedWebhooks: prev.interceptedWebhooks + 1,
      protectedMRR: prev.protectedMRR + (newTxn.expectedValue > 0 ? newTxn.expectedValue : 0),
      recoveredAccounts:
        prev.recoveredAccounts + (newTxn.expectedValue > 0 ? 1 : 0),
    }));

    // Automatically inspect the newly triggered scenario
    setSelectedTransaction(newTxn);
    setDrawerOpen(true);
  };

  const handleClearFeed = () => {
    setTransactions([]);
  };

  // Prevent flash while reading localStorage
  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-cyan-500 border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthView onAuthenticate={handleAuthenticate} />;
  }

  return (
    <div className="min-h-screen bg-obsidian text-slate-100 flex flex-col selection:bg-cyan-500/20 selection:text-cyan-300">
      {/* Top Navbar */}
      <Header
        userEmail={userEmail}
        onSignOut={handleSignOut}
        streamPaused={streamPaused}
        onToggleStream={() => setStreamPaused(!streamPaused)}
      />

      {/* Main Dashboard Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {/* Workspace Title & Telemetry Status */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
              <span>Telemetry & Dunning Orchestrator</span>
              <span className="text-xs font-mono font-medium text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded-full border border-cyan-500/20">
                FT-04 Live
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Deterministic decline circuit breaker, Calibrated CatBoost ML, and Net EV schedule optimization.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>Multi-Gateway Active Routing:</span>
            <span className="text-slate-200">Stripe • Adyen • Braintree • Checkout</span>
          </div>
        </div>

        {/* 1. Command & Telemetry Ribbon */}
        <CommandRibbon kpis={kpis} />

        {/* 2. Live Interception Feed Table */}
        <LiveFeed
          transactions={transactions}
          selectedTxnId={selectedTransaction?.id || null}
          onSelectTransaction={handleSelectTransaction}
          streamPaused={streamPaused}
          onToggleStream={() => setStreamPaused(!streamPaused)}
          onClearFeed={handleClearFeed}
          onTriggerScenario={handleTriggerScenario}
        />
      </main>

      {/* 3. Deep-Dive Slide-Over Decision Drawer */}
      <DecisionDrawer
        transaction={selectedTransaction}
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  );
}

