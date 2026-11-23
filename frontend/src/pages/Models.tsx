import { useApi, type ModelReport } from "../api";
import { BarSeries, LineSeries, ReferenceLine } from "../components/charts";
import { Async, Card, PageHeader, Stat, fmt, td, th } from "../components/ui";

export default function Models() {
  const report = useApi<ModelReport>("/models");
  return (
    <>
      <PageHeader title="Models" requirement="FR-10">
        Chronological comparison on the validation partition, then one evaluation of the selected model on the
        held-out publisher test file.
      </PageHeader>
      <Async result={report}>{(data) => <Body data={data} />}</Async>
    </>
  );
}

function Body({ data }: { data: ModelReport }) {
  const t = data.test;
  const cm = t.confusion_matrix;
  const p = data.partitions;
  return (
    <div className="space-y-6">
      <Card title="Active model">
        <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div><dt className="text-slate-500">Version</dt><dd className="font-mono text-xs">{data.active_version ?? data.version}</dd></div>
          <div><dt className="text-slate-500">Algorithm</dt><dd>{data.selected_model}</dd></div>
          <div><dt className="text-slate-500">Threshold</dt><dd className="tabular-nums">{data.threshold.toFixed(4)}</dd></div>
          <div><dt className="text-slate-500">Trained</dt><dd>{fmt.time(data.trained_at)}</dd></div>
        </dl>
        <p className="mt-3 text-xs text-slate-500">{data.selection_rule} {data.threshold_rule}</p>
        <p className="mt-1 text-xs text-slate-500">
          Train {p.train.start.slice(0, 10)}–{p.train.end.slice(0, 10)} ({fmt.int.format(p.train.rows)} rows) ·
          Validation {p.validation.start.slice(0, 10)}–{p.validation.end.slice(0, 10)} ({fmt.int.format(p.validation.rows)}) ·
          Test {p.test.start.slice(0, 10)}–{p.test.end.slice(0, 10)} ({fmt.int.format(p.test.rows)})
        </p>
      </Card>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="Test precision" value={fmt.pct(t.precision)} />
        <Stat label="Test recall" value={fmt.pct(t.recall)} />
        <Stat label="Test PR-AUC" value={t.pr_auc.toFixed(4)} />
        <Stat label="Test ROC-AUC" value={t.roc_auc.toFixed(4)} />
        <Stat label="Inference latency" value={`${data.latency.p50_ms.toFixed(2)} ms`} note={`p95 ${data.latency.p95_ms.toFixed(2)} ms`} />
      </div>

      <Card title="Model comparison" subtitle="Validation partition, each at its own cost-optimal threshold">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm tabular-nums">
            <thead className="border-b border-slate-200"><tr>
              <th className={th}>Model</th><th className={`${th} text-right`}>PR-AUC</th><th className={`${th} text-right`}>ROC-AUC</th>
              <th className={`${th} text-right`}>Precision</th><th className={`${th} text-right`}>Recall</th><th className={`${th} text-right`}>F1</th>
              <th className={`${th} text-right`}>FPR</th><th className={`${th} text-right`}>Cost</th><th className={`${th} text-right`}>Fit</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {data.comparison.map((m) => (
                <tr key={m.name} className={m.name === data.selected_model ? "bg-sky-50" : ""}>
                  <td className={td}><span className="font-medium">{m.name}</span>{m.name === data.selected_model && <span className="ml-2 text-xs text-sky-800">selected</span>}
                    <span className="block text-xs text-slate-500">{m.description}</span></td>
                  <td className={`${td} text-right`}>{m.validation.pr_auc.toFixed(4)}</td>
                  <td className={`${td} text-right`}>{m.validation.roc_auc.toFixed(4)}</td>
                  <td className={`${td} text-right`}>{fmt.pct(m.validation.precision)}</td>
                  <td className={`${td} text-right`}>{fmt.pct(m.validation.recall)}</td>
                  <td className={`${td} text-right`}>{m.validation.f1.toFixed(3)}</td>
                  <td className={`${td} text-right`}>{fmt.pct(m.validation.false_positive_rate, 2)}</td>
                  <td className={`${td} text-right`}>{fmt.compactMoney.format(m.validation.cost)}</td>
                  <td className={`${td} text-right`}>{m.fit_seconds}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-slate-500">Not compared: {data.not_compared.join("; ")}.</p>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Precision-recall curve" subtitle="Held-out test file">
          <LineSeries data={t.pr} name="Precision-recall curve" xLabel="Recall" yLabel="Precision"
                      reference={<ReferenceLine x={t.recall} stroke="#94a3b8" strokeDasharray="4 4" />} />
        </Card>
        <Card title="ROC curve" subtitle="Held-out test file">
          <LineSeries data={t.roc} name="ROC curve" xLabel="False positive rate" yLabel="True positive rate" />
        </Card>
        <Card title="Confusion matrix" subtitle={`Held-out test file at threshold ${t.threshold.toFixed(4)} · ${fmt.int.format(t.rows)} transactions`}>
          <table className="w-full text-center text-sm tabular-nums">
            <thead><tr><th /><th className={th}>Predicted fraud</th><th className={th}>Predicted legitimate</th></tr></thead>
            <tbody>
              <tr><th className={`${th} text-left`}>Actual fraud</th>
                <td className="rounded bg-sky-50 p-3 font-semibold">{fmt.int.format(cm.tp)}<span className="block text-xs font-normal text-slate-500">true positives</span></td>
                <td className="rounded bg-orange-50 p-3 font-semibold">{fmt.int.format(cm.fn)}<span className="block text-xs font-normal text-slate-500">missed fraud</span></td></tr>
              <tr><th className={`${th} text-left`}>Actual legitimate</th>
                <td className="rounded bg-orange-50 p-3 font-semibold">{fmt.int.format(cm.fp)}<span className="block text-xs font-normal text-slate-500">false alerts</span></td>
                <td className="rounded bg-sky-50 p-3 font-semibold">{fmt.int.format(cm.tn)}<span className="block text-xs font-normal text-slate-500">true negatives</span></td></tr>
            </tbody>
          </table>
          <p className="mt-3 text-xs text-slate-500">Missed fraud amount {fmt.money.format(t.missed_fraud_amount)} · false positive rate {fmt.pct(t.false_positive_rate, 3)}</p>
        </Card>
        <Card title="Feature importance" subtitle="Mean |SHAP| on 20,000 validation transactions">
          <BarSeries data={data.feature_importance} x="label" y="mean_abs_shap" name="Mean |SHAP|" xLabel="Feature"
                     format={(v) => v.toFixed(2)} horizontal />
        </Card>
      </div>
      <p className="text-xs text-slate-500">Latency measurement: {data.latency.conditions} ({fmt.int.format(data.latency.samples)} samples)</p>
    </div>
  );
}
