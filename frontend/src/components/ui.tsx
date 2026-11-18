import { AlertTriangle, Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import type { DependencyStatus } from "../api";

export function PageHeader({ title, requirement, children }: { title: string; requirement: string; children?: ReactNode }) {
  return (
    <header className="mb-6">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{requirement}</p>
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      {children && <p className="mt-1 max-w-3xl text-sm text-slate-600">{children}</p>}
    </header>
  );
}

export function Card({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      {title && <h2 className="mb-3 text-sm font-semibold text-slate-700">{title}</h2>}
      {children}
    </section>
  );
}

const STATUS_STYLES: Record<DependencyStatus, { label: string; className: string }> = {
  ok: { label: "OK", className: "bg-emerald-50 text-emerald-800 ring-emerald-600/30" },
  missing: { label: "Missing", className: "bg-amber-50 text-amber-800 ring-amber-600/30" },
  failed: { label: "Failed", className: "bg-red-50 text-red-800 ring-red-600/30" },
  not_available: { label: "Not available yet", className: "bg-slate-100 text-slate-700 ring-slate-500/30" },
  not_configured: { label: "Not configured yet", className: "bg-slate-100 text-slate-700 ring-slate-500/30" },
};

/** Status always shows a text label alongside its color. */
export function StatusBadge({ status }: { status: DependencyStatus }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.not_available;
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${style.className}`}>
      {style.label}
    </span>
  );
}

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

export function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
      {note && <p className="mt-1 text-xs text-slate-500">{note}</p>}
    </div>
  );
}
