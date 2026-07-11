import { useState } from "react";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await onLogin(username, password);
    } catch {
      setError("Invalid username or password.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="hero">
      <div className="card">
        <h1>BIG MACS</h1>
        <p className="subtitle">Log your workouts. Track your progress.</p>

        {error && (
          <div role="alert" style={{ color: "var(--danger)", fontSize: "0.85rem", marginBottom: "12px", padding: "8px 12px", background: "rgba(239,68,68,0.08)", borderRadius: "var(--radius-sm)" }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input type="text" id="username" placeholder="Enter username…" required autoFocus
              value={username} onChange={(e) => setUsername(e.target.value)} spellCheck={false} autoComplete="username" />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input type="password" id="password" placeholder="Enter password…" required
              value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
          </div>
          <button type="submit" className="btn btn-primary w-full" disabled={submitting}>
            {submitting ? <><span className="spinner spinner--white" /> Signing in…</> : "Sign In"}
          </button>
        </form>

        <p className="text-muted text-center mt-md">Demo: user / 1234</p>
      </div>
    </div>
  );
}
