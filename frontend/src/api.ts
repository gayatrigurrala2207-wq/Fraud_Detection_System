import { useCallback, useEffect, useRef, useState } from "react";

export type DependencyStatus = "ok" | "missing" | "failed" | "not_available" | "not_configured";
export type RiskLevel = "low" | "medium" | "elevated" | "high";
export type FeedStatus = "cleared" | "flagged" | "confirmed_fraud" | "legitimate";

export interface Health {
  status: string;
  version: string;
  environment: string;
  dependencies: { name: string; status: DependencyStatus; detail: string }[];
}

export interface FileSummary {
  rows: number;
  label_counts: Record<"0" | "1", number>;
  timestamp_min: string;
  timestamp_max: string;
  malformed_rows: number;
  duplicate_transaction_id_rows: number;
  out_of_order_rows: number;
}

export interface DatasetValidation {
  archive_sha256: string;
  passed: boolean;
  train_ends_before_test: boolean;
  warnings: string[];
  columns: number;
  files: Record<string, FileSummary>;
}

export interface ActiveSettings {
  version: string;
  settings: { key: string; value: string; description: string; source: string }[];
}

export interface Transaction {
  id: number;
  trans_num: string;
  event_time: string;
  processed_at: string;
  merchant: string;
  category: string;
  amount: number;
  state: string | null;
  score: number;
  risk_level: RiskLevel;
  source: "replay" | "simulated";
  latency_ms: number;
  case_id: number | null;
  status: FeedStatus;
}

export interface Overview {
  model_version: string | null;
  threshold: number | null;
  processed: { count: number; value: number; queued: number; simulated: number;
    event_window: { start: string | null; end: string | null } };
  flagged: { count: number; value: number; rate: number | null };
  high_risk: { count: number };
  risk_distribution: Record<RiskLevel, number>;
  potential_fraud_value: number;
  outcomes: {
    predicted: { flagged: number; cleared: number };
    confirmed: { fraud: number; legitimate: number; unreviewed: number };
    review_coverage: number | null;
    alert_precision: number | null;
    min_reviewed_for_precision: number;
  };
  latency: { mean_ms: number | null; p95_ms: number | null; samples: number };
  timeline: { hour: string; processed: number; flagged: number }[];
  recent_alerts: { id: number; event_time: string; merchant: string; category: string; amount: number;
    score: number; risk_level: RiskLevel; case_id: number }[];
  definitions: Record<string, string>;
}

export interface CaseSummary {
  id: number;
  status: "open" | "resolved";
  disposition: "fraud" | "legitimate" | null;
  created_at: string;
  transaction_id: number;
  event_time: string;
  merchant: string;
  category: string;
  amount: number;
  score: number;
  risk_level: RiskLevel;
  source: "replay" | "simulated";
  notes: number;
}

export interface Contribution { feature: string; label: string; value: string | number | null; contribution: number }
export interface Explanation { base_value: number; unit: string; contributions: Contribution[] }

export interface CaseDetail {
  case: { id: number; status: "open" | "resolved"; disposition: "fraud" | "legitimate" | null;
    created_at: string; updated_at: string };
  transaction: { id: number; trans_num: string; event_time: string; processed_at: string; merchant: string;
    category: string; amount: number; state: string | null; card_key: string | null; source: string;
    score: number; risk_level: RiskLevel; threshold: number; model_version: string; latency_ms: number };
  explanation: Explanation | null;
  anomalies: { label: string; display: string; percentile_in_reference: number | null; unusual: boolean }[];
  anomaly_reference: string | null;
  history: { id: number; event_time: string; merchant: string; category: string; amount: number;
    score: number | null; risk_level: RiskLevel | null; status: string | null }[];
  notes: { id: number; author: string; body: string; created_at: string }[];
  audit: { id: number; actor: string; action: string; detail: string | null; created_at: string }[];
}

export interface RateRow { transactions: number; fraud: number; fraud_rate: number; amount: number }

export interface Analytics {
  population: string;
  time_window: { start: string; end: string };
  outcome_source: string;
  totals: { transactions: number; fraud: number; amount: number };
  monthly: (RateRow & { month: string })[];
  by_category: (RateRow & { category: string })[];
  by_hour: (RateRow & { hour: string })[];
  by_weekday: (RateRow & { weekday: string })[];
  by_state: (RateRow & { state: string })[];
  by_amount: (RateRow & { bucket: string })[];
  spending_anomaly: (RateRow & { bucket: string })[];
  score_distribution: { population: string; time_window: { start: string | null; end: string | null };
    outcome_source: string; bins: { bucket: string; transactions: number }[]; total: number };
}

export interface Metrics {
  threshold: number; precision: number; recall: number; f1: number; pr_auc: number; roc_auc: number;
  false_positive_rate: number; confusion_matrix: { tp: number; fp: number; fn: number; tn: number };
  alerts: number; missed_fraud_amount: number; cost: number; rows: number; fraud_rows: number;
}

export interface ModelReport {
  version: string;
  active_version: string | null;
  trained_at: string;
  selected_model: string;
  best_validation_model: string;
  selection_rule: string;
  threshold: number;
  threshold_rule: string;
  partitions: Record<"train" | "validation" | "test", { start: string; end: string; rows: number; fraud: number }>;
  comparison: { name: string; family: string; description: string; fit_seconds: number; validation: Metrics }[];
  test: Metrics & { pr: { x: number; y: number }[]; roc: { x: number; y: number }[] };
  feature_importance: { feature: string; label: string; mean_abs_shap: number; gain_share: number }[];
  latency: { p50_ms: number; p95_ms: number; samples: number; conditions: string };
  not_compared: string[];
}

export interface Monitoring {
  drift: { reference_window: string; current_window: string;
    items: { feature: string; label: string; psi: number; status: "stable" | "moderate" | "significant" }[] } | null;
  drift_rows: number;
  min_drift_rows: number;
  drift_method: string;
  confirmed_performance: { reviewed: number; fraud: number; legitimate: number; alert_precision: number | null;
    note: string };
  experiments: { run_id: string; trained_at: string; selected_model: string; threshold: number;
    test: { pr_auc: number; roc_auc: number; recall: number; precision: number; f1: number };
    validation: Record<string, { pr_auc: number; roc_auc: number; recall: number; precision: number }> }[];
}

export interface ReplayStatus {
  running: boolean; speed: number; total: number; processed: number; remaining: number;
  last_event_time: string | null;
}

export type Role = "viewer" | "analyst" | "admin";

export interface User {
  id: number;
  username: string;
  display_name: string;
  role: Role;
  active: boolean;
  created_at: string;
  last_login_at: string | null;
}

const RANK: Record<Role, number> = { viewer: 0, analyst: 1, admin: 2 };
export const hasRole = (user: User | null, minimum: Role) => !!user && RANK[user.role] >= RANK[minimum];

/** Fired when the server says the session is missing or expired; the auth provider returns to sign-in. */
export const UNAUTHORIZED_EVENT = "fraudshield:unauthorized";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      credentials: "same-origin",
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error("Cannot reach the backend. Is it running on port 8000?");
  }
  const body = await response.json().catch(() => null);
  if (response.status === 401 && !path.startsWith("/auth/")) {
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
  if (!response.ok) {
    const detail = body?.detail;
    if (typeof detail === "string") throw new Error(detail);
    if (Array.isArray(detail)) {
      // FastAPI validation errors: name the field and the problem.
      throw new Error(detail.map((d: { loc?: string[]; msg?: string }) =>
        `${String(d.loc?.at(-1) ?? "value").replaceAll("_", " ")}: ${d.msg ?? "invalid"}`).join("; "));
    }
    throw new Error(`Request failed with status ${response.status}.`);
  }
  return body as T;
}

export function get<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function post<T>(path: string, data: unknown = {}): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(data) });
}

export function patch<T>(path: string, data: unknown): Promise<T> {
  return request<T>(path, { method: "PATCH", body: JSON.stringify(data) });
}
type State<T> = { state: "loading" } | { state: "error"; message: string } | { state: "ready"; data: T };
type Result<T> = State<T> & { reload: () => void };

/** Fetch an endpoint, optionally re-polling. Keeps the last good data visible while refreshing. */
export function useApi<T>(path: string, refreshMs?: number): Result<T> {
  const [state, setState] = useState<State<T>>({ state: "loading" });
  const generation = useRef(0);

  const load = useCallback(() => {
    const current = ++generation.current;
    request<T>(path)
      .then((data) => current === generation.current && setState({ state: "ready", data }))
      .catch((error: Error) => current === generation.current &&
        setState((previous) => previous.state === "ready" && refreshMs ? previous : { state: "error", message: error.message }));
  }, [path, refreshMs]);

  useEffect(() => {
    setState({ state: "loading" });
    load();
    if (!refreshMs) return () => void generation.current++;
    const timer = window.setInterval(load, refreshMs);
    return () => {
      window.clearInterval(timer);
      generation.current++;
    };
  }, [load, refreshMs]);

  return { ...state, reload: load } as Result<T>;
}
