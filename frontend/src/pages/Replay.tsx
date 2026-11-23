import { FastForward, Pause, Play, RotateCcw } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { post, useApi, type Explanation, type ReplayStatus, type RiskLevel } from "../api";
import { Async, Button, Card, ErrorNotice, PageHeader, RiskBadge, SimulatedBadge, fmt } from "../components/ui";

const SPEEDS = [1, 5, 20, 50, 100];

export default function Replay() {
  const status = useApi<ReplayStatus>("/replay", 2000);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const command = async (body: object) => {
    setBusy(true);
    setError(null);
    try {
      await post("/replay", body);
      status.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader title="Replay & Simulator" requirement="FR-11">
        Replay the held-out transactions in event-time order at a chosen speed, or score a manual transaction.
        Manual entries are stored and shown as simulated.
      </PageHeader>
      {error && <div className="mb-4"><ErrorNotice message={error} /></div>}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Replay">
          <Async result={status}>
            {(s) => (
              <div className="space-y-4">
                <div>
                  <div className="mb-1 flex justify-between text-sm"><span>{s.running ? "Running" : s.remaining === 0 ? "Finished" : "Paused"}</span>
                    <span className="tabular-nums text-slate-600">{fmt.int.format(s.processed)} / {fmt.int.format(s.total)}</span></div>
                  <div className="h-2 rounded bg-slate-100" role="progressbar" aria-valuemin={0} aria-valuemax={s.total} aria-valuenow={s.processed}>
                    <div className="h-2 rounded bg-navy-800" style={{ width: `${s.total ? (s.processed / s.total) * 100 : 0}%` }} />
                  </div>
                  <p className="mt-1 text-xs text-slate-500">Replay clock: {s.last_event_time ?? "not started"}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {s.running ? <Button disabled={busy} onClick={() => command({ action: "pause" })}><Pause className="size-4" aria-hidden /> Pause</Button>
                    : <Button variant="primary" disabled={busy || s.remaining === 0} onClick={() => command({ action: "start" })}><Play className="size-4" aria-hidden /> Start</Button>}
                  <Button disabled={busy || s.remaining === 0} onClick={() => command({ action: "step", step_size: 1000 })}>
                    <FastForward className="size-4" aria-hidden /> Score next 1,000</Button>
                  <Button variant="danger" disabled={busy} onClick={() => {
                    if (confirm("Reset the replay? This deletes all scores, cases, notes, audit events, and simulated transactions.")) command({ action: "reset" });
                  }}><RotateCcw className="size-4" aria-hidden /> Reset</Button>
                </div>
                <label className="flex items-center gap-2 text-sm">Speed
                  <select value={s.speed} disabled={busy} onChange={(e) => command({ action: s.running ? "start" : "pause", speed: Number(e.target.value) })}
                          className="rounded-md border border-slate-300 bg-white px-2 py-1">
                    {[...new Set([...SPEEDS, s.speed])].sort((a, b) => a - b).map((v) => <option key={v} value={v}>{v} transactions / second</option>)}
                  </select>
                </label>
              </div>
            )}
          </Async>
        </Card>
        <Simulator />
      </div>
    </>
  );
}

interface SimResult { transaction_id: number; score: number; risk_level: RiskLevel; flagged: boolean; latency_ms: number;
  case_id: number | null; threshold: number; explanation: Explanation }

const DEFAULTS = { merchant: "Manual entry", category: "", amount: 950, hour: 23, weekday: 5, age_years: 45, distance_km: 70,
  city_pop: 25000, gender: "F", secs_since_last: 1800, card_prior_count: 120, card_mean_amt: 65, count_24h: 4, amt_sum_24h: 300 };
type Form = typeof DEFAULTS;
const FIELDS: [keyof Form, string, number?][] = [
  ["amount", "Amount (USD)", 0.01], ["hour", "Hour (0-23)", 1], ["weekday", "Weekday (0 = Mon)", 1], ["age_years", "Customer age", 1],
  ["distance_km", "Customer-merchant distance (km)", 1], ["city_pop", "City population", 1],
  ["secs_since_last", "Seconds since card's last transaction", 1], ["card_prior_count", "Card's prior transactions", 1],
  ["card_mean_amt", "Card's average amount", 0.01], ["count_24h", "Card transactions in previous 24h", 1],
  ["amt_sum_24h", "Card spend in previous 24h", 0.01],
];

function Simulator() {
  const options = useApi<{ categories: string[]; threshold: number }>("/simulate/options");
  const [form, setForm] = useState<Form>(DEFAULTS);
  const [result, setResult] = useState<SimResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (options.state === "ready" && !form.category) setForm((f) => ({ ...f, category: options.data.categories.includes("shopping_net") ? "shopping_net" : options.data.categories[0] }));
  }, [options, form.category]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setResult(await post<SimResult>("/simulate", form));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Manual transaction" subtitle="Scored by the deployed model and stored as simulated">
      <Async result={options}>
        {({ categories }) => (
          <form onSubmit={submit} className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-sm">Merchant label
                <input value={form.merchant} maxLength={60} onChange={(e) => setForm({ ...form, merchant: e.target.value })}
                       className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1" /></label>
              <label className="text-sm">Category
                <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
                        className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-1">
                  {categories.map((c) => <option key={c}>{c}</option>)}</select></label>
              <label className="text-sm">Gender
                <select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}
                        className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-1">
                  <option value="F">F</option><option value="M">M</option></select></label>
              {FIELDS.map(([key, label, step]) => (
                <label key={key} className="text-sm">{label}
                  <input type="number" step={step} min={0} required value={form[key] as number}
                         onChange={(e) => setForm({ ...form, [key]: e.target.value === "" ? "" : Number(e.target.value) })}
                         className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 tabular-nums" /></label>
              ))}
            </div>
            <Button type="submit" variant="primary" disabled={busy}>Score transaction</Button>
            {error && <ErrorNotice message={error} />}
            {result && (
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
                <p className="flex flex-wrap items-center gap-2"><SimulatedBadge /> Score <strong className="tabular-nums">{fmt.score(result.score)}</strong>
                  <RiskBadge level={result.risk_level} /> <span className="text-slate-500">threshold {fmt.score(result.threshold)} · {fmt.ms(result.latency_ms)}</span></p>
                <p className="mt-2 text-xs text-slate-600">Top factors: {result.explanation.contributions.slice(0, 3)
                  .map((c) => `${c.label} (${c.contribution > 0 ? "+" : ""}${c.contribution.toFixed(2)})`).join(", ")}</p>
                {result.case_id && <Link to={`/cases/${result.case_id}`} className="mt-2 inline-block text-sky-700 hover:underline">Flagged: open case #{result.case_id} →</Link>}
              </div>
            )}
          </form>
        )}
      </Async>
    </Card>
  );
}
