import { useApi, type ActiveSettings } from "../api";
import { Async, Card, PageHeader } from "../components/ui";

export default function Settings() {
  const settings = useApi<ActiveSettings>("/settings");
  return (
    <>
      <PageHeader title="Settings" requirement="FR-12">
        Active, non-secret configuration. Environment values come from <code className="text-xs">backend/.env.example</code> variables;
        threshold costs come from <code className="text-xs">configs/training.json</code> and apply at the next training run.
      </PageHeader>
      <Card title="Active configuration">
        <Async result={settings}>
          {(data) => (
            <dl className="divide-y divide-slate-100">
              {data.settings.map((item) => (
                <div key={item.key} className="grid gap-1 py-3 sm:grid-cols-[14rem_1fr_1.5fr]">
                  <dt className="font-mono text-xs text-slate-700">{item.key}<span className="block font-sans text-slate-400">{item.source}</span></dt>
                  <dd className="text-sm font-medium break-all">{item.value}</dd>
                  <dd className="text-sm text-slate-600">{item.description}</dd>
                </div>
              ))}
            </dl>
          )}
        </Async>
      </Card>
    </>
  );
}
