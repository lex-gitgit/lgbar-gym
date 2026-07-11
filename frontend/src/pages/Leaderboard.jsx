import { useState, useEffect, useMemo } from "react";
import { api } from "../api";

function formatDate(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function Row({ rank, username, value, isYou }) {
  return (
    <div
      className="analytics-pr-row"
      style={isYou ? { background: "var(--bg-card-hover)" } : undefined}
    >
      <span className="analytics-pr-rank">#{rank}</span>
      <span className="analytics-pr-exercise">
        {username}
        {isYou && <span className="text-muted"> (you)</span>}
      </span>
      <span className="analytics-pr-value">{value}</span>
    </div>
  );
}

function ExerciseBoard({ user }) {
  const [exerciseList, setExerciseList] = useState([]);
  const [exerciseId, setExerciseId] = useState("");
  const [board, setBoard] = useState(null);
  const [boardLoading, setBoardLoading] = useState(false);

  useEffect(() => {
    api.get("/exercises/").then(setExerciseList).catch(() => {});
  }, []);

  useEffect(() => {
    if (!exerciseId) {
      setBoard(null);
      return;
    }
    setBoardLoading(true);
    api.get(`/leaderboard/exercise/${exerciseId}/`)
      .then(setBoard)
      .catch(() => setBoard(null))
      .finally(() => setBoardLoading(false));
  }, [exerciseId]);

  return (
    <div className="card">
      <div className="card-header">
        <h2>By Exercise</h2>
        <span className="text-muted">best estimated 1RM</span>
      </div>

      <div className="form-group">
        <select value={exerciseId} onChange={(e) => setExerciseId(e.target.value)}>
          <option value="">Choose an exercise…</option>
          {exerciseList.map((ex) => (
            <option key={ex.id} value={ex.id}>{ex.name}</option>
          ))}
        </select>
      </div>

      {!exerciseId ? (
        <div className="empty-state">
          <p>Pick an exercise above to see who's strongest.</p>
        </div>
      ) : boardLoading ? (
        <div className="skeleton skeleton-card" />
      ) : !board || board.entries.length === 0 ? (
        <div className="empty-state">
          <p>No one has logged {board?.exercise?.name || "this exercise"} yet.</p>
        </div>
      ) : (
        <div className="analytics-pr-list">
          {board.entries.map((row, i) => (
            <Row
              key={row.username}
              rank={i + 1}
              username={row.username}
              isYou={row.username === user}
              value={`~${row.e1rm} kg · ${row.weight_kg} kg × ${row.reps}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function Leaderboard({ user }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("consistency");

  useEffect(() => {
    api.get("/leaderboard/").then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const byVolume = useMemo(() => {
    if (!data) return [];
    return [...data.entries].sort((a, b) => b.week_volume_kg - a.week_volume_kg);
  }, [data]);

  const byStreak = useMemo(() => {
    if (!data) return [];
    return [...data.entries].sort((a, b) => b.streak_weeks - a.streak_weeks);
  }, [data]);

  const prBoards = useMemo(() => {
    if (!data) return [];
    return data.big_lifts.map((lift) => ({
      lift,
      rows: data.entries
        .filter((e) => e.prs[lift])
        .map((e) => ({ username: e.username, ...e.prs[lift] }))
        .sort((a, b) => b.e1rm - a.e1rm),
    }));
  }, [data]);

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

      <div className="tabs">
        <button className={`tab ${tab === "consistency" ? "tab--active" : ""}`} onClick={() => setTab("consistency")}>Consistency</button>
        <button className={`tab ${tab === "volume" ? "tab--active" : ""}`} onClick={() => setTab("volume")}>Volume</button>
        <button className={`tab ${tab === "prs" ? "tab--active" : ""}`} onClick={() => setTab("prs")}>Big Lifts</button>
        <button className={`tab ${tab === "streaks" ? "tab--active" : ""}`} onClick={() => setTab("streaks")}>Streaks</button>
        <button className={`tab ${tab === "exercise" ? "tab--active" : ""}`} onClick={() => setTab("exercise")}>By Exercise</button>
      </div>

      {tab === "consistency" && (
        <div className="card">
          <div className="card-header">
            <h2>Consistency</h2>
            <span className="text-muted">Week of {formatDate(data.week_start)}</span>
          </div>
          <div className="analytics-pr-list">
            {data.entries.map((entry, i) => (
              <Row
                key={entry.username}
                rank={i + 1}
                username={entry.username}
                isYou={entry.username === user}
                value={`${entry.week_count} this week · ${entry.month_count} this month`}
              />
            ))}
          </div>
        </div>
      )}

      {tab === "volume" && (
        <div className="card">
          <div className="card-header">
            <h2>Volume</h2>
            <span className="text-muted">kg lifted this week</span>
          </div>
          <div className="analytics-pr-list">
            {byVolume.map((entry, i) => (
              <Row
                key={entry.username}
                rank={i + 1}
                username={entry.username}
                isYou={entry.username === user}
                value={`${entry.week_volume_kg.toLocaleString()} kg`}
              />
            ))}
          </div>
        </div>
      )}

      {tab === "prs" && (
        <div className="card">
          <div className="card-header">
            <h2>Big Lifts</h2>
            <span className="text-muted">best estimated 1RM</span>
          </div>
          {prBoards.every((b) => b.rows.length === 0) ? (
            <div className="empty-state">
              <p>No one has logged a big lift yet.</p>
            </div>
          ) : (
            prBoards.map(({ lift, rows }) =>
              rows.length > 0 ? (
                <div key={lift} style={{ marginBottom: 20 }}>
                  <h3 style={{ fontSize: "0.9rem", marginBottom: 8 }}>{lift}</h3>
                  <div className="analytics-pr-list">
                    {rows.map((row, i) => (
                      <Row
                        key={row.username}
                        rank={i + 1}
                        username={row.username}
                        isYou={row.username === user}
                        value={`~${row.e1rm} kg · ${row.weight_kg} kg × ${row.reps}`}
                      />
                    ))}
                  </div>
                </div>
              ) : null
            )
          )}
        </div>
      )}

      {tab === "streaks" && (
        <div className="card">
          <div className="card-header">
            <h2>Streaks</h2>
            <span className="text-muted">consecutive weeks trained</span>
          </div>
          <div className="analytics-pr-list">
            {byStreak.map((entry, i) => (
              <Row
                key={entry.username}
                rank={i + 1}
                username={entry.username}
                isYou={entry.username === user}
                value={`${entry.streak_weeks} week${entry.streak_weeks !== 1 ? "s" : ""}`}
              />
            ))}
          </div>
        </div>
      )}

      {tab === "exercise" && <ExerciseBoard user={user} />}
    </>
  );
}
