import { AlertTriangle, Hourglass, Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { DependencyStatus, FeedStatus, RiskLevel } from "../api";

export const fmt = {
  int: new Intl.NumberFormat("en-US"),
  money: new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }),
  compactMoney: new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }),
  pct: (value: number | null | undefined, digits = 1) => (value == null ? "—" : `${(value * 100).toFixed(digits)}%`),
  score: (value: number | null | undefined) => (value == null ? "—" : value.toFixed(3)),
  ms: (value: number | null | undefined) => (value == null ? "—" : `${value.toFixed(2)} ms`),
  time: (iso: string | null | undefined) => (iso ? new Date(iso).toLocaleString() : "—"),
};

export function PageHeader({ title, requirement, children, actions }: {
  title: string; requirement: string; children?: ReactNode; actions?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{requirement}</p>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {children && <p className="mt-1 max-w-3xl text-sm text-slate-600">{children}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

export function Card({ title, subtitle, children, actions }: {
  title?: string; subtitle?: ReactNode; children: ReactNode; actions?: ReactNode;
}) {
  return (
    <section className="min-w-0 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      {(title || actions) && (
        <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div>
            {title && <h2 className="text-sm font-semibold text-slate-800">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

const DEPENDENCY: Record<DependencyStatus, { label: string; className: string }> = {
  ok: { label: "OK", className: "bg-emerald-50 text-emerald-800 ring-emerald-600/30" },
  missing: { label: "Missing", className: "bg-amber-50 text-amber-900 ring-amber-600/30" },
  failed: { label: "Failed", className: "bg-red-50 text-red-800 ring-red-600/30" },
  not_available: { label: "Not available yet", className: "bg-slate-100 text-slate-700 ring-slate-500/30" },
  not_configured: { label: "Not configured", className: "bg-slate-100 text-slate-700 ring-slate-500/30" },
};

const RISK: Record<RiskLevel, { label: string; className: string }> = {
  low: { label: "Low", className: "bg-emerald-50 text-emerald-800 ring-emerald-600/30" },
  medium: { label: "Medium", className: "bg-amber-50 text-amber-900 ring-amber-600/30" },
  elevated: { label: "Elevated", className: "bg-orange-50 text-orange-900 ring-orange-600/30" },
  high: { label: "High", className: "bg-red-50 text-red-800 ring-red-600/30" },
};

const FEED: Record<FeedStatus, { label: string; className: string }> = {
  cleared: { label: "Cleared", className: "bg-slate-100 text-slate-700 ring-slate-500/30" },
  flagged: { label: "Flagged", className: "bg-orange-50 text-orange-900 ring-orange-600/30" },
  confirmed_fraud: { label: "Confirmed fraud", className: "bg-red-50 text-red-800 ring-red-600/30" },
  legitimate: { label: "Legitimate", className: "bg-emerald-50 text-emerald-800 ring-emerald-600/30" },
};

function Pill({ label, className }: { label: string; className: string }) {
  return (
    <span className={`inline-flex whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${className}`}>
      {label}
    </span>
  );
}

/** Every status shows a text label alongside its color. */
export const StatusBadge = ({ status }: { status: DependencyStatus }) => <Pill {...(DEPENDENCY[status] ?? DEPENDENCY.not_available)} />;
export const RiskBadge = ({ level }: { level: RiskLevel | null }) => (level ? <Pill {...RISK[level]} /> : <span className="text-slate-400">—</span>);
export const FeedBadge = ({ status }: { status: FeedStatus }) => <Pill {...FEED[status]} />;
export const SimulatedBadge = () => <Pill label="Simulated" className="bg-violet-50 text-violet-800 ring-violet-600/30" />;

export function Loading() {
  return (
    <p className="flex items-center gap-2 text-sm text-slate-500">
      <Loader2 className="size-4 animate-spin" aria-hidden /> Loading…
    </p>
  );
}

export function ErrorNotice({ message }: { message: string }) {
  return (
    <p role="alert" className="flex items-start gap-2 rounded-md bg-amber-50 p-3 text-sm text-amber-900">
      <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden /> {message}
    </p>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-center">
      <Hourglass className="size-8 text-slate-400" aria-hidden />
      <p className="font-medium">{title}</p>
      {children && <p className="max-w-md text-sm text-slate-600">{children}</p>}
    </div>
  );
}

export function Stat({ label, value, note }: { label: string; value: string; note?: ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
      {note && <p className="mt-1 text-xs text-slate-500">{note}</p>}
    </div>
  );
}

export function Button({ variant = "secondary", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger";
}) {
  const styles = {
    primary: "bg-navy-900 text-white hover:bg-navy-800",
    secondary: "bg-white text-slate-800 ring-1 ring-inset ring-slate-300 hover:bg-slate-50",
    danger: "bg-white text-red-700 ring-1 ring-inset ring-red-300 hover:bg-red-50",
  }[variant];
  return (
    <button
      type="button"
      className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
      {...props}
    />
  );
}

/** Render a fetch result: loading, error, or the ready view. */
export function Async<T>({ result, children }: {
  result: { state: "loading" } | { state: "error"; message: string } | { state: "ready"; data: T };
  children: (data: T) => ReactNode;
}) {
  if (result.state === "loading") return <Loading />;
  if (result.state === "error") return <ErrorNotice message={result.message} />;
  return <>{children(result.data)}</>;
}

export const th = "py-2 pr-4 text-xs font-medium text-slate-500";
export const td = "py-2 pr-4";
