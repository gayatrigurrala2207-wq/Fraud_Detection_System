import { useApi, type DatasetValidation, type Health as HealthData } from "../api";
import { Card, ErrorNotice, Loading, PageHeader, StatusBadge } from "../components/ui";

const number = new Intl.NumberFormat("en-US");

export default function Health() {
  const health = useApi<HealthData>("/health");
  const dataset = useApi<DatasetValidation>("/dataset/validation");
  return (
    <>
      <PageHeader title="System Health" requirement="FR-12">
        Status of the API and every dependency the platform will use. Components from later roadmap phases are
        listed as not configured until they exist.
      </PageHeader>
      <div className="space-y-6">
        <Card title="Dependencies">
          {health.state === "loading" && <Loading />}
          {health.state === "error" && <ErrorNotice message={health.message} />}
          {health.state === "ready" && (
            <>
              <p className="mb-3 text-sm text-slate-600">
                API version {health.data.version} · environment {health.data.environment}
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-200 text-xs text-slate-500">
                    <tr>
                      <th className="py-2 pr-4 font-medium">Component</th>
                      <th className="py-2 pr-4 font-medium">Status</th>
                      <th className="py-2 font-medium">Detail</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {health.data.dependencies.map((item) => (
                      <tr key={item.name}>
                        <td className="py-2 pr-4 font-medium whitespace-nowrap">{item.name}</td>
                        <td className="py-2 pr-4"><StatusBadge status={item.status} /></td>
                        <td className="py-2 text-slate-600">{item.detail}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Card>

        <Card title="Dataset validation (FR-01)">
          {dataset.state === "loading" && <Loading />}
          {dataset.state === "error" && <ErrorNotice message={dataset.message} />}
          {dataset.state === "ready" && <DatasetDetails report={dataset.data} />}
        </Card>
      </div>
    </>
  );
}

function DatasetDetails({ report }: { report: DatasetValidation }) {
  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 text-xs text-slate-500">
            <tr>
              <th className="py-2 pr-4 font-medium">File</th>
              <th className="py-2 pr-4 text-right font-medium">Rows</th>
              <th className="py-2 pr-4 text-right font-medium">Fraud</th>
              <th className="py-2 pr-4 font-medium">Time range</th>
              <th className="py-2 text-right font-medium">Out of order</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 tabular-nums">
            {Object.entries(report.files).map(([name, file]) => (
              <tr key={name}>
                <td className="py-2 pr-4 font-medium">{name}</td>
                <td className="py-2 pr-4 text-right">{number.format(file.rows)}</td>
                <td className="py-2 pr-4 text-right">{number.format(file.label_counts["1"])}</td>
                <td className="py-2 pr-4 whitespace-nowrap">{file.timestamp_min} → {file.timestamp_max}</td>
                <td className="py-2 text-right">{number.format(file.out_of_order_rows)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-slate-500">Result</dt>
          <dd><StatusBadge status={report.passed ? "ok" : "failed"} /></dd>
        </div>
        <div>
          <dt className="text-slate-500">Train ends before test</dt>
          <dd>{report.train_ends_before_test ? "Yes" : "No"}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-slate-500">Archive SHA-256</dt>
          <dd className="font-mono text-xs break-all">{report.archive_sha256}</dd>
        </div>
      </dl>
      {report.warnings.length > 0 && (
        <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-amber-900">
          {report.warnings.map((warning) => <li key={warning}>{warning}</li>)}
        </ul>
      )}
    </>
  );
}
