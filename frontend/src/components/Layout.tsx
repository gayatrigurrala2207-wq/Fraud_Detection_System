import {
  Activity,
  BarChart3,
  Brain,
  BriefcaseBusiness,
  Gauge,
  HeartPulse,
  LayoutDashboard,
  PlayCircle,
  LogOut,
  Settings,
  ShieldCheck,
  UserCog,
  Users,
  type LucideIcon,
} from "lucide-react";
import { Suspense } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { hasRole, useApi, type ReplayStatus } from "../api";
import { useAuth } from "../auth";
import { Loading } from "./ui";

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

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `flex shrink-0 items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
    isActive ? "bg-navy-800 text-white" : "text-slate-300 hover:bg-navy-900 hover:text-white"
  }`;

function UserMenu() {
  const { user, logout } = useAuth();
  if (!user) return null;
  const initials = user.display_name.split(/\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase();
  return (
    <div className="flex items-center gap-3 border-t border-navy-800 px-4 py-3">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-sky-600 text-sm font-semibold text-white" aria-hidden>
        {initials}
      </span>
      <Link to="/account" className="min-w-0 flex-1 hover:text-white">
        <span className="block truncate text-sm font-medium text-white">{user.display_name}</span>
        <span className="block text-xs capitalize text-slate-400">{user.role}</span>
      </Link>
      <button type="button" onClick={() => void logout()} title="Sign out" aria-label="Sign out"
              className="rounded-md p-2 text-slate-400 hover:bg-navy-900 hover:text-white">
        <LogOut className="size-4" />
      </button>
    </div>
  );
}

export default function Layout() {
  const { user } = useAuth();
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="flex flex-col bg-navy-950 text-slate-200 md:sticky md:top-0 md:h-screen md:w-60 md:shrink-0">
        <div className="flex items-center gap-2 px-5 py-4 text-white">
          <ShieldCheck className="size-6 text-sky-400" aria-hidden />
          <span className="text-lg font-semibold tracking-tight">FraudShield</span>
        </div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-1 md:flex-col md:overflow-y-auto">
          {NAVIGATION.map(({ path, label, icon: Icon }) => (
            <NavLink key={path} to={path} end={path === "/"} className={linkClass}>
              <Icon className="size-4" aria-hidden />
              {label}
            </NavLink>
          ))}
          <p className="mt-4 hidden px-3 text-[11px] font-medium uppercase tracking-wider text-slate-500 md:block">Account</p>
          <NavLink to="/account" className={linkClass}><UserCog className="size-4" aria-hidden />Account</NavLink>
          {hasRole(user, "admin") && <NavLink to="/users" className={linkClass}><Users className="size-4" aria-hidden />Users</NavLink>}
        </nav>
        <ReplayIndicator />
        <UserMenu />
      </aside>
      <main className="min-w-0 flex-1 px-4 py-6 md:px-8">
        <div className="mx-auto max-w-6xl">
          <Suspense fallback={<Loading />}><Outlet /></Suspense>
        </div>
      </main>
    </div>
  );
}
