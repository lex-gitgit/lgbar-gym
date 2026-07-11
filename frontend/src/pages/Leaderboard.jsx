import { useState, useEffect } from "react";
import { api } from "../api";

function formatDate(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function Leaderboard({ user }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/leaderboard/").then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <>
        <div className="skeleton skeleton-text" style={{ height: 32, width: 180, marginBottom: 24 }} />
        <div className="skeleton skeleton-card" />
      </>
    );
  }

  if (!data || data.entries.length === 0) {
    return (
      <>
        <div className="page-header">
          <h1>Leaderboard</h1>
        </div>
        <div className="empty-state">
          <p>No one has logged a workout yet.</p>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="page-header">
        <h1>Leaderboard</h1>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Consistency</h2>
          <span className="text-muted">Week of {formatDate(data.week_start)}</span>
        </div>

        <div className="analytics-pr-list">
          {data.entries.map((entry, i) => (
            <div
              key={entry.username}
              className="analytics-pr-row"
              style={entry.username === user ? { background: "var(--bg-card-hover)" } : undefined}
            >
              <span className="analytics-pr-rank">#{i + 1}</span>
              <span className="analytics-pr-exercise">
                {entry.username}
                {entry.username === user && <span className="text-muted"> (you)</span>}
              </span>
              <span className="analytics-pr-value">
                {entry.week_count} this week &middot; {entry.month_count} this month
              </span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
