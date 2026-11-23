import { KeyRound, UserPlus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { patch, post, useApi, type Role, type User } from "../api";
import { useAuth } from "../auth";
import { Async, Button, Card, ErrorNotice, PageHeader, fmt, td, th } from "../components/ui";

const ROLE_HELP: Record<Role, string> = {
  viewer: "Read-only access to every page.",
  analyst: "Viewer, plus label, annotate, and resolve cases; run the replay and simulator.",
  admin: "Analyst, plus manage users and reset the replay.",
};
const input = "w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm";

export default function Users() {
  const users = useApi<{ items: User[] }>("/users");
  const { user: me, minPasswordLength } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const run = async (action: () => Promise<unknown>, message: string) => {
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(message);
      users.reload();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const resetPassword = (user: User) => {
    const password = prompt(`New password for ${user.display_name} (at least ${minPasswordLength} characters):`);
    if (password) void run(() => post(`/users/${user.id}/password`, { new_password: password }),
      `Password reset for ${user.username}. Their existing sessions were signed out.`);
  };

  return (
    <>
      <PageHeader title="Users" requirement="Administration">
        Create accounts and control access. Changing a role or disabling an account signs that user out immediately.
      </PageHeader>
      {error && <div className="mb-4"><ErrorNotice message={error} /></div>}
      {notice && <p className="mb-4 rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}
      <div className="grid gap-6 xl:grid-cols-[1fr_22rem]">
        <Card title="Accounts">
          <Async result={users}>
            {({ items }) => (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-200"><tr>
                    <th className={th}>User</th><th className={th}>Role</th><th className={th}>Status</th>
                    <th className={th}>Last sign-in</th><th className={th}><span className="sr-only">Actions</span></th></tr></thead>
                  <tbody className="divide-y divide-slate-100">
                    {items.map((u) => (
                      <tr key={u.id} className={u.active ? "" : "text-slate-400"}>
                        <td className={td}><span className="font-medium">{u.display_name}</span>{u.id === me?.id && <span className="ml-2 text-xs text-sky-700">you</span>}
                          <span className="block text-xs text-slate-500">{u.username}</span></td>
                        <td className={td}>
                          <select value={u.role} aria-label={`Role for ${u.username}`} className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
                                  onChange={(e) => run(() => patch(`/users/${u.id}`, { role: e.target.value }), `${u.username} is now ${e.target.value}.`)}>
                            <option value="viewer">Viewer</option><option value="analyst">Analyst</option><option value="admin">Admin</option>
                          </select>
                        </td>
                        <td className={td}>{u.active ? "Active" : "Disabled"}</td>
                        <td className={`${td} whitespace-nowrap text-xs`}>{u.last_login_at ? fmt.time(u.last_login_at) : "Never"}</td>
                        <td className={`${td} whitespace-nowrap text-right`}>
                          <Button onClick={() => resetPassword(u)} title="Reset password"><KeyRound className="size-4" aria-hidden /><span className="sr-only">Reset password</span></Button>{" "}
                          <Button variant={u.active ? "danger" : "secondary"} disabled={u.id === me?.id}
                                  onClick={() => run(() => patch(`/users/${u.id}`, { active: !u.active }), `${u.username} ${u.active ? "disabled" : "enabled"}.`)}>
                            {u.active ? "Disable" : "Enable"}
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Async>
          <dl className="mt-4 space-y-1 border-t border-slate-100 pt-3 text-xs text-slate-600">
            {(Object.keys(ROLE_HELP) as Role[]).map((role) => (
              <div key={role}><dt className="inline font-medium capitalize">{role}: </dt><dd className="inline">{ROLE_HELP[role]}</dd></div>
            ))}
          </dl>
        </Card>
        <NewUserForm minPasswordLength={minPasswordLength}
                     onCreate={(body) => run(() => post("/users", body), `Created ${body.username}.`)} />
      </div>
    </>
  );
}

function NewUserForm({ onCreate, minPasswordLength }: {
  onCreate: (body: { username: string; display_name: string; password: string; role: Role }) => Promise<void>;
  minPasswordLength: number;
}) {
  const empty = { username: "", display_name: "", password: "", role: "analyst" as Role };
  const [form, setForm] = useState(empty);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    await onCreate(form);
    setForm(empty);
  };
  return (
    <Card title="Add a user">
      <form onSubmit={submit} className="space-y-3">
        <label className="block text-sm">Full name
          <input required maxLength={60} value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} className={`${input} mt-1`} /></label>
        <label className="block text-sm">Username
          <input required minLength={3} maxLength={32} pattern="[A-Za-z0-9._\-]+" autoComplete="off" value={form.username}
                 onChange={(e) => setForm({ ...form, username: e.target.value })} className={`${input} mt-1`} /></label>
        <label className="block text-sm">Temporary password
          <input required type="password" minLength={minPasswordLength} autoComplete="new-password" value={form.password}
                 onChange={(e) => setForm({ ...form, password: e.target.value })} className={`${input} mt-1`} />
          <span className="text-xs text-slate-500">At least {minPasswordLength} characters. Ask them to change it under Account.</span></label>
        <label className="block text-sm">Role
          <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })} className={`${input} mt-1`}>
            <option value="viewer">Viewer</option><option value="analyst">Analyst</option><option value="admin">Admin</option>
          </select></label>
        <Button type="submit" variant="primary"><UserPlus className="size-4" aria-hidden /> Create user</Button>
      </form>
    </Card>
  );
}
