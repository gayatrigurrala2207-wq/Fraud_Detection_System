import { useApi, type ActiveSettings } from "../api";
import { Card, ErrorNotice, Loading, PageHeader } from "../components/ui";

export default function Settings() {
  const settings = useApi<ActiveSettings>("/settings");
  return (
    <>
      <PageHeader title="Settings" requirement="FR-12">
        Active, non-secret backend configuration. Change values with environment variables
        (see <code className="text-xs">backend/.env.example</code>) and restart the backend.
      </PageHeader>
      <Card>
        {settings.state === "loading" && <Loading />}
        {settings.state === "error" && <ErrorNotice message={settings.message} />}
        {settings.state === "ready" && (
          <dl className="divide-y divide-slate-100">
            {settings.data.settings.map((item) => (
              <div key={item.key} className="grid gap-1 py-3 sm:grid-cols-3">
                <dt className="font-mono text-xs text-slate-700">{item.key}</dt>
                <dd className="text-sm font-medium">{item.value}</dd>
                <dd className="text-sm text-slate-600">{item.description}</dd>
              </div>
            ))}
          </dl>
        )}
      </Card>
    </>
  );
}
