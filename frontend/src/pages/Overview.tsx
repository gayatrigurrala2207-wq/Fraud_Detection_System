import { Link } from "react-router-dom";
import { useApi, type Overview as OverviewData } from "../api";
import { BarSeries, SERIES } from "../components/charts";
import { Async, Card, EmptyState, PageHeader, RiskBadge, Stat, fmt, td, th } from "../components/ui";

export default function Overview() {
  const overview = useApi<OverviewData>("/overview", 5000);
  return (
    <>
      <PageHeader title="Overview" requirement="FR-06">
        Live totals from the replay of held-out transactions. Scores are predictions; only analyst-labeled cases
        count as confirmed outcomes.
      </PageHeader>
      <Async result={overview}>{(data) => <OverviewBody data={data} />}</Async>
    </>
  );
}

function OverviewBody({ data }: { data: OverviewData }) {
  const d = data.definitions;
  if (data.processed.count === 0) {
    return <Card><EmptyState title="No transactions processed yet">Start the replay on the Replay & Simulator page.</EmptyState></Card>;
  }
  const { outcomes } = data;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Processed transactions" value={fmt.int.format(data.processed.count)}
              note={`${fmt.compactMoney.format(data.processed.value)} value · ${fmt.int.format(data.processed.queued)} queued`} />
        <Stat label="Flagged (opened a case)" value={fmt.int.format(data.flagged.count)}
              note={`${fmt.pct(data.flagged.rate, 2)} of processed · threshold ${fmt.score(data.threshold)}`} />
        <Stat label="High risk" value={fmt.int.format(data.high_risk.count)} note="Subset of flagged" />
        <Stat label="Potential fraud value" value={fmt.money.format(data.potential_fraud_value)} note="Flagged amounts (predicted)" />
        <Stat label="Confirmed fraud" value={fmt.int.format(outcomes.confirmed.fraud)}
              note={`${fmt.int.format(outcomes.confirmed.legitimate)} legitimate · ${fmt.int.format(outcomes.confirmed.unreviewed)} unreviewed`} />
        <Stat label="Review coverage" value={fmt.pct(outcomes.review_coverage)} note="Reviewed / all cases" />
        <Stat label="Alert precision (confirmed)"
              value={outcomes.alert_precision == null ? "Not enough reviews" : fmt.pct(outcomes.alert_precision)}
              note={`Shown after ${outcomes.min_reviewed_for_precision} reviewed cases`} />
        <Stat label="Scoring latency" value={fmt.ms(data.latency.mean_ms)} note={`p95 ${fmt.ms(data.latency.p95_ms)} · ${fmt.int.format(data.latency.samples)} samples`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Processed transactions per event hour"
              subtitle={`Replay event time ${data.processed.event_window.start ?? ""} to ${data.processed.event_window.end ?? ""}`}>
          <BarSeries data={data.timeline} x="hour" y="processed" name="Processed" xLabel="Event hour"
                     format={(v) => fmt.int.format(v)} height={200} />
        </Card>
        <Card title="Flagged transactions per event hour" subtitle="Model predictions at the deployed threshold">
          <BarSeries data={data.timeline} x="hour" y="flagged" name="Flagged" xLabel="Event hour"
                     format={(v) => fmt.int.format(v)} height={200} color={SERIES[1]} />
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Risk distribution" subtitle="Processed replay transactions by risk level">
          <ul className="space-y-2 text-sm">
            {(["low", "medium", "elevated", "high"] as const).map((level) => {
              const count = data.risk_distribution[level];
              return (
                <li key={level} className="flex items-center justify-between gap-3">
                  <RiskBadge level={level} />
                  <span className="tabular-nums text-slate-700">
                    {fmt.int.format(count)} <span className="text-slate-400">({fmt.pct(count / data.processed.count, 2)})</span>
                  </span>
                </li>
              );
            })}
          </ul>
        </Card>
        <Card title="Latest alerts" actions={<Link to="/cases" className="text-xs text-sky-700 hover:underline">All cases</Link>}>
          {data.recent_alerts.length === 0 ? <p className="text-sm text-slate-500">No alerts yet.</p> : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead><tr><th className={th}>Merchant</th><th className={`${th} text-right`}>Amount</th><th className={th}>Risk</th></tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {data.recent_alerts.map((alert) => (
                    <tr key={alert.id}>
                      <td className={td}><Link to={`/cases/${alert.case_id}`} className="text-sky-700 hover:underline">{alert.merchant}</Link>
                        <span className="block text-xs text-slate-500">{alert.category} · {alert.event_time}</span></td>
                      <td className={`${td} text-right tabular-nums`}>{fmt.money.format(alert.amount)}</td>
                      <td className={td}><RiskBadge level={alert.risk_level} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <Card title="Metric definitions">
        <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
          {Object.entries(d).map(([key, value]) => (
            <div key={key}><dt className="font-medium capitalize">{key.replaceAll("_", " ")}</dt><dd className="text-slate-600">{value}</dd></div>
          ))}
        </dl>
      </Card>
    </div>
  );
}
