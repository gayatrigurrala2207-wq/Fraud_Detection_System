import { useState } from "react";
import { Link } from "react-router-dom";
import { useApi, type CaseSummary } from "../api";
import { Async, Card, EmptyState, PageHeader, RiskBadge, SimulatedBadge, fmt, td, th } from "../components/ui";

const TABS = [["open", "Open"], ["resolved", "Resolved"], ["", "All"]] as const;

export default function Cases() {
  const [status, setStatus] = useState<string>("open");
  const cases = useApi<{ items: CaseSummary[]; counts: { open: number; resolved: number } }>(
    `/cases?limit=200${status ? `&status=${status}` : ""}`, 5000);
  const counts = cases.state === "ready" ? cases.data.counts : null;

  return (
    <>
      <PageHeader title="Cases" requirement="FR-08">
        Every transaction scored at or above the threshold opens a case. Open cases are sorted by score.
      </PageHeader>
      <div className="mb-4 flex gap-1" role="tablist">
        {TABS.map(([value, label]) => (
          <button key={value} role="tab" type="button" aria-selected={status === value} onClick={() => setStatus(value)}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium ${status === value ? "bg-navy-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}>
            {label}{counts && value ? ` (${fmt.int.format(counts[value])})` : ""}
          </button>
        ))}
      </div>
      <Card>
        <Async result={cases}>
          {({ items }) => items.length === 0 ? <EmptyState title="No cases" /> : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200">
                  <tr><th className={th}>Case</th><th className={th}>Merchant</th><th className={th}>Event time</th>
                    <th className={`${th} text-right`}>Amount</th><th className={`${th} text-right`}>Score</th>
                    <th className={th}>Risk</th><th className={th}>Status</th><th className={th}>Disposition</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {items.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-50">
                      <td className={td}><Link to={`/cases/${c.id}`} className="font-medium text-sky-700 hover:underline">#{c.id}</Link></td>
                      <td className={td}>{c.merchant} {c.source === "simulated" && <SimulatedBadge />}
                        <span className="block text-xs text-slate-500">{c.category}{c.notes ? ` · ${c.notes} note${c.notes > 1 ? "s" : ""}` : ""}</span></td>
                      <td className={`${td} whitespace-nowrap text-xs`}>{c.event_time}</td>
                      <td className={`${td} text-right tabular-nums`}>{fmt.money.format(c.amount)}</td>
                      <td className={`${td} text-right tabular-nums`}>{fmt.score(c.score)}</td>
                      <td className={td}><RiskBadge level={c.risk_level} /></td>
                      <td className={`${td} capitalize`}>{c.status}</td>
                      <td className={`${td} capitalize`}>{c.disposition ?? <span className="text-slate-400">Unlabeled</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Async>
      </Card>
    </>
  );
}
