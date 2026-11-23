import { Loader2, ShieldCheck } from "lucide-react";
import { lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { hasRole } from "./api";
import { AuthProvider, useAuth } from "./auth";
import Layout from "./components/Layout";
import { ErrorNotice } from "./components/ui";
import { Login, Setup } from "./pages/Login";

const Account = lazy(() => import("./pages/Account"));
const Analytics = lazy(() => import("./pages/Analytics"));
const CaseDetail = lazy(() => import("./pages/CaseDetail"));
const Cases = lazy(() => import("./pages/Cases"));
const Health = lazy(() => import("./pages/Health"));
const LiveFeed = lazy(() => import("./pages/LiveFeed"));
const Models = lazy(() => import("./pages/Models"));
const Monitoring = lazy(() => import("./pages/Monitoring"));
const Overview = lazy(() => import("./pages/Overview"));
const Replay = lazy(() => import("./pages/Replay"));
const Settings = lazy(() => import("./pages/Settings"));
const Users = lazy(() => import("./pages/Users"));

function Splash({ error }: { error?: string | null }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 px-4">
      <ShieldCheck className="size-10 text-sky-600" aria-hidden />
      {error ? <div className="max-w-sm"><ErrorNotice message={error} /></div>
        : <Loader2 className="size-5 animate-spin text-slate-400" aria-label="Loading" />}
    </div>
  );
}

function Gate() {
  const { state, error, user, setupRequired } = useAuth();
  if (state === "loading") return <Splash />;
  if (state === "error") return <Splash error={error} />;
  if (setupRequired) return <Setup />;
  if (!user) return <Login />;
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Overview />} />
        <Route path="/feed" element={<LiveFeed />} />
        <Route path="/cases" element={<Cases />} />
        <Route path="/cases/:caseId" element={<CaseDetail />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/models" element={<Models />} />
        <Route path="/monitoring" element={<Monitoring />} />
        <Route path="/replay" element={<Replay />} />
        <Route path="/health" element={<Health />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/account" element={<Account />} />
        {hasRole(user, "admin") && <Route path="/users" element={<Users />} />}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Gate />
    </AuthProvider>
  );
}
