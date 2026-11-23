import { useApi, type Monitoring as MonitoringData } from "../api";
import { Async, Card, EmptyState, PageHeader, Stat, fmt, td, th } from "../components/ui";

const DRIFT = {
  stable: "bg-emerald-50 text-emerald-800 ring-emerald-600/30",
  moderate: "bg-amber-50 text-amber-900 ring-amber-600/30",
  significant: "bg-red-50 text-red-800 ring-red-600/30",
};

export default function Monitoring() {
  const monitoring = useApi<MonitoringData>("/monitoring", 15000);
  return (
    <>
      <PageHeader title="Monitoring" requirement="FR-10">
        Input and score drift of replayed traffic against the validation window, confirmed-label performance
        (reported separately), and the experiment log.
      </PageHeader>
      <Async result={monitoring}>{(data) => <Body data={data} />}</Async>
    </>
  );
}

function Body({ data }: { data: MonitoringData }) {
  const perf = data.confirmed_performance;
  return (
    <div className="space-y-6">
      <Card title="Drift" subtitle={data.drift ? `${data.drift.current_window} vs ${data.drift.reference_window}` : data.drift_method}>
        {data.drift ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200"><tr><th className={th}>Signal</th><th className={`${th} text-right`}>PSI</th><th className={th}>Status</th></tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {data.drift.items.map((item) => (
                    <tr key={item.feature}>
                      <td className={td}>{item.label}</td>
                      <td className={`${td} text-right tabular-nums`}>{item.psi.toFixed(4)}</td>
                      <td className={td}><span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize ring-1 ring-inset ${DRIFT[item.status]}`}>{item.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-xs text-slate-500">{data.drift_method}</p>
          </>
        ) : (
          <EmptyState title="Not enough replayed transactions yet">
            Drift needs at least {data.min_drift_rows} scored transactions; {data.drift_rows} so far.
          </EmptyState>
        )}
      </Card>

      <Card title="Confirmed-label performance" subtitle={perf.note}>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat label="Reviewed cases" value={fmt.int.format(perf.reviewed)} />
          <Stat label="Confirmed fraud" value={fmt.int.format(perf.fraud)} />
          <Stat label="Confirmed legitimate" value={fmt.int.format(perf.legitimate)} />
          <Stat label="Alert precision" value={fmt.pct(perf.alert_precision)} note="Confirmed fraud / reviewed" />
        </div>
      </Card>

      <Card title="Experiments" subtitle="One row per training run (backend/data/reports/runs.json)">
        {data.experiments.length === 0 ? <EmptyState title="No training runs recorded" /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm tabular-nums">
              <thead className="border-b border-slate-200"><tr><th className={th}>Run</th><th className={th}>Trained</th><th className={th}>Selected model</th>
                <th className={`${th} text-right`}>Threshold</th><th className={`${th} text-right`}>Test PR-AUC</th>
                <th className={`${th} text-right`}>Test precision</th><th className={`${th} text-right`}>Test recall</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {data.experiments.map((run) => (
                  <tr key={run.run_id}>
                    <td className={`${td} font-mono text-xs`}>{run.run_id}</td>
                    <td className={td}>{fmt.time(run.trained_at)}</td>
                    <td className={td}>{run.selected_model}</td>
                    <td className={`${td} text-right`}>{run.threshold.toFixed(4)}</td>
                    <td className={`${td} text-right`}>{run.test.pr_auc.toFixed(4)}</td>
                    <td className={`${td} text-right`}>{fmt.pct(run.test.precision)}</td>
                    <td className={`${td} text-right`}>{fmt.pct(run.test.recall)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
