import { ArrowLeft, CheckCircle2, RotateCcw } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { post, useApi, type CaseDetail as CaseData, type Explanation } from "../api";
import { SERIES } from "../components/charts";
import { Async, Button, Card, ErrorNotice, PageHeader, RiskBadge, SimulatedBadge, fmt, td, th } from "../components/ui";

export default function CaseDetail() {
  const { caseId } = useParams();
  const detail = useApi<CaseData>(`/cases/${caseId}`);
  return (
    <>
      <Link to="/cases" className="mb-3 inline-flex items-center gap-1 text-sm text-sky-700 hover:underline">
        <ArrowLeft className="size-4" aria-hidden /> Cases
      </Link>
      <Async result={detail}>{(data) => <Workspace data={data} reload={detail.reload} />}</Async>
    </>
  );
}

function Workspace({ data, reload }: { data: CaseData; reload: () => void }) {
  const { case: c, transaction: tx } = data;
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");

  const act = async (path: string, body: unknown = {}) => {
    setBusy(true);
    setError(null);
    try {
      await post(`/cases/${c.id}${path}`, body);
      reload();
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  };
  const submitNote = async (event: FormEvent) => {
    event.preventDefault();
    if (note.trim() && (await act("/notes", { body: note }))) setNote("");
  };

  return (
    <>
      <PageHeader title={`Case #${c.id}`} requirement="FR-08"
        actions={c.status === "open" ? (
          <>
            <Button disabled={busy} variant={c.disposition === "fraud" ? "primary" : "danger"}
                    onClick={() => act("/label", { disposition: "fraud" })}>Label fraud</Button>
            <Button disabled={busy} variant={c.disposition === "legitimate" ? "primary" : "secondary"}
                    onClick={() => act("/label", { disposition: "legitimate" })}>Label legitimate</Button>
            <Button disabled={busy || !c.disposition} variant="primary" onClick={() => act("/resolve")}
                    title={c.disposition ? undefined : "Label the case first"}>
              <CheckCircle2 className="size-4" aria-hidden /> Resolve
            </Button>
          </>
        ) : (
          <Button disabled={busy} onClick={() => act("/reopen")}><RotateCcw className="size-4" aria-hidden /> Reopen</Button>
        )}>
        {tx.merchant} · {fmt.money.format(tx.amount)} · <span className="capitalize">{c.status}</span>
        {c.disposition && <> · labeled <strong className="capitalize">{c.disposition}</strong></>}
      </PageHeader>
      {error && <div className="mb-4"><ErrorNotice message={error} /></div>}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Risk evidence">
          <dl className="space-y-2 text-sm">
            {([
              ["Score", <span className="font-semibold tabular-nums">{fmt.score(tx.score)}</span>],
              ["Threshold", fmt.score(tx.threshold)], ["Risk", <RiskBadge level={tx.risk_level} />],
              ["Model", <span className="font-mono text-xs">{tx.model_version}</span>],
              ["Event time", tx.event_time], ["Category", tx.category], ["State", tx.state ?? "—"],
              ["Card (pseudonym)", <span className="font-mono text-xs">{tx.card_key ?? "—"}</span>],
              ["Source", tx.source === "simulated" ? <SimulatedBadge /> : "Replay"],
              ["Transaction ID", <span className="break-all font-mono text-xs">{tx.trans_num}</span>],
            ] as [string, React.ReactNode][]).map(([label, value]) => (
              <div key={label} className="flex justify-between gap-3"><dt className="text-slate-500">{label}</dt><dd className="text-right">{value}</dd></div>
            ))}
          </dl>
        </Card>

        <Card title="Why the model flagged it" subtitle="SHAP contributions to the score (log-odds). Positive pushes toward fraud.">
          {data.explanation ? <ShapBars explanation={data.explanation} /> : <p className="text-sm text-slate-500">No trained model loaded.</p>}
        </Card>

        <Card title="Behavioral anomalies" subtitle={data.anomaly_reference ? `Compared with ${data.anomaly_reference}` : undefined}>
          <ul className="space-y-3 text-sm">
            {data.anomalies.map((a) => (
              <li key={a.label} className="flex items-start justify-between gap-3">
                <div><p>{a.label}</p><p className="text-xs text-slate-500">{a.display}
                  {a.percentile_in_reference != null && ` · above ${fmt.pct(a.percentile_in_reference, 0)} of reference`}</p></div>
                {a.unusual ? <span className="rounded-full bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-900 ring-1 ring-inset ring-orange-600/30">Unusual</span>
                  : <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">Typical</span>}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card title="Card history" subtitle="Earlier transactions on the same pseudonymous card (masked: no card number, name, or address)">
          {data.history.length === 0 ? <p className="text-sm text-slate-500">No earlier transactions in the replay set.</p> : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead><tr><th className={th}>Event time</th><th className={th}>Merchant</th><th className={`${th} text-right`}>Amount</th><th className={th}>Risk</th></tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {data.history.map((h) => (
                    <tr key={h.id}>
                      <td className={`${td} whitespace-nowrap text-xs`}>{h.event_time}</td>
                      <td className={td}>{h.merchant}<span className="block text-xs text-slate-500">{h.category}</span></td>
                      <td className={`${td} text-right tabular-nums`}>{fmt.money.format(h.amount)}</td>
                      <td className={td}>{h.risk_level ? <RiskBadge level={h.risk_level} /> : <span className="text-xs text-slate-400">Not scored yet</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <div className="space-y-6">
          <Card title="Notes">
            <ul className="mb-3 space-y-2 text-sm">
              {data.notes.length === 0 && <li className="text-slate-500">No notes yet.</li>}
              {data.notes.map((n) => (
                <li key={n.id} className="rounded-md bg-slate-50 p-2">
                  <p className="whitespace-pre-wrap">{n.body}</p>
                  <p className="mt-1 text-xs text-slate-500">{n.author} · {fmt.time(n.created_at)}</p>
                </li>
              ))}
            </ul>
            <form onSubmit={submitNote} className="flex gap-2">
              <input value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000} placeholder="Add a note"
                     aria-label="Note" className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm" />
              <Button type="submit" disabled={busy || !note.trim()}>Add</Button>
            </form>
          </Card>
          <Card title="Audit trail">
            <ol className="space-y-2 text-sm">
              {data.audit.map((e) => (
                <li key={e.id}>
                  <span className="font-medium">{e.actor}</span> <span className="text-slate-600">{e.action.replaceAll("_", " ")}</span>
                  {e.detail && <span className="text-slate-600"> — {e.detail}</span>}
                  <span className="block text-xs text-slate-500">{fmt.time(e.created_at)}</span>
                </li>
              ))}
            </ol>
          </Card>
        </div>
      </div>
    </>
  );
}

function ShapBars({ explanation }: { explanation: Explanation }) {
  const items = explanation.contributions.slice(0, 8);
  const max = Math.max(...items.map((i) => Math.abs(i.contribution)), 1e-6);
  const show = (v: string | number | null) => (v == null ? "—" : typeof v === "number" ? (Number.isInteger(v) ? v : v.toFixed(2)) : v);
  return (
    <ul className="space-y-2 text-sm">
      {items.map((item) => {
        const width = `${(Math.abs(item.contribution) / max) * 50}%`;
        const positive = item.contribution > 0;
        return (
          <li key={item.feature} title={`${item.label}: ${item.contribution.toFixed(3)} log-odds`}>
            <div className="flex justify-between gap-2 text-xs"><span>{item.label} <span className="text-slate-500">= {show(item.value)}</span></span>
              <span className="tabular-nums text-slate-700">{positive ? "+" : ""}{item.contribution.toFixed(2)}</span></div>
            <div className="relative mt-1 h-2 rounded bg-slate-100">
              <div className="absolute inset-y-0 left-1/2 w-px bg-slate-300" aria-hidden />
              <div className="absolute inset-y-0 rounded" style={{ width, background: positive ? SERIES[1] : SERIES[0],
                ...(positive ? { left: "50%" } : { right: "50%" }) }} aria-hidden />
            </div>
          </li>
        );
      })}
      <li className="pt-1 text-xs text-slate-500">Orange raises fraud risk, blue lowers it. Baseline {explanation.base_value.toFixed(2)} log-odds.</li>
    </ul>
  );
}
