import {useEffect, useState} from "react";

import {listUsers, type SessionUser} from "../api";
import {errorMessage} from "../lib/errors";

export function AccountsPage() {
  const [users, setUsers] = useState<SessionUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { listUsers().then((result) => setUsers(result.items)).catch((loadError) => setError(errorMessage(loadError))); }, []);
  return <div className="page-stack"><section className="page-header"><div><p className="eyebrow">Administration</p><h1>Accounts</h1><p>Manage WGS Control Tower access.</p></div></section><section className="panel">{error ? <div className="inline-error" role="alert">{error}</div> : null}<div className="table-wrap"><table className="data-table"><thead><tr><th>Username</th><th>Display name</th><th>Role</th></tr></thead><tbody>{users.map((user) => <tr key={user.username}><td>{user.username}</td><td>{user.display_name || "-"}</td><td>{user.role}</td></tr>)}{users.length === 0 ? <tr><td className="empty-cell" colSpan={3}>No accounts returned.</td></tr> : null}</tbody></table></div></section></div>;
}
