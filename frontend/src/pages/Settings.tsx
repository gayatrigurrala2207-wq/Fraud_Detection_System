import { useState, type FormEvent } from "react";
import { getAnalyst, setAnalyst, useApi, type ActiveSettings } from "../api";
import { Async, Button, Card, PageHeader } from "../components/ui";

export default function Settings() {
  const settings = useApi<ActiveSettings>("/settings");
  const [name, setName] = useState(getAnalyst());
  const [saved, setSaved] = useState(false);

  const save = (event: FormEvent) => {
    event.preventDefault();
    setAnalyst(name.trim() || "analyst");
    setSaved(true);
  };

  return (
    <>
      <PageHeader title="Settings" requirement="FR-12">
        Active, non-secret configuration. Environment values come from <code className="text-xs">backend/.env.example</code> variables;
        threshold costs come from <code className="text-xs">configs/training.json</code> and apply at the next training run.
      </PageHeader>
      <div className="space-y-6">
        <Card title="Analyst name" subtitle="Recorded on labels, notes, and resolutions in this browser.">
          <form onSubmit={save} className="flex flex-wrap items-center gap-2">
            <input value={name} maxLength={40} onChange={(e) => { setName(e.target.value); setSaved(false); }}
                   aria-label="Analyst name" className="rounded-md border border-slate-300 px-2 py-1.5 text-sm" />
            <Button type="submit" variant="primary">Save</Button>
            {saved && <span className="text-sm text-emerald-700">Saved</span>}
          </form>
        </Card>
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
      </div>
    </>
  );
}
