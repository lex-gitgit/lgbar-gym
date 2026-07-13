import { useState, useEffect, useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import ExercisePicker from "../components/ExercisePicker";

function todayLocal() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function daysAgoLabel(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const diffDays = Math.round((now.getTime() - d.getTime()) / 86400000);
  if (diffDays <= 0) return "today";
  if (diffDays === 1) return "yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function DayCreate({ showFlash }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [exercises, setExercises] = useState([]);
  const [presets, setPresets] = useState([]);
  const [presetExercises, setPresetExercises] = useState({});
  const [days, setDays] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [date, setDate] = useState(todayLocal());
  const [presetId, setPresetId] = useState(searchParams.get("preset") || "");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showCustom, setShowCustom] = useState(() => Boolean(searchParams.get("preset")));
  const [quickLoggingId, setQuickLoggingId] = useState(null);
  const [loading, setLoading] = useState(true);

  const lastUsedByPreset = useMemo(() => {
    const map = {};
    for (const d of days) {
      if (d.preset && !(d.preset in map)) map[d.preset] = d.date;
    }
    return map;
  }, [days]);

  useEffect(() => {
    Promise.all([
      api.get("/exercises/"),
      api.get("/presets/"),
      api.get("/days/"),
    ]).then(([exData, presetData, dayData]) => {
      setExercises(exData);
      setPresets(presetData);
      setDays(dayData);
      const pe = {};
      Promise.all(
        presetData.map((p) =>
          api.get(`/presets/${p.id}/`).then((d) => {
            pe[p.id] = d.exercises.map((e) => e.exercise);
          })
        )
      ).then(() => {
        setPresetExercises(pe);
        setLoading(false);
      });
    });
  }, []);

  useEffect(() => {
    if (presetId && presetExercises[presetId]) {
      setSelected(new Set(presetExercises[presetId]));
    } else if (!presetId) {
      setSelected(new Set());
    }
  }, [presetId, presetExercises]);

  const toggle = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const quickLog = async (preset) => {
    if (quickLoggingId) return;
    setQuickLoggingId(preset.id);
    try {
      const data = await api.post(`/presets/${preset.id}/quick-log/`, {
        date: todayLocal(),
      });
      showFlash(`"${preset.name}" logged — review your sets!`);
      navigate(`/day/${data.id}`);
    } catch (err) {
      showFlash(err.message, "error");
      setQuickLoggingId(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (selected.size === 0) {
      showFlash("Please select at least one exercise.", "error");
      return;
    }
    setSubmitting(true);
    try {
      const data = await api.post("/days/", {
        date,
        preset: presetId || null,
        notes,
        exercises: Array.from(selected).join(","),
      });
      showFlash("Workout logged!");
      navigate(`/day/${data.id}`);
    } catch (err) {
      showFlash(err.message, "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <>
        <div className="page-header">
          <h1>Log Workout</h1>
        </div>
        <div className="skeleton skeleton-text" style={{ height: 32, width: 180, marginBottom: 24 }} />
        <div className="skeleton skeleton-card" />
      </>
    );
  }

  return (
    <>
      <div className="page-header">
        <h1>Log Workout</h1>
        <div className="flex gap-sm">
          <Link to="/presets/new" className="btn btn-secondary btn-sm">+ New Preset</Link>
        </div>
      </div>

      {presets.length > 0 && (
        <>
          <div className="card">
            <h2>Quick Start</h2>
            <div className="preset-quick-grid">
              {presets.map((p) => {
                const count = (presetExercises[p.id] || []).length;
                const lastDate = lastUsedByPreset[p.id];
                const busy = quickLoggingId === p.id;
                return (
                  <button
                    type="button"
                    key={p.id}
                    className={`preset-quick-btn ${busy ? "preset-quick-btn--busy" : ""}`}
                    onClick={() => quickLog(p)}
                    disabled={Boolean(quickLoggingId)}
                  >
                    {busy ? (
                      <span className="spinner" />
                    ) : (
                      <>
                        <span className="preset-quick-name">{p.name}</span>
                        <span className="preset-quick-meta">
                          {count} exercise{count !== 1 ? "s" : ""}
                          {lastDate ? ` · last ${daysAgoLabel(lastDate)}` : ""}
                        </span>
                      </>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          <button
            type="button"
            className="btn btn-secondary w-full mb-md"
            onClick={() => setShowCustom((s) => !s)}
          >
            {showCustom ? "Hide Custom Workout" : "+ Custom Workout"}
          </button>
        </>
      )}

      {(showCustom || presets.length === 0) && (
        <form onSubmit={handleSubmit}>
          <div className="card">
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="date">Date</label>
                <input type="date" id="date" value={date} onChange={(e) => setDate(e.target.value)} required />
              </div>
              <div className="form-group">
                <label htmlFor="preset">Preset (optional)</label>
                <select id="preset" value={presetId} onChange={(e) => setPresetId(e.target.value)}>
                  <option value="">— Custom Day —</option>
                  {presets.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label htmlFor="notes">Notes</label>
              <textarea id="notes" rows="2" placeholder="Optional notes…" value={notes}
                onChange={(e) => setNotes(e.target.value)} />
            </div>
          </div>

          <div className="card">
            <h2>Choose Exercises</h2>
            <ExercisePicker exercises={exercises} selected={selected} onToggle={toggle} />
          </div>

          <button type="submit" className="btn btn-primary w-full" style={{ padding: "14px", marginBottom: 16 }} disabled={submitting}>
            {submitting ? <><span className="spinner spinner--white" /> Saving…</> : "Start Logging"}
          </button>
        </form>
      )}
    </>
  );
}
