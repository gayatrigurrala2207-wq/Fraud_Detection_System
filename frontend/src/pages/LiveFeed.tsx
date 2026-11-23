import { Pause, Play, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useApi, type RiskLevel, type Transaction } from "../api";
import { Async, Button, Card, EmptyState, FeedBadge, PageHeader, RiskBadge, SimulatedBadge, fmt, td, th } from "../components/ui";

const RISKS: RiskLevel[] = ["low", "medium", "elevated", "high"];
const STATUSES = [["", "All statuses"], ["flagged", "Flagged"], ["cleared", "Cleared"],
  ["confirmed_fraud", "Confirmed fraud"], ["legitimate", "Legitimate"]] as const;

export default function LiveFeed() {
  const [paused, setPaused] = useState(false);
  const [risks, setRisks] = useState<RiskLevel[]>([]);
  const [status, setStatus] = useState("");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Transaction | null>(null);

  const path = useMemo(() => {
    const params = new URLSearchParams({ limit: "100" });
    risks.forEach((r) => params.append("risk", r));
    if (status) params.set("status", status);
    if (query.trim()) params.set("q", query.trim());
    return `/transactions?${params}`;
  }, [risks, status, query]);
  const feed = useApi<{ items: Transaction[] }>(path, paused ? undefined : 2000);

  const toggleRisk = (risk: RiskLevel) =>
    setRisks((current) => (current.includes(risk) ? current.filter((r) => r !== risk) : [...current, risk]));

  return (
    <>
      <PageHeader title="Live Feed" requirement="FR-07"
        actions={<Button variant={paused ? "primary" : "secondary"} onClick={() => setPaused(!paused)}>
          {paused ? <Play className="size-4" aria-hidden /> : <Pause className="size-4" aria-hidden />}
          {paused ? "Resume" : "Pause"}
        </Button>}>
        Most recently scored transactions, refreshed every 2 seconds{paused ? " (paused)" : ""}. Select a row to inspect it.
      </PageHeader>

      <div className="mb-4 flex flex-wrap items-center gap-2" role="group" aria-label="Filters">
        {RISKS.map((risk) => (
          <button key={risk} type="button" aria-pressed={risks.includes(risk)} onClick={() => toggleRisk(risk)}
                  className={`rounded-full px-3 py-1 text-xs font-medium capitalize ring-1 ring-inset ${risks.includes(risk)
                    ? "bg-navy-900 text-white ring-navy-900" : "bg-white text-slate-700 ring-slate-300 hover:bg-slate-50"}`}>
            {risk}
          </button>
        ))}
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status"
                className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm">
          {STATUSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search merchant, category, ID"
               aria-label="Search" className="w-56 rounded-md border border-slate-300 px-2 py-1 text-sm" />
        {(risks.length > 0 || status || query) && (
          <Button onClick={() => { setRisks([]); setStatus(""); setQuery(""); }}>Clear filters</Button>
        )}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_20rem]">
        <Card>
          <Async result={feed}>
            {({ items }) => items.length === 0 ? <EmptyState title="No matching transactions" /> : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-200">
                    <tr>
                      <th className={th}>Transaction</th><th className={th}>Merchant</th><th className={th}>Event time</th>
                      <th className={`${th} text-right`}>Amount</th><th className={`${th} text-right`}>Score</th>
                      <th className={th}>Risk</th><th className={th}>Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {items.map((tx) => (
                      <tr key={tx.id} onClick={() => setSelected(tx)} tabIndex={0}
                          onKeyDown={(e) => e.key === "Enter" && setSelected(tx)}
                          className={`cursor-pointer hover:bg-slate-50 ${selected?.id === tx.id ? "bg-sky-50" : ""}`}>
                        <td className={`${td} font-mono text-xs`}>{tx.trans_num.slice(0, 10)}</td>
                        <td className={td}>{tx.merchant} {tx.source === "simulated" && <SimulatedBadge />}
                          <span className="block text-xs text-slate-500">{tx.category}</span></td>
                        <td className={`${td} whitespace-nowrap text-xs`}>{tx.event_time}</td>
                        <td className={`${td} text-right tabular-nums`}>{fmt.money.format(tx.amount)}</td>
                        <td className={`${td} text-right tabular-nums`}>{fmt.score(tx.score)}</td>
                        <td className={td}><RiskBadge level={tx.risk_level} /></td>
                        <td className={td}><FeedBadge status={tx.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Async>
        </Card>
        <Inspector tx={selected} onClose={() => setSelected(null)} />
      </div>
    </>
  );
}

function Inspector({ tx, onClose }: { tx: Transaction | null; onClose: () => void }) {
  if (!tx) return <Card title="Inspect"><p className="text-sm text-slate-500">Select a transaction to see its details.</p></Card>;
  const rows: [string, React.ReactNode][] = [
    ["Transaction ID", <span className="break-all font-mono text-xs">{tx.trans_num}</span>],
    ["Event time", tx.event_time], ["Scored at", fmt.time(tx.processed_at)],
    ["Merchant", tx.merchant], ["Category", tx.category], ["State", tx.state ?? "—"],
    ["Amount", fmt.money.format(tx.amount)], ["Score", fmt.score(tx.score)],
    ["Risk", <RiskBadge level={tx.risk_level} />], ["Status", <FeedBadge status={tx.status} />],
    ["Source", tx.source === "simulated" ? <SimulatedBadge /> : "Replay"], ["Scoring latency", fmt.ms(tx.latency_ms)],
  ];
  return (
    <Card title="Inspect" actions={<button type="button" onClick={onClose} aria-label="Close" className="text-slate-400 hover:text-slate-700"><X className="size-4" /></button>}>
      <dl className="space-y-2 text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-3"><dt className="text-slate-500">{label}</dt><dd className="text-right">{value}</dd></div>
        ))}
      </dl>
      {tx.case_id && <Link to={`/cases/${tx.case_id}`} className="mt-4 inline-block text-sm font-medium text-sky-700 hover:underline">Open case #{tx.case_id} →</Link>}
    </Card>
  );
}
