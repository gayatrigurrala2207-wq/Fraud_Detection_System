import { useApi, type Analytics as AnalyticsData } from "../api";
import { BarSeries } from "../components/charts";
import { Async, Card, PageHeader, Stat, fmt } from "../components/ui";

const rate = (v: number) => fmt.pct(v, 2);

export default function Analytics() {
  const analytics = useApi<AnalyticsData>("/analytics");
  return (
    <>
      <PageHeader title="Analytics" requirement="FR-09">
        Fraud patterns in the publisher training file, plus the live score distribution. Each chart states its
        population, time window, and whether outcomes come from labels or model scores.
      </PageHeader>
      <Async result={analytics}>{(data) => <Body data={data} />}</Async>
    </>
  );
}

function Body({ data }: { data: AnalyticsData }) {
  const source = `${data.population} · ${data.time_window.start.slice(0, 10)} to ${data.time_window.end.slice(0, 10)} · ${data.outcome_source}`;
  const scores = data.score_distribution;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Stat label="Transactions analyzed" value={fmt.int.format(data.totals.transactions)} note={data.population} />
        <Stat label="Labeled fraud" value={fmt.int.format(data.totals.fraud)} note={`${rate(data.totals.fraud / data.totals.transactions)} fraud rate`} />
        <Stat label="Transaction value" value={fmt.compactMoney.format(data.totals.amount)} />
      </div>
      <Card title="Fraud rate by month" subtitle={source}>
        <BarSeries data={data.monthly} x="month" y="fraud_rate" name="Fraud rate" xLabel="Month" format={rate} />
      </Card>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Fraud rate by category" subtitle={source}>
          <BarSeries data={data.by_category} x="category" y="fraud_rate" name="Fraud rate" xLabel="Category" format={rate} horizontal />
        </Card>
        <Card title="Fraud rate by state (top 15, at least 1,000 transactions)" subtitle={source}>
          <BarSeries data={data.by_state} x="state" y="fraud_rate" name="Fraud rate" xLabel="State" format={rate} horizontal />
        </Card>
        <Card title="Fraud rate by hour of day" subtitle={source}>
          <BarSeries data={data.by_hour} x="hour" y="fraud_rate" name="Fraud rate" xLabel="Hour" format={rate} />
        </Card>
        <Card title="Fraud rate by day of week" subtitle={source}>
          <BarSeries data={data.by_weekday} x="weekday" y="fraud_rate" name="Fraud rate" xLabel="Day" format={rate} />
        </Card>
        <Card title="Fraud rate by transaction amount (USD)" subtitle={source}>
          <BarSeries data={data.by_amount} x="bucket" y="fraud_rate" name="Fraud rate" xLabel="Amount" format={rate} />
        </Card>
        <Card title="Spending anomalies: amount vs card's earlier average" subtitle={`${source}. Cards with prior history only.`}>
          <BarSeries data={data.spending_anomaly} x="bucket" y="fraud_rate" name="Fraud rate" xLabel="Amount / card average" format={rate} />
        </Card>
      </div>
      <Card title="Risk score distribution"
            subtitle={`${scores.population} · ${scores.time_window.start ?? "—"} to ${scores.time_window.end ?? "—"} · ${scores.outcome_source} · ${fmt.int.format(scores.total)} transactions`}>
        <BarSeries data={scores.bins} x="bucket" y="transactions" name="Transactions" xLabel="Score" format={(v) => fmt.int.format(v)} />
      </Card>
    </div>
  );
}
