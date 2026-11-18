import {
  Activity,
  BarChart3,
  Brain,
  BriefcaseBusiness,
  Gauge,
  HeartPulse,
  LayoutDashboard,
  PlayCircle,
  Settings,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

export interface NavItem {
  path: string;
  label: string;
  icon: LucideIcon;
  requirement: string;
  summary: string;
  phase: string;
}

/** The nine navigation areas required by FR-06 to FR-12. */
export const NAVIGATION: NavItem[] = [
  { path: "/", label: "Overview", icon: LayoutDashboard, requirement: "FR-06", phase: "Phase 9",
    summary: "Processed counts and value, flagged and high-risk counts, outcomes, potential fraud value, and latency." },
  { path: "/feed", label: "Live Feed", icon: Activity, requirement: "FR-07", phase: "Phase 9",
    summary: "Streaming transactions with ID, merchant, time, amount, score, risk level, and status. Pause, filter, and inspect." },
  { path: "/cases", label: "Cases", icon: BriefcaseBusiness, requirement: "FR-08", phase: "Phase 8",
    summary: "Risk evidence, SHAP explanations, behavioral anomalies, masked history, labels, notes, and audit events." },
  { path: "/analytics", label: "Analytics", icon: BarChart3, requirement: "FR-09", phase: "Phase 3",
    summary: "Fraud trends, category risk, geography, amounts, spending anomalies, and risk score distributions." },
  { path: "/models", label: "Models", icon: Brain, requirement: "FR-10", phase: "Phases 5-7",
    summary: "Active model version, model comparison, PR and ROC curves, confusion matrix, feature importance, and latency." },
  { path: "/monitoring", label: "Monitoring", icon: Gauge, requirement: "FR-10", phase: "Phase 11",
    summary: "Input and score drift against a reference window, and experiment tracking." },
  { path: "/replay", label: "Replay & Simulator", icon: PlayCircle, requirement: "FR-11", phase: "Phase 9",
    summary: "Replay original transactions at configurable speeds and score manually submitted, visibly simulated transactions." },
  { path: "/health", label: "System Health", icon: HeartPulse, requirement: "FR-12", phase: "Available",
    summary: "Service and dependency status." },
  { path: "/settings", label: "Settings", icon: Settings, requirement: "FR-12", phase: "Available",
    summary: "Active application configuration." },
];

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="bg-navy-950 text-slate-200 md:sticky md:top-0 md:h-screen md:w-60 md:shrink-0">
        <div className="flex items-center gap-2 px-5 py-4 text-white">
          <ShieldCheck className="size-6 text-sky-400" aria-hidden />
          <span className="text-lg font-semibold tracking-tight">FraudShield</span>
        </div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:overflow-visible">
          {NAVIGATION.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              end={path === "/"}
              className={({ isActive }) =>
                `flex shrink-0 items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive ? "bg-navy-800 text-white" : "text-slate-300 hover:bg-navy-900 hover:text-white"
                }`
              }
            >
              <Icon className="size-4" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 px-4 py-6 md:px-8">
        <div className="mx-auto max-w-6xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
