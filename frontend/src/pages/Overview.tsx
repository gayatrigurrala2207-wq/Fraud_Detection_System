import { useApi, type DatasetValidation } from "../api";
import { NAVIGATION } from "../components/Layout";
import { Card, ErrorNotice, Loading, Stat } from "../components/ui";
import PlannedView from "./PlannedView";

const number = new Intl.NumberFormat("en-US");

export default function Overview() {
  const dataset = useApi<DatasetValidation>("/dataset/validation");
  return (
    <>
      <PlannedView item={NAVIGATION[0]} />
      <div className="mt-6">
        <Card title="Source dataset (validated, not yet processed)">
          {dataset.state === "loading" && <Loading />}
          {dataset.state === "error" && <ErrorNotice message={dataset.message} />}
          {dataset.state === "ready" && <DatasetSummary report={dataset.data} />}
        </Card>
      </div>
    </>
  );
}

function DatasetSummary({ report }: { report: DatasetValidation }) {
  const files = Object.values(report.files);
  const rows = files.reduce((sum, file) => sum + file.rows, 0);
  const fraud = files.reduce((sum, file) => sum + file.label_counts["1"], 0);
  return (
    <>
      <p className="mb-4 text-sm text-slate-600">
        Counts come from the dataset validation report, not from scoring. Fraud labels are the publisher's ground truth.
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Transactions in dataset" value={number.format(rows)} note="Train and test partitions" />
        <Stat label="Labeled fraud" value={number.format(fraud)} note={`${((fraud / rows) * 100).toFixed(2)}% of all rows`} />
        <Stat label="Columns" value={String(report.columns)} />
        <Stat label="Validation" value={report.passed ? "Passed" : "Failed"} note={`${report.warnings.length} warnings`} />
      </div>
    </>
  );
}
