import { useState, type FormEvent } from "react";
import { post } from "../api";
import { useAuth } from "../auth";
import { Button, Card, ErrorNotice, PageHeader, fmt } from "../components/ui";

const input = "mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm";

export default function Account() {
  const { user, minPasswordLength } = useAuth();
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setDone(false);
    if (form.next !== form.confirm) {
      setError("New passwords do not match.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await post("/auth/password", { current_password: form.current, new_password: form.next });
      setForm({ current: "", next: "", confirm: "" });
      setDone(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!user) return null;
  return (
    <>
      <PageHeader title="Account" requirement="Your profile" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Profile">
          <dl className="space-y-2 text-sm">
            {([["Name", user.display_name], ["Username", user.username], ["Role", user.role],
              ["Member since", fmt.time(user.created_at)], ["Last sign-in", fmt.time(user.last_login_at)]] as const).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3"><dt className="text-slate-500">{k}</dt><dd className={k === "Role" ? "capitalize" : ""}>{v}</dd></div>
            ))}
          </dl>
          <p className="mt-4 text-xs text-slate-500">Your username is recorded on every label, note, and resolution you make.</p>
        </Card>
        <Card title="Change password" subtitle="Changing it signs out your other sessions.">
          <form onSubmit={submit} className="space-y-3">
            {error && <ErrorNotice message={error} />}
            {done && <p className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">Password changed.</p>}
            <label className="block text-sm">Current password
              <input type="password" required autoComplete="current-password" value={form.current} onChange={(e) => setForm({ ...form, current: e.target.value })} className={input} /></label>
            <label className="block text-sm">New password
              <input type="password" required minLength={minPasswordLength} autoComplete="new-password" value={form.next} onChange={(e) => setForm({ ...form, next: e.target.value })} className={input} />
              <span className="text-xs text-slate-500">At least {minPasswordLength} characters.</span></label>
            <label className="block text-sm">Confirm new password
              <input type="password" required minLength={minPasswordLength} autoComplete="new-password" value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} className={input} /></label>
            <Button type="submit" variant="primary" disabled={busy}>Update password</Button>
          </form>
        </Card>
      </div>
    </>
  );
}
