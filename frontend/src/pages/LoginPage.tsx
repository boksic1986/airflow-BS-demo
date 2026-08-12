import {useState, type FormEvent} from "react";

import {useSession} from "../features/auth/SessionContext";
import {errorMessage} from "../lib/errors";

export function LoginPage() {
  const session = useSession();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await session.login(username, password);
    } catch (loginError) {
      setError(errorMessage(loginError));
    } finally {
      setSubmitting(false);
    }
  }

  return <main className="login-page"><section className="panel login-panel"><p className="eyebrow">WGS production</p><h1>Sign in</h1><p>Use an approved account to access the WGS control plane.</p><form onSubmit={submit} className="form-grid"><label className="field"><span>Username</span><input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} /></label><label className="field"><span>Password</span><input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>{error ? <div className="inline-error" role="alert">{error}</div> : null}<button className="button primary" disabled={submitting || !username || !password} type="submit">{submitting ? "Signing in..." : "Sign in"}</button></form></section></main>;
}
