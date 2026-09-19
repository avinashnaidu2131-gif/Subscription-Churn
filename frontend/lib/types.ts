export type DeclineCategory =
  | "hard_decline"
  | "soft_liquidity"
  | "soft_technical"
  | "soft_authorization";

export type TransactionStatus =
  | "intercepted"
  | "rescheduled"
  | "circuit_tripped";

export type SubscriptionTier = "Enterprise" | "Pro" | "Growth" | "Starter";

export interface SHAPFeature {
  feature: string;
  value: string | number;
  formattedAttribution: string;
  attributionPct: number;
}

export interface SHAPExplanation {
  baseValue: number;
  predictionMargin: number;
  topPositiveFeatures: SHAPFeature[];
  topNegativeFeatures: SHAPFeature[];
  rationale: string;
}

export interface CircuitBreakerMeta {
  isUnrecoverable: boolean;
  routingAction: string;
  reason: string;
  suggestedAction: string;
}

export interface TransactionItem {
  id: string;
  timestamp: string;
  customerEmail: string;
  subscriptionTier: SubscriptionTier;
  invoiceAmount: number;
  declineCode: string;
  declineCategory: DeclineCategory;
  issuingBank: string;
  cardNetwork: "visa" | "mastercard" | "amex" | "rupay";
  cardType: "debit" | "credit" | "prepaid";
  binCountry: string;
  status: TransactionStatus;
  routingAction: string;
  currentGateway: string;
  targetGateway: string;
  targetTime: string;
  targetTimeFormatted: string;
  retryAttempt: number;
  successProbability: number;
  baselineProbability: number;
  recoveryLift: number;
  expectedValue: number;
  gatewayAuthFee: number;
  fatigueCost: number;
  isTerminal: boolean;
  shapExplanation: SHAPExplanation | null;
  circuitBreaker: CircuitBreakerMeta | null;
}

export interface GatewayStatus {
  name: string;
  latencyMs: number;
  loadPct: number;
  status: "healthy" | "degraded" | "optimal";
  fee: number;
}

export interface TelemetryKPIs {
  interceptedWebhooks: number;
  webhookRatePerSec: number;
  protectedMRR: number;
  recoveredAccounts: number;
  meanRecoveryDelta: number;
  sparklineHistory: { value: number }[];
  gateways: GatewayStatus[];
}

export interface TestScenario {
  id: string;
  label: string;
  tier: SubscriptionTier;
  amount: number;
  code: string;
  bank: string;
  description: string;
}

