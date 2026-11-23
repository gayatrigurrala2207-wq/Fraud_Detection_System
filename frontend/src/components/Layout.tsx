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
import { useApi, type ReplayStatus } from "../api";

export interface NavItem {
  path: string;
  label: string;
  icon: LucideIcon;
  requirement: string;
}

/** The nine navigation areas required by FR-06 to FR-12. */
export const NAVIGATION: NavItem[] = [
  { path: "/", label: "Overview", icon: LayoutDashboard, requirement: "FR-06" },
  { path: "/feed", label: "Live Feed", icon: Activity, requirement: "FR-07" },
  { path: "/cases", label: "Cases", icon: BriefcaseBusiness, requirement: "FR-08" },
  { path: "/analytics", label: "Analytics", icon: BarChart3, requirement: "FR-09" },
  { path: "/models", label: "Models", icon: Brain, requirement: "FR-10" },
  { path: "/monitoring", label: "Monitoring", icon: Gauge, requirement: "FR-10" },
  { path: "/replay", label: "Replay & Simulator", icon: PlayCircle, requirement: "FR-11" },
  { path: "/health", label: "System Health", icon: HeartPulse, requirement: "FR-12" },
  { path: "/settings", label: "Settings", icon: Settings, requirement: "FR-12" },
];

function ReplayIndicator() {
  const replay = useApi<ReplayStatus>("/replay", 5000);
  if (replay.state !== "ready") return null;
  const { running, processed, total } = replay.data;
  return (
    <div className="hidden px-5 py-4 text-xs text-slate-400 md:block">
      <p className="flex items-center gap-2">
        <span className={`inline-block size-2 rounded-full ${running ? "bg-emerald-400" : "bg-slate-500"}`} aria-hidden />
        Replay {running ? "running" : "paused"}
      </p>
      <p className="mt-1 tabular-nums">{processed.toLocaleString()} / {total.toLocaleString()} scored</p>
    </div>
  );
}

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="flex flex-col bg-navy-950 text-slate-200 md:sticky md:top-0 md:h-screen md:w-60 md:shrink-0">
        <div className="flex items-center gap-2 px-5 py-4 text-white">
          <ShieldCheck className="size-6 text-sky-400" aria-hidden />
          <span className="text-lg font-semibold tracking-tight">FraudShield</span>
        </div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-1 md:flex-col md:overflow-visible">
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
        <ReplayIndicator />
      </aside>
      <main className="min-w-0 flex-1 px-4 py-6 md:px-8">
        <div className="mx-auto max-w-6xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
