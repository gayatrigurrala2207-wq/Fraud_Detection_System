import { Activity, BriefcaseBusiness, Eye, EyeOff, Loader2, Lock, ShieldCheck, Sparkles } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";
import { useAuth } from "../auth";

const FEATURES = [
  { icon: Activity, title: "Real-time scoring", text: "Replay held-out card transactions through a validated LightGBM model." },
  { icon: Sparkles, title: "Explainable alerts", text: "Every flagged transaction shows the SHAP factors behind its score." },
  { icon: BriefcaseBusiness, title: "Audited investigations", text: "Label, annotate, and resolve cases with an attributed audit trail." },
];

function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <aside className="relative hidden overflow-hidden bg-navy-950 px-12 py-10 text-slate-200 lg:flex lg:flex-col">
        <div className="flex items-center gap-2 text-white">
          <ShieldCheck className="size-7 text-sky-400" aria-hidden />
          <span className="text-xl font-semibold tracking-tight">FraudShield</span>
        </div>
        <div className="my-auto max-w-md">
          <h1 className="text-3xl font-semibold leading-tight tracking-tight text-white">
            Fraud detection and investigation, in one workspace.
          </h1>
          <p className="mt-3 text-slate-400">
            Score transactions, understand every alert, and close cases with evidence your team can audit.
          </p>
          <ul className="mt-10 space-y-6">
            {FEATURES.map(({ icon: Icon, title: heading, text }) => (
              <li key={heading} className="flex gap-4">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-navy-800 text-sky-300">
                  <Icon className="size-5" aria-hidden />
                </span>
                <span><span className="block font-medium text-white">{heading}</span>
                  <span className="text-sm text-slate-400">{text}</span></span>
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-slate-500">Local deployment · data stays on this machine</p>
        <div className="pointer-events-none absolute -right-24 -bottom-24 size-96 rounded-full bg-sky-500/10 blur-3xl" aria-hidden />
      </aside>

      <main className="flex items-center justify-center bg-slate-50 px-4 py-10">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2 lg:hidden">
            <ShieldCheck className="size-7 text-sky-600" aria-hidden />
            <span className="text-xl font-semibold tracking-tight">FraudShield</span>
          </div>
          <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
          <p className="mt-1 mb-6 text-sm text-slate-600">{subtitle}</p>
          {children}
        </div>
      </main>
    </div>
  );
}

function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <div className="mt-1">{children}</div>
      {hint && <span className="mt-1 block text-xs font-normal text-slate-500">{hint}</span>}
    </label>
  );
}

const input = "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm outline-none focus:border-sky-600 focus:ring-2 focus:ring-sky-600/20";

function PasswordInput({ value, onChange, autoComplete, minLength }: {
  value: string; onChange: (v: string) => void; autoComplete: string; minLength?: number;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <input type={visible ? "text" : "password"} required value={value} minLength={minLength} autoComplete={autoComplete}
             onChange={(e) => onChange(e.target.value)} className={`${input} pr-10`} />
      <button type="button" onClick={() => setVisible(!visible)} aria-label={visible ? "Hide password" : "Show password"}
              className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-400 hover:text-slate-700">
        {visible ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
      </button>
    </div>
  );
}

function SubmitButton({ busy, children }: { busy: boolean; children: ReactNode }) {
  return (
    <button type="submit" disabled={busy}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-navy-900 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-navy-800 disabled:opacity-60">
      {busy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Lock className="size-4" aria-hidden />}
      {children}
    </button>
  );
}

function FormError({ message }: { message: string | null }) {
  return message ? <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-800">{message}</p> : null;
}

export function Login() {
  const { login, sessionExpired } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username, password);
    } catch (e) {
      setError((e as Error).message);
      setPassword("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout title="Sign in" subtitle="Use the account your FraudShield administrator created for you.">
      <form onSubmit={submit} className="space-y-4">
        {sessionExpired && <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-900">Your session ended. Please sign in again.</p>}
        <FormError message={error} />
        <Field label="Username">
          <input required autoFocus autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} className={input} />
        </Field>
        <Field label="Password"><PasswordInput value={password} onChange={setPassword} autoComplete="current-password" /></Field>
        <SubmitButton busy={busy}>Sign in</SubmitButton>
        <p className="text-center text-xs text-slate-500">Forgot your password? Ask an administrator to reset it.</p>
      </form>
    </AuthLayout>
  );
}

export function Setup() {
  const { setup, minPasswordLength } = useAuth();
  const [form, setForm] = useState({ username: "", displayName: "", password: "", confirm: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (form.password !== form.confirm) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await setup(form.username, form.displayName, form.password);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout title="Create the administrator account"
                subtitle="First-time setup. This account can add analysts and viewers afterwards.">
      <form onSubmit={submit} className="space-y-4">
        <FormError message={error} />
        <Field label="Full name">
          <input required autoFocus maxLength={60} value={form.displayName} onChange={(e) => setForm({ ...form, displayName: e.target.value })} className={input} />
        </Field>
        <Field label="Username" hint="3-32 characters: letters, numbers, dot, dash, underscore.">
          <input required minLength={3} maxLength={32} pattern="[A-Za-z0-9._\-]+" autoComplete="username" value={form.username}
                 onChange={(e) => setForm({ ...form, username: e.target.value })} className={input} />
        </Field>
        <Field label="Password" hint={`At least ${minPasswordLength} characters.`}>
          <PasswordInput value={form.password} minLength={minPasswordLength} autoComplete="new-password" onChange={(v) => setForm({ ...form, password: v })} />
        </Field>
        <Field label="Confirm password">
          <PasswordInput value={form.confirm} minLength={minPasswordLength} autoComplete="new-password" onChange={(v) => setForm({ ...form, confirm: v })} />
        </Field>
        <SubmitButton busy={busy}>Create account and sign in</SubmitButton>
      </form>
    </AuthLayout>
  );
}
